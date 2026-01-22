"""
Download endpoints for trigpoint data exports.

Supports multiple formats (CSV, GeoJSON, KML, GPX) with optional filtering
and user-personalised data inclusion.
"""

from datetime import datetime
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from api.api.deps import get_current_user, get_db
from api.api.lifecycle import lifecycle, openapi_lifecycle
from api.core.logging import get_logger
from api.crud import tphoto as tphoto_crud
from api.crud import trig as trig_crud
from api.models.server import Server
from api.models.trig import Trig
from api.models.user import TLog, User
from api.services.download_limits import get_download_rate_limiter
from api.services.export_formats import (
    trigs_to_csv,
    trigs_to_geojson,
    trigs_to_gpx,
    trigs_to_kml,
    trigs_to_kmz,
)

router = APIRouter()
logger = get_logger(__name__)


def _get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request, considering proxy headers.

    Cloudflare and ALB set X-Forwarded-For headers.
    """
    # Check X-Forwarded-For header (set by Cloudflare/ALB)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # First IP in the list is the original client
        return forwarded_for.split(",")[0].strip()

    # Check CF-Connecting-IP (Cloudflare specific)
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip

    # Fallback to direct connection IP
    return request.client.host if request.client else "127.0.0.1"


# Maximum trigs for immediate download (configurable threshold)
MAX_IMMEDIATE_TRIGS = 50000


def _get_user_logs_map(db: Session, user_id: int) -> dict[int, dict]:
    """
    Get a mapping of trig_id to user's log data for quick lookup.

    Returns dict of trig_id -> {date, condition, comment}
    """
    from api.models.user import TLog

    logs = db.query(TLog).filter(TLog.user_id == user_id).all()

    result: dict[int, dict[str, str]] = {}
    for log in logs:
        # If user has multiple logs for same trig, keep the most recent
        trig_id = int(log.trig_id) if log.trig_id else 0
        if trig_id not in result or (
            log.date and str(log.date) > str(result[trig_id].get("date", ""))
        ):
            result[trig_id] = {
                "date": str(log.date) if log.date else "",
                "condition": str(log.condition) if log.condition else "",
                "comment": str(log.comment) if log.comment else "",
            }

    return result


@router.get(
    "/trigs",
    openapi_extra=openapi_lifecycle(
        "beta", note="Download trigpoints in various formats"
    ),
)
def download_trigs(
    request: Request,
    format: Literal["csv", "geojson", "kml", "gpx", "kmz"] = Query(
        "csv", description="Output format (csv, geojson, kml, kmz, gpx)"
    ),
    # Filters (reusing existing list_trigs patterns)
    categories: Optional[str] = Query(
        None,
        description="Comma-separated category codes to filter by (e.g., 'PILLAR,FBM')",
    ),
    area_id: Optional[int] = Query(
        None, description="Filter to trigpoints within the specified area"
    ),
    lat: Optional[float] = Query(
        None, description="Centre latitude for distance filter"
    ),
    lon: Optional[float] = Query(
        None, description="Centre longitude for distance filter"
    ),
    max_km: Optional[float] = Query(
        None, ge=0, description="Maximum distance from centre (km)"
    ),
    county: Optional[str] = Query(None, description="Filter by county (exact match)"),
    name: Optional[str] = Query(None, description="Filter by trig name (contains)"),
    # User-specific options (require authentication)
    include_my_logs: bool = Query(
        False, description="Include user's log data in export (requires authentication)"
    ),
    only_found: bool = Query(
        False,
        description="Include only trigpoints logged by user (requires authentication)",
    ),
    exclude_found: bool = Query(
        False,
        description="Exclude trigpoints already logged by user (requires authentication)",
    ),
    _lc=lifecycle("beta"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Download trigpoints in the specified format (requires authentication).

    Supports filtering by status, area, location/distance, county, and name.
    You can also include your personal log data and filter by logged/not-logged status.

    **Formats:**
    - `csv`: Comma-separated values (spreadsheet compatible)
    - `geojson`: GeoJSON FeatureCollection
    - `kml`: Keyhole Markup Language (Google Earth)
    - `gpx`: GPS Exchange Format (GPS devices)
    - `kmz`: Zipped KML with embedded icons (Google Earth / My Maps)

    **Rate limits:** This endpoint is rate-limited to prevent abuse.
    """
    # Get client IP for rate limiting
    client_ip = _get_client_ip(request)
    user_id = int(current_user.id)

    # Check rate limits
    limiter = get_download_rate_limiter()
    allowed, error_message = limiter.check_limit(
        format, user_id=user_id, client_ip=client_ip
    )
    if not allowed:
        logger.warning(
            f"Download request blocked: {error_message} "
            f"(format={format}, user={user_id}, ip={client_ip})"
        )
        raise HTTPException(status_code=429, detail=error_message)

    # Parse categories from comma-separated string
    parsed_categories: Optional[list[str]] = None
    if categories:
        parsed_categories = [
            c.strip().upper() for c in categories.split(",") if c.strip()
        ]

    # Mutually exclusive filters
    if only_found and exclude_found:
        raise HTTPException(
            status_code=400,
            detail="Cannot use both only_found and exclude_found simultaneously",
        )

    # Fetch trigpoints with filters
    trigs = trig_crud.list_trigs_filtered(
        db,
        name=name,
        county=county,
        skip=0,
        limit=MAX_IMMEDIATE_TRIGS,
        center_lat=lat,
        center_lon=lon,
        max_km=max_km,
        category_codes=parsed_categories,
        exclude_found_by_user_id=user_id if exclude_found else None,
        only_found_by_user_id=user_id if only_found else None,
        exclude_soft_deleted=True,
        area_id=area_id,
    )

    # Get count for logging
    count = len(trigs)
    logger.info(
        f"Download request: format={format}, count={count}, user={user_id or 'anonymous'}"
    )

    # Get user logs if requested
    user_logs: Optional[dict[int, dict]] = None
    if include_my_logs and user_id:
        user_logs = _get_user_logs_map(db, user_id)

    # Generate output in requested format
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    content: str | bytes

    if format == "csv":
        content = trigs_to_csv(trigs, user_logs)
        filename = f"trigpoints_{timestamp}.csv"
        media_type = "text/csv"

    elif format == "geojson":
        import json

        content = json.dumps(trigs_to_geojson(trigs, user_logs), indent=2)
        filename = f"trigpoints_{timestamp}.geojson"
        media_type = "application/geo+json"

    elif format == "kml":
        content = trigs_to_kml(trigs, user_logs)
        filename = f"trigpoints_{timestamp}.kml"
        media_type = "application/vnd.google-earth.kml+xml"

    elif format == "gpx":
        content = trigs_to_gpx(trigs, user_logs)
        filename = f"trigpoints_{timestamp}.gpx"
        media_type = "application/gpx+xml"

    elif format == "kmz":
        content = trigs_to_kmz(trigs, user_logs, db=db)
        filename = f"trigpoints_{timestamp}.kmz"
        media_type = "application/vnd.google-earth.kmz"

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")

    # Record the download for rate limiting
    limiter.record_download(format, user_id=user_id, client_ip=client_ip)

    # Return as downloadable file
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Trigpoint-Count": str(count),
        },
    )


@router.get(
    "/trigs/count",
    openapi_extra=openapi_lifecycle("beta", note="Preview count before download"),
)
def download_trigs_count(
    categories: Optional[str] = Query(
        None,
        description="Comma-separated category codes to filter by (e.g., 'PILLAR,FBM')",
    ),
    area_id: Optional[int] = Query(
        None, description="Filter to trigpoints within the specified area"
    ),
    lat: Optional[float] = Query(
        None, description="Centre latitude for distance filter"
    ),
    lon: Optional[float] = Query(
        None, description="Centre longitude for distance filter"
    ),
    max_km: Optional[float] = Query(
        None, ge=0, description="Maximum distance from centre (km)"
    ),
    county: Optional[str] = Query(None, description="Filter by county (exact match)"),
    name: Optional[str] = Query(None, description="Filter by trig name (contains)"),
    only_found: bool = Query(
        False, description="Include only trigpoints logged by user"
    ),
    exclude_found: bool = Query(
        False, description="Exclude trigpoints already logged by user"
    ),
    _lc=lifecycle("beta"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a count of trigpoints that would be included in a download (requires authentication).

    Use this endpoint to preview the size of a download before requesting it.
    """
    # Parse categories from comma-separated string
    parsed_categories: Optional[list[str]] = None
    if categories:
        parsed_categories = [
            c.strip().upper() for c in categories.split(",") if c.strip()
        ]

    user_id = int(current_user.id)

    if only_found and exclude_found:
        raise HTTPException(
            status_code=400,
            detail="Cannot use both only_found and exclude_found simultaneously",
        )

    count = trig_crud.count_trigs_filtered(
        db,
        name=name,
        county=county,
        center_lat=lat,
        center_lon=lon,
        max_km=max_km,
        category_codes=parsed_categories,
        exclude_found_by_user_id=user_id if exclude_found else None,
        only_found_by_user_id=user_id if only_found else None,
        exclude_soft_deleted=True,
        area_id=area_id,
    )

    return {
        "count": count,
        "max_immediate": MAX_IMMEDIATE_TRIGS,
        "requires_queue": count > MAX_IMMEDIATE_TRIGS,
    }


def _logs_to_csv(db: Session, logs: list[TLog], include_photos: bool = False) -> str:
    """Convert user's logs to CSV format."""
    import csv
    import io

    output = io.StringIO()

    fieldnames = [
        "log_id",
        "trig_id",
        "trig_waypoint",
        "trig_name",
        "date",
        "time",
        "condition",
        "comment",
        "score",
        "osgb_gridref",
        "fb_number",
    ]

    if include_photos:
        fieldnames.extend(["photo_count", "photo_urls"])

    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for log in logs:
        # Get trig info
        trig = db.query(Trig).filter(Trig.id == log.trig_id).first()

        row: dict[str, Any] = {
            "log_id": log.id,
            "trig_id": log.trig_id,
            "trig_waypoint": trig.waypoint if trig else "",
            "trig_name": trig.name if trig else "",
            "date": str(log.date) if log.date else "",
            "time": str(log.time) if log.time else "",
            "condition": log.condition or "",
            "comment": log.comment or "",
            "score": log.score or "",
            "osgb_gridref": log.osgb_gridref or "",
            "fb_number": log.fb_number or "",
        }

        if include_photos:
            photos = tphoto_crud.list_all_photos_for_log(db, log_id=int(log.id))
            row["photo_count"] = len(photos)
            if photos:
                urls = []
                for p in photos:
                    server = db.query(Server).filter(Server.id == p.server_id).first()
                    base_url = str(server.url) if server and server.url else ""
                    urls.append(f"{base_url}{p.filename}")
                row["photo_urls"] = "; ".join(urls)
            else:
                row["photo_urls"] = ""

        writer.writerow(row)

    return output.getvalue()


def _logs_to_json(
    db: Session, logs: list[TLog], include_photos: bool = False
) -> list[dict[str, Any]]:
    """Convert user's logs to JSON format."""
    result: list[dict[str, Any]] = []

    for log in logs:
        # Get trig info
        trig = db.query(Trig).filter(Trig.id == log.trig_id).first()

        log_data: dict[str, Any] = {
            "log_id": log.id,
            "trig_id": log.trig_id,
            "trig_waypoint": trig.waypoint if trig else None,
            "trig_name": trig.name if trig else None,
            "trig_gridref": trig.osgb_gridref if trig else None,
            "date": str(log.date) if log.date else None,
            "time": str(log.time) if log.time else None,
            "condition": log.condition,
            "comment": log.comment,
            "score": log.score,
            "osgb_gridref": log.osgb_gridref,
            "fb_number": log.fb_number,
        }

        if include_photos:
            photos = tphoto_crud.list_all_photos_for_log(db, log_id=int(log.id))
            log_data["photos"] = []
            for p in photos:
                server = db.query(Server).filter(Server.id == p.server_id).first()
                base_url = str(server.url) if server and server.url else ""
                log_data["photos"].append(
                    {
                        "photo_id": p.id,
                        "name": p.name,
                        "text_desc": p.text_desc,
                        "type": p.type,
                        "photo_url": f"{base_url}{p.filename}",
                        "icon_url": f"{base_url}{p.icon_filename}",
                        "width": p.width,
                        "height": p.height,
                    }
                )

        result.append(log_data)

    return result


@router.get(
    "/my-data",
    openapi_extra=openapi_lifecycle(
        "beta", note="Download your personal data (logs and photos)"
    ),
)
def download_my_data(
    request: Request,
    format: Literal["csv", "json"] = Query("csv", description="Output format"),
    include: str = Query(
        "logs",
        description="Comma-separated list of data to include: logs, photos_metadata",
    ),
    _lc=lifecycle("beta"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Download your personal data from TrigpointingUK.

    This endpoint allows you to download all your logs and photo metadata.
    Useful for backup or data portability.

    **Include options:**
    - `logs`: Your log entries (default)
    - `photos_metadata`: Include photo URLs and metadata with logs

    **Formats:**
    - `csv`: Comma-separated values (spreadsheet compatible)
    - `json`: JSON format (for programmatic use)

    **Rate limits:** This endpoint is rate-limited to prevent abuse.
    """
    # Get client IP for rate limiting
    client_ip = _get_client_ip(request)
    user_id = int(current_user.id)

    # Check rate limits
    limiter = get_download_rate_limiter()
    allowed, error_message = limiter.check_limit(
        "my_logs", user_id=user_id, client_ip=client_ip
    )
    if not allowed:
        logger.warning(
            f"My-data download blocked: {error_message} (user={user_id}, ip={client_ip})"
        )
        raise HTTPException(status_code=429, detail=error_message)

    # Parse include options
    include_set = {i.strip().lower() for i in include.split(",") if i.strip()}
    valid_includes = {"logs", "photos_metadata"}
    invalid_includes = include_set - valid_includes
    if invalid_includes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid include option(s): {', '.join(invalid_includes)}. "
            f"Valid options: {', '.join(valid_includes)}",
        )

    # Default to logs if nothing specified
    if not include_set:
        include_set = {"logs"}

    include_photos = "photos_metadata" in include_set

    # Fetch all user's logs (no pagination for full export)
    logs = (
        db.query(TLog)
        .filter(TLog.user_id == user_id)
        .order_by(TLog.date.desc(), TLog.time.desc())
        .all()
    )

    count = len(logs)
    logger.info(f"My-data download: user={user_id}, log_count={count}, format={format}")

    # Generate output
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    username = current_user.name or f"user_{user_id}"

    if format == "csv":
        content = _logs_to_csv(db, logs, include_photos)
        filename = f"trigpointinguk_{username}_{timestamp}.csv"
        media_type = "text/csv"

    elif format == "json":
        import json as json_lib

        data = {
            "user": {
                "id": user_id,
                "username": current_user.name,
            },
            "export_date": datetime.utcnow().isoformat(),
            "log_count": count,
            "logs": _logs_to_json(db, logs, include_photos),
        }
        content = json_lib.dumps(data, indent=2)
        filename = f"trigpointinguk_{username}_{timestamp}.json"
        media_type = "application/json"

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")

    # Record the download for rate limiting
    limiter.record_download("my_logs", user_id=user_id, client_ip=client_ip)

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Log-Count": str(count),
        },
    )

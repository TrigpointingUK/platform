"""
Trig endpoints for trigpoint data.
"""

import io
import json
import os
from datetime import date as date_type
from datetime import datetime
from math import cos, radians, sqrt
from typing import Optional

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from PIL import Image, ImageDraw
from sqlalchemy.orm import Session

from api.api.deps import get_current_user_optional, get_db
from api.api.lifecycle import lifecycle, openapi_lifecycle
from api.crud import attr as attr_crud
from api.crud import status as status_crud
from api.crud import tlog as tlog_crud
from api.crud import tphoto as tphoto_crud
from api.crud import trig as trig_crud
from api.crud import trigstats as trigstats_crud
from api.models.server import Server
from api.models.trig import Trig
from api.models.user import TLog, User
from api.schemas.tphoto import TPhotoResponse
from api.schemas.trig import (
    TrigAttrsData,
    TrigDetails,
    TrigMinimal,
)
from api.schemas.trig import TrigStats as TrigStatsSchema
from api.schemas.trig import (
    TrigWithIncludes,
)
from api.utils.cache_decorator import cached
from api.utils.geocalibrate import CalibrationResult
from api.utils.url import join_url

router = APIRouter()


@router.get(
    "/export",
    openapi_extra=openapi_lifecycle("beta", note="Bulk export for offline apps"),
)
@cached(
    resource_type="trigs",
    ttl=31536000,  # 1 year (matching tile endpoints)
    subresource="export",
    include_query_params=False,  # Ignore query params for caching
)
def export_trigs(
    _lc=lifecycle("beta"),
    db: Session = Depends(get_db),
):
    """
    Export all trigpoints for offline use (Android app).

    Returns all ~30,000 trigpoints with minimal fields.
    This endpoint is heavily cached and not automatically invalidated.
    Cache can be manually cleared via admin endpoints if needed.
    """
    # Get all trigs (no pagination, no filters)
    items = trig_crud.list_trigs_filtered(
        db,
        skip=0,
        limit=50000,  # Large enough for all trigs
    )

    # Serialize minimally
    items_serialized = [TrigMinimal.model_validate(i).model_dump() for i in items]

    # Attach status_name to each item
    for item, orig in zip(items_serialized, items):
        item["status_name"] = status_crud.get_status_name_by_id(db, int(orig.status_id))

    # Return with Cloudflare-friendly cache headers
    return JSONResponse(
        content={
            "items": items_serialized,
            "total": len(items_serialized),
            "generated_at": datetime.utcnow().isoformat(),
            "cache_info": "This export is cached for 1 year",
        },
        headers={
            "Cache-Control": "public, max-age=31536000",  # 1 year for Cloudflare
        },
    )


@router.get(
    "/{trig_id}",
    response_model=TrigWithIncludes,
    openapi_extra=openapi_lifecycle(
        "beta", note="Shape may change; fieldset stabilising"
    ),
)
@cached(resource_type="trig", ttl=86400, resource_id_param="trig_id")  # 24 hours
def get_trig(
    trig_id: int,
    include: Optional[str] = Query(
        None, description="Comma-separated list of includes: details,stats,attrs"
    ),
    _lc=lifecycle("beta", note="Shape may change"),
    db: Session = Depends(get_db),
):
    """
    Get a trigpoint by ID.

    Default: minimal fields. Supports include=details,stats,attrs.
    """
    trig = trig_crud.get_trig_by_id(db, trig_id=trig_id)
    if trig is None:
        raise HTTPException(status_code=404, detail="Trigpoint not found")

    # Build minimal response with status_name
    minimal_data = TrigMinimal.model_validate(trig).model_dump()
    status_name = status_crud.get_status_name_by_id(db, int(trig.status_id))
    minimal_data["status_name"] = status_name

    # Attach includes
    details_obj: Optional[TrigDetails] = None
    stats_obj: Optional[TrigStatsSchema] = None
    attrs_obj: Optional[list[TrigAttrsData]] = None
    if include:
        tokens = {t.strip() for t in include.split(",") if t.strip()}

        # Validate include tokens
        valid_includes = {"details", "stats", "attrs"}
        invalid_tokens = tokens - valid_includes
        if invalid_tokens:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid include parameter(s): {', '.join(sorted(invalid_tokens))}. Valid options: {', '.join(sorted(valid_includes))}",
            )
        if "details" in tokens:
            details_obj = TrigDetails.model_validate(trig)
        if "stats" in tokens:
            stats = trigstats_crud.get_trigstats_by_id(db, trig_id=trig_id)
            if stats:
                stats_obj = TrigStatsSchema.model_validate(stats)
        if "attrs" in tokens:
            attrs_data = attr_crud.get_attrs_for_trig(db, trig_id=trig_id)
            if attrs_data:
                attrs_obj = [TrigAttrsData(**item) for item in attrs_data]

    return TrigWithIncludes(
        **minimal_data, details=details_obj, stats=stats_obj, attrs=attrs_obj
    )


@router.get(
    "/waypoint/{waypoint}",
    response_model=TrigWithIncludes,
    openapi_extra=openapi_lifecycle("beta", note="Returns minimal shape only"),
)
def get_trig_by_waypoint(
    waypoint: str, _lc=lifecycle("beta"), db: Session = Depends(get_db)
):
    """
    Get a trigpoint by waypoint code (e.g., "TP0001").

    Returns minimal data by waypoint.
    """
    trig = trig_crud.get_trig_by_waypoint(db, waypoint=waypoint)
    if trig is None:
        raise HTTPException(status_code=404, detail="Trigpoint not found")

    minimal_data = TrigMinimal.model_validate(trig).model_dump()
    status_name = status_crud.get_status_name_by_id(db, int(trig.status_id))
    minimal_data["status_name"] = status_name
    return TrigWithIncludes(**minimal_data)


# removed deprecated name search endpoint


@router.get(
    "",
    openapi_extra=openapi_lifecycle("beta", note="Filtered collection listing"),
)
@cached(resource_type="trigs", ttl=43200, subresource="list")  # 12 hours
def list_trigs(
    name: Optional[str] = Query(None, description="Filter by trig name (contains)"),
    county: Optional[str] = Query(None, description="Filter by county (exact)"),
    lat: Optional[float] = Query(None, description="Centre latitude (WGS84)"),
    lon: Optional[float] = Query(None, description="Centre longitude (WGS84)"),
    max_km: Optional[float] = Query(
        None, ge=0, description="Max distance from centre (km)"
    ),
    order: Optional[str] = Query(None, description="id | name | distance"),
    physical_types: Optional[str] = Query(
        None, description="Comma-separated physical types to include"
    ),
    exclude_found: Optional[bool] = Query(
        False, description="Exclude trigpoints already logged by authenticated user"
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    _lc=lifecycle("beta"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    """
    Filtered collection endpoint for trigs returning envelope with items, pagination, links.

    New filters:
    - physical_types: Filter by physical type (e.g., "Pillar,Bolt,FBM")
    - exclude_found: Exclude trigpoints the user has already logged (requires authentication)
    """
    # Parse physical types
    physical_types_list = None
    if physical_types:
        physical_types_list = [
            pt.strip() for pt in physical_types.split(",") if pt.strip()
        ]

    # Get user ID for exclude_found filter
    exclude_found_by_user_id = None
    if exclude_found and current_user:
        exclude_found_by_user_id = int(current_user.id)

    items = trig_crud.list_trigs_filtered(
        db,
        name=name,
        county=county,
        skip=skip,
        limit=limit,
        center_lat=lat,
        center_lon=lon,
        max_km=max_km,
        order=order,
        physical_types=physical_types_list,
        exclude_found_by_user_id=exclude_found_by_user_id,
    )
    total = trig_crud.count_trigs_filtered(
        db,
        name=name,
        county=county,
        center_lat=lat,
        center_lon=lon,
        max_km=max_km,
        physical_types=physical_types_list,
        exclude_found_by_user_id=exclude_found_by_user_id,
    )

    # serialise
    items_serialized = [TrigMinimal.model_validate(i).model_dump() for i in items]

    # Compute distance_km for returned page only (cheap), matching SQL formula
    if lat is not None and lon is not None:
        deg_km = 111.32
        cos_lat = cos(radians(lat))
        for d in items_serialized:
            dlat_km = (float(d["wgs_lat"]) - lat) * deg_km
            dlon_km = (float(d["wgs_long"]) - lon) * deg_km * cos_lat
            d["distance_km"] = round(sqrt(dlat_km * dlat_km + dlon_km * dlon_km), 1)

    has_more = (skip + len(items)) < total
    base = "/v1/trigs"
    params = []
    if name:
        params.append(f"name={name}")
    if county:
        params.append(f"county={county}")
    if lat is not None:
        params.append(f"lat={lat}")
    if lon is not None:
        params.append(f"lon={lon}")
    if max_km is not None:
        params.append(f"max_km={max_km}")
    if order:
        params.append(f"order={order}")
    if physical_types:
        params.append(f"physical_types={physical_types}")
    if exclude_found:
        params.append("exclude_found=true")
    params.append(f"limit={limit}")
    # self link
    self_link = base + "?" + "&".join(params + [f"skip={skip}"])
    next_link = (
        base + "?" + "&".join(params + [f"skip={skip + limit}"]) if has_more else None
    )
    prev_offset = max(skip - limit, 0)
    prev_link = (
        base + "?" + "&".join(params + [f"skip={prev_offset}"]) if skip > 0 else None
    )

    # Serialize items minimally
    # items_serialized = [TrigMinimal.model_validate(i).model_dump() for i in items]
    # Attach status_name to each item
    for item, orig in zip(items_serialized, items):
        item["status_name"] = status_crud.get_status_name_by_id(db, int(orig.status_id))

    response = {
        "items": items_serialized,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": skip,
            "has_more": has_more,
        },
        "links": {"self": self_link, "next": next_link, "prev": prev_link},
    }
    if lat is not None and lon is not None:
        response["context"] = {
            "centre": {"lat": lat, "lon": lon, "srid": 4326},
            "max_km": max_km,
            "order": order or "distance",
        }
    else:
        response["context"] = {"order": order or "id"}
    return response


# -----------------------------------------------------------------------------
# Map for a single trig
# -----------------------------------------------------------------------------


@router.get(
    "/{trig_id}/map",
    responses={200: {"content": {"image/png": {}}, "description": "PNG map for trig"}},
    openapi_extra=openapi_lifecycle(
        "beta",
        note=(
            "Loads a pre-styled map PNG and draws a single dot at the trig's WGS84 position. "
            "Use scripts/make_styled_map.py to create new map styles."
        ),
    ),
)
@cached(
    resource_type="trig", ttl=14400, resource_id_param="trig_id", subresource="map"
)  # 4 hours
async def get_trig_map(
    trig_id: int,
    style: str = Query(
        "stretched53_default",
        description="Style name (base filename without extension) from res/ directory",
    ),
    dot_colour: str = Query("#0000ff", description="Hex #RRGGBB for the trig dot"),
    dot_diameter: int = Query(
        5, ge=1, le=100, description="Dot diameter in pixels (default 5)"
    ),
    db: Session = Depends(get_db),
):
    """
    Render a map PNG with a dot at the trig location.

    This endpoint loads pre-styled [.png, .json] pairs from res/ directory.
    To create new styles, use scripts/make_styled_map.py.
    """
    # Fetch trig
    trig = trig_crud.get_trig_by_id(db, trig_id=trig_id)
    if trig is None:
        raise HTTPException(status_code=404, detail="Trigpoint not found")

    # Load pre-styled assets
    res_dir = os.path.normpath(
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "..",
            "..",
            "res",
        )
    )
    map_path = os.path.join(res_dir, f"{style}.png")
    calib_path = os.path.join(res_dir, f"{style}.json")

    # Validate files exist
    if not os.path.isfile(map_path):
        raise HTTPException(
            status_code=404, detail=f"Map style '{style}' not found (missing PNG)"
        )
    if not os.path.isfile(calib_path):
        raise HTTPException(
            status_code=404, detail=f"Map style '{style}' not found (missing JSON)"
        )

    # Load image and calibration
    base = Image.open(map_path).convert("RGBA")
    with open(calib_path, "r") as f:
        d = json.load(f)
    calib = CalibrationResult(
        affine=np.array(d["affine"], dtype=float),
        inverse=np.array(d["inverse"], dtype=float),
        pixel_bbox=tuple(d.get("pixel_bbox", (0, 0, base.size[0], base.size[1]))),
        bounds_geo=tuple(d.get("bounds_geo", (-11.0, 49.0, 2.5, 61.5))),
    )

    # Draw a single opaque dot at trig location
    x, y = calib.lonlat_to_xy(float(trig.wgs_long), float(trig.wgs_lat))
    draw = ImageDraw.Draw(base)
    r = max(1, int(round(dot_diameter / 2)))

    # Parse dot colour
    s = dot_colour.strip()
    if s.startswith("#"):
        s = s[1:]
    if len(s) >= 6:
        rr = int(s[0:2], 16)
        gg = int(s[2:4], 16)
        bb = int(s[4:6], 16)
        fill = (rr, gg, bb, 255)  # hardcoded 100% alpha
    else:
        fill = (0, 0, 170, 255)  # fallback blue

    bbox = [
        int(round(x - r)),
        int(round(y - r)),
        int(round(x + r)),
        int(round(y + r)),
    ]
    draw.ellipse(bbox, fill=fill, outline=None)

    # Return PNG
    buf = io.BytesIO()
    base.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


@router.get(
    "/{trig_id}/logs",
    openapi_extra=openapi_lifecycle("beta", note="List logs for a trig"),
)
@cached(
    resource_type="trig", ttl=7200, resource_id_param="trig_id", subresource="logs"
)  # 2 hours
def list_logs_for_trig(
    trig_id: int,
    include: Optional[str] = Query(
        None, description="Comma-separated list of includes: photos"
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items = tlog_crud.list_logs_filtered(db, trig_id=trig_id, skip=skip, limit=limit)
    total = tlog_crud.count_logs_filtered(db, trig_id=trig_id)

    # Import helper from logs endpoint
    from api.api.v1.endpoints.logs import enrich_logs_with_names

    items_serialized = enrich_logs_with_names(db, items)

    # Handle includes
    if include:
        tokens = {t.strip() for t in include.split(",") if t.strip()}

        # Validate include tokens
        valid_includes = {"photos"}
        invalid_tokens = tokens - valid_includes
        if invalid_tokens:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid include parameter(s): {', '.join(sorted(invalid_tokens))}. Valid options: {', '.join(sorted(valid_includes))}",
            )
        if "photos" in tokens:
            for out, orig in zip(items_serialized, items):
                photos = tphoto_crud.list_all_photos_for_log(db, log_id=int(orig.id))
                out["photos"] = []
                for p in photos:
                    server: Server | None = (
                        db.query(Server).filter(Server.id == p.server_id).first()
                    )
                    base_url = str(server.url) if server and server.url else ""
                    # Handle empty type field by defaulting to 'O' (other)
                    photo_type = str(p.type) if p.type and p.type.strip() else "O"
                    out["photos"].append(
                        TPhotoResponse(
                            id=int(p.id),
                            log_id=int(p.tlog_id),
                            user_id=int(orig.user_id),
                            type=photo_type,
                            filesize=int(p.filesize),
                            height=int(p.height),
                            width=int(p.width),
                            icon_filesize=int(p.icon_filesize),
                            icon_height=int(p.icon_height),
                            icon_width=int(p.icon_width),
                            name=str(p.name),
                            text_desc=str(p.text_desc),
                            public_ind=str(p.public_ind),
                            photo_url=join_url(base_url, str(p.filename)),
                            icon_url=join_url(base_url, str(p.icon_filename)),
                        ).model_dump()
                    )
    has_more = (skip + len(items)) < total
    base = f"/v1/trigs/{trig_id}/logs"
    self_link = base + f"?limit={limit}&skip={skip}"
    next_link = base + f"?limit={limit}&skip={skip + limit}" if has_more else None
    prev_offset = max(skip - limit, 0)
    prev_link = base + f"?limit={limit}&skip={prev_offset}" if skip > 0 else None
    return {
        "items": items_serialized,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": skip,
            "has_more": has_more,
        },
        "links": {"self": self_link, "next": next_link, "prev": prev_link},
    }


# removed POST /{trig_id}/logs to keep mutations on their resource endpoints


@router.get(
    "/{trig_id}/photos",
    openapi_extra=openapi_lifecycle("beta", note="List photos for a trig"),
)
@cached(
    resource_type="trig", ttl=7200, resource_id_param="trig_id", subresource="photos"
)  # 2 hours
def list_photos_for_trig(
    trig_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items = tphoto_crud.list_photos_filtered(
        db, trig_id=trig_id, skip=skip, limit=limit
    )
    total = (
        db.query(tphoto_crud.TPhoto)
        .join(tlog_crud.TLog, tlog_crud.TLog.id == tphoto_crud.TPhoto.tlog_id)
        .filter(
            tlog_crud.TLog.trig_id == trig_id, tphoto_crud.TPhoto.deleted_ind != "Y"
        )
        .count()
    )
    result_items = []
    # Get trig info once (for all photos)
    trig = db.query(Trig).filter(Trig.id == trig_id).first()

    for p in items:
        # Defer URLs; provide minimal fields consistent with collection shape
        # Resolve user via TLog join
        tlog = db.query(TLog).filter(TLog.id == p.tlog_id).first()
        user = db.query(User).filter(User.id == tlog.user_id).first() if tlog else None

        server: Server | None = (
            db.query(Server).filter(Server.id == p.server_id).first()
        )
        base_url = str(server.url) if server and server.url else ""
        # Handle empty type field by defaulting to 'O' (other)
        photo_type = str(p.type) if p.type and p.type.strip() else "O"
        result_items.append(
            TPhotoResponse(
                id=int(p.id),
                log_id=int(p.tlog_id),
                user_id=int(tlog.user_id) if tlog else 0,
                type=photo_type,
                filesize=int(p.filesize),
                height=int(p.height),
                width=int(p.width),
                icon_filesize=int(p.icon_filesize),
                icon_height=int(p.icon_height),
                icon_width=int(p.icon_width),
                name=str(p.name),
                text_desc=str(p.text_desc),
                public_ind=str(p.public_ind),
                photo_url=join_url(base_url, str(p.filename)),
                icon_url=join_url(base_url, str(p.icon_filename)),
                user_name=str(user.name) if user else None,
                trig_id=trig_id,
                trig_name=str(trig.name) if trig else None,
                log_date=(
                    date_type(tlog.date.year, tlog.date.month, tlog.date.day)
                    if tlog and tlog.date
                    else None
                ),
            ).model_dump()
        )

    has_more = (skip + len(items)) < total
    base = f"/v1/trigs/{trig_id}/photos"
    self_link = base + f"?limit={limit}&skip={skip}"
    next_link = base + f"?limit={limit}&skip={skip + limit}" if has_more else None
    prev_offset = max(skip - limit, 0)
    prev_link = base + f"?limit={limit}&skip={prev_offset}" if skip > 0 else None
    return {
        "items": result_items,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": skip,
            "has_more": has_more,
        },
        "links": {"self": self_link, "next": next_link, "prev": prev_link},
    }

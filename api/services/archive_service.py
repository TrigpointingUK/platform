"""
Archive service for generating zip file exports of user data.

Produces in-memory zip files containing CSV, JSON, and README for a user's
published logs and photo metadata. Uses batch queries to avoid N+1 patterns.
"""

import csv
import io
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from api.core.logging import get_logger
from api.models.condition import Condition
from api.models.server import Server
from api.models.tphoto import TPhoto
from api.models.trig import Trig
from api.models.user import TLog, User
from api.utils.url import join_url

logger = get_logger(__name__)

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
_VIEWER_TEMPLATE: str | None = None


def _get_viewer_template() -> str:
    global _VIEWER_TEMPLATE
    if _VIEWER_TEMPLATE is None:
        _VIEWER_TEMPLATE = (_TEMPLATE_DIR / "archive_viewer.html").read_text()
    return _VIEWER_TEMPLATE


def _build_viewer_html(json_data: dict[str, Any]) -> str:
    """Embed JSON data into the self-contained HTML viewer template."""
    template = _get_viewer_template()
    username = json_data.get("user", {}).get("username", "")
    compact_json = json.dumps(json_data, separators=(",", ":"))
    html = template.replace("__ARCHIVE_DATA__", compact_json)
    html = html.replace("__USERNAME__", username)
    return html


def _build_lookups(
    db: Session, logs: list[TLog]
) -> tuple[dict[int, Trig], dict[int, list[TPhoto]], dict[int, Server], dict[str, str]]:
    """Batch-load trigs, photos, servers, and condition names for a set of logs."""
    trig_ids = {int(log.trig_id) for log in logs if log.trig_id}
    log_ids = [int(log.id) for log in logs]

    trigs_map: dict[int, Trig] = {}
    if trig_ids:
        trigs = db.query(Trig).filter(Trig.id.in_(trig_ids)).all()
        trigs_map = {int(t.id): t for t in trigs}

    photos_by_log: dict[int, list[TPhoto]] = {lid: [] for lid in log_ids}
    if log_ids:
        photos = (
            db.query(TPhoto)
            .filter(TPhoto.tlog_id.in_(log_ids), TPhoto.deleted_ind != "Y")
            .all()
        )
        server_ids = {int(p.server_id) for p in photos if p.server_id}
        for p in photos:
            photos_by_log.setdefault(int(p.tlog_id), []).append(p)
    else:
        server_ids = set()

    servers_map: dict[int, Server] = {}
    if server_ids:
        servers = db.query(Server).filter(Server.id.in_(server_ids)).all()
        servers_map = {int(s.id): s for s in servers}

    conditions = db.query(Condition).all()
    conditions_map: dict[str, str] = {
        str(c.code).strip(): str(c.name) for c in conditions
    }

    return trigs_map, photos_by_log, servers_map, conditions_map


def _logs_to_csv_batch(
    logs: list[TLog],
    trigs_map: dict[int, Trig],
    photos_by_log: dict[int, list[TPhoto]],
    servers_map: dict[int, Server],
    conditions_map: dict[str, str],
    include_photos: bool = True,
) -> str:
    """Convert logs to CSV using pre-loaded lookup maps."""
    output = io.StringIO()

    fieldnames = [
        "log_id",
        "trig_id",
        "trig_waypoint",
        "trig_name",
        "date",
        "time",
        "condition_code",
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
        trig = trigs_map.get(int(log.trig_id)) if log.trig_id else None
        code = str(log.condition or "").strip()

        row: dict[str, Any] = {
            "log_id": log.id,
            "trig_id": log.trig_id,
            "trig_waypoint": trig.waypoint if trig else "",
            "trig_name": trig.name if trig else "",
            "date": str(log.date) if log.date else "",
            "time": str(log.time) if log.time else "",
            "condition_code": code,
            "condition": conditions_map.get(code, ""),
            "comment": log.comment or "",
            "score": log.score or "",
            "osgb_gridref": log.osgb_gridref or "",
            "fb_number": log.fb_number or "",
        }

        if include_photos:
            photos = photos_by_log.get(int(log.id), [])
            row["photo_count"] = len(photos)
            if photos:
                urls = []
                for p in photos:
                    server = servers_map.get(int(p.server_id)) if p.server_id else None
                    base_url = str(server.url) if server and server.url else ""
                    urls.append(join_url(base_url, str(p.filename)))
                row["photo_urls"] = "; ".join(urls)
            else:
                row["photo_urls"] = ""

        writer.writerow(row)

    return output.getvalue()


def _logs_to_json_batch(
    logs: list[TLog],
    trigs_map: dict[int, Trig],
    photos_by_log: dict[int, list[TPhoto]],
    servers_map: dict[int, Server],
    conditions_map: dict[str, str],
    include_photos: bool = True,
) -> list[dict[str, Any]]:
    """Convert logs to JSON dicts using pre-loaded lookup maps."""
    result: list[dict[str, Any]] = []

    for log in logs:
        trig = trigs_map.get(int(log.trig_id)) if log.trig_id else None
        code = str(log.condition or "").strip()

        log_data: dict[str, Any] = {
            "log_id": log.id,
            "trig_id": log.trig_id,
            "trig_waypoint": trig.waypoint if trig else None,
            "trig_name": trig.name if trig else None,
            "trig_gridref": trig.osgb_gridref if trig else None,
            "wgs_lat": float(trig.wgs_lat) if trig and trig.wgs_lat else None,
            "wgs_lon": float(trig.wgs_long) if trig and trig.wgs_long else None,
            "date": str(log.date) if log.date else None,
            "time": str(log.time) if log.time else None,
            "condition_code": code,
            "condition": conditions_map.get(code, None),
            "comment": log.comment,
            "score": log.score,
            "osgb_gridref": log.osgb_gridref,
            "fb_number": log.fb_number,
        }

        if include_photos:
            photos = photos_by_log.get(int(log.id), [])
            log_data["photos"] = []
            for p in photos:
                server = servers_map.get(int(p.server_id)) if p.server_id else None
                base_url = str(server.url) if server and server.url else ""
                log_data["photos"].append(
                    {
                        "photo_id": p.id,
                        "caption": p.name,
                        "description": p.text_desc,
                        "type": p.type,
                        "photo_url": join_url(base_url, str(p.filename)),
                        "icon_url": join_url(base_url, str(p.icon_filename)),
                        "width": p.width,
                        "height": p.height,
                    }
                )

        result.append(log_data)

    return result


def generate_archive_zip(db: Session, user: User, archive_format: str = "R") -> bytes:
    """
    Generate an in-memory zip archive of a user's published logs.

    Args:
        db: Database session
        user: The user whose data to export
        archive_format: C=CSV only, J=CSV+JSON, R=CSV+JSON+HTML viewer

    Returns:
        bytes of the zip file
    """
    user_id = int(user.id)
    username = str(user.name or f"user_{user_id}")
    export_time = datetime.now(UTC)
    timestamp = export_time.strftime("%Y%m%d_%H%M%S")

    logs = (
        db.query(TLog)
        .filter(TLog.user_id == user_id, TLog.status == "P")
        .order_by(TLog.date.desc(), TLog.time.desc())
        .all()
    )

    trigs_map, photos_by_log, servers_map, conditions_map = _build_lookups(db, logs)

    csv_content = _logs_to_csv_batch(
        logs,
        trigs_map,
        photos_by_log,
        servers_map,
        conditions_map,
        include_photos=True,
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"trigpointinguk_{username}_{timestamp}/logs.csv", csv_content)

        if archive_format in ("J", "R"):
            json_data = {
                "user": {"id": user_id, "username": username},
                "export_date": export_time.isoformat(),
                "log_count": len(logs),
                "logs": _logs_to_json_batch(
                    logs,
                    trigs_map,
                    photos_by_log,
                    servers_map,
                    conditions_map,
                    include_photos=True,
                ),
            }

        if archive_format == "J":
            json_content = json.dumps(json_data, indent=2)
            zf.writestr(
                f"trigpointinguk_{username}_{timestamp}/logs.json", json_content
            )
        elif archive_format == "R":
            viewer_html = _build_viewer_html(json_data)
            zf.writestr(
                f"trigpointinguk_{username}_{timestamp}/index.html", viewer_html
            )

        photo_count = sum(len(v) for v in photos_by_log.values())
        trig_count = len(trigs_map)
        readme = _build_readme(
            username, export_time, len(logs), trig_count, photo_count, archive_format
        )
        zf.writestr(f"trigpointinguk_{username}_{timestamp}/README.txt", readme)

    zip_bytes = buf.getvalue()
    logger.info(
        "Archive zip generated",
        extra={
            "user_id": user_id,
            "log_count": len(logs),
            "photo_count": photo_count,
            "zip_size_bytes": len(zip_bytes),
            "format": archive_format,
        },
    )
    return zip_bytes


def _build_readme(
    username: str,
    export_time: datetime,
    log_count: int,
    trig_count: int,
    photo_count: int,
    archive_format: str,
) -> str:
    """Build the README.txt for the archive zip."""
    lines = [
        f"TrigpointingUK Data Archive for {username}",
        f"{'=' * 50}",
        "",
        f"Export date: {export_time.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"Published logs: {log_count}",
        f"Distinct trigpoints: {trig_count}",
        f"Photos referenced: {photo_count}",
        "",
        "Contents:",
        "  logs.csv  - All published logs in CSV format",
    ]

    if archive_format == "J":
        lines.append(
            "  logs.json - All published logs in JSON format with photo metadata"
        )
    elif archive_format == "R":
        lines.append("  index.html - Interactive viewer (open in any web browser)")
        lines.append(
            '              Use the "JSON" button to export the data as a JSON file'
        )

    lines.extend(
        [
            "",
            "Notes:",
            "  - Only published logs are included (drafts are excluded)",
            "  - Photo URLs point to the live TrigpointingUK photo server",
            "  - This archive was generated by TrigpointingUK (https://trigpointing.uk)",
            "",
        ]
    )

    return "\n".join(lines)

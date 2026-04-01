"""
Export format generators for trigpoint data downloads.

Supports CSV, GeoJSON, KML, and GPX formats.
"""

import csv
import io
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.orm import Session

from api.crud.area import COUNTY_1991_AREA_TYPE_ID, TRIG_AREA
from api.models.area import Area
from api.models.trig import Trig

_KMZ_ICONS_DIR = Path(__file__).resolve().parents[1] / "assets" / "kmz" / "icons"

# Icon families supported by KMZ export (matches available `mapicon_*.png` assets)
_KMZ_ICON_FAMILIES = ("pillar", "fbm", "passive", "intersected")
_KMZ_ICON_COLOURS = ("green", "yellow", "red", "grey")


def get_county_names_for_trigs(db: Session, trig_ids: list[int]) -> dict[int, str]:
    """
    Batch-fetch county names for a list of trigpoints.

    Uses the trig_area table with area_type_id = 7 (county_1991).

    Args:
        db: Database session
        trig_ids: List of trig IDs to look up

    Returns:
        Dict mapping trig_id to county name
    """
    if not trig_ids:
        return {}

    # Check if trig_area table exists before querying
    try:
        from typing import Any, cast

        from sqlalchemy import inspect

        inspector = cast(Any, inspect(db.bind))
        if "trig_area" not in inspector.get_table_names():
            return {}
    except Exception:
        return {}

    # Query the trig_area table joined with area
    results = (
        db.query(TRIG_AREA.c.trig_id, Area.name)
        .join(Area, Area.id == TRIG_AREA.c.area_id)
        .filter(
            TRIG_AREA.c.trig_id.in_(trig_ids),
            TRIG_AREA.c.area_type_id == COUNTY_1991_AREA_TYPE_ID,
        )
        .all()
    )

    return {int(row[0]): str(row[1]) for row in results}


def _get_category_info(trig: Trig) -> tuple[str, str]:
    """
    Get category code and name from a trig's type relationship.

    Returns (category_code, category_name) tuple, defaulting to ("", "") if not available.
    """
    if trig.trig_type and trig.trig_type.category:
        return (
            str(trig.trig_type.category.code or ""),
            str(trig.trig_type.category.name or ""),
        )
    return ("", "")


def _get_type_info(trig: Trig) -> tuple[str, str]:
    """
    Get type code and name from a trig's type relationship.

    Returns (type_code, type_name) tuple, defaulting to ("", "") if not available.
    """
    if trig.trig_type:
        return (
            str(trig.trig_type.code or ""),
            str(trig.trig_type.name or ""),
        )
    return ("", "")


def _get_type_name(trig: Trig) -> str:
    """
    Get the type name from a trig's type relationship.

    Returns the type name if available, otherwise an empty string.
    """
    if trig.trig_type and trig.trig_type.name:
        return str(trig.trig_type.name)
    return ""


def trigs_to_csv(
    trigs: list[Trig],
    user_logs: Optional[dict[int, dict[str, Any]]] = None,
    county_names: Optional[dict[int, str]] = None,
) -> str:
    """
    Convert trigpoints to CSV format.

    Args:
        trigs: List of Trig objects
        user_logs: Optional mapping of trig_id to user's log data
        county_names: Optional mapping of trig_id to county name (from trig_area)

    Returns:
        CSV string
    """
    output = io.StringIO()

    # Base fields always included
    fieldnames = [
        "id",
        "waypoint",
        "name",
        "condition",
        "type_code",
        "type_name",
        "category_code",
        "category_name",
        "wgs_lat",
        "wgs_long",
        "wgs_height",
        "osgb_gridref",
        "osgb_eastings",
        "osgb_northings",
        "osgb_height",
        "county",
        "town",
        "fb_number",
        "current_use",
        "historic_use",
    ]

    # Add user log fields if provided
    if user_logs is not None:
        fieldnames.extend(["logged", "log_date", "log_condition", "log_comment"])

    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for trig in trigs:
        type_code, type_name = _get_type_info(trig)
        category_code, category_name = _get_category_info(trig)
        row = {
            "id": trig.id,
            "waypoint": trig.waypoint,
            "name": trig.name,
            "condition": trig.condition,
            "type_code": type_code,
            "type_name": type_name,
            "category_code": category_code,
            "category_name": category_name,
            "wgs_lat": float(trig.wgs_lat),
            "wgs_long": float(trig.wgs_long),
            "wgs_height": (
                float(trig.wgs_height) if trig.wgs_height is not None else None
            ),
            "osgb_gridref": trig.osgb_gridref,
            "osgb_eastings": float(trig.osgb_eastings),
            "osgb_northings": float(trig.osgb_northings),
            "osgb_height": (
                float(trig.osgb_height) if trig.osgb_height is not None else None
            ),
            "county": county_names.get(int(trig.id), "") if county_names else "",
            "town": trig.town,
            "fb_number": trig.fb_number,
            "current_use": trig.current_use,
            "historic_use": trig.historic_use,
        }

        # Add user log data if available
        if user_logs is not None:
            log_data = user_logs.get(int(trig.id))
            if log_data:
                row["logged"] = "Y"
                row["log_date"] = log_data.get("date", "")
                row["log_condition"] = log_data.get("condition", "")
                row["log_comment"] = log_data.get("comment", "")
            else:
                row["logged"] = "N"
                row["log_date"] = ""
                row["log_condition"] = ""
                row["log_comment"] = ""

        writer.writerow(row)

    return output.getvalue()


def trigs_to_geojson(
    trigs: list[Trig],
    user_logs: Optional[dict[int, dict[str, Any]]] = None,
    county_names: Optional[dict[int, str]] = None,
) -> dict:
    """
    Convert trigpoints to GeoJSON FeatureCollection format.

    Args:
        trigs: List of Trig objects
        user_logs: Optional mapping of trig_id to user's log data
        county_names: Optional mapping of trig_id to county name (from trig_area)

    Returns:
        GeoJSON dict
    """
    features = []

    for trig in trigs:
        type_code, type_name = _get_type_info(trig)
        category_code, category_name = _get_category_info(trig)
        properties = {
            "id": trig.id,
            "waypoint": trig.waypoint,
            "name": trig.name,
            "condition": trig.condition,
            "type_code": type_code,
            "type_name": type_name,
            "category_code": category_code,
            "category_name": category_name,
            "osgb_gridref": trig.osgb_gridref,
            "county": county_names.get(int(trig.id), "") if county_names else "",
            "town": trig.town,
            "fb_number": trig.fb_number,
        }

        # Add user log data if available
        if user_logs is not None:
            log_data = user_logs.get(int(trig.id))
            if log_data:
                properties["logged"] = True
                properties["log_date"] = str(log_data.get("date", ""))
                properties["log_condition"] = log_data.get("condition", "")
            else:
                properties["logged"] = False

        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(trig.wgs_long), float(trig.wgs_lat)],
                },
                "properties": properties,
            }
        )

    return {
        "type": "FeatureCollection",
        "features": features,
        "generated_at": datetime.now(UTC).isoformat(),
    }


def trigs_to_gpx(
    trigs: list[Trig],
    user_logs: Optional[dict[int, dict[str, Any]]] = None,
) -> str:
    """
    Convert trigpoints to GPX format.

    Creates waypoints for each trigpoint with metadata in descriptions.

    Args:
        trigs: List of Trig objects
        user_logs: Optional mapping of trig_id to user's log data

    Returns:
        GPX XML string
    """

    # XML escape helper
    def escape_xml(text: str) -> str:
        if not text:
            return ""
        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<gpx version="1.1" creator="TrigpointingUK"',
        '     xmlns="http://www.topografix.com/GPX/1/1"',
        '     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
        '     xsi:schemaLocation="http://www.topografix.com/GPX/1/1',
        '     http://www.topografix.com/GPX/1/1/gpx.xsd">',
        "  <metadata>",
        "    <name>TrigpointingUK Export</name>",
        f"    <time>{datetime.now(UTC).isoformat()}Z</time>",
        "  </metadata>",
    ]

    for trig in trigs:
        # Build description
        type_name = _get_type_name(trig)
        desc_parts = [
            f"Type: {type_name}",
            f"Grid Ref: {trig.osgb_gridref}",
            f"Condition: {trig.condition}",
        ]
        if trig.fb_number:
            desc_parts.append(f"FB: {trig.fb_number}")

        # Add log details if logged (basic logged/not logged is in cmt field)
        if user_logs is not None:
            log_data = user_logs.get(int(trig.id))
            if log_data:
                if log_data.get("date"):
                    desc_parts.append(f"Log Date: {log_data.get('date')}")
                if log_data.get("condition"):
                    desc_parts.append(f"My Condition: {log_data.get('condition')}")

        description = " | ".join(desc_parts)

        lines.append(
            f'  <wpt lat="{float(trig.wgs_lat)}" lon="{float(trig.wgs_long)}">'
        )
        ele_value = float(trig.wgs_height) if trig.wgs_height is not None else 0
        lines.append(f"    <ele>{ele_value}</ele>")
        lines.append(
            f"    <name>{escape_xml(str(trig.waypoint))} - {escape_xml(str(trig.name))}</name>"
        )
        # Only include cmt if user_logs was provided (log info available)
        if user_logs is not None:
            log_data = user_logs.get(int(trig.id))
            cmt_text = "Logged" if log_data else "Not Logged"
            lines.append(f"    <cmt>{cmt_text}</cmt>")
        lines.append(f"    <desc>{escape_xml(description)}</desc>")
        lines.append(f'    <link href="https://trigpointing.uk/trigs/{trig.id}">')
        lines.append("      <text>View on TrigpointingUK</text>")
        lines.append("    </link>")
        lines.append("    <sym>Triangle</sym>")
        lines.append(f"    <type>{escape_xml(type_name)}</type>")
        lines.append("  </wpt>")

    lines.append("</gpx>")

    return "\n".join(lines)


def trigs_to_kml(
    trigs: list[Trig],
    user_logs: Optional[dict[int, dict[str, Any]]] = None,
    county_names: Optional[dict[int, str]] = None,
) -> str:
    """
    Convert trigpoints to KML format.

    Creates placemarks for each trigpoint with metadata in descriptions.

    Args:
        trigs: List of Trig objects
        user_logs: Optional mapping of trig_id to user's log data
        county_names: Optional mapping of trig_id to county name (from trig_area)

    Returns:
        KML XML string
    """

    # XML escape helper
    def escape_xml(text: str) -> str:
        if not text:
            return ""
        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        "  <Document>",
        "    <name>TrigpointingUK Export</name>",
        f"    <description>Generated {datetime.now(UTC).isoformat()}Z</description>",
        # Define styles for different conditions
        '    <Style id="logged">',
        "      <IconStyle>",
        "        <color>ff00ff00</color>",
        "        <Icon><href>http://maps.google.com/mapfiles/kml/shapes/triangle.png</href></Icon>",
        "      </IconStyle>",
        "    </Style>",
        '    <Style id="not-logged">',
        "      <IconStyle>",
        "        <color>ff0000ff</color>",
        "        <Icon><href>http://maps.google.com/mapfiles/kml/shapes/triangle.png</href></Icon>",
        "      </IconStyle>",
        "    </Style>",
    ]

    for trig in trigs:
        type_name = _get_type_name(trig)
        category_code, category_name = _get_category_info(trig)

        # Build description HTML
        desc_lines = [
            "<![CDATA[",
            f"<b>Type:</b> {escape_xml(type_name)}<br/>",
            f"<b>Category:</b> {escape_xml(category_name)}<br/>",
            f"<b>Grid Ref:</b> {escape_xml(str(trig.osgb_gridref))}<br/>",
            f"<b>Condition:</b> {escape_xml(str(trig.condition))}<br/>",
        ]
        county = county_names.get(int(trig.id), "") if county_names else ""
        if county:
            desc_lines.append(f"<b>County:</b> {escape_xml(county)}<br/>")
        if trig.fb_number:
            desc_lines.append(
                f"<b>FB Number:</b> {escape_xml(str(trig.fb_number))}<br/>"
            )

        # Determine style based on log status
        style_url = "#not-logged"
        if user_logs is not None:
            log_data = user_logs.get(int(trig.id))
            if log_data:
                style_url = "#logged"
                desc_lines.append(f"<b>Logged:</b> {log_data.get('date', 'Yes')}<br/>")
                if log_data.get("condition"):
                    desc_lines.append(
                        f"<b>My Condition:</b> {escape_xml(log_data.get('condition', ''))}<br/>"
                    )

        desc_lines.append("]]>")
        description = "\n".join(desc_lines)

        lines.append("    <Placemark>")
        lines.append(
            f"      <name>{escape_xml(str(trig.name))} ({trig.waypoint})</name>"
        )
        lines.append(f"      <description>{description}</description>")
        lines.append(f"      <styleUrl>{style_url}</styleUrl>")
        lines.append("      <Point>")
        ele_value = float(trig.wgs_height) if trig.wgs_height is not None else 0
        lines.append(
            f"        <coordinates>{float(trig.wgs_long)},{float(trig.wgs_lat)},{ele_value}</coordinates>"
        )
        lines.append("      </Point>")
        lines.append("    </Placemark>")

    lines.append("  </Document>")
    lines.append("</kml>")

    return "\n".join(lines)


def _build_condition_colour_maps(
    db: Optional[Session],
) -> tuple[dict[str, str], dict[str, str]]:
    """
    Build condition code to colour mappings from the database.

    Returns:
        (trig_colour_map, log_colour_map) - dicts mapping condition code to colour name
    """
    # Fallback maps if db not available
    fallback_trig = {
        "G": "green",
        "S": "green",
        "C": "yellow",
        "D": "yellow",
        "R": "yellow",
        "T": "yellow",
        "M": "yellow",
        "V": "yellow",
        "Q": "red",
        "X": "red",
        "N": "red",
        "P": "grey",
        "U": "grey",
        "Z": "grey",
    }
    fallback_log = fallback_trig.copy()

    if not db:
        return fallback_trig, fallback_log

    try:
        from api.crud.condition import get_all_conditions

        conditions = get_all_conditions(db)
        if not conditions:
            return fallback_trig, fallback_log

        trig_map: dict[str, str] = {}
        log_map: dict[str, str] = {}

        for c in conditions:
            code = str(c.code).upper()
            # Map trig_colour to our 4 colour names
            trig_colour = (c.trig_colour or "").lower()
            if trig_colour in ("green", "lime"):
                trig_map[code] = "green"
            elif trig_colour in ("yellow", "orange", "amber"):
                trig_map[code] = "yellow"
            elif trig_colour in ("red", "maroon"):
                trig_map[code] = "red"
            else:
                trig_map[code] = "grey"

            # Map log_colour to our 4 colour names
            log_colour = (c.log_colour or "").lower()
            if log_colour in ("green", "lime"):
                log_map[code] = "green"
            elif log_colour in ("yellow", "orange", "amber"):
                log_map[code] = "yellow"
            elif log_colour in ("red", "maroon"):
                log_map[code] = "red"
            else:
                log_map[code] = "grey"

        return trig_map, log_map
    except Exception:
        return fallback_trig, fallback_log


def trigs_to_kmz(
    trigs: list[Trig],
    user_logs: Optional[dict[int, dict[str, Any]]] = None,
    db: Optional[Session] = None,
    county_names: Optional[dict[int, str]] = None,
) -> bytes:
    """
    Convert trigpoints to a KMZ (zipped KML + embedded icons).

    This is intended for Google Earth / Google My Maps exploration.

    Args:
        trigs: List of Trig objects
        user_logs: Optional mapping of trig_id to user's log data
        db: Optional database session for condition lookups
        county_names: Optional mapping of trig_id to county name (from trig_area)

    Notes:
    - OS map thumbnails are NOT embedded (licence restriction); description HTML links to an API URL.
    - Icon colours follow the TrigpointingUK wiki `Condition` mapping (authoritative):
      - Condition mode (no user logs): colour derived from `trig.condition`
      - My log mode (user logs provided): grey for not logged by that user; otherwise derived from `tlog.condition`
        with special case: blank/NULL/'Z' -> green; 'P'/'U' -> red; 'N' -> red
    - Icon families are restricted to: pillar, fbm, passive, intersected.
    """
    # Build colour maps from database (or use fallbacks)
    trig_colour_map, log_colour_map = _build_condition_colour_maps(db)

    # ---- helpers ---------------------------------------------------------
    def _escape_xml(text: str) -> str:
        if text is None:
            return ""
        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

    def _safe_cdata(text: str) -> str:
        # Guard against accidental CDATA terminators
        return str(text).replace("]]>", "]]&gt;")

    def _api_base_domain() -> str:
        # Use environment to choose API domain
        from api.core.config import settings

        if settings.ENVIRONMENT == "production":
            return "https://api.trigpointing.uk"
        # staging + development default to trigpointing.me for now
        return "https://api.trigpointing.me"

    def _site_base_domain() -> str:
        # Use environment to choose site (non-API) domain
        from api.core.config import settings

        if settings.ENVIRONMENT == "production":
            return "https://trigpointing.uk"
        return "https://trigpointing.me"

    def _thumb_url(trig_id: int) -> str:
        return f"{_api_base_domain()}/v1/maps/thumb/{trig_id}"

    def _trig_url(trig_id: int) -> str:
        return f"{_site_base_domain()}/trigs/{trig_id}"

    def _icon_family_from_type_name(type_name: str, category_name: str) -> str:
        """
        Map type_name to one of the 4 KMZ icon families.

        This mapping intentionally absorbs many type names into `passive`.
        """
        pt = (type_name or "").strip().lower()
        gn = (category_name or "").strip().lower()

        # Strong group fallbacks
        if gn == "pillar":
            return "pillar"
        if gn == "intersected":
            return "intersected"

        if pt in {"pillar"}:
            return "pillar"

        # Major marks (FBM + related)
        if pt in {"fbm", "flush bracket", "curry stool", "curry stool bracket"}:
            return "fbm"

        # Intersected stations
        if pt in {"intersection", "intersected station", "intersection station"}:
            return "intersected"

        # Everything else is treated as passive (bolts, berntsens, blocks, etc.)
        return "passive"

    def _colour_condition_mode(condition: str) -> str:
        code = (condition or "").strip().upper()
        return trig_colour_map.get(code, "grey")

    def _colour_mylog_mode(log_data: Optional[dict[str, Any]]) -> str:
        # Not logged by the user at all
        if not log_data:
            return "grey"

        code = (str(log_data.get("condition") or "")).strip().upper()

        # Logged but blank/NULL/'Z' => green (treat as found/OK)
        if code in {"", "Z"}:
            return "green"

        # Unknown / inaccessible counts as "failed attempt" when logged by the user
        if code in {"P", "U"}:
            return "red"

        # Use log_colour_map for logged conditions
        return log_colour_map.get(code, "grey")

    def _style_map_id(family: str, colour: str) -> str:
        return f"sm_{family}_{colour}"

    def _style_id(family: str, colour: str, highlighted: bool) -> str:
        return f"s_{family}_{colour}{'_h' if highlighted else ''}"

    def _icon_href(family: str, colour: str, highlighted: bool) -> str:
        suffix = "_h" if highlighted else ""
        return f"icons/mapicon_{family}_{colour}{suffix}.png"

    def _iter_icon_assets() -> list[Path]:
        if not _KMZ_ICONS_DIR.exists():
            raise FileNotFoundError(
                f"KMZ icons directory missing: {_KMZ_ICONS_DIR}. "
                "Expected vendored `mapicon_*.png` assets."
            )
        return sorted(_KMZ_ICONS_DIR.glob("mapicon_*.png"))

    def _kml_category_folder_name(trig: Trig) -> str:
        """Get category name for folder organization."""
        _, category_name = _get_category_info(trig)
        return category_name.strip() if category_name else "Unknown"

    def _condition_description(code: str) -> str:
        # Definitive wording comes from the wiki (mirrored by our mapping helper).
        from api.utils.condition_mapping import get_condition_description

        return get_condition_description(code, db)

    def _log_condition_description(log_data: Optional[dict[str, Any]]) -> str:
        """
        Descriptive condition for user log data.

        Special case: blank/NULL is treated as 'Z' (Not Logged) for display consistency.
        """
        if not log_data:
            return ""
        raw = str(log_data.get("condition") or "").strip()
        return _condition_description(raw or "Z")

    # ---- build styles -----------------------------------------------------
    # Predefine all style maps for all family+colour combinations so the KMZ is self-contained and stable.
    kml_lines: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        "  <Document>",
        "    <name>TrigpointingUK</name>",
        f"    <description>Generated {datetime.now(UTC).isoformat()}Z</description>",
    ]

    for family in _KMZ_ICON_FAMILIES:
        for colour in _KMZ_ICON_COLOURS:
            normal_style_id = _style_id(family, colour, highlighted=False)
            highlight_style_id = _style_id(family, colour, highlighted=True)
            sm_id = _style_map_id(family, colour)

            kml_lines.extend(
                [
                    f'    <Style id="{normal_style_id}">',
                    "      <IconStyle>",
                    "        <Icon>",
                    f"          <href>{_icon_href(family, colour, highlighted=False)}</href>",
                    "        </Icon>",
                    "      </IconStyle>",
                    "    </Style>",
                    f'    <Style id="{highlight_style_id}">',
                    "      <IconStyle>",
                    "        <Icon>",
                    f"          <href>{_icon_href(family, colour, highlighted=True)}</href>",
                    "        </Icon>",
                    "      </IconStyle>",
                    "    </Style>",
                    f'    <StyleMap id="{sm_id}">',
                    "      <Pair>",
                    "        <key>normal</key>",
                    f"        <styleUrl>#{normal_style_id}</styleUrl>",
                    "      </Pair>",
                    "      <Pair>",
                    "        <key>highlight</key>",
                    f"        <styleUrl>#{highlight_style_id}</styleUrl>",
                    "      </Pair>",
                    "    </StyleMap>",
                ]
            )

    # ---- group trigs into folders ----------------------------------------
    # Folder hierarchy:
    #   Level 1: category (category_name)
    #   Level 2: type_name (from trig_type.name)
    grouped: dict[str, dict[str, list[Trig]]] = {}
    for trig in trigs:
        category = _kml_category_folder_name(trig)
        type_folder = _get_type_name(trig) or "Unknown"
        grouped.setdefault(category, {}).setdefault(type_folder, []).append(trig)

    # Stable folder ordering: alphabetical by group name
    group_order = sorted(grouped.keys())

    for group_folder in group_order:
        types_in_group = grouped.get(group_folder, {})
        if not types_in_group:
            continue

        kml_lines.append("    <Folder>")
        kml_lines.append(f"      <name>{_escape_xml(group_folder)}</name>")

        for type_folder in sorted(types_in_group.keys()):
            trigs_in_type = types_in_group.get(type_folder, [])
            if not trigs_in_type:
                continue

            kml_lines.append("      <Folder>")
            kml_lines.append(f"        <name>{_escape_xml(type_folder)}</name>")

            for trig in trigs_in_type:
                trig_id = int(trig.id)
                waypoint = str(trig.waypoint)
                name = str(trig.name)
                type_name = _get_type_name(trig)
                category_code, category_name = _get_category_info(trig)
                family = _icon_family_from_type_name(type_name, category_name)

                if user_logs is None:
                    colour = _colour_condition_mode(str(getattr(trig, "condition", "")))
                else:
                    colour = _colour_mylog_mode(user_logs.get(trig_id))

                sm_id = _style_map_id(family, colour)

                # Description HTML (CDATA)
                lat = float(trig.wgs_lat)
                lon = float(trig.wgs_long)
                condition_desc = _condition_description(
                    str(getattr(trig, "condition", ""))
                )
                log_data = user_logs.get(trig_id) if user_logs is not None else None
                my_condition_desc = _log_condition_description(log_data)
                desc_html = _safe_cdata(
                    "\n".join(
                        [
                            (
                                f'<b><a href="{_escape_xml(_trig_url(trig_id))}">'
                                f"{_escape_xml(waypoint)} – {_escape_xml(name)}</a></b><br/>"
                            ),
                            # f"<b>Type:</b> {_escape_xml(type_name)}<br/>",
                            # f"<b>Category:</b> {_escape_xml(status_name)}<br/>",
                            # f"<b>Grid ref:</b> {_escape_xml(str(trig.osgb_gridref))}<br/>",
                            # f"<b>Condition:</b> {_escape_xml(condition_desc)}<br/>",
                            # (
                            #     f"<b>My condition:</b> {_escape_xml(my_condition_desc)}<br/>"
                            #     if user_logs is not None and log_data
                            #     else ""
                            # ),
                            # f"<b>Coordinates:</b> {lat:.5f}, {lon:.5f}<br/>",
                            f'<img src="{_escape_xml(_thumb_url(trig_id))}" width="240"/><br/>',
                        ]
                    )
                )

                kml_lines.append("        <Placemark>")
                kml_lines.append(
                    f"          <name>{_escape_xml(waypoint)} – {_escape_xml(name)}</name>"
                )
                kml_lines.append(f"          <styleUrl>#{sm_id}</styleUrl>")
                kml_lines.append("          <description><![CDATA[")
                kml_lines.append(f"{desc_html}")
                kml_lines.append("          ]]></description>")
                kml_lines.append("          <Point>")
                kml_lines.append(
                    f"            <coordinates>{lon},{lat},0</coordinates>"
                )
                kml_lines.append("          </Point>")

                # ExtendedData (flat key/value pairs; safe to grow)
                kml_lines.append("          <ExtendedData>")
                ext: dict[str, Any] = {
                    "waypoint": waypoint,
                    "name": name,
                    "category_code": category_code,
                    "category_name": category_name,
                    "type_name": type_name,
                    # Descriptive string per wiki, not letter code.
                    "condition": condition_desc,
                    "osgb_gridref": str(getattr(trig, "osgb_gridref", "")),
                }
                if user_logs is not None:
                    log_data = user_logs.get(trig_id)
                    ext["logged"] = "Y" if log_data else "N"
                    if log_data:
                        ext["log_date"] = str(log_data.get("date", ""))
                        # Descriptive string per wiki, not letter code.
                        ext["log_condition"] = my_condition_desc

                for key, val in ext.items():
                    kml_lines.append(f'            <Data name="{_escape_xml(key)}">')
                    kml_lines.append(
                        f"              <value>{_escape_xml(str(val))}</value>"
                    )
                    kml_lines.append("            </Data>")
                kml_lines.append("          </ExtendedData>")

                kml_lines.append("        </Placemark>")

            kml_lines.append("      </Folder>")

        kml_lines.append("    </Folder>")

    kml_lines.append("  </Document>")
    kml_lines.append("</kml>")
    doc_kml = "\n".join(kml_lines).encode("utf-8")

    # ---- build KMZ --------------------------------------------------------
    icon_paths = _iter_icon_assets()

    # Ensure the icons we reference actually exist (avoid broken KMZ styles).
    expected_icon_names: set[str] = set()
    for family in _KMZ_ICON_FAMILIES:
        for colour in _KMZ_ICON_COLOURS:
            expected_icon_names.add(Path(_icon_href(family, colour, False)).name)
            expected_icon_names.add(Path(_icon_href(family, colour, True)).name)
    actual_icon_names = {p.name for p in icon_paths}
    missing = sorted(expected_icon_names - actual_icon_names)
    if missing:
        raise FileNotFoundError(
            "Missing KMZ icon assets: "
            + ", ".join(missing[:10])
            + ("..." if len(missing) > 10 else "")
        )

    out = io.BytesIO()
    with zipfile.ZipFile(out, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("doc.kml", doc_kml)
        for icon_path in icon_paths:
            # Maintain a clean KMZ layout
            zf.write(icon_path, arcname=f"icons/{icon_path.name}")

    return out.getvalue()

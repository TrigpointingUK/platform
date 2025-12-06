"""
Export format generators for trigpoint data downloads.

Supports CSV, GeoJSON, KML, and GPX formats.
"""

import csv
import io
from datetime import datetime
from typing import Any, Optional

from api.models.trig import Trig


def trigs_to_csv(
    trigs: list[Trig],
    status_names: Optional[dict[int, str]] = None,
    user_logs: Optional[dict[int, dict[str, Any]]] = None,
) -> str:
    """
    Convert trigpoints to CSV format.

    Args:
        trigs: List of Trig objects
        status_names: Optional mapping of status_id to status name
        user_logs: Optional mapping of trig_id to user's log data

    Returns:
        CSV string
    """
    output = io.StringIO()

    # Base fields always included
    fieldnames = [
        "id",
        "waypoint",
        "name",
        "physical_type",
        "condition",
        "status_id",
        "status_name",
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
        row = {
            "id": trig.id,
            "waypoint": trig.waypoint,
            "name": trig.name,
            "physical_type": trig.physical_type,
            "condition": trig.condition,
            "status_id": trig.status_id,
            "status_name": (
                status_names.get(int(trig.status_id), "") if status_names else ""
            ),
            "wgs_lat": float(trig.wgs_lat),
            "wgs_long": float(trig.wgs_long),
            "wgs_height": trig.wgs_height,
            "osgb_gridref": trig.osgb_gridref,
            "osgb_eastings": trig.osgb_eastings,
            "osgb_northings": trig.osgb_northings,
            "osgb_height": trig.osgb_height,
            "county": trig.county,
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
    status_names: Optional[dict[int, str]] = None,
    user_logs: Optional[dict[int, dict[str, Any]]] = None,
) -> dict:
    """
    Convert trigpoints to GeoJSON FeatureCollection format.

    Args:
        trigs: List of Trig objects
        status_names: Optional mapping of status_id to status name
        user_logs: Optional mapping of trig_id to user's log data

    Returns:
        GeoJSON dict
    """
    features = []

    for trig in trigs:
        properties = {
            "id": trig.id,
            "waypoint": trig.waypoint,
            "name": trig.name,
            "physical_type": trig.physical_type,
            "condition": trig.condition,
            "status_id": trig.status_id,
            "status_name": (
                status_names.get(int(trig.status_id), "") if status_names else ""
            ),
            "osgb_gridref": trig.osgb_gridref,
            "county": trig.county,
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
        "generated_at": datetime.utcnow().isoformat(),
    }


def trigs_to_gpx(
    trigs: list[Trig],
    status_names: Optional[dict[int, str]] = None,
    user_logs: Optional[dict[int, dict[str, Any]]] = None,
) -> str:
    """
    Convert trigpoints to GPX format.

    Creates waypoints for each trigpoint with metadata in descriptions.

    Args:
        trigs: List of Trig objects
        status_names: Optional mapping of status_id to status name
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
        f"    <time>{datetime.utcnow().isoformat()}Z</time>",
        "  </metadata>",
    ]

    for trig in trigs:
        status_name = status_names.get(int(trig.status_id), "") if status_names else ""

        # Build description
        desc_parts = [
            f"Type: {trig.physical_type}",
            f"Status: {status_name}",
            f"Grid Ref: {trig.osgb_gridref}",
            f"Condition: {trig.condition}",
        ]
        if trig.county:
            desc_parts.append(f"County: {trig.county}")
        if trig.fb_number:
            desc_parts.append(f"FB: {trig.fb_number}")

        # Add log info if available
        if user_logs is not None:
            log_data = user_logs.get(int(trig.id))
            if log_data:
                desc_parts.append(f"Logged: {log_data.get('date', 'Yes')}")
                if log_data.get("condition"):
                    desc_parts.append(f"My Condition: {log_data.get('condition')}")
            else:
                desc_parts.append("Logged: No")

        description = " | ".join(desc_parts)

        lines.append(
            f'  <wpt lat="{float(trig.wgs_lat)}" lon="{float(trig.wgs_long)}">'
        )
        lines.append(f"    <ele>{trig.wgs_height}</ele>")
        lines.append(f"    <name>{escape_xml(str(trig.waypoint))}</name>")
        lines.append(f"    <desc>{escape_xml(description)}</desc>")
        lines.append(f"    <cmt>{escape_xml(str(trig.name))}</cmt>")
        lines.append("    <sym>Triangle</sym>")
        lines.append("  </wpt>")

    lines.append("</gpx>")

    return "\n".join(lines)


def trigs_to_kml(
    trigs: list[Trig],
    status_names: Optional[dict[int, str]] = None,
    user_logs: Optional[dict[int, dict[str, Any]]] = None,
) -> str:
    """
    Convert trigpoints to KML format.

    Creates placemarks for each trigpoint with metadata in descriptions.

    Args:
        trigs: List of Trig objects
        status_names: Optional mapping of status_id to status name
        user_logs: Optional mapping of trig_id to user's log data

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
        f"    <description>Generated {datetime.utcnow().isoformat()}Z</description>",
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
        status_name = status_names.get(int(trig.status_id), "") if status_names else ""

        # Build description HTML
        desc_lines = [
            "<![CDATA[",
            f"<b>Type:</b> {escape_xml(str(trig.physical_type))}<br/>",
            f"<b>Status:</b> {escape_xml(status_name)}<br/>",
            f"<b>Grid Ref:</b> {escape_xml(str(trig.osgb_gridref))}<br/>",
            f"<b>Condition:</b> {escape_xml(str(trig.condition))}<br/>",
        ]
        if trig.county:
            desc_lines.append(f"<b>County:</b> {escape_xml(str(trig.county))}<br/>")
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
        lines.append(
            f"        <coordinates>{float(trig.wgs_long)},{float(trig.wgs_lat)},{trig.wgs_height}</coordinates>"
        )
        lines.append("      </Point>")
        lines.append("    </Placemark>")

    lines.append("  </Document>")
    lines.append("</kml>")

    return "\n".join(lines)

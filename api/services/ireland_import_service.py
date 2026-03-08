"""
Service for comparing Ireland25 CSV data with Irish trigpoints in the database.

The Ireland25 CSV contains authoritative data for Irish trigpoints provided by
OSI (Ordnance Survey Ireland) and OSNI (Ordnance Survey Northern Ireland).

Irish trigs in the database are identified via the trig_area table where
area_type_id=3 and area_id IN (339, 342):
  - 339 = Northern Ireland
  - 342 = Republic of Ireland
"""

import csv
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.orm import Session

from api.core.logging import get_logger
from api.models.trig import Trig
from api.services.coordinate_service import (
    convert_irish_to_wgs84,
    eastings_northings_to_irish_gridref,
    is_irish_gridref,
)

logger = get_logger(__name__)

# Path to bundled CSV
CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "ireland25.csv"

# Proximity threshold in metres for matching
MATCH_THRESHOLD_METRES = 500.0

# Area IDs for Irish trigs (area_type_id = 3 = country)
AREA_ID_NORTHERN_IRELAND = 339
AREA_ID_REPUBLIC_OF_IRELAND = 342

AREA_NAMES = {
    AREA_ID_NORTHERN_IRELAND: "Northern Ireland",
    AREA_ID_REPUBLIC_OF_IRELAND: "Republic of Ireland",
}

# Mapping from CSV "Ord" column to historic_use values
ORD_TO_HISTORIC_USE = {
    "1": "Primary",
    "2": "Secondary",
    "3": "3rd order",
    "U": "none",
}


@dataclass
class CSVRow:
    """Parsed row from Ireland25 CSV."""

    row_index: int  # 0-based index (excluding header)
    station_name: str
    osi_ni_no: str
    eastings: float
    northings: float
    height: Optional[float]  # None if "H" or "h" or empty
    fb_sort: str
    fb_number: str
    date_built: str
    order: str  # "1", "2", "3", "U", or ""
    dr: str
    grid_ref: str
    notes: str


@dataclass
class DBIrishTrig:
    """An Irish trig from the database (identified via trig_area)."""

    trig_id: int
    waypoint: str
    name: str
    fb_number: str
    stn_number: str
    osgb_eastings: float
    osgb_northings: float
    osgb_gridref: str
    osgb_height: Optional[float]
    condition: str
    historic_use: str
    current_use: str
    status_id: int
    type_id: Optional[int]
    area_id: int  # 339 or 342
    has_non_irish_gridref: bool = False


@dataclass
class FieldDiff:
    """A single field difference."""

    field_name: str
    csv_value: Optional[str]
    db_value: Optional[str]


@dataclass
class ComparisonResult:
    """Result of comparing one CSV row or DB trig."""

    category: (
        str  # matched_identical, matched_different, ambiguous, new_in_csv, orphan_in_db
    )
    csv_row: Optional[CSVRow] = None
    db_trig: Optional[DBIrishTrig] = None
    additional_db_matches: list[DBIrishTrig] = field(default_factory=list)
    differences: list[FieldDiff] = field(default_factory=list)
    distance_metres: Optional[float] = None
    description: str = ""


@dataclass
class FullComparisonResult:
    """Full comparison of CSV vs DB."""

    csv_count: int
    db_irish_count: int
    items: list[ComparisonResult]
    matched_identical_count: int = 0
    matched_different_count: int = 0
    ambiguous_count: int = 0
    new_in_csv_count: int = 0
    orphan_in_db_count: int = 0
    non_irish_gridref_count: int = 0


def parse_csv() -> list[CSVRow]:
    """
    Parse the Ireland25 CSV file.

    Returns:
        List of CSVRow objects, one per data row.
    """
    rows: list[CSVRow] = []

    with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for idx, raw in enumerate(reader):
            # Parse height - can be numeric, "H"/"h" (unknown), or empty
            height_str = raw.get("Height", "").strip()
            height: Optional[float] = None
            if height_str and height_str.upper() != "H":
                try:
                    height = float(height_str)
                except ValueError:
                    height = None

            # Parse eastings and northings (always numeric)
            try:
                eastings = float(raw.get("Eastings", "0"))
                northings = float(raw.get("Northings", "0"))
            except ValueError:
                logger.warning("Skipping CSV row %d: invalid coordinates", idx)
                continue

            row = CSVRow(
                row_index=idx,
                station_name=raw.get("Station Name", "").strip(),
                osi_ni_no=raw.get("OSI/NI No", "").strip(),
                eastings=eastings,
                northings=northings,
                height=height,
                fb_sort=raw.get("FB Sort", "").strip(),
                fb_number=raw.get("FB No", "").strip(),
                date_built=raw.get("Date built", "").strip(),
                order=raw.get("Ord", "").strip(),
                dr=raw.get("DR", "").strip(),
                grid_ref=raw.get("Grid Ref", "").strip(),
                notes=raw.get("Notes", "").strip(),
            )
            rows.append(row)

    logger.info("Parsed %d rows from Ireland25 CSV", len(rows))
    return rows


def get_csv_row_by_index(row_index: int) -> Optional[CSVRow]:
    """
    Get a single CSV row by its 0-based index.

    Args:
        row_index: 0-based row index in the CSV (excluding header).

    Returns:
        CSVRow or None if not found.
    """
    rows = parse_csv()
    for row in rows:
        if row.row_index == row_index:
            return row
    return None


def get_irish_trigs_from_db(db: Session) -> list[DBIrishTrig]:
    """
    Get all Irish trigs from the database, identified via trig_area table.

    Uses: SELECT t.* FROM trig t
          JOIN trig_area ta ON ta.trig_id = t.id
          WHERE ta.area_type_id = 3 AND ta.area_id IN (339, 342)
    """
    trig_area = sa.table(
        "trig_area",
        sa.column("trig_id", sa.Integer),
        sa.column("area_id", sa.Integer),
        sa.column("area_type_id", sa.Integer),
    )

    stmt = (
        sa.select(Trig, trig_area.c.area_id)
        .select_from(Trig.__table__.join(trig_area, Trig.id == trig_area.c.trig_id))
        .where(
            sa.and_(
                trig_area.c.area_type_id == 3,
                trig_area.c.area_id.in_(
                    [AREA_ID_NORTHERN_IRELAND, AREA_ID_REPUBLIC_OF_IRELAND]
                ),
            )
        )
    )

    result = db.execute(stmt).all()

    trigs: list[DBIrishTrig] = []
    for row in result:
        t = row[0]  # Trig object
        area_id = row[1]  # area_id

        gridref_str = str(t.osgb_gridref) if t.osgb_gridref else ""
        non_irish = bool(gridref_str) and not is_irish_gridref(gridref_str)

        trigs.append(
            DBIrishTrig(
                trig_id=int(t.id),
                waypoint=str(t.waypoint),
                name=str(t.name),
                fb_number=str(t.fb_number) if t.fb_number else "",
                stn_number=str(t.stn_number) if t.stn_number else "",
                osgb_eastings=float(t.osgb_eastings) if t.osgb_eastings else 0.0,
                osgb_northings=float(t.osgb_northings) if t.osgb_northings else 0.0,
                osgb_gridref=gridref_str,
                osgb_height=float(t.osgb_height) if t.osgb_height else None,
                condition=str(t.condition) if t.condition else "",
                historic_use=str(t.historic_use) if t.historic_use else "none",
                current_use=str(t.current_use) if t.current_use else "none",
                status_id=int(t.status_id) if t.status_id else 1,
                type_id=int(t.type_id) if t.type_id else None,
                area_id=int(area_id),
                has_non_irish_gridref=non_irish,
            )
        )

    logger.info("Found %d Irish trigs in database", len(trigs))
    return trigs


def _euclidean_distance(e1: float, n1: float, e2: float, n2: float) -> float:
    """Euclidean distance in metres between two Irish Grid coordinate pairs."""
    return math.sqrt((e2 - e1) ** 2 + (n2 - n1) ** 2)


def _compare_fields(csv_row: CSVRow, db_trig: DBIrishTrig) -> list[FieldDiff]:
    """
    Compare mapped fields between a CSV row and a DB trig, returning differences.
    """
    diffs: list[FieldDiff] = []

    # Name
    csv_name = csv_row.station_name.strip()
    db_name = db_trig.name.strip()
    if csv_name.lower() != db_name.lower():
        diffs.append(FieldDiff("name", csv_name, db_name))

    # FB number - compare normalised (strip leading zeros from both)
    csv_fb = csv_row.fb_number.strip().lstrip("0") or "0"
    db_fb = db_trig.fb_number.strip().lstrip("0") or "0"
    if csv_fb != db_fb:
        diffs.append(FieldDiff("fb_number", csv_row.fb_number, db_trig.fb_number))

    # Station number
    csv_stn = csv_row.osi_ni_no.strip()
    db_stn = db_trig.stn_number.strip()
    if csv_stn and csv_stn.lower() != db_stn.lower():
        diffs.append(FieldDiff("stn_number", csv_stn, db_stn))

    # Eastings - compare to 1m tolerance
    if abs(csv_row.eastings - db_trig.osgb_eastings) > 1.0:
        diffs.append(
            FieldDiff(
                "osgb_eastings",
                f"{csv_row.eastings:.3f}",
                f"{db_trig.osgb_eastings:.3f}",
            )
        )

    # Northings - compare to 1m tolerance
    if abs(csv_row.northings - db_trig.osgb_northings) > 1.0:
        diffs.append(
            FieldDiff(
                "osgb_northings",
                f"{csv_row.northings:.3f}",
                f"{db_trig.osgb_northings:.3f}",
            )
        )

    # Height - compare if CSV has a value
    if csv_row.height is not None and db_trig.osgb_height is not None:
        if abs(csv_row.height - db_trig.osgb_height) > 0.5:
            diffs.append(
                FieldDiff(
                    "osgb_height",
                    f"{csv_row.height:.1f}",
                    f"{db_trig.osgb_height:.1f}",
                )
            )
    elif csv_row.height is not None and db_trig.osgb_height is None:
        diffs.append(FieldDiff("osgb_height", f"{csv_row.height:.1f}", None))

    # Grid reference
    csv_gridref = csv_row.grid_ref.strip()
    db_gridref = db_trig.osgb_gridref.strip()
    if csv_gridref and db_gridref:
        # Normalise by removing extra spaces for comparison
        csv_gr_norm = " ".join(csv_gridref.split())
        db_gr_norm = " ".join(db_gridref.split())
        if csv_gr_norm.upper() != db_gr_norm.upper():
            diffs.append(FieldDiff("osgb_gridref", csv_gridref, db_gridref))
    elif csv_gridref and not db_gridref:
        diffs.append(FieldDiff("osgb_gridref", csv_gridref, ""))

    # Historic use (from Ord column)
    csv_historic = ORD_TO_HISTORIC_USE.get(csv_row.order, "")
    db_historic = db_trig.historic_use.strip()
    if csv_historic and csv_historic.lower() != db_historic.lower():
        diffs.append(FieldDiff("historic_use", csv_historic, db_historic))

    # Condition (from Notes column - only compare if Notes contains a clear condition code)
    csv_condition = _extract_condition_from_notes(csv_row.notes)
    if csv_condition and csv_condition != db_trig.condition:
        diffs.append(FieldDiff("condition", csv_condition, db_trig.condition))

    return diffs


def _extract_condition_from_notes(notes: str) -> Optional[str]:
    """
    Extract a condition code from the CSV Notes column.

    Known codes from Ireland25_columns.csv:
    - X or X1 = Destroyed
    - R = Remains
    - H = Height unknown (not a condition)
    - bolt = Bolt (not a condition code per se)

    Returns:
        Single-character condition code or None.
    """
    if not notes:
        return None

    notes_upper = notes.strip().upper()

    # Check for destroyed markers
    if notes_upper.startswith("X"):
        return "X"

    # Check for "R" (remains) - only if it's the sole or primary code
    # "R  H" means remains + height unknown
    parts = notes_upper.split()
    if parts and parts[0] == "R":
        return "R"

    return None


def compare_ireland_csv_with_db(db: Session) -> FullComparisonResult:
    """
    Compare the Ireland25 CSV with Irish trigs in the database.

    Matching strategy:
    - Euclidean distance on Irish Grid eastings/northings
    - Threshold: 500 metres
    - Multiple matches flagged as ambiguous

    Returns:
        FullComparisonResult with all comparison items.
    """
    csv_rows = parse_csv()
    db_trigs = get_irish_trigs_from_db(db)

    items: list[ComparisonResult] = []

    # Track which DB trigs have been matched to at least one CSV row
    matched_db_ids: set[int] = set()

    for csv_row in csv_rows:
        # Find all DB trigs within threshold distance
        matches: list[tuple[DBIrishTrig, float]] = []
        for db_trig in db_trigs:
            dist = _euclidean_distance(
                csv_row.eastings,
                csv_row.northings,
                db_trig.osgb_eastings,
                db_trig.osgb_northings,
            )
            if dist <= MATCH_THRESHOLD_METRES:
                matches.append((db_trig, dist))

        # Sort matches by distance
        matches.sort(key=lambda m: m[1])

        if len(matches) == 0:
            # No match - new in CSV
            items.append(
                ComparisonResult(
                    category="new_in_csv",
                    csv_row=csv_row,
                    description=(
                        f"'{csv_row.station_name}' ({csv_row.grid_ref}) "
                        f"has no match within {MATCH_THRESHOLD_METRES:.0f}m in database"
                    ),
                )
            )
        elif len(matches) == 1:
            # Single match
            db_trig, dist = matches[0]
            matched_db_ids.add(db_trig.trig_id)
            diffs = _compare_fields(csv_row, db_trig)

            if diffs:
                items.append(
                    ComparisonResult(
                        category="matched_different",
                        csv_row=csv_row,
                        db_trig=db_trig,
                        differences=diffs,
                        distance_metres=round(dist, 2),
                        description=(
                            f"'{csv_row.station_name}' matched "
                            f"'{db_trig.name}' ({db_trig.waypoint}) "
                            f"at {dist:.1f}m with {len(diffs)} difference(s)"
                        ),
                    )
                )
            else:
                items.append(
                    ComparisonResult(
                        category="matched_identical",
                        csv_row=csv_row,
                        db_trig=db_trig,
                        distance_metres=round(dist, 2),
                        description=(
                            f"'{csv_row.station_name}' matches "
                            f"'{db_trig.name}' ({db_trig.waypoint}) "
                            f"at {dist:.1f}m - all fields identical"
                        ),
                    )
                )
        else:
            # Multiple matches - ambiguous
            primary_trig, primary_dist = matches[0]
            additional = [m[0] for m in matches[1:]]
            for m_trig, _ in matches:
                matched_db_ids.add(m_trig.trig_id)

            diffs = _compare_fields(csv_row, primary_trig)

            items.append(
                ComparisonResult(
                    category="ambiguous",
                    csv_row=csv_row,
                    db_trig=primary_trig,
                    additional_db_matches=additional,
                    differences=diffs,
                    distance_metres=round(primary_dist, 2),
                    description=(
                        f"'{csv_row.station_name}' has {len(matches)} DB records "
                        f"within {MATCH_THRESHOLD_METRES:.0f}m"
                    ),
                )
            )

    # Find orphan DB trigs (no CSV match)
    for db_trig in db_trigs:
        if db_trig.trig_id not in matched_db_ids:
            items.append(
                ComparisonResult(
                    category="orphan_in_db",
                    db_trig=db_trig,
                    description=(
                        f"'{db_trig.name}' ({db_trig.waypoint}) "
                        f"has no match in CSV within {MATCH_THRESHOLD_METRES:.0f}m"
                    ),
                )
            )

    # Sort alphabetically by name so that related items (e.g. an orphan_in_db
    # and a new_in_csv for the same trigpoint) appear adjacent to each other.
    def _sort_name(item: ComparisonResult) -> str:
        if item.csv_row:
            return item.csv_row.station_name.upper()
        if item.db_trig:
            return item.db_trig.name.upper()
        return ""

    items.sort(key=_sort_name)

    # Count non-Irish gridref warnings
    non_irish_count = sum(1 for t in db_trigs if t.has_non_irish_gridref)

    # Build summary counts
    all_categories = [
        "matched_identical",
        "matched_different",
        "ambiguous",
        "new_in_csv",
        "orphan_in_db",
    ]
    counts: dict[str, int] = {cat: 0 for cat in all_categories}
    for item in items:
        counts[item.category] = counts.get(item.category, 0) + 1

    return FullComparisonResult(
        csv_count=len(csv_rows),
        db_irish_count=len(db_trigs),
        items=items,
        matched_identical_count=counts.get("matched_identical", 0),
        matched_different_count=counts.get("matched_different", 0),
        ambiguous_count=counts.get("ambiguous", 0),
        new_in_csv_count=counts.get("new_in_csv", 0),
        orphan_in_db_count=counts.get("orphan_in_db", 0),
        non_irish_gridref_count=non_irish_count,
    )


def build_trig_data_from_csv(csv_row: CSVRow) -> dict:
    """
    Build a trig_data dictionary suitable for create_trig_admin() or
    update_trig_admin() from a CSV row.

    Converts Irish Grid to WGS84 and computes grid reference.

    Returns:
        Dictionary of field values ready for the trig CRUD functions.
    """
    # Convert Irish Grid to WGS84
    wgs_long, wgs_lat, wgs_height = convert_irish_to_wgs84(
        csv_row.eastings, csv_row.northings, csv_row.height
    )

    # Compute Irish Grid reference from eastings/northings (standardised format)
    try:
        computed_gridref = eastings_northings_to_irish_gridref(
            csv_row.eastings, csv_row.northings
        )
    except ValueError:
        computed_gridref = csv_row.grid_ref

    # Use CSV grid_ref if available, else computed
    gridref = csv_row.grid_ref.strip() or computed_gridref

    # Map "Ord" to historic_use
    historic_use = ORD_TO_HISTORIC_USE.get(csv_row.order, "none")

    # Map Notes to condition
    condition = _extract_condition_from_notes(csv_row.notes) or "G"

    return {
        "name": csv_row.station_name,
        "fb_number": csv_row.fb_number or "",
        "stn_number": csv_row.osi_ni_no or "",
        "stn_number_active": "",
        "stn_number_passive": "",
        "stn_number_osgb36": "",
        "status_id": 1,  # Default status
        "type_id": None,
        "current_use": "none",
        "historic_use": historic_use,
        "condition": condition,
        "wgs_lat": wgs_lat,
        "wgs_long": wgs_long,
        "wgs_height": wgs_height,
        "osgb_eastings": csv_row.eastings,
        "osgb_northings": csv_row.northings,
        "osgb_gridref": gridref,
        "osgb_height": csv_row.height,
        # Original location fields (provenance from Ireland25)
        "original_osgb_eastings": csv_row.eastings,
        "original_osgb_northings": csv_row.northings,
        "original_osgb_gridref": gridref,
        "original_osgb_height": csv_row.height,
        "original_wgs_lat": wgs_lat,
        "original_wgs_long": wgs_long,
        "original_wgs_height": wgs_height,
        "original_grid_system": "ie",
        "original_provenance": "Ireland25",
    }

"""
Service for fetching and comparing OS Net active station data with the database.

The OS Net coordinates file contains GPS reference stations that correspond to
trigpoints in the 'Active station' category (trig_category.id = 5).
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.core.logging import get_logger
from api.models.trig import Trig
from api.models.trig_type import TrigCategory, TrigType

logger = get_logger(__name__)

# OS Net coordinates file URL
OSNET_URL = (
    "https://www.ordnancesurvey.co.uk/documents/resources/osnet-coordinates-file.txt"
)

# Cache duration for the OS Net file (1 hour)
OSNET_CACHE_DURATION = timedelta(hours=1)

# Coordinate comparison tolerance in metres
COORDINATE_TOLERANCE_METRES = 0.01


# Section identifiers for the OS Net file
SECTION_CURRENT = 1  # Part (i) - Current OS Net v2009 stations
SECTION_LEGACY = 2  # Part (ii) - Older OS Net v2001 stations
SECTION_DESTROYED = 3  # Part (iii) - Destroyed or Moved stations

SECTION_NAMES = {
    SECTION_CURRENT: "Current (v2009)",
    SECTION_LEGACY: "Legacy (v2001)",
    SECTION_DESTROYED: "Destroyed/Moved",
}


@dataclass
class OSNetStation:
    """Parsed OS Net station data."""

    code: str  # 4-letter station code (e.g., "THUR")
    easting: float  # OSGB36 easting
    northing: float  # OSGB36 northing
    gridref: str  # OS grid reference (e.g., "NC9967")
    height: float  # Orthometric height
    lat_dms: str  # Latitude in DMS format
    lon_dms: str  # Longitude in DMS format
    datum: str  # Height datum (e.g., "Newlyn")
    section: int = SECTION_CURRENT  # Which part of the file (1, 2, or 3)


@dataclass
class ActiveStationDB:
    """Database active station record."""

    trig_id: int
    waypoint: str
    name: str
    stn_number_active: Optional[str]
    osgb_eastings: float
    osgb_northings: float
    osgb_gridref: str
    osgb_height: Optional[float]


@dataclass
class StationDifference:
    """A difference found between OS Net and database."""

    station_code: str
    difference_type: str  # 'new_in_osnet', 'destroyed_not_in_db', 'missing_from_osnet', 'coordinate_mismatch', 'unmatched_db'
    description: str
    osnet_data: Optional[dict] = None
    db_data: Optional[dict] = None
    distance_metres: Optional[float] = None
    osnet_section: Optional[int] = None  # Which section of the OS Net file (1, 2, or 3)


@dataclass
class OSNetComparisonResult:
    """Result of comparing OS Net data with the database."""

    osnet_count: int
    osnet_current_count: int  # Part (i) - current stations
    osnet_legacy_count: int  # Part (ii) - legacy v2001 stations
    osnet_destroyed_count: int  # Part (iii) - destroyed/moved stations
    db_count: int
    matched_count: int
    differences: list[StationDifference]
    osnet_fetch_time: datetime
    changelog_entries: list[str]  # Recent changes from the file header


class OSNetCache:
    """Simple in-memory cache for OS Net data."""

    _instance: Optional["OSNetCache"] = None
    _data: Optional[str] = None
    _fetch_time: Optional[datetime] = None

    @classmethod
    def get_instance(cls) -> "OSNetCache":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_cached_data(self) -> Optional[tuple[str, datetime]]:
        """Get cached data if still valid."""
        if self._data is None or self._fetch_time is None:
            return None
        if datetime.now() - self._fetch_time > OSNET_CACHE_DURATION:
            return None
        return self._data, self._fetch_time

    def set_data(self, data: str) -> None:
        """Cache the fetched data."""
        self._data = data
        self._fetch_time = datetime.now()

    def clear(self) -> None:
        """Clear the cache."""
        self._data = None
        self._fetch_time = None


def fetch_osnet_file(force_refresh: bool = False) -> tuple[str, datetime]:
    """
    Fetch the OS Net coordinates file, using cache if available.

    Args:
        force_refresh: If True, bypass the cache and fetch fresh data.

    Returns:
        Tuple of (file content, fetch timestamp).
    """
    cache = OSNetCache.get_instance()

    if not force_refresh:
        cached = cache.get_cached_data()
        if cached:
            logger.info("Using cached OS Net data from %s", cached[1].isoformat())
            return cached

    logger.info("Fetching OS Net coordinates file from %s", OSNET_URL)

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(OSNET_URL)
            response.raise_for_status()
            content = response.text

        cache.set_data(content)
        logger.info(
            "Fetched OS Net file: %d bytes, %d lines",
            len(content),
            content.count("\n"),
        )
        return content, datetime.now()

    except httpx.HTTPError as e:
        logger.error("Failed to fetch OS Net file: %s", str(e))
        raise RuntimeError(f"Failed to fetch OS Net coordinates file: {e}") from e


def parse_osnet_file(content: str) -> tuple[list[OSNetStation], list[str]]:
    """
    Parse the OS Net coordinates file.

    The file format has three sections:
    - Part (i): Current OS Net v2009 stations
    - Part (ii): Older OS Net v2001 stations
    - Part (iii): Destroyed or Moved stations

    Each section is delimited by comment lines containing "part (i)", "part (ii)", etc.

    Returns:
        Tuple of (list of stations, list of changelog entries from header).
    """
    stations: list[OSNetStation] = []
    changelog: list[str] = []
    current_section = SECTION_CURRENT  # Default to part (i)

    for line in content.split("\n"):
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Process comment lines
        if line.startswith("#"):
            line_lower = line.lower()

            # Detect section markers
            if "part (iii)" in line_lower or "part(iii)" in line_lower:
                current_section = SECTION_DESTROYED
                logger.debug("Entering section 3 (Destroyed/Moved)")
            elif "part (ii)" in line_lower or "part(ii)" in line_lower:
                current_section = SECTION_LEGACY
                logger.debug("Entering section 2 (Legacy v2001)")
            elif "part (i)" in line_lower or "part(i)" in line_lower:
                # Could be "part (i)" or "part (ii)" etc, only match exactly part (i)
                if "part (ii)" not in line_lower and "part (iii)" not in line_lower:
                    current_section = SECTION_CURRENT
                    logger.debug("Entering section 1 (Current v2009)")

            # Extract changelog entries from comments (date patterns)
            if re.match(r"^#\s*\d{4}-\d{2}-\d{2}\.", line):
                changelog.append(line[1:].strip())
            continue

        # Parse data line
        # Format: CODE,X,Y,Z,LAT,LON,ELLIPS_H,EASTING,NORTHING,ORTHO_H,DATUM,ORDER,GRIDREF,ANTENNA_H[,ANTENNA,RECEIVER]
        parts = line.split(",")
        if len(parts) < 13:
            continue

        try:
            code = parts[0].strip()
            # Skip if code is empty or looks like a header
            if not code or code.upper() in ("STATION", "CODE", "NAME"):
                continue

            station = OSNetStation(
                code=code,
                easting=float(parts[7]),
                northing=float(parts[8]),
                gridref=parts[12].strip(),
                height=float(parts[9]),
                lat_dms=parts[4].strip(),
                lon_dms=parts[5].strip(),
                datum=parts[10].strip(),
                section=current_section,
            )
            stations.append(station)

        except (ValueError, IndexError) as e:
            logger.warning("Failed to parse OS Net line: %s - %s", line[:50], str(e))
            continue

    # Log section counts
    section_counts = {
        s: 0 for s in [SECTION_CURRENT, SECTION_LEGACY, SECTION_DESTROYED]
    }
    for s in stations:
        section_counts[s.section] += 1
    logger.info(
        "Parsed %d OS Net stations (current: %d, legacy: %d, destroyed: %d), %d changelog entries",
        len(stations),
        section_counts[SECTION_CURRENT],
        section_counts[SECTION_LEGACY],
        section_counts[SECTION_DESTROYED],
        len(changelog),
    )
    return stations, changelog


def get_active_stations_from_db(db: Session) -> list[ActiveStationDB]:
    """
    Get all active stations from the database.

    Active stations are those where trig.type_id points to a trig_type
    that belongs to the 'ACTIVE' category (trig_category.code = 'ACTIVE').
    """
    # Single query with joins: trig -> trig_type -> trig_category
    trigs = (
        db.execute(
            select(Trig)
            .join(TrigType, Trig.type_id == TrigType.id)
            .join(TrigCategory, TrigType.category_id == TrigCategory.id)
            .where(TrigCategory.code == "ACTIVE")
        )
        .scalars()
        .all()
    )

    stations: list[ActiveStationDB] = [
        ActiveStationDB(
            trig_id=int(t.id),
            waypoint=str(t.waypoint),
            name=str(t.name),
            stn_number_active=str(t.stn_number_active) if t.stn_number_active else None,
            osgb_eastings=float(t.osgb_eastings),
            osgb_northings=float(t.osgb_northings),
            osgb_gridref=str(t.osgb_gridref),
            osgb_height=float(t.osgb_height) if t.osgb_height else None,
        )
        for t in trigs
    ]

    logger.info("Found %d active stations in database", len(stations))
    return stations


def calculate_distance(e1: float, n1: float, e2: float, n2: float) -> float:
    """Calculate distance in metres between two OSGB coordinates."""
    return ((e2 - e1) ** 2 + (n2 - n1) ** 2) ** 0.5


def compare_osnet_with_db(
    db: Session,
    force_refresh: bool = False,
) -> OSNetComparisonResult:
    """
    Compare OS Net stations with database active stations.

    The OS Net file has three sections:
    - Part (i): Current active stations - these are the primary comparison target
    - Part (ii): Legacy v2001 coordinates - informational only
    - Part (iii): Destroyed/moved stations - informational, not flagged as "new"

    Args:
        db: Database session.
        force_refresh: If True, bypass cache and fetch fresh OS Net data.

    Returns:
        Comparison result with all differences found.
    """
    # Fetch and parse OS Net data
    content, fetch_time = fetch_osnet_file(force_refresh)
    osnet_stations, changelog = parse_osnet_file(content)

    # Get database stations
    db_stations = get_active_stations_from_db(db)

    # Build lookup maps - separate by section
    # For current stations (Part i), we use the latest entry if duplicates exist
    osnet_current: dict[str, OSNetStation] = {}
    osnet_legacy: dict[str, OSNetStation] = {}
    osnet_destroyed: dict[str, OSNetStation] = {}

    for s in osnet_stations:
        code = s.code.upper()
        if s.section == SECTION_CURRENT:
            osnet_current[code] = s
        elif s.section == SECTION_LEGACY:
            osnet_legacy[code] = s
        elif s.section == SECTION_DESTROYED:
            osnet_destroyed[code] = s

    # Combined lookup for all OS Net stations (for checking if DB station exists anywhere)
    osnet_all_codes = (
        set(osnet_current.keys())
        | set(osnet_legacy.keys())
        | set(osnet_destroyed.keys())
    )

    # DB stations by stn_number_active (uppercase for matching)
    db_by_stn: dict[str, ActiveStationDB] = {}
    for db_stn in db_stations:
        if db_stn.stn_number_active:
            db_by_stn[db_stn.stn_number_active.upper().strip()] = db_stn

    differences: list[StationDifference] = []
    matched_codes: set[str] = set()

    # Check current OS Net stations (Part i) against database
    for code, osnet in osnet_current.items():
        db_station = db_by_stn.get(code)

        if db_station is None:
            # Current station in OS Net but not in database - this is actionable
            differences.append(
                StationDifference(
                    station_code=code,
                    difference_type="new_in_osnet",
                    description=f"Current station {code} in OS Net but not in database",
                    osnet_data={
                        "code": osnet.code,
                        "easting": osnet.easting,
                        "northing": osnet.northing,
                        "gridref": osnet.gridref,
                        "height": osnet.height,
                        "lat_dms": osnet.lat_dms,
                        "lon_dms": osnet.lon_dms,
                    },
                    osnet_section=osnet.section,
                )
            )
        else:
            matched_codes.add(code)

            # Check for coordinate differences (only against current coordinates)
            distance = calculate_distance(
                osnet.easting,
                osnet.northing,
                float(db_station.osgb_eastings),
                float(db_station.osgb_northings),
            )

            if distance > COORDINATE_TOLERANCE_METRES:
                differences.append(
                    StationDifference(
                        station_code=code,
                        difference_type="coordinate_mismatch",
                        description=f"Coordinates differ by {distance:.1f}m",
                        osnet_data={
                            "easting": osnet.easting,
                            "northing": osnet.northing,
                            "gridref": osnet.gridref,
                            "height": osnet.height,
                        },
                        db_data={
                            "trig_id": db_station.trig_id,
                            "waypoint": db_station.waypoint,
                            "name": db_station.name,
                            "easting": db_station.osgb_eastings,
                            "northing": db_station.osgb_northings,
                            "gridref": db_station.osgb_gridref,
                            "height": db_station.osgb_height,
                        },
                        distance_metres=distance,
                        osnet_section=osnet.section,
                    )
                )

    # Check destroyed stations (Part iii) not in database - informational
    for code, osnet in osnet_destroyed.items():
        db_station = db_by_stn.get(code)
        if db_station is None:
            differences.append(
                StationDifference(
                    station_code=code,
                    difference_type="destroyed_not_in_db",
                    description=f"Destroyed station {code} not in database (informational)",
                    osnet_data={
                        "code": osnet.code,
                        "easting": osnet.easting,
                        "northing": osnet.northing,
                        "gridref": osnet.gridref,
                        "height": osnet.height,
                        "lat_dms": osnet.lat_dms,
                        "lon_dms": osnet.lon_dms,
                    },
                    osnet_section=osnet.section,
                )
            )

    # Check legacy stations (Part ii) not in database - informational
    for code, osnet in osnet_legacy.items():
        db_station = db_by_stn.get(code)
        if db_station is None and code not in osnet_current:
            # Only report if not also in current section
            differences.append(
                StationDifference(
                    station_code=code,
                    difference_type="legacy_not_in_db",
                    description=f"Legacy station {code} (v2001) not in database (informational)",
                    osnet_data={
                        "code": osnet.code,
                        "easting": osnet.easting,
                        "northing": osnet.northing,
                        "gridref": osnet.gridref,
                        "height": osnet.height,
                        "lat_dms": osnet.lat_dms,
                        "lon_dms": osnet.lon_dms,
                    },
                    osnet_section=osnet.section,
                )
            )

    # Check for DB stations not in any OS Net section
    for stn_code, db_station in db_by_stn.items():
        if stn_code not in osnet_all_codes:
            differences.append(
                StationDifference(
                    station_code=stn_code,
                    difference_type="missing_from_osnet",
                    description=f"Station {stn_code} in database but not found in OS Net",
                    db_data={
                        "trig_id": db_station.trig_id,
                        "waypoint": db_station.waypoint,
                        "name": db_station.name,
                        "stn_number_active": db_station.stn_number_active,
                        "easting": db_station.osgb_eastings,
                        "northing": db_station.osgb_northings,
                        "gridref": db_station.osgb_gridref,
                    },
                )
            )

    # Check for DB stations without stn_number_active set
    for db_station in db_stations:
        if not db_station.stn_number_active or not db_station.stn_number_active.strip():
            differences.append(
                StationDifference(
                    station_code="",
                    difference_type="unmatched_db",
                    description=f"Active station '{db_station.name}' has no stn_number_active set",
                    db_data={
                        "trig_id": db_station.trig_id,
                        "waypoint": db_station.waypoint,
                        "name": db_station.name,
                        "easting": db_station.osgb_eastings,
                        "northing": db_station.osgb_northings,
                        "gridref": db_station.osgb_gridref,
                    },
                )
            )

    # Sort differences by type then code
    type_order = {
        "new_in_osnet": 0,
        "missing_from_osnet": 1,
        "coordinate_mismatch": 2,
        "unmatched_db": 3,
        "destroyed_not_in_db": 4,
        "legacy_not_in_db": 5,
    }
    differences.sort(
        key=lambda d: (type_order.get(d.difference_type, 99), d.station_code)
    )

    return OSNetComparisonResult(
        osnet_count=len(osnet_stations),
        osnet_current_count=len(osnet_current),
        osnet_legacy_count=len(osnet_legacy),
        osnet_destroyed_count=len(osnet_destroyed),
        db_count=len(db_stations),
        matched_count=len(matched_codes),
        differences=differences,
        osnet_fetch_time=fetch_time,
        changelog_entries=changelog[:20],  # Limit to recent entries
    )

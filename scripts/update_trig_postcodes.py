#!/usr/bin/env python3
"""
Batch update trig.postcode values from nearest postcode in postcodes table.

For each trig record:
- Find nearest postcode using Haversine distance formula
- If distance <= 1000m: set trig.postcode = postcodes.code
- If distance > 1000m: set trig.postcode = NULL

Usage:
    python scripts/update_trig_postcodes.py
"""

import sys
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from typing import Optional

import math  # For bounding box calculations

# Add api directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from api.db.database import get_engine, get_session_local  # noqa: E402
from api.models.trig import Trig  # noqa: E402


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance in meters between two WGS84 coordinates.
    Uses Haversine formula for great-circle distance.

    Args:
        lat1: Latitude of point 1 (degrees)
        lon1: Longitude of point 1 (degrees)
        lat2: Latitude of point 2 (degrees)
        lon2: Longitude of point 2 (degrees)

    Returns:
        Distance in meters
    """
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))

    # Earth radius in meters
    r = 6371000
    return c * r


def find_nearest_postcode(
    db: Session, trig_lat: float, trig_lon: float
) -> Optional[tuple[str, float]]:
    """
    Find nearest postcode to given coordinates using MySQL geospatial functions.

    Args:
        db: Database session
        trig_lat: Trig latitude (WGS84)
        trig_lon: Trig longitude (WGS84)

    Returns:
        Tuple of (postcode_code, distance_m) or None if no postcodes found

    Note:
        Uses MySQL's ST_Distance_Sphere() for optimized distance calculation.
        This function is much faster than manual Haversine calculations.
        POINT() expects (longitude, latitude) order per GIS standards.
        Filters out invalid coordinates (lat must be -90 to 90, long must be -180 to 180).
        Uses a bounding box of ~2km to pre-filter candidates before distance calculation.
    """
    # Calculate bounding box approximately 2km on each side
    # At UK latitudes (~50-60°N):
    # - 1 degree latitude ≈ 111km everywhere
    # - 1 degree longitude ≈ 111km * cos(latitude)
    #
    # For 2km box:
    # - lat_delta = 2 / 111 ≈ 0.018 degrees
    # - lon_delta = 2 / (111 * cos(lat)) degrees
    #
    # Using cos(55°) ≈ 0.574 as average for UK:
    # - lon_delta ≈ 2 / (111 * 0.574) ≈ 0.031 degrees

    lat_delta = 2.0 / 111.0  # ~0.018 degrees
    lon_delta = 2.0 / (
        111.0 * math.cos(math.radians(trig_lat))
    )  # Adjusted for latitude

    min_lat = trig_lat - lat_delta
    max_lat = trig_lat + lat_delta
    min_lon = trig_lon - lon_delta
    max_lon = trig_lon + lon_delta

    sql = text(
        """
        SELECT
            code,
            ST_Distance_Sphere(
                POINT(:trig_lon, :trig_lat),
                POINT(`long`, `lat`)
            ) AS distance_m
        FROM postcodes
        WHERE `lat` BETWEEN :min_lat AND :max_lat
          AND `long` BETWEEN :min_lon AND :max_lon
          AND `lat` BETWEEN -90 AND 90
          AND `long` BETWEEN -180 AND 180
        ORDER BY distance_m
        LIMIT 1
        """
    )

    result = db.execute(
        sql,
        {
            "trig_lat": trig_lat,
            "trig_lon": trig_lon,
            "min_lat": min_lat,
            "max_lat": max_lat,
            "min_lon": min_lon,
            "max_lon": max_lon,
        },
    ).fetchone()

    if result:
        return (result[0], float(result[1]))
    return None


def update_trig_postcodes():
    """Update all trig postcodes based on nearest postcode."""
    engine = get_engine()
    SessionLocal = get_session_local()
    db = SessionLocal()

    try:
        # 1. Add spatial index for performance (if it doesn't already exist)
        print("Checking for spatial index on postcodes table...")
        with engine.connect() as conn:
            # Check if index exists
            result = conn.execute(
                text(
                    "SELECT COUNT(*) as cnt FROM information_schema.statistics "
                    "WHERE table_schema = DATABASE() "
                    "AND table_name = 'postcodes' "
                    "AND index_name = 'idx_postcodes_spatial'"
                )
            )
            index_exists = result.fetchone()[0] > 0

            if not index_exists:
                print("Creating spatial index...")
                conn.execute(
                    text("CREATE INDEX idx_postcodes_spatial ON postcodes(lat, `long`)")
                )
                conn.commit()
                print("Spatial index created.\n")
            else:
                print("Spatial index already exists.\n")

        # 2. Get all trigs
        trigs = db.query(Trig).all()
        total = len(trigs)
        print(f"Found {total:,} trig records to process.\n")

        # 3. Process each trig
        updated_count = 0
        set_null_count = 0

        for i, trig in enumerate(trigs, 1):
            result = find_nearest_postcode(
                db, float(trig.wgs_lat), float(trig.wgs_long)
            )

            if result:
                postcode_code, distance = result

                if distance <= 1000:
                    # Update to nearest postcode
                    trig.postcode = postcode_code
                    updated_count += 1
                else:
                    # Too far, set to NULL
                    trig.postcode = None
                    set_null_count += 1
            else:
                # No postcodes found (shouldn't happen)
                trig.postcode = None
                set_null_count += 1

            # Commit every 10 rows
            if i % 10 == 0:
                db.commit()
                print(
                    f"Progress: {i:,}/{total:,} ({100 * i / total:.1f}%) - "
                    f"Updated: {updated_count}, Set NULL: {set_null_count}"
                )

        # Final commit
        db.commit()

        print("\n✓ Update complete!")
        print(f"  Total processed: {total:,}")
        print(f"  Updated with postcode: {updated_count:,}")
        print(f"  Set to NULL (>1000m): {set_null_count:,}")

    except Exception as e:
        db.rollback()
        print(f"✗ Error: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    update_trig_postcodes()

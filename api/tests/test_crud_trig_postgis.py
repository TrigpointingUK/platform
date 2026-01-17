"""
Tests for PostGIS spatial functionality in trig CRUD operations.

Tests ST_Distance ordering and ST_DWithin filtering in list_trigs_filtered
and count_trigs_filtered. These tests require PostgreSQL with PostGIS.
"""

import uuid
from datetime import date, time
from decimal import Decimal

import pytest
from geoalchemy2.functions import ST_MakePoint, ST_SetSRID
from sqlalchemy.orm import Session

from api.crud.trig import (
    _is_sqlite,
    count_trigs_filtered,
    list_trigs_filtered,
)
from api.models.trig import Trig


def skip_if_sqlite(db: Session):
    """Skip test if database is SQLite (no PostGIS support)."""
    if _is_sqlite(db):
        pytest.skip("Test requires PostgreSQL with PostGIS")


@pytest.fixture
def seed_trigs_with_locations(db: Session):
    """Seed trigs with PostGIS location column populated.

    Creates trigs at known distances from a center point (London).
    Center: 51.5074, -0.1278 (London)
    - Trig 1: ~10km away (51.5974, -0.1278)
    - Trig 2: ~50km away (51.9574, -0.1278)
    - Trig 3: ~100km away (52.4074, -0.1278)
    - Trig 4: ~200km away (53.3074, -0.1278)
    """
    skip_if_sqlite(db)

    base_id = abs(hash(uuid.uuid4().hex[:8])) % 5000 + 20000

    # Center point (London)
    center_lat = 51.5074
    center_lon = -0.1278

    # Create trigs at increasing distances (north of London)
    # Approximate: 1 degree latitude ≈ 111km
    trig_data = [
        ("Close Trig", center_lat + 0.09, center_lon),  # ~10km
        ("Medium Trig", center_lat + 0.45, center_lon),  # ~50km
        ("Far Trig", center_lat + 0.90, center_lon),  # ~100km
        ("Very Far Trig", center_lat + 1.80, center_lon),  # ~200km
    ]

    trigs = []
    for i, (name, lat, lon) in enumerate(trig_data):
        # Create PostGIS geography point using ST_MakePoint
        location = ST_SetSRID(ST_MakePoint(lon, lat), 4326)

        trig = Trig(
            waypoint=f"P{base_id + i}"[:8],
            name=name,
            fb_number=f"FB{base_id + i}",
            stn_number=f"STN{base_id + i}",
            status_id=10,
            user_added=0,
            current_use="Passive station",
            historic_use="Primary",
            physical_type="Pillar",
            wgs_lat=Decimal(str(lat)),
            wgs_long=Decimal(str(lon)),
            wgs_height=100,
            location=location,
            osgb_eastings=530000 + i * 10000,
            osgb_northings=180000 + i * 10000,
            osgb_gridref=f"TQ {30000 + i * 10000} 80000",
            osgb_height=95,
            condition="G",
            county="London",
            town="Westminster",
            permission_ind="Y",
            needs_attention=0,
            attention_comment="",
            crt_date=date(2023, 1, 1),
            crt_time=time(12, 0, 0),
            crt_ip_addr="127.0.0.1",
        )
        trigs.append(trig)

    db.add_all(trigs)
    db.flush()

    return {
        "trigs": trigs,
        "center_lat": center_lat,
        "center_lon": center_lon,
        "base_id": base_id,
    }


class TestPostgisDistanceOrdering:
    """Tests for PostGIS ST_Distance ordering in list_trigs_filtered."""

    def test_results_ordered_by_distance(self, db: Session, seed_trigs_with_locations):
        """Results are ordered by ST_Distance from center point."""
        skip_if_sqlite(db)
        data = seed_trigs_with_locations

        result = list_trigs_filtered(
            db,
            center_lat=data["center_lat"],
            center_lon=data["center_lon"],
            order="distance",
            limit=100,
        )

        # Get only our seeded trigs
        seeded_ids = [t.id for t in data["trigs"]]
        our_trigs = [t for t in result if t.id in seeded_ids]

        # Should be ordered by distance (closest first)
        assert len(our_trigs) >= 4
        names = [str(t.name) for t in our_trigs]

        # Close should come before Far
        close_idx = names.index("Close Trig")
        far_idx = names.index("Far Trig")
        assert close_idx < far_idx

    def test_distance_ordering_is_default(self, db: Session, seed_trigs_with_locations):
        """When center coordinates provided, default ordering is by distance."""
        skip_if_sqlite(db)
        data = seed_trigs_with_locations

        # Without explicit order parameter
        result = list_trigs_filtered(
            db,
            center_lat=data["center_lat"],
            center_lon=data["center_lon"],
            limit=100,
        )

        seeded_ids = [t.id for t in data["trigs"]]
        our_trigs = [t for t in result if t.id in seeded_ids]

        names = [str(t.name) for t in our_trigs]
        close_idx = names.index("Close Trig")
        medium_idx = names.index("Medium Trig")
        assert close_idx < medium_idx


class TestPostgisMaxKmFilter:
    """Tests for PostGIS ST_DWithin filtering in list_trigs_filtered."""

    def test_filters_by_max_km(self, db: Session, seed_trigs_with_locations):
        """ST_DWithin filters correctly by max_km."""
        skip_if_sqlite(db)
        data = seed_trigs_with_locations

        # Get trigs within 30km (should include Close trig only)
        result = list_trigs_filtered(
            db,
            center_lat=data["center_lat"],
            center_lon=data["center_lon"],
            max_km=30.0,
            limit=100,
        )

        seeded_ids = [t.id for t in data["trigs"]]
        our_trigs = [t for t in result if t.id in seeded_ids]
        names = [t.name for t in our_trigs]

        # Close trig (~10km) should be included
        assert "Close Trig" in names
        # Far trig (~100km) should NOT be included
        assert "Far Trig" not in names
        assert "Very Far Trig" not in names

    def test_larger_radius_includes_more(self, db: Session, seed_trigs_with_locations):
        """Larger max_km includes more trigs."""
        skip_if_sqlite(db)
        data = seed_trigs_with_locations

        # 30km radius
        small_result = list_trigs_filtered(
            db,
            center_lat=data["center_lat"],
            center_lon=data["center_lon"],
            max_km=30.0,
            limit=100,
        )

        # 150km radius
        large_result = list_trigs_filtered(
            db,
            center_lat=data["center_lat"],
            center_lon=data["center_lon"],
            max_km=150.0,
            limit=100,
        )

        # Larger radius should include more trigs
        assert len(large_result) > len(small_result)

    def test_zero_km_returns_nothing(self, db: Session, seed_trigs_with_locations):
        """max_km=0 returns no results (nothing at exact point)."""
        skip_if_sqlite(db)
        data = seed_trigs_with_locations

        result = list_trigs_filtered(
            db,
            center_lat=data["center_lat"],
            center_lon=data["center_lon"],
            max_km=0.0,
            limit=100,
        )

        # Filter our seeded trigs
        seeded_ids = [t.id for t in data["trigs"]]
        our_trigs = [t for t in result if t.id in seeded_ids]

        # None of our trigs should be at exactly the center
        assert len(our_trigs) == 0


class TestPostgisCountWithMaxKm:
    """Tests for count_trigs_filtered with PostGIS spatial filtering."""

    def test_count_uses_spatial_filter(self, db: Session, seed_trigs_with_locations):
        """Count uses ST_DWithin when max_km provided."""
        skip_if_sqlite(db)
        data = seed_trigs_with_locations

        # Count within 30km
        small_count = count_trigs_filtered(
            db,
            center_lat=data["center_lat"],
            center_lon=data["center_lon"],
            max_km=30.0,
        )

        # Count within 150km
        large_count = count_trigs_filtered(
            db,
            center_lat=data["center_lat"],
            center_lon=data["center_lon"],
            max_km=150.0,
        )

        # Larger radius should have higher count
        assert large_count > small_count

    def test_count_matches_list_length(self, db: Session, seed_trigs_with_locations):
        """Count matches the length of list results."""
        skip_if_sqlite(db)
        data = seed_trigs_with_locations

        max_km = 75.0  # Should include Close and Medium trigs

        list_result = list_trigs_filtered(
            db,
            center_lat=data["center_lat"],
            center_lon=data["center_lon"],
            max_km=max_km,
            limit=10000,
        )

        count_result = count_trigs_filtered(
            db,
            center_lat=data["center_lat"],
            center_lon=data["center_lon"],
            max_km=max_km,
        )

        assert count_result == len(list_result)


class TestPostgisCombinedFilters:
    """Tests for combining PostGIS with other filters."""

    def test_distance_combined_with_status(
        self, db: Session, seed_trigs_with_locations
    ):
        """Distance filtering works with status_id filter."""
        skip_if_sqlite(db)
        data = seed_trigs_with_locations

        # All our trigs have status_id=10
        result = list_trigs_filtered(
            db,
            center_lat=data["center_lat"],
            center_lon=data["center_lon"],
            max_km=150.0,
            status_ids=[10],
            limit=100,
        )

        seeded_ids = [t.id for t in data["trigs"]]
        our_trigs = [t for t in result if t.id in seeded_ids]

        # Should include our seeded trigs (Close, Medium, Far)
        assert len(our_trigs) >= 3

    def test_distance_combined_with_name(self, db: Session, seed_trigs_with_locations):
        """Distance filtering works with name filter."""
        skip_if_sqlite(db)
        data = seed_trigs_with_locations

        result = list_trigs_filtered(
            db,
            center_lat=data["center_lat"],
            center_lon=data["center_lon"],
            max_km=150.0,
            name="Close",
            limit=100,
        )

        seeded_ids = [t.id for t in data["trigs"]]
        our_trigs = [t for t in result if t.id in seeded_ids]

        # Should only include Close Trig
        assert len(our_trigs) == 1
        assert our_trigs[0].name == "Close Trig"

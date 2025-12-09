"""
Tests for cache_service module.
"""

import json
from datetime import date, datetime

from api.services.cache_service import CacheKeyEncoder


class TestCacheKeyEncoder:
    """Tests for CacheKeyEncoder class."""

    def test_encodes_date_to_iso_string(self):
        """Test that date objects are encoded to ISO format strings."""
        test_date = date(2024, 6, 15)
        result = json.dumps({"date": test_date}, cls=CacheKeyEncoder)
        assert result == '{"date": "2024-06-15"}'

    def test_encodes_datetime_to_iso_string(self):
        """Test that datetime objects are encoded to ISO format strings."""
        test_datetime = datetime(2024, 6, 15, 10, 30, 45)
        result = json.dumps({"datetime": test_datetime}, cls=CacheKeyEncoder)
        assert result == '{"datetime": "2024-06-15T10:30:45"}'

    def test_handles_regular_types(self):
        """Test that regular JSON types still work."""
        data = {"string": "hello", "number": 42, "bool": True, "null": None}
        result = json.dumps(data, cls=CacheKeyEncoder, sort_keys=True)
        assert result == '{"bool": true, "null": null, "number": 42, "string": "hello"}'

    def test_handles_mixed_types_with_date(self):
        """Test encoding mixed data including date objects."""
        data = {
            "from_date": date(2024, 1, 1),
            "to_date": date(2024, 12, 31),
            "limit": 20,
        }
        result = json.dumps(data, cls=CacheKeyEncoder, sort_keys=True)
        assert '"from_date": "2024-01-01"' in result
        assert '"to_date": "2024-12-31"' in result
        assert '"limit": 20' in result

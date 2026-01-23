"""Tests for condition mapping utilities."""

from unittest.mock import MagicMock, patch

from api.utils.condition_mapping import (
    FALLBACK_CONDITION_MAP,
    build_condition_map_from_db,
    get_condition_counts_by_description,
    get_condition_description,
)


class TestFallbackConditionMap:
    """Tests for the fallback condition mapping."""

    def test_fallback_map_contains_all_expected_codes(self):
        """Fallback map should contain all standard condition codes."""
        expected_codes = [
            "Z",
            "N",
            "G",
            "S",
            "C",
            "D",
            "R",
            "T",
            "M",
            "Q",
            "X",
            "V",
            "P",
            "U",
        ]
        for code in expected_codes:
            assert code in FALLBACK_CONDITION_MAP

    def test_fallback_map_has_human_readable_names(self):
        """Fallback map values should be human-readable strings."""
        for code, name in FALLBACK_CONDITION_MAP.items():
            assert isinstance(name, str)
            assert len(name) > 0
            # Names should be title case or sentence case
            assert name[0].isupper() or name[0].isalpha()


class TestGetConditionDescription:
    """Tests for get_condition_description function."""

    def test_returns_fallback_without_db(self):
        """Should return fallback value when no db provided."""
        assert get_condition_description("G") == "Good"
        assert get_condition_description("D") == "Damaged"
        assert get_condition_description("X") == "Destroyed"

    def test_handles_lowercase_codes(self):
        """Should handle lowercase condition codes."""
        assert get_condition_description("g") == "Good"
        assert get_condition_description("d") == "Damaged"

    def test_returns_unknown_for_invalid_codes(self):
        """Should return 'Unknown' for unrecognised codes."""
        assert get_condition_description("INVALID") == "Unknown"
        assert get_condition_description("123") == "Unknown"
        assert get_condition_description("") == "Unknown"

    def test_uses_db_when_provided(self):
        """Should use database lookup when db session provided."""
        mock_db = MagicMock()

        with patch("api.crud.condition.get_condition_name_by_code") as mock_get:
            mock_get.return_value = "Database Value"

            result = get_condition_description("G", mock_db)

            assert result == "Database Value"
            mock_get.assert_called_once_with(mock_db, "G")

    def test_falls_back_when_db_returns_none(self):
        """Should fall back to hardcoded when db returns None."""
        mock_db = MagicMock()

        with patch("api.crud.condition.get_condition_name_by_code") as mock_get:
            mock_get.return_value = None

            result = get_condition_description("G", mock_db)

            assert result == "Good"  # Fallback value

    def test_all_standard_codes_have_descriptions(self):
        """All standard codes should have non-Unknown descriptions."""
        standard_codes = [
            "Z",
            "N",
            "G",
            "S",
            "C",
            "D",
            "R",
            "T",
            "M",
            "Q",
            "X",
            "V",
            "P",
        ]
        for code in standard_codes:
            result = get_condition_description(code)
            assert result != "Unknown", f"Code {code} should have a description"


class TestGetConditionCountsByDescription:
    """Tests for get_condition_counts_by_description function."""

    def test_converts_codes_to_descriptions(self):
        """Should convert condition codes to human-readable descriptions."""
        counts = {"G": 10, "D": 5, "X": 2}

        result = get_condition_counts_by_description(counts)

        assert result == {"Good": 10, "Damaged": 5, "Destroyed": 2}

    def test_handles_empty_dict(self):
        """Should handle empty input."""
        result = get_condition_counts_by_description({})
        assert result == {}

    def test_combines_duplicate_descriptions(self):
        """Should combine counts when codes map to same description."""
        # Using lowercase which .upper() should normalise
        counts = {"G": 10, "g": 5}

        result = get_condition_counts_by_description(counts)

        assert "Good" in result
        assert result["Good"] == 15

    def test_handles_unknown_codes(self):
        """Should handle unknown codes gracefully."""
        counts = {"G": 10, "UNKNOWN": 3}

        result = get_condition_counts_by_description(counts)

        assert result["Good"] == 10
        assert result["Unknown"] == 3

    def test_uses_db_when_provided(self):
        """Should use database for lookups when db provided."""
        mock_db = MagicMock()
        counts = {"G": 10, "D": 5}

        with patch("api.crud.condition.get_condition_name_by_code") as mock_get:
            mock_get.side_effect = lambda db, code: f"DB-{code}"

            result = get_condition_counts_by_description(counts, mock_db)

            assert result == {"DB-G": 10, "DB-D": 5}

    def test_preserves_count_values(self):
        """Should preserve exact count values."""
        counts = {"G": 1000000, "D": 0, "X": 1}

        result = get_condition_counts_by_description(counts)

        assert result["Good"] == 1000000
        assert result["Damaged"] == 0
        assert result["Destroyed"] == 1


class TestBuildConditionMapFromDb:
    """Tests for build_condition_map_from_db function."""

    def test_builds_map_from_conditions(self):
        """Should build a code->name map from database conditions."""
        mock_db = MagicMock()

        # Create mock condition objects with spec to make str() work properly
        class MockCondition:
            def __init__(self, code: str, name: str):
                self.code = code
                self.name = name

        mock_conditions = [
            MockCondition("G", "Good"),
            MockCondition("D", "Damaged"),
            MockCondition("X", "Destroyed"),
        ]

        with patch("api.crud.condition.get_all_conditions") as mock_get:
            mock_get.return_value = mock_conditions

            result = build_condition_map_from_db(mock_db)

            assert result == {"G": "Good", "D": "Damaged", "X": "Destroyed"}
            mock_get.assert_called_once_with(mock_db)

    def test_handles_empty_conditions(self):
        """Should return empty dict when no conditions in db."""
        mock_db = MagicMock()

        with patch("api.crud.condition.get_all_conditions") as mock_get:
            mock_get.return_value = []

            result = build_condition_map_from_db(mock_db)

            assert result == {}


class TestConditionMappingIntegration:
    """Integration tests for condition mapping with actual database."""

    def test_get_condition_description_with_real_db(self, db):
        """Test with actual database (if conditions exist)."""
        from api.crud.condition import get_all_conditions

        conditions = get_all_conditions(db)

        if conditions:
            # If there are conditions in the db, test with one
            first_condition = conditions[0]
            result = get_condition_description(str(first_condition.code), db)
            assert result == str(first_condition.name)
        else:
            # If no conditions, should fall back
            result = get_condition_description("G", db)
            assert result == "Good"

    def test_get_condition_counts_with_real_db(self, db):
        """Test counts conversion with actual database."""
        counts = {"G": 10, "D": 5}

        result = get_condition_counts_by_description(counts, db)

        # Should have converted the codes
        assert len(result) == 2
        # Values should be preserved
        assert sum(result.values()) == 15

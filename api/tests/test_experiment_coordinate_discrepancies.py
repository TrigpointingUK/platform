"""
Tests for the coordinate discrepancies experiment endpoint.

Tests cover:
- dist_wgs_original column in CoordinateDiscrepancyItem schema
- Sorting field enum includes dist_wgs_original
"""

# ============================================================================
# Schema Tests
# ============================================================================


class TestCoordinateDiscrepancySchema:
    """Tests for CoordinateDiscrepancyItem schema."""

    def test_schema_includes_dist_wgs_original(self):
        """Test that CoordinateDiscrepancyItem schema includes dist_wgs_original."""
        from api.api.v1.endpoints.experiment import CoordinateDiscrepancyItem

        schema = CoordinateDiscrepancyItem.model_json_schema()
        properties = schema["properties"]

        assert "dist_wgs_original" in properties
        # Should be a number type (nullable)
        prop = properties["dist_wgs_original"]
        assert prop.get("type") == "number" or "anyOf" in prop

    def test_sort_field_includes_dist_wgs_original(self):
        """Test that CoordinateDiscrepancySortField includes dist_wgs_original."""
        from api.api.v1.endpoints.experiment import CoordinateDiscrepancySortField

        assert hasattr(CoordinateDiscrepancySortField, "dist_wgs_original")
        assert (
            CoordinateDiscrepancySortField.dist_wgs_original.value
            == "dist_wgs_original"
        )

    def test_sort_field_enum_values(self):
        """Test that all expected sort fields are present."""
        from api.api.v1.endpoints.experiment import CoordinateDiscrepancySortField

        # Verify the enum has all expected values
        expected_fields = [
            "waypoint",
            "dist_wgs_osgb",
            "dist_osgb_osgb",
            "dist_wgs_original",
        ]

        for field in expected_fields:
            assert hasattr(CoordinateDiscrepancySortField, field)

    def test_coordinate_discrepancy_item_fields(self):
        """Test that CoordinateDiscrepancyItem has all required fields."""
        from api.api.v1.endpoints.experiment import CoordinateDiscrepancyItem

        schema = CoordinateDiscrepancyItem.model_json_schema()
        properties = schema["properties"]

        # Core fields
        assert "trig_id" in properties
        assert "waypoint" in properties
        assert "name" in properties
        assert "condition" in properties

        # Distance fields
        assert "dist_wgs_osgb" in properties
        assert "dist_osgb_osgb" in properties
        assert "dist_wgs_original" in properties

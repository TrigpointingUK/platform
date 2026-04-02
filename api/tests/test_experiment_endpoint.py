"""
Tests for the experiment endpoints (coordinate discrepancies, survey timeline).
"""

from api.api.v1.endpoints.experiment import (
    CoordinateDiscrepancyItem,
    CoordinateDiscrepancyResponse,
    CoordinateDiscrepancySortField,
    MovedFilter,
)


class TestPydanticModels:
    def test_coordinate_discrepancy_item_optional_fields(self):
        item = CoordinateDiscrepancyItem(
            trig_id=1,
            waypoint="TP1234",
            name="Test",
            condition="G",
            condition_name="Good",
            condition_icon="c_good.png",
        )
        assert item.dist_wgs_osgb is None
        assert item.dist_osgb_osgb is None
        assert item.dist_wgs_original is None

    def test_coordinate_discrepancy_response(self):
        resp = CoordinateDiscrepancyResponse(
            items=[], total=0, page=1, per_page=50, total_pages=1
        )
        assert resp.total == 0

    def test_sort_field_enum(self):
        assert CoordinateDiscrepancySortField.waypoint == "waypoint"
        assert CoordinateDiscrepancySortField.dist_wgs_osgb == "dist_wgs_osgb"

    def test_moved_filter_enum(self):
        assert MovedFilter.all == "all"
        assert MovedFilter.exclude_moved == "exclude_moved"
        assert MovedFilter.only_moved == "only_moved"


class TestSurveyTimelineEndpoint:
    def test_returns_list(self, client, db):
        resp = client.get("/v1/experiment/survey-timeline")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestCoordinateDiscrepanciesEndpoint:
    def test_returns_paginated_response(self, client, db, make_trig):
        make_trig()
        resp = client.get("/v1/experiment/coordinate-discrepancies")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert data["page"] == 1

    def test_custom_pagination(self, client, db, make_trig):
        make_trig()
        resp = client.get("/v1/experiment/coordinate-discrepancies?page=1&per_page=5")
        assert resp.status_code == 200
        assert resp.json()["per_page"] == 5

    def test_sort_by_waypoint(self, client, db, make_trig):
        make_trig()
        resp = client.get(
            "/v1/experiment/coordinate-discrepancies?sort_by=waypoint&sort_order=asc"
        )
        assert resp.status_code == 200

    def test_exclude_irish_filter(self, client, db, make_trig):
        make_trig()
        resp = client.get("/v1/experiment/coordinate-discrepancies?exclude_irish=true")
        assert resp.status_code == 200

    def test_moved_filter_exclude(self, client, db, make_trig):
        make_trig()
        resp = client.get(
            "/v1/experiment/coordinate-discrepancies?moved_filter=exclude_moved"
        )
        assert resp.status_code == 200

    def test_moved_filter_only_moved(self, client, db, make_trig):
        make_trig()
        resp = client.get(
            "/v1/experiment/coordinate-discrepancies?moved_filter=only_moved"
        )
        assert resp.status_code == 200

    def test_min_threshold_filters(self, client, db, make_trig):
        make_trig()
        resp = client.get(
            "/v1/experiment/coordinate-discrepancies?min_dist_wgs_osgb=100&min_dist_osgb_osgb=50"
        )
        assert resp.status_code == 200

    def test_empty_result_has_one_page(self, client, db):
        resp = client.get(
            "/v1/experiment/coordinate-discrepancies?min_dist_wgs_osgb=99999999"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_pages"] >= 1

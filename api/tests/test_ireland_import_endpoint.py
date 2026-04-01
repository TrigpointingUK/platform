"""
Tests for the Ireland import admin endpoints.
"""

from unittest.mock import MagicMock, patch


class TestIrelandImportComparisonEndpoint:
    @patch("api.api.v1.endpoints.ireland_import_admin.compare_ireland_csv_with_db")
    def test_returns_comparison(self, mock_compare, client, make_user):
        make_user(auth0_user_id="auth0|admin")
        mock_result = MagicMock()
        mock_result.items = []
        mock_result.csv_count = 100
        mock_result.db_irish_count = 95
        mock_result.matched_identical_count = 80
        mock_result.matched_different_count = 10
        mock_result.ambiguous_count = 2
        mock_result.new_in_csv_count = 8
        mock_result.orphan_in_db_count = 5
        mock_result.non_irish_gridref_count = 3
        mock_compare.return_value = mock_result

        resp = client.get(
            "/v1/admin/ireland-import/comparison",
            headers={"Authorization": "Bearer auth0_admin"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["csv_count"] == 100
        assert data["matched_identical_count"] == 80
        assert data["new_in_csv_count"] == 8

    def test_requires_admin_auth(self, client):
        resp = client.get("/v1/admin/ireland-import/comparison")
        assert resp.status_code in (401, 403)

    @patch("api.api.v1.endpoints.ireland_import_admin.compare_ireland_csv_with_db")
    def test_handles_service_error(self, mock_compare, client, make_user):
        make_user(auth0_user_id="auth0|admin")
        mock_compare.side_effect = RuntimeError("CSV file not found")
        resp = client.get(
            "/v1/admin/ireland-import/comparison",
            headers={"Authorization": "Bearer auth0_admin"},
        )
        assert resp.status_code == 500

    @patch("api.api.v1.endpoints.ireland_import_admin.compare_ireland_csv_with_db")
    def test_comparison_with_items(self, mock_compare, client, make_user):
        make_user(auth0_user_id="auth0|admin")

        mock_csv_row = MagicMock()
        mock_csv_row.row_index = 0
        mock_csv_row.station_name = "Test Station"
        mock_csv_row.osi_ni_no = "123"
        mock_csv_row.eastings = 100000
        mock_csv_row.northings = 200000
        mock_csv_row.height = 50.0
        mock_csv_row.fb_sort = "P"
        mock_csv_row.fb_number = "FB123"
        mock_csv_row.date_built = "1950"
        mock_csv_row.order = "1"
        mock_csv_row.dr = ""
        mock_csv_row.grid_ref = "I 000 000"
        mock_csv_row.notes = ""

        mock_item = MagicMock()
        mock_item.category = "new_in_csv"
        mock_item.csv_row = mock_csv_row
        mock_item.db_trig = None
        mock_item.additional_db_matches = []
        mock_item.differences = []
        mock_item.distance_metres = None
        mock_item.description = "No match found"

        mock_result = MagicMock()
        mock_result.items = [mock_item]
        mock_result.csv_count = 1
        mock_result.db_irish_count = 0
        mock_result.matched_identical_count = 0
        mock_result.matched_different_count = 0
        mock_result.ambiguous_count = 0
        mock_result.new_in_csv_count = 1
        mock_result.orphan_in_db_count = 0
        mock_result.non_irish_gridref_count = 0
        mock_compare.return_value = mock_result

        resp = client.get(
            "/v1/admin/ireland-import/comparison",
            headers={"Authorization": "Bearer auth0_admin"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["category"] == "new_in_csv"


class TestApplyCsvToTrig:
    @patch("api.api.v1.endpoints.ireland_import_admin.get_csv_row_by_index")
    @patch("api.api.v1.endpoints.ireland_import_admin.build_trig_data_from_csv")
    @patch("api.api.v1.endpoints.ireland_import_admin.trig_crud")
    @patch("api.api.v1.endpoints.ireland_import_admin.location_crud")
    @patch("api.api.v1.endpoints.ireland_import_admin.invalidate_trig_caches")
    def test_apply_success(
        self,
        mock_invalidate,
        mock_loc_crud,
        mock_trig_crud,
        mock_build,
        mock_get_csv,
        client,
        make_user,
        make_trig,
    ):
        make_user(auth0_user_id="auth0|admin")
        trig = make_trig()

        mock_csv_row = MagicMock()
        mock_csv_row.station_name = "Test Station"
        mock_get_csv.return_value = mock_csv_row
        mock_build.return_value = {
            "name": "Test Station",
            "fb_number": "FB123",
            "stn_number": "STN456",
            "historic_use": "Primary",
            "condition": "G",
            "wgs_lat": 53.0,
            "wgs_long": -6.0,
            "original_osgb_eastings": 100000,
            "original_osgb_northings": 200000,
            "original_osgb_gridref": "I 000 000",
            "original_osgb_height": 50,
            "original_wgs_lat": 53.0,
            "original_wgs_long": -6.0,
            "original_wgs_height": 50,
            "original_grid_system": "ie",
            "original_provenance": "ireland25",
        }
        mock_trig_crud.get_trig_by_id.return_value = trig
        mock_trig_crud.update_trig_admin.return_value = trig
        mock_loc_crud.find_nearest_postcode.return_value = None

        resp = client.post(
            f"/v1/admin/ireland-import/apply/{trig.id}",
            json={"csv_row_index": 0, "admin_comment": "Test apply"},
            headers={"Authorization": "Bearer auth0_admin"},
        )
        assert resp.status_code == 200

    @patch("api.api.v1.endpoints.ireland_import_admin.trig_crud")
    def test_apply_trig_not_found(self, mock_trig_crud, client, make_user):
        make_user(auth0_user_id="auth0|admin")
        mock_trig_crud.get_trig_by_id.return_value = None
        resp = client.post(
            "/v1/admin/ireland-import/apply/999999",
            json={"csv_row_index": 0, "admin_comment": "Test"},
            headers={"Authorization": "Bearer auth0_admin"},
        )
        assert resp.status_code == 404

    @patch("api.api.v1.endpoints.ireland_import_admin.trig_crud")
    @patch("api.api.v1.endpoints.ireland_import_admin.get_csv_row_by_index")
    def test_apply_csv_row_not_found(
        self, mock_get_csv, mock_trig_crud, client, make_user, make_trig
    ):
        make_user(auth0_user_id="auth0|admin")
        trig = make_trig()
        mock_trig_crud.get_trig_by_id.return_value = trig
        mock_get_csv.return_value = None
        resp = client.post(
            f"/v1/admin/ireland-import/apply/{trig.id}",
            json={"csv_row_index": 9999, "admin_comment": "Test"},
            headers={"Authorization": "Bearer auth0_admin"},
        )
        assert resp.status_code == 404


class TestCreateTrigFromCsv:
    @patch("api.api.v1.endpoints.ireland_import_admin.get_csv_row_by_index")
    def test_csv_row_not_found(self, mock_get_csv, client, make_user):
        make_user(auth0_user_id="auth0|admin")
        mock_get_csv.return_value = None
        resp = client.post(
            "/v1/admin/ireland-import/create",
            json={"csv_row_index": 9999, "admin_comment": "Test"},
            headers={"Authorization": "Bearer auth0_admin"},
        )
        assert resp.status_code == 404

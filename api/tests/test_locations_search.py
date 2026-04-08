"""
Tests for the /v1/locations search endpoints.

Tests location search across multiple sources including trigpoints,
places, users, postcodes, coordinates, and log text.
"""

import uuid
from datetime import date, time

import pytest
from fastapi.testclient import TestClient

from api.models.location import Postcode, Town
from api.models.trig import Trig
from api.models.user import TLog, User


@pytest.fixture
def location_search_data(db):
    """Create test data for location search tests."""
    unique_suffix = uuid.uuid4().hex[:6]

    # Create test user
    user = User(
        name=f"SearchTestUser_{unique_suffix}",
        firstname="Search",
        surname="Test",
        email=f"search_{unique_suffix}@example.invalid",
        cryptpw="",
        email_valid="Y",
        public_ind="Y",
    )
    db.add(user)
    db.flush()

    # Create test trigpoint with searchable name
    trig = Trig(
        waypoint=f"TP{unique_suffix[:4]}",
        name=f"SearchTestTrig_{unique_suffix}",
        fb_number=f"FB{unique_suffix[:4]}",
        stn_number=f"STN{unique_suffix[:4]}",
        stn_number_active=f"ACT{unique_suffix[:4]}",
        stn_number_passive=f"PAS{unique_suffix[:4]}",
        stn_number_osgb36=f"OSGB{unique_suffix[:4]}",
        status_id=1,
        user_added=0,
        current_use="Passive station",
        historic_use="Primary",
        condition="G",
        wgs_lat=51.5,
        wgs_long=-0.1,
        wgs_height=100,
        osgb_eastings=530000,
        osgb_northings=180000,
        osgb_gridref="TQ 30000 80000",
        osgb_height=100,
        town="Westminster",
        permission_ind="Y",
        needs_attention=0,
        attention_comment="",
        crt_date=date(2023, 1, 1),
        crt_time=time(0, 0, 0),
        crt_ip_addr="127.0.0.1",
    )
    db.add(trig)
    db.flush()

    # Create test town (all fields required)
    town = Town(
        name=f"SearchTestTown_{unique_suffix}",
        wgs_lat=52.0,
        wgs_long=-1.0,
        osgb_eastings=400000,
        osgb_northings=300000,
        osgb_gridref="SK 00000 00000",
    )
    db.add(town)

    # Create test postcode
    postcode = Postcode(
        code=f"XX{unique_suffix[:2]} {unique_suffix[2:4]}Y".upper(),
        lat=53.0,
        long=-2.0,
    )
    db.add(postcode)

    # Create test log with searchable comment
    log = TLog(
        trig_id=trig.id,
        user_id=user.id,
        date=date(2023, 12, 15),
        time=time(14, 30, 0),
        osgb_eastings=530000,
        osgb_northings=180000,
        osgb_gridref="TQ 30000 80000",
        fb_number="",
        condition="G",
        comment=f"SearchableLogComment_{unique_suffix} with unique text for testing",
        score=7,
        ip_addr="127.0.0.1",
        source="W",
    )
    db.add(log)

    db.commit()

    return {
        "user": user,
        "trig": trig,
        "town": town,
        "postcode": postcode,
        "log": log,
        "suffix": unique_suffix,
    }


class TestUnifiedSearch:
    """Tests for GET /v1/locations/search."""

    def test_search_returns_results(self, client: TestClient, location_search_data, db):
        """Test that unified search returns results."""
        suffix = location_search_data["suffix"]
        query = f"SearchTestTrig_{suffix}"

        response = client.get(f"/v1/locations/search?q={query}")

        assert response.status_code == 200
        data = response.json()

        # Should return a list
        assert isinstance(data, list)

        # Should find our test trig
        trig_results = [r for r in data if r["type"] == "trigpoint"]
        assert len(trig_results) > 0
        assert any(query in r["name"] for r in trig_results)

    def test_search_by_waypoint(self, client: TestClient, location_search_data, db):
        """Test search by waypoint code."""
        suffix = location_search_data["suffix"][:4]
        query = f"TP{suffix}"

        response = client.get(f"/v1/locations/search?q={query}")

        assert response.status_code == 200
        data = response.json()

        # Should find results with waypoint
        assert len(data) > 0

    def test_search_by_gridref(self, client: TestClient, db):
        """Test search with grid reference."""
        response = client.get("/v1/locations/search?q=TQ300800")

        assert response.status_code == 200
        data = response.json()

        # Should find a gridref result
        gridref_results = [r for r in data if r["type"] == "gridref"]
        assert len(gridref_results) > 0

    def test_search_by_latlon(self, client: TestClient, db):
        """Test search with lat/lon coordinates."""
        response = client.get("/v1/locations/search?q=51.5,-0.1")

        assert response.status_code == 200
        data = response.json()

        # Should find a latlon result
        latlon_results = [r for r in data if r["type"] == "latlon"]
        assert len(latlon_results) > 0
        assert latlon_results[0]["lat"] == 51.5

    def test_search_by_user(self, client: TestClient, location_search_data, db):
        """Test search finds users."""
        suffix = location_search_data["suffix"]
        query = f"SearchTestUser_{suffix}"

        response = client.get(f"/v1/locations/search?q={query}")

        assert response.status_code == 200
        data = response.json()

        # Should find user results
        user_results = [r for r in data if r["type"] == "user"]
        assert len(user_results) > 0
        assert any(query in r["name"] for r in user_results)

    def test_search_limit_parameter(self, client: TestClient, db):
        """Test limit parameter is respected."""
        response = client.get("/v1/locations/search?q=test&limit=2")

        assert response.status_code == 200
        data = response.json()

        # Should not exceed limit
        assert len(data) <= 2

    def test_search_min_query_length(self, client: TestClient, db):
        """Test minimum query length validation."""
        response = client.get("/v1/locations/search?q=a")

        assert response.status_code == 422  # Validation error


class TestSearchAll:
    """Tests for GET /v1/locations/search/all."""

    def test_search_all_returns_categories(
        self, client: TestClient, location_search_data, db
    ):
        """Test that search/all returns categorized results."""
        suffix = location_search_data["suffix"]
        query = f"SearchTest_{suffix}"

        response = client.get(f"/v1/locations/search/all?q={query}")

        assert response.status_code == 200
        data = response.json()

        # Check all categories are present
        assert "query" in data
        assert "trigpoints" in data
        assert "places" in data
        assert "users" in data
        assert "postcodes" in data
        assert "coordinates" in data
        assert "log_substring" in data
        assert "log_regex" in data

    def test_search_all_category_structure(
        self, client: TestClient, location_search_data, db
    ):
        """Test that each category has proper structure."""
        suffix = location_search_data["suffix"]
        query = f"SearchTestTrig_{suffix}"

        response = client.get(f"/v1/locations/search/all?q={query}")

        assert response.status_code == 200
        data = response.json()

        # Check trigpoints category structure
        trigpoints = data["trigpoints"]
        assert "total" in trigpoints
        assert "items" in trigpoints
        assert "has_more" in trigpoints
        assert "query" in trigpoints

    def test_search_all_with_coordinates(self, client: TestClient, db):
        """Test search/all finds coordinates."""
        response = client.get("/v1/locations/search/all?q=51.5,-0.1")

        assert response.status_code == 200
        data = response.json()

        # Should find coordinate results
        coordinates = data["coordinates"]
        assert len(coordinates["items"]) > 0
        assert coordinates["items"][0]["type"] == "latlon"

    def test_search_all_with_gridref(self, client: TestClient, db):
        """Test search/all finds grid references."""
        response = client.get("/v1/locations/search/all?q=TQ300800")

        assert response.status_code == 200
        data = response.json()

        # Should find coordinate results (gridref)
        coordinates = data["coordinates"]
        assert len(coordinates["items"]) > 0


class TestSearchTrigpointsOnly:
    """Tests for GET /v1/locations/search/trigpoints."""

    def test_search_trigpoints(self, client: TestClient, location_search_data, db):
        """Test dedicated trigpoint search."""
        suffix = location_search_data["suffix"]
        query = f"SearchTestTrig_{suffix}"

        response = client.get(f"/v1/locations/search/trigpoints?q={query}")

        assert response.status_code == 200
        data = response.json()

        assert "total" in data
        assert "items" in data
        assert "has_more" in data

        # Should find our trig
        assert any(query in item["name"] for item in data["items"])

    def test_search_trigpoints_pagination(self, client: TestClient, db):
        """Test trigpoint search pagination."""
        response = client.get("/v1/locations/search/trigpoints?q=test&skip=0&limit=5")

        assert response.status_code == 200
        data = response.json()

        # Should respect limit
        assert len(data["items"]) <= 5


class TestSearchStationNumbers:
    """Tests for GET /v1/locations/search/station-numbers."""

    def test_search_station_numbers(self, client: TestClient, location_search_data, db):
        """Test station number search."""
        suffix = location_search_data["suffix"][:4]
        query = f"FB{suffix}"

        response = client.get(f"/v1/locations/search/station-numbers?q={query}")

        assert response.status_code == 200
        data = response.json()

        assert "total" in data
        assert "items" in data

    def test_search_active_station(self, client: TestClient, location_search_data, db):
        """Test search by active station number."""
        suffix = location_search_data["suffix"][:4]
        query = f"ACT{suffix}"

        response = client.get(f"/v1/locations/search/station-numbers?q={query}")

        assert response.status_code == 200
        data = response.json()

        # Should find results
        assert "items" in data


class TestSearchPlaces:
    """Tests for GET /v1/locations/search/places."""

    def test_search_places(self, client: TestClient, location_search_data, db):
        """Test place/town search endpoint returns valid response structure."""
        # Test with a generic query - we're mainly testing the endpoint structure
        response = client.get("/v1/locations/search/places?q=London")

        assert response.status_code == 200
        data = response.json()

        assert "total" in data
        assert "items" in data
        assert "has_more" in data
        assert "query" in data

        # Verify any returned items have correct structure
        for item in data["items"]:
            assert item["type"] == "town"
            assert "name" in item
            assert "lat" in item
            assert "lon" in item

    def test_search_places_type(self, client: TestClient, location_search_data, db):
        """Test that place results have correct type."""
        suffix = location_search_data["suffix"]
        query = f"SearchTestTown_{suffix}"

        response = client.get(f"/v1/locations/search/places?q={query}")

        assert response.status_code == 200
        data = response.json()

        for item in data["items"]:
            assert item["type"] == "town"


class TestSearchUsers:
    """Tests for GET /v1/locations/search/users."""

    def test_search_users(self, client: TestClient, location_search_data, db):
        """Test user search."""
        suffix = location_search_data["suffix"]
        query = f"SearchTestUser_{suffix}"

        response = client.get(f"/v1/locations/search/users?q={query}")

        assert response.status_code == 200
        data = response.json()

        assert "total" in data
        assert "items" in data

        # Should find our user
        assert any(query in item["name"] for item in data["items"])

    def test_search_users_type(self, client: TestClient, location_search_data, db):
        """Test that user results have correct type."""
        suffix = location_search_data["suffix"]
        query = f"SearchTestUser_{suffix}"

        response = client.get(f"/v1/locations/search/users?q={query}")

        assert response.status_code == 200
        data = response.json()

        for item in data["items"]:
            assert item["type"] == "user"
            assert item["id"] is not None


class TestSearchPostcodes:
    """Tests for GET /v1/locations/search/postcodes."""

    def test_search_postcodes(self, client: TestClient, location_search_data, db):
        """Test postcode search."""
        suffix = location_search_data["suffix"]
        # Construct the postcode pattern we created
        query = f"XX{suffix[:2]}".upper()

        response = client.get(f"/v1/locations/search/postcodes?q={query}")

        assert response.status_code == 200
        data = response.json()

        assert "total" in data
        assert "items" in data

    def test_search_postcodes_type(self, client: TestClient, db):
        """Test that postcode results have correct type."""
        # Search for a pattern that might match existing postcodes
        response = client.get("/v1/locations/search/postcodes?q=SW1")

        assert response.status_code == 200
        data = response.json()

        for item in data["items"]:
            assert item["type"] == "postcode"


class TestSearchLogsSubstring:
    """Tests for GET /v1/locations/search/logs/substring."""

    def test_search_logs_substring(self, client: TestClient, location_search_data, db):
        """Test log substring search."""
        suffix = location_search_data["suffix"]
        query = f"SearchableLogComment_{suffix}"

        response = client.get(f"/v1/locations/search/logs/substring?q={query}")

        assert response.status_code == 200
        data = response.json()

        assert "total" in data
        assert "items" in data

        # Should find our log
        if data["total"] > 0:
            item = data["items"][0]
            assert "id" in item
            assert "trig_id" in item
            assert "comment" in item
            assert "comment_excerpt" in item

    def test_search_logs_substring_structure(
        self, client: TestClient, location_search_data, db
    ):
        """Test log search result structure."""
        suffix = location_search_data["suffix"]
        query = f"SearchableLogComment_{suffix}"

        response = client.get(f"/v1/locations/search/logs/substring?q={query}")

        assert response.status_code == 200
        data = response.json()

        if data["items"]:
            item = data["items"][0]
            assert "date" in item
            assert "time" in item
            assert "condition" in item
            assert "score" in item


class TestSearchLogsRegex:
    """Tests for GET /v1/locations/search/logs/regex."""

    def test_search_logs_regex_simple(
        self, client: TestClient, location_search_data, db
    ):
        """Test log regex search with simple pattern."""
        suffix = location_search_data["suffix"]
        # Use a regex pattern
        query = f"SearchableLogComment_{suffix[:4]}.*"

        response = client.get(f"/v1/locations/search/logs/regex?q={query}")

        assert response.status_code == 200
        data = response.json()

        assert "total" in data
        assert "items" in data

    def test_search_logs_regex_invalid_pattern(self, client: TestClient, db):
        """Test that invalid regex returns error."""
        # Invalid regex pattern with unmatched parenthesis
        response = client.get("/v1/locations/search/logs/regex?q=(invalid")

        # Should return 400 for invalid regex
        assert response.status_code == 400

    def test_search_logs_regex_with_groups(
        self, client: TestClient, location_search_data, db
    ):
        """Test log regex search with capture groups."""
        # Pattern with alternation
        response = client.get("/v1/locations/search/logs/regex?q=(test|unique)")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data


class TestSearchResultNewFields:
    """Tests for location, category_code, and town title-casing."""

    def test_trig_result_includes_location_field(
        self, client: TestClient, location_search_data, db
    ):
        """Test that trig search results include the location field."""
        suffix = location_search_data["suffix"]
        query = f"SearchTestTrig_{suffix}"

        response = client.get(f"/v1/locations/search?q={query}")

        assert response.status_code == 200
        data = response.json()
        trig_results = [r for r in data if r["type"] == "trigpoint"]
        assert len(trig_results) > 0

        item = trig_results[0]
        assert "location" in item
        # Trig was created with town="Westminster" so location should contain it
        assert item["location"] is not None
        assert "Westminster" in item["location"]

    def test_trig_result_includes_category_code(
        self, client: TestClient, location_search_data, db
    ):
        """Test that trig search results include category_code field."""
        suffix = location_search_data["suffix"]
        query = f"SearchTestTrig_{suffix}"

        response = client.get(f"/v1/locations/search?q={query}")

        assert response.status_code == 200
        data = response.json()
        trig_results = [r for r in data if r["type"] == "trigpoint"]
        assert len(trig_results) > 0
        # category_code should be present (may be None if no trig_type in test DB)
        assert "category_code" in trig_results[0]

    def test_trig_description_does_not_contain_town(
        self, client: TestClient, location_search_data, db
    ):
        """Test that trig description contains waypoint/type, not town."""
        suffix = location_search_data["suffix"]
        query = f"SearchTestTrig_{suffix}"

        response = client.get(f"/v1/locations/search?q={query}")

        assert response.status_code == 200
        data = response.json()
        trig_results = [r for r in data if r["type"] == "trigpoint"]
        assert len(trig_results) > 0

        item = trig_results[0]
        # Description should contain the waypoint
        assert f"TP{suffix[:4]}" in item["description"]
        # Town info should be in location, not description
        assert "Westminster" not in item["description"]

    def test_town_name_is_title_cased(
        self, client: TestClient, location_search_data, db
    ):
        """Test that town names in search results are title-cased."""
        suffix = location_search_data["suffix"]
        query = f"SearchTestTown_{suffix}"

        response = client.get(f"/v1/locations/search/places?q={query}")

        assert response.status_code == 200
        data = response.json()

        if data["items"]:
            name = data["items"][0]["name"]
            # Title case: first letter of each word capitalised
            assert name == name.title()

    def test_town_description_starts_with_uk_town(
        self, client: TestClient, location_search_data, db
    ):
        """Test that town descriptions start with 'UK Town'."""
        suffix = location_search_data["suffix"]
        query = f"SearchTestTown_{suffix}"

        response = client.get(f"/v1/locations/search/places?q={query}")

        assert response.status_code == 200
        data = response.json()

        if data["items"]:
            desc = data["items"][0]["description"]
            assert desc.startswith("UK Town")

    def test_search_all_trig_results_have_location_and_category(
        self, client: TestClient, location_search_data, db
    ):
        """Test search/all trig results include location and category_code."""
        suffix = location_search_data["suffix"]
        query = f"SearchTestTrig_{suffix}"

        response = client.get(f"/v1/locations/search/all?q={query}")

        assert response.status_code == 200
        data = response.json()

        trig_items = data["trigpoints"]["items"]
        assert len(trig_items) > 0
        assert "location" in trig_items[0]
        assert "category_code" in trig_items[0]

    def test_station_number_results_have_location_and_category(
        self, client: TestClient, location_search_data, db
    ):
        """Test station number results include location and category_code."""
        suffix = location_search_data["suffix"][:4]
        query = f"FB{suffix}"

        response = client.get(f"/v1/locations/search/station-numbers?q={query}")

        assert response.status_code == 200
        data = response.json()

        if data["items"]:
            assert "location" in data["items"][0]
            assert "category_code" in data["items"][0]

    def test_non_trig_results_have_null_location_and_category(
        self, client: TestClient, db
    ):
        """Test that non-trig results have null location and category_code."""
        response = client.get("/v1/locations/search?q=51.5,-0.1")

        assert response.status_code == 200
        data = response.json()
        latlon_results = [r for r in data if r["type"] == "latlon"]
        assert len(latlon_results) > 0

        item = latlon_results[0]
        assert item["location"] is None
        assert item["category_code"] is None


class TestLocationSearchResultStructure:
    """Tests for response structure validation."""

    def test_location_search_result_structure(
        self, client: TestClient, location_search_data, db
    ):
        """Test LocationSearchResult has all expected fields."""
        suffix = location_search_data["suffix"]
        query = f"SearchTestTrig_{suffix}"

        response = client.get(f"/v1/locations/search?q={query}")

        assert response.status_code == 200
        data = response.json()

        if len(data) > 0:
            item = data[0]
            assert "type" in item
            assert "name" in item
            assert "lat" in item
            assert "lon" in item
            assert "description" in item
            assert "id" in item
            assert "location" in item
            assert "category_code" in item

    def test_log_search_result_structure(
        self, client: TestClient, location_search_data, db
    ):
        """Test LogSearchResult has all expected fields."""
        suffix = location_search_data["suffix"]
        query = f"SearchableLogComment_{suffix}"

        response = client.get(f"/v1/locations/search/logs/substring?q={query}")

        assert response.status_code == 200
        data = response.json()

        if data["items"]:
            item = data["items"][0]
            required_fields = [
                "id",
                "trig_id",
                "trig_name",
                "date",
                "time",
                "condition",
                "comment",
                "score",
                "comment_excerpt",
            ]
            for field in required_fields:
                assert field in item, f"Missing field: {field}"


class TestSearchValidation:
    """Tests for search parameter validation."""

    def test_search_query_required(self, client: TestClient, db):
        """Test that query parameter is required."""
        response = client.get("/v1/locations/search")

        assert response.status_code == 422

    def test_search_query_min_length(self, client: TestClient, db):
        """Test minimum query length."""
        response = client.get("/v1/locations/search?q=a")

        assert response.status_code == 422

    def test_search_limit_max(self, client: TestClient, db):
        """Test maximum limit validation."""
        response = client.get("/v1/locations/search?q=test&limit=100")

        # Should reject limit > 50 for /search
        assert response.status_code == 422

    def test_search_trigpoints_limit_max(self, client: TestClient, db):
        """Test maximum limit for trigpoints search."""
        response = client.get("/v1/locations/search/trigpoints?q=test&limit=200")

        # Should reject limit > 100
        assert response.status_code == 422

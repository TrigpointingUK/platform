"""
Tests for core/metrics.py — MetricsCollector and helper functions.
"""

from unittest.mock import MagicMock, patch

from api.core.metrics import (
    MetricsCollector,
    get_metrics_collector,
    initialize_metrics,
    shutdown_metrics,
)


class TestMetricsCollector:
    def test_initialisation_creates_instruments(self):
        collector = MetricsCollector()
        assert collector.http_request_count is not None
        assert collector.http_request_duration is not None
        assert collector.http_active_requests is not None
        assert collector.db_query_count is not None
        assert collector.db_query_duration is not None
        assert collector.trigs_viewed is not None
        assert collector.photos_uploaded is not None
        assert collector.cache_hits is not None

    def test_record_http_request(self):
        collector = MetricsCollector()
        collector.http_request_count = MagicMock()
        collector.http_request_duration = MagicMock()
        collector.record_http_request("GET", "/v1/trigs", 200, 42.5)
        collector.http_request_count.add.assert_called_once()
        collector.http_request_duration.record.assert_called_once()

    def test_track_active_request_context_manager(self):
        collector = MetricsCollector()
        collector.http_active_requests = MagicMock()
        with collector.track_active_request("GET", "/v1/trigs"):
            collector.http_active_requests.add.assert_called_with(
                1, {"http.method": "GET", "http.route": "/v1/trigs"}
            )
        assert collector.http_active_requests.add.call_count == 2

    def test_record_db_query(self):
        collector = MetricsCollector()
        collector.db_query_count = MagicMock()
        collector.db_query_duration = MagicMock()
        collector.record_db_query("SELECT", 5.0, table="trig")
        collector.db_query_count.add.assert_called_once()
        collector.db_query_duration.record.assert_called_once()

    def test_record_db_query_without_table(self):
        collector = MetricsCollector()
        collector.db_query_count = MagicMock()
        collector.db_query_duration = MagicMock()
        collector.record_db_query("SELECT", 5.0)
        attrs = collector.db_query_count.add.call_args[0][1]
        assert "db.table" not in attrs

    def test_track_db_query_context_manager(self):
        collector = MetricsCollector()
        collector.db_query_count = MagicMock()
        collector.db_query_duration = MagicMock()
        with collector.track_db_query("SELECT", "trig"):
            pass
        collector.db_query_count.add.assert_called_once()
        collector.db_query_duration.record.assert_called_once()

    def test_update_db_pool_metrics_noop(self):
        collector = MetricsCollector()
        collector.update_db_pool_metrics(10, 5)

    def test_record_trig_view(self):
        collector = MetricsCollector()
        collector.trigs_viewed = MagicMock()
        collector.record_trig_view(123, cache_status="hit")
        collector.trigs_viewed.add.assert_called_once()

    def test_record_trig_search(self):
        collector = MetricsCollector()
        collector.trigs_searched = MagicMock()
        collector.record_trig_search("nearby")
        collector.trigs_searched.add.assert_called_once()

    def test_record_photo_upload(self):
        collector = MetricsCollector()
        collector.photos_uploaded = MagicMock()
        collector.record_photo_upload("success", trig_id=42)
        collector.photos_uploaded.add.assert_called_once()

    def test_record_photo_upload_without_trig(self):
        collector = MetricsCollector()
        collector.photos_uploaded = MagicMock()
        collector.record_photo_upload("failure")
        attrs = collector.photos_uploaded.add.call_args[0][1]
        assert "trig_id" not in attrs

    def test_track_photo_processing(self):
        collector = MetricsCollector()
        collector.photos_processing_duration = MagicMock()
        with collector.track_photo_processing():
            pass
        collector.photos_processing_duration.record.assert_called_once()

    def test_record_cache_hit(self):
        collector = MetricsCollector()
        collector.cache_hits = MagicMock()
        collector.record_cache_hit("api_response")
        collector.cache_hits.add.assert_called_once_with(
            1, {"cache_type": "api_response"}
        )

    def test_record_cache_miss(self):
        collector = MetricsCollector()
        collector.cache_misses = MagicMock()
        collector.record_cache_miss("tiles")
        collector.cache_misses.add.assert_called_once_with(1, {"cache_type": "tiles"})


class TestModuleFunctions:
    def test_get_metrics_collector_initially_none(self):
        import api.core.metrics as mod

        original = mod._metrics_collector
        mod._metrics_collector = None
        assert get_metrics_collector() is None
        mod._metrics_collector = original

    def test_initialize_metrics(self):
        import api.core.metrics as mod

        original = mod._metrics_collector
        mod._metrics_collector = None
        initialize_metrics()
        assert mod._metrics_collector is not None
        mod._metrics_collector = original

    def test_shutdown_metrics(self):
        import api.core.metrics as mod

        mod._metrics_collector = MetricsCollector()
        shutdown_metrics()
        assert mod._metrics_collector is None

    @patch("api.core.metrics.MetricsCollector", side_effect=Exception("oops"))
    def test_initialize_metrics_handles_error(self, mock_cls):
        import api.core.metrics as mod

        original = mod._metrics_collector
        mod._metrics_collector = None
        initialize_metrics()
        assert mod._metrics_collector is None
        mod._metrics_collector = original

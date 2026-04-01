"""
Tests for services/chat/agent.py — agent orchestration.
"""

import json
from unittest.mock import MagicMock, patch

from api.services.chat.agent import _execute_tool, stream_response


class TestExecuteTool:
    def test_vector_search(self):
        db = MagicMock()
        with patch(
            "api.services.chat.agent.vector_search", return_value=[{"text": "result"}]
        ) as mock_vs:
            result = _execute_tool("vector_search", json.dumps({"query": "test"}), db)
            assert "result" in result
            mock_vs.assert_called_once()

    def test_lookup_trig(self):
        db = MagicMock()
        with patch(
            "api.services.chat.agent.lookup_trig", return_value=[{"name": "Test"}]
        ) as mock_lt:
            result = _execute_tool("lookup_trig", json.dumps({"query": "TP1234"}), db)
            assert "Test" in result
            mock_lt.assert_called_once()

    def test_query_database(self):
        db = MagicMock()
        with patch("api.services.chat.agent.query_database", return_value="1 row"):
            result = _execute_tool(
                "query_database", json.dumps({"question": "How many trigs?"}), db
            )
            assert result == "1 row"

    def test_unknown_tool(self):
        db = MagicMock()
        result = _execute_tool("unknown_tool", "{}", db)
        assert "Unknown tool" in result


class TestStreamResponse:
    @patch("api.services.chat.agent._get_client")
    def test_yields_error_on_exception(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.responses.stream.side_effect = Exception("API Error")

        db = MagicMock()
        messages = [{"role": "user", "content": "Hello"}]
        events = list(stream_response(messages, db))
        assert any(e["type"] == "error" for e in events)

    @patch("api.services.chat.agent._get_client")
    def test_builds_input_messages(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)
        mock_stream.__iter__ = MagicMock(return_value=iter([]))
        mock_response = MagicMock()
        mock_response.id = "resp_123"
        mock_stream.get_final_response.return_value = mock_response
        mock_client.responses.stream.return_value = mock_stream

        db = MagicMock()
        messages = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello"},
            {"role": "user", "content": "Question"},
        ]
        events = list(stream_response(messages, db))
        assert any(e["type"] == "done" for e in events)

"""
Tests for the badge service.
"""

import io
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PIL import Image
from sqlalchemy.orm import Session

from api.models.user import User
from api.services.badge_service import BadgeService


@pytest.fixture
def _test_logo(tmp_path: Path) -> Path:
    """Create a small temporary PNG to stand in for the real logo."""
    logo = Image.new("RGBA", (40, 40), (255, 0, 0, 255))
    path = tmp_path / "tuk_logo.png"
    logo.save(path, format="PNG")
    return path


def _mock_db_queries(mock_db, trigs=5, photos=12):
    """Wire up mock_db.query to return trig count and photo count."""
    mock_trig_query = Mock()
    mock_trig_query.filter.return_value = mock_trig_query
    mock_trig_query.distinct.return_value = mock_trig_query
    mock_trig_query.count.return_value = trigs

    mock_photo_query = Mock()
    mock_photo_query.join.return_value = mock_photo_query
    mock_photo_query.filter.return_value = mock_photo_query
    mock_photo_query.count.return_value = photos

    mock_db.query.side_effect = [mock_trig_query, mock_photo_query]


class TestBadgeService:
    """Test cases for BadgeService."""

    def test_init(self):
        """Test BadgeService initialization."""
        service = BadgeService()
        assert service.base_width == 200
        assert service.base_height == 50
        assert service.logo_path.name == "tuk_logo.png"

    @patch("api.services.badge_service.get_user_by_id")
    def test_get_user_statistics(self, mock_get_user):
        """Test getting user statistics."""
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_get_user.return_value = mock_user

        mock_db = Mock(spec=Session)
        _mock_db_queries(mock_db, trigs=5, photos=12)

        service = BadgeService()
        distinct_trigs, total_photos = service.get_user_statistics(mock_db, 1)

        assert distinct_trigs == 5
        assert total_photos == 12

    @patch("api.services.badge_service.get_user_by_id")
    def test_generate_badge_user_not_found(self, mock_get_user):
        """Test badge generation when user is not found."""
        mock_get_user.return_value = None
        mock_db = Mock(spec=Session)

        service = BadgeService()

        with pytest.raises(ValueError, match="User with ID 999 not found"):
            service.generate_badge(mock_db, 999)

    @patch("api.services.badge_service.get_user_by_id")
    def test_generate_badge_logo_not_found(self, mock_get_user):
        """Test badge generation when logo file is not found."""
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.name = "testuser"
        mock_get_user.return_value = mock_user

        mock_db = Mock(spec=Session)

        service = BadgeService()
        service.logo_path = Path("/nonexistent/logo.png")

        with pytest.raises(FileNotFoundError, match="Logo file not found"):
            service.generate_badge(mock_db, 1)

    def test_long_username_truncation(self):
        """Test that long usernames are properly truncated."""
        long_name = "verylongusernamethatshouldbetrunca"
        truncated = long_name[:20]
        assert len(truncated) == 20
        assert truncated == "verylongusernamethat"

    @patch("api.services.badge_service.get_user_by_id")
    def test_generate_badge_integration(self, mock_get_user, _test_logo):
        """Integration test that actually generates a badge using real PIL operations."""
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.name = "testuser"
        mock_get_user.return_value = mock_user

        mock_db = Mock(spec=Session)
        _mock_db_queries(mock_db, trigs=3, photos=7)

        service = BadgeService()
        service.logo_path = _test_logo

        result = service.generate_badge(mock_db, 1)

        assert isinstance(result, io.BytesIO)
        assert result.tell() == 0
        assert len(result.getvalue()) > 0

    @patch("api.services.badge_service.get_user_by_id")
    def test_generate_badge_with_scale(self, mock_get_user, _test_logo):
        """Test badge generation with different scale factors."""
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.name = "testuser"
        mock_get_user.return_value = mock_user

        service = BadgeService()
        service.logo_path = _test_logo

        for scale in [0.5, 1.0, 2.0]:
            mock_db = Mock(spec=Session)
            _mock_db_queries(mock_db, trigs=5, photos=10)

            result = service.generate_badge(mock_db, 1, scale=scale)

            assert isinstance(result, io.BytesIO)
            assert len(result.getvalue()) > 0

            result.seek(0)
            image = Image.open(result)
            expected_width = int(200 * scale)
            expected_height = int(50 * scale)
            assert image.size == (expected_width, expected_height)

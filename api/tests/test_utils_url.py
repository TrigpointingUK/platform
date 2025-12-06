"""Tests for URL utilities."""

from api.utils.url import join_url


def test_join_url_empty_base():
    """Empty base returns path unchanged."""
    assert join_url("", "photos/123.jpg") == "photos/123.jpg"


def test_join_url_base_with_trailing_slash():
    """Base with trailing slash doesn't double up."""
    assert (
        join_url("https://example.com/", "photos/123.jpg")
        == "https://example.com/photos/123.jpg"
    )


def test_join_url_base_without_trailing_slash():
    """Base without trailing slash adds one."""
    assert (
        join_url("https://example.com", "photos/123.jpg")
        == "https://example.com/photos/123.jpg"
    )

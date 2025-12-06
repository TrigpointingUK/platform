"""Tests for IP address utilities."""

from api.utils.ip_address import get_client_ip_normalized, normalize_ip_for_storage


class TestNormalizeIpForStorage:
    """Tests for normalize_ip_for_storage function."""

    def test_ipv4_address(self):
        """IPv4 addresses are returned unchanged."""
        assert normalize_ip_for_storage("192.168.1.1") == "192.168.1.1"

    def test_ipv4_max_length(self):
        """IPv4 addresses fit within 15 chars."""
        result = normalize_ip_for_storage("255.255.255.255")
        assert result == "255.255.255.255"
        assert len(result) <= 15

    def test_ipv4_mapped_ipv6(self):
        """IPv4-mapped IPv6 addresses extract the IPv4 portion."""
        assert normalize_ip_for_storage("::ffff:192.168.1.1") == "192.168.1.1"

    def test_pure_ipv6_truncated(self):
        """Pure IPv6 addresses are truncated with marker."""
        result = normalize_ip_for_storage("2001:0db8:85a3::8a2e:0370:7334")
        assert len(result) <= 15
        assert result.endswith(":")  # Truncation marker

    def test_short_ipv6(self):
        """Short IPv6 addresses that fit are returned as-is."""
        # ::1 compresses to "::1" which is 3 chars
        result = normalize_ip_for_storage("::1")
        assert result == "::1"
        assert len(result) <= 15

    def test_empty_string(self):
        """Empty string returns empty string."""
        assert normalize_ip_for_storage("") == ""

    def test_unknown_string(self):
        """'unknown' string is handled."""
        assert normalize_ip_for_storage("unknown") == "unknown"

    def test_invalid_ip_short(self):
        """Invalid IP strings within length are returned as-is."""
        assert normalize_ip_for_storage("not-an-ip") == "not-an-ip"

    def test_invalid_ip_long(self):
        """Invalid IP strings exceeding length are truncated with ellipsis."""
        result = normalize_ip_for_storage("this-is-not-a-valid-ip-address")
        assert len(result) <= 15
        assert result.endswith("…")

    def test_custom_max_length(self):
        """Custom max_length is respected for invalid strings."""
        # IPv4 addresses don't get truncated (they're always <= 15 chars)
        # But invalid strings do respect max_length
        result = normalize_ip_for_storage("this-is-invalid", max_length=10)
        assert len(result) <= 10
        assert result.endswith("…")


class TestGetClientIpNormalized:
    """Tests for get_client_ip_normalized convenience wrapper."""

    def test_ipv4(self):
        """IPv4 addresses work through the wrapper."""
        assert get_client_ip_normalized("10.0.0.1") == "10.0.0.1"

    def test_ipv6_mapped(self):
        """IPv4-mapped IPv6 addresses work through the wrapper."""
        assert get_client_ip_normalized("::ffff:10.0.0.1") == "10.0.0.1"

    def test_empty(self):
        """Empty string works through the wrapper."""
        assert get_client_ip_normalized("") == ""

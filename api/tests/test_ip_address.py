"""
Tests for IP address normalization utilities.
"""

from api.utils.ip_address import get_client_ip_normalized, normalize_ip_for_storage


class TestIPAddressNormalization:
    """Test IP address normalization for legacy database storage."""

    def test_ipv4_address_unchanged(self):
        """Test that IPv4 addresses pass through unchanged."""
        assert normalize_ip_for_storage("192.168.1.1") == "192.168.1.1"
        assert normalize_ip_for_storage("10.0.0.1") == "10.0.0.1"
        assert normalize_ip_for_storage("127.0.0.1") == "127.0.0.1"

    def test_ipv4_mapped_ipv6_extracted(self):
        """Test that IPv4-mapped IPv6 addresses are converted to IPv4."""
        assert normalize_ip_for_storage("::ffff:192.168.1.1") == "192.168.1.1"
        assert normalize_ip_for_storage("::ffff:10.0.0.1") == "10.0.0.1"

    def test_pure_ipv6_compressed(self):
        """Test that pure IPv6 addresses are compressed."""
        # Short IPv6 that fits in 15 chars
        assert normalize_ip_for_storage("::1") == "::1"
        assert normalize_ip_for_storage("::") == "::"

    def test_long_ipv6_truncated(self):
        """Test that long IPv6 addresses are truncated intelligently."""
        long_ipv6 = "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
        result = normalize_ip_for_storage(long_ipv6)

        # Should be truncated to 15 chars max
        assert len(result) <= 15
        # Should end with colon to indicate truncation
        assert result.endswith(":")
        # Should preserve the start of the address
        assert result.startswith("2001:db8")

    def test_unknown_address(self):
        """Test handling of unknown/missing addresses."""
        assert normalize_ip_for_storage("unknown") == "unknown"
        assert normalize_ip_for_storage("") == ""

    def test_invalid_ip_address(self):
        """Test handling of invalid IP addresses."""
        invalid = "not-an-ip-address"
        result = normalize_ip_for_storage(invalid)

        # Should truncate if too long
        assert len(result) <= 15

    def test_custom_max_length(self):
        """Test custom max_length parameter."""
        long_ipv6 = "2001:0db8:85a3:0000:0000:8a2e:0370:7334"

        # With max_length=45, should fit the whole compressed address
        result = normalize_ip_for_storage(long_ipv6, max_length=45)
        assert len(result) <= 45

        # With max_length=10, should truncate more aggressively
        result = normalize_ip_for_storage(long_ipv6, max_length=10)
        assert len(result) <= 10

    def test_get_client_ip_normalized_wrapper(self):
        """Test the convenience wrapper function."""
        assert get_client_ip_normalized("192.168.1.1") == "192.168.1.1"
        assert get_client_ip_normalized("::ffff:10.0.0.1") == "10.0.0.1"

        long_ipv6 = "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
        result = get_client_ip_normalized(long_ipv6)
        assert len(result) <= 15

    def test_real_world_ipv6_examples(self):
        """Test with real-world IPv6 addresses."""
        # Google DNS IPv6 - 20 chars when compressed, will be truncated
        google_dns = "2001:4860:4860::8888"
        result = normalize_ip_for_storage(google_dns)
        assert len(result) <= 15
        # Should be truncated with colon marker
        assert result.endswith(":")

        # Cloudflare DNS IPv6
        cloudflare = "2606:4700:4700::1111"
        result = normalize_ip_for_storage(cloudflare)
        assert len(result) <= 15

    def test_localhost_addresses(self):
        """Test localhost addresses in both IPv4 and IPv6."""
        assert normalize_ip_for_storage("127.0.0.1") == "127.0.0.1"
        assert normalize_ip_for_storage("::1") == "::1"

    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        # Exactly 15 characters (should fit)
        assert len(normalize_ip_for_storage("123.456.789.012")) <= 15

        # Empty string
        assert normalize_ip_for_storage("") == ""

        # Very long invalid string
        long_str = "x" * 100
        result = normalize_ip_for_storage(long_str)
        assert len(result) <= 15

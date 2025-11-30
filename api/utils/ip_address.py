"""
IP address utilities for handling IPv4 and IPv6 addresses.

This module provides functions to normalize and truncate IP addresses
to fit legacy database constraints while preserving as much information
as possible.
"""

import ipaddress


def normalize_ip_for_storage(ip_str: str, max_length: int = 15) -> str:
    """
    Normalize an IP address for storage in legacy varchar(15) columns.

    Handles IPv4, IPv6, and IPv4-mapped IPv6 addresses. For IPv6 addresses
    that exceed max_length, attempts to extract the IPv4 portion if present,
    otherwise truncates with a marker.

    Args:
        ip_str: IP address string to normalize
        max_length: Maximum length for the returned string (default: 15)

    Returns:
        Normalized IP address string, truncated if necessary

    Examples:
        >>> normalize_ip_for_storage("192.168.1.1")
        '192.168.1.1'
        >>> normalize_ip_for_storage("::ffff:192.168.1.1")  # IPv4-mapped IPv6
        '192.168.1.1'
        >>> normalize_ip_for_storage("2001:0db8:85a3::8a2e:0370:7334")
        '2001:db8:85a3:'  # Truncated with marker
    """
    if not ip_str:
        return ""

    if ip_str == "unknown":
        return "unknown"[:max_length]

    try:
        # Parse the IP address
        ip = ipaddress.ip_address(ip_str)

        # If it's IPv4, return as-is (max 15 chars)
        if isinstance(ip, ipaddress.IPv4Address):
            return str(ip)

        # If it's IPv6
        if isinstance(ip, ipaddress.IPv6Address):
            # Check if it's an IPv4-mapped IPv6 address (::ffff:192.168.1.1)
            if ip.ipv4_mapped:
                # Extract and return the IPv4 portion
                return str(ip.ipv4_mapped)

            # For pure IPv6, try to compress and truncate intelligently
            compressed = ip.compressed  # Use compressed form (shortest representation)

            if len(compressed) <= max_length:
                return compressed

            # If still too long, truncate with colon to indicate truncation
            # This preserves the network portion which is usually most useful
            return compressed[: max_length - 1] + ":"

    except ValueError:
        # If parsing fails, just truncate the string
        pass

    # Fallback: truncate the original string
    if len(ip_str) <= max_length:
        return ip_str

    return ip_str[: max_length - 1] + "…"


def get_client_ip_normalized(ip_str: str) -> str:
    """
    Get normalized client IP for storage in varchar(15) columns.

    This is a convenience wrapper around normalize_ip_for_storage
    specifically for client IP addresses from requests.

    Args:
        ip_str: IP address from request.client.host or similar

    Returns:
        Normalized IP address suitable for varchar(15) storage

    Example:
        >>> client_ip = request.client.host if request.client else "unknown"
        >>> db_ip = get_client_ip_normalized(client_ip)
    """
    return normalize_ip_for_storage(ip_str, max_length=15)

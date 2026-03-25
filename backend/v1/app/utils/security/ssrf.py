"""
SSRF Protection and Utility Functions
"""

import ipaddress
import socket
import re
import uuid
from urllib.parse import urlparse


# Private and reserved IP ranges that should be blocked for SSRF protection
BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network('10.0.0.0/8'),        # Private Class A
    ipaddress.ip_network('172.16.0.0/12'),     # Private Class B
    ipaddress.ip_network('192.168.0.0/16'),    # Private Class C
    ipaddress.ip_network('169.254.0.0/16'),    # Link-local (AWS/GCP metadata)
    ipaddress.ip_network('127.0.0.0/8'),       # Loopback
    ipaddress.ip_network('0.0.0.0/8'),         # Current network
    ipaddress.ip_network('100.64.0.0/10'),     # Carrier-grade NAT
    ipaddress.ip_network('192.0.0.0/24'),      # IETF Protocol Assignments
    ipaddress.ip_network('192.0.2.0/24'),      # TEST-NET-1 (documentation)
    ipaddress.ip_network('198.51.100.0/24'),   # TEST-NET-2 (documentation)
    ipaddress.ip_network('203.0.113.0/24'),    # TEST-NET-3 (documentation)
    ipaddress.ip_network('224.0.0.0/4'),       # Multicast
    ipaddress.ip_network('240.0.0.0/4'),       # Reserved for future use
    ipaddress.ip_network('255.255.255.255/32'), # Broadcast
    # IPv6 equivalents
    ipaddress.ip_network('::1/128'),           # IPv6 loopback
    ipaddress.ip_network('fc00::/7'),          # IPv6 unique local
    ipaddress.ip_network('fe80::/10'),         # IPv6 link-local
    ipaddress.ip_network('::ffff:0:0/96'),     # IPv4-mapped IPv6 (prevents bypass via ::ffff:127.0.0.1)
]


def is_safe_url_for_ssrf(url: str) -> tuple[bool, str]:
    """
    Validate that a URL doesn't point to private/internal addresses (SSRF protection).

    This function should be called before making HTTP requests to user-controlled URLs
    to prevent Server-Side Request Forgery attacks.

    Args:
        url: The URL to validate

    Returns:
        Tuple of (is_safe, error_message)
        - is_safe: True if URL is safe to request, False if blocked
        - error_message: Empty string if safe, description of why blocked otherwise

    Security:
        Blocks requests to:
        - Private IP ranges (10.x, 172.16.x, 192.168.x)
        - Loopback addresses (127.x, localhost)
        - Link-local addresses (169.254.x - cloud metadata endpoints)
        - IPv6 private/local addresses
        - Other reserved ranges

    Example:
        >>> is_safe_url_for_ssrf("https://api.stripe.com/v1/charges")
        (True, "")

        >>> is_safe_url_for_ssrf("https://169.254.169.254/latest/meta-data/")
        (False, "URL resolves to blocked IP range (link-local/metadata)")

        >>> is_safe_url_for_ssrf("https://localhost:8080/admin")
        (False, "URL resolves to blocked IP range (loopback)")
    """
    try:
        parsed = urlparse(url)

        # Validate URL scheme - only allow http/https
        allowed_schemes = {'http', 'https'}
        if parsed.scheme.lower() not in allowed_schemes:
            return False, f"URL scheme '{parsed.scheme}' is not allowed (only http/https)"

        hostname = parsed.hostname

        if not hostname:
            return False, "Invalid URL: no hostname found"

        # Block common internal hostnames directly (before DNS resolution)
        blocked_hostnames = ['localhost', 'metadata', 'metadata.google.internal']
        if hostname.lower() in blocked_hostnames:
            return False, f"Hostname '{hostname}' is blocked"

        # Resolve hostname to IP address
        try:
            # Use getaddrinfo to handle both IPv4 and IPv6
            addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            if not addr_info:
                return False, f"Cannot resolve hostname: {hostname}"

            # Check all resolved IPs (some hostnames resolve to multiple IPs)
            for family, _, _, _, sockaddr in addr_info:
                ip_str = sockaddr[0]

                try:
                    ip = ipaddress.ip_address(ip_str)
                except ValueError:
                    continue

                # Check against blocked networks
                for network in BLOCKED_IP_NETWORKS:
                    if ip in network:
                        return False, f"URL resolves to blocked IP range: {network}"

                # Additional check: reject non-global IPs
                if not ip.is_global:
                    return False, f"URL resolves to non-public IP: {ip_str}"

        except socket.gaierror as e:
            return False, f"DNS resolution failed for '{hostname}': {str(e)}"
        except socket.timeout:
            return False, f"DNS resolution timed out for '{hostname}'"

        return True, ""

    except Exception as e:
        # On any unexpected error, fail closed (block the request)
        return False, f"URL validation error: {str(e)}"


def validate_node_id_format(node_id: str) -> bool:
    """
    Validate node_id format

    Args:
        node_id: Node identifier

    Returns:
        True if valid format, False otherwise

    Rules:
        - Alphanumeric and underscores only
        - No spaces
        - Length <= 96 characters
    """
    if not node_id or len(node_id) > 96:
        return False

    return bool(re.match(r'^[A-Za-z0-9_]+$', node_id))


def generate_session_id() -> str:
    """
    Generate a unique session ID

    Returns:
        UUID string for session
    """
    return str(uuid.uuid4())

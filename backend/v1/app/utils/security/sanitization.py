"""
Input Sanitization and Validation
"""

import re
from typing import Optional


def sanitize_input(text: str) -> tuple[str, dict]:
    """
    Layer 1: Baseline Sanitization (Universal, Always Applied)

    Removes dangerous characters and enforces length limits per spec Section 10.1.

    Args:
        text: Raw user input text

    Returns:
        Tuple of (sanitized_text, sanitization_metadata)

    Sanitization metadata contains:
        - original_length: Original text length
        - sanitized_length: Final text length
        - null_bytes_removed: Count of null bytes removed
        - control_chars_removed: Count of control characters removed
        - was_truncated: Whether text was truncated to 4096 chars

    Operations:
        1. Remove null bytes (\x00)
        2. Remove control characters (except \n, \t, \r)
        3. Trim leading/trailing whitespace
        4. Truncate to 4096 characters maximum

    Note:
        This is Layer 1 of the 3-layer sanitization system.
        Layer 2 (context-aware escaping) happens at point of use.
        Layer 3 (pattern rejection) is checked separately via check_suspicious_patterns().
    """
    original_length = len(text)
    null_bytes_removed = 0
    control_chars_removed = 0

    # 1. Remove null bytes
    if '\x00' in text:
        null_bytes_removed = text.count('\x00')
        text = text.replace('\x00', '')

    # 2. Remove control characters (except newline, tab, carriage return)
    cleaned_chars = []
    for char in text:
        char_code = ord(char)
        # Keep printable chars, newline (\n = 10), tab (\t = 9), carriage return (\r = 13)
        if char in '\n\t\r' or char_code >= 32:
            cleaned_chars.append(char)
        else:
            control_chars_removed += 1

    text = ''.join(cleaned_chars)

    # 3. Trim whitespace
    text = text.strip()

    # 4. Enforce length limit (4096 characters)
    was_truncated = False
    if len(text) > 4096:
        text = text[:4096]
        was_truncated = True

    sanitized_length = len(text)

    metadata = {
        'original_length': original_length,
        'sanitized_length': sanitized_length,
        'null_bytes_removed': null_bytes_removed,
        'control_chars_removed': control_chars_removed,
        'was_truncated': was_truncated
    }

    return text, metadata


def check_suspicious_patterns(text: str) -> tuple[bool, Optional[str]]:
    """
    Layer 3: Pattern Rejection (Universal, Always Applied)

    Detects dangerous patterns that indicate attack attempts per spec Section 10.1.

    Args:
        text: User input text (after Layer 1 sanitization)

    Returns:
        Tuple of (is_safe, pattern_type)
        - is_safe: True if no suspicious patterns found, False otherwise
        - pattern_type: Type of pattern detected (None if safe)

    Detected Patterns:
        - Script tags: <script>, </script>
        - JavaScript protocols: javascript:
        - Event handlers: onclick=, onerror=, onload=
        - Template injection: {{, }}, ${...}
        - Command injection: ;, |, &&
        - Path traversal: ../, ..\\
        - SQL comments: --, /*, */

    Note:
        This is Layer 3 of the 3-layer sanitization system.
        When suspicious pattern detected, input is rejected with error message.
    """
    # Patterns that indicate attack attempts
    patterns = [
        (r'<script[^>]*>', 'script_tag'),
        (r'</script>', 'script_tag'),
        (r'javascript:', 'javascript_protocol'),
        (r'on\w+\s*=', 'event_handler'),  # onclick=, onerror=, etc.
        (r'\{\{', 'template_injection'),
        (r'\}\}', 'template_injection'),
        (r'\$\{[^}]*\}', 'template_injection'),  # Fixed: complete ${...} pattern
        (r';\s*\w+', 'command_injection'),  # ; followed by command
        (r'\|\|', 'command_injection'),
        (r'&&', 'command_injection'),
        (r'\|', 'command_injection'),
        (r'\.\./|\.\.\\', 'path_traversal'),
        (r'--', 'sql_comment'),
        (r'/\*', 'sql_comment'),
        (r'\*/', 'sql_comment'),
    ]

    for pattern, pattern_type in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return False, pattern_type

    return True, None


def escape_html(text: str) -> str:
    """
    Layer 2: Context-Aware Escaping - HTML

    Escapes HTML special characters to prevent XSS attacks.

    Args:
        text: Text to escape

    Returns:
        HTML-escaped text

    Escapes:
        < → &lt;
        > → &gt;
        & → &amp;
        " → &quot;
        ' → &#x27;

    Note:
        This is part of Layer 2 (context-aware escaping).
        Called when rendering content in web interfaces.
    """
    return (text
            .replace('&', '&amp;')  # Must be first
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#x27;'))


class SanitizationError(Exception):
    """
    Raised when input fails sanitization checks (Layer 3 pattern rejection)

    Attributes:
        message: User-facing error message
        pattern_type: Type of suspicious pattern detected
        original_input_length: Length of original input (for logging)
    """
    def __init__(self, message: str, pattern_type: str, original_input_length: int):
        super().__init__(message)
        self.message = message
        self.pattern_type = pattern_type
        self.original_input_length = original_input_length

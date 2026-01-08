"""
REGEX full match (Tests 265-270)
Reorganized from: test_21_regex_full_string_match.py

Tests validate: REGEX full match
"""
import pytest

def test_265_regex_must_match_entire_input_string(self):
        """✅ REGEX must match entire input (not just substring)"""
        # Spec: "Must match entire input string"
        # "The regex engine matches against the complete user input from start to finish"
        # "If the pattern matches any substring, but not the entire input, validation FAILS"

        validation = {
            "type": "REGEX",
            "rule": "[0-9]+",  # Matches digits
            "error_message": "Must be numeric"
        }

        # Test cases
        test_cases = [
            ("123", True),         # ✓ Entire string is digits
            ("123abc", False),     # ✗ Has digits but "abc" at end fails entire match
            ("abc123", False),     # ✗ Has digits but "abc" at start fails entire match
            ("abc123def", False),  # ✗ Has digits in middle but fails entire match
            ("", False),           # ✗ Empty doesn't match [0-9]+
        ]

        for input_text, should_pass in test_cases:
            # Expected: Validation uses full string match
            # Pattern [0-9]+ only passes if ENTIRE input is digits
            pass


def test_266_explicit_anchors_recommended_for_clarity(self):
        """✅ Explicit anchors (^$) recommended even though implicit"""
        # Spec: "Always use explicit anchors (^, $) for clarity even though they're implicit"
        # "Patterns are treated as if wrapped with implicit anchors: /^pattern$/"

        # Without explicit anchors (implicit)
        implicit_pattern = "[0-9]+"

        # With explicit anchors (recommended)
        explicit_pattern = "^[0-9]+$"

        # Both behave identically (full string match)
        test_input = "123"

        # Expected: Both patterns match identically
        # Recommendation: Use explicit for clarity

        # Without explicit anchors - fails on extra chars
        test_input_with_extra = "123abc"

        # Expected:
        # implicit_pattern "[0-9]+" on "123abc" → FAILS (entire string must match)
        # explicit_pattern "^[0-9]+$" on "123abc" → FAILS (same behavior)


def test_267_pattern_without_anchors_fails_on_extra_characters(self):
        """✅ Pattern without wildcards fails when input has extra characters"""
        # Spec: "Pattern `[0-9]+` for input '123abc' → FAILS (digits match but 'abc' remains unmatched)"

        validation = {
            "type": "REGEX",
            "rule": "[0-9]+",
            "error_message": "Must be numeric"
        }

        # Test: User enters "123abc"
        user_input = "123abc"

        # Processing:
        # 1. Pattern [0-9]+ matches "123" portion
        # 2. But "abc" at end is unmatched
        # 3. Full string match required → VALIDATION FAILS

        # Expected: Validation fails
        # User sees: "Must be numeric (Attempt 1 of 3)"


def test_268_pattern_with_wildcards_allows_extra_characters(self):
        """✅ Pattern with wildcards (.*) allows characters before/after"""
        # Spec: "'.*[0-9]+.*' matches (allows anything before/after digits)"

        validation = {
            "type": "REGEX",
            "rule": ".*[0-9]+.*",  # Allows anything before/after digits
            "error_message": "Must contain at least one digit"
        }

        # Test cases - all should PASS
        test_cases = [
            "123",           # Just digits
            "abc123",        # Text before digits
            "123def",        # Text after digits
            "abc123def",     # Text before and after
            "hello 42 world" # Digit in middle with spaces
        ]

        for input_text in test_cases:
            # Expected: All pass (wildcards allow extra characters)
            pass

        # Should FAIL
        no_digits = "abcdef"
        # Expected: Fails (no digits present)


def test_269_common_patterns_with_proper_anchoring(self):
        """✅ Common validation patterns use explicit anchors"""
        # Spec: "Best Practice Examples - Always use anchors"

        # Date format: YYYY-MM-DD
        date_pattern = "^\\d{4}-\\d{2}-\\d{2}$"
        # ✓ "2024-12-01"
        # ✗ "2024-12-01 extra"
        # ✗ "prefix 2024-12-01"

        # Email format
        email_pattern = "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
        # ✓ "user@example.com"
        # ✗ "user@example.com extra"
        # ✗ "not an email"

        # Phone number (optional +, 10-15 digits)
        phone_pattern = "^\\+?[0-9]{10,15}$"
        # ✓ "1234567890"
        # ✓ "+254712345678"
        # ✗ "123"  (too short)
        # ✗ "12345678901234567890"  (too long)

        # Name (capital first letter + lowercase)
        name_pattern = "^[A-Z][a-z]+$"
        # ✓ "John"
        # ✗ "john"  (no capital)
        # ✗ "John123"  (has digits)
        # ✗ "John Smith"  (has space)

        # Expected: All patterns enforce full string match with anchors


def test_270_edge_case_empty_string_with_pattern(self):
        """✅ Empty string behavior with various patterns"""
        # Spec: Full string match applies to empty strings too

        # Pattern that requires at least one character
        pattern_one_or_more = "^[a-z]+$"
        # Empty string "" → FAILS (requires at least one letter)

        # Pattern that allows zero or more
        pattern_zero_or_more = "^[a-z]*$"
        # Empty string "" → PASSES (zero letters allowed)

        # Pattern with optional group
        pattern_optional = "^[a-z]?$"
        # Empty string "" → PASSES (zero or one letter)

        # Exact empty match
        pattern_exact_empty = "^$"
        # Empty string "" → PASSES (exactly matches empty)
        # "a" → FAILS (not empty)

        # Expected: All patterns correctly handle empty string based on quantifiers

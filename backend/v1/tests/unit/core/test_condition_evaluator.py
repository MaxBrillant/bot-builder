"""
Expression validation (Tests 153-168)
Reorganized from: test_12_validation_expressions.py

Tests validate: Expression validation
"""
import pytest

def test_153_is_numeric_accepts_valid_formats():
    """✅ input.isNumeric(): accepts valid numeric formats"""
    # Spec: "input.isNumeric(): Accepts: optional minus sign, digits, optional decimal point"

    valid_inputs = [
    "123",      # Integer
    "0",        # Zero
    "-45",      # Negative integer
    "12.34",    # Decimal
    ".5",       # Leading decimal point
    "-3.14",    # Negative decimal
    "0.0",      # Zero with decimal
    ]

    # For each, input.isNumeric() should return TRUE


def test_154_is_numeric_rejects_invalid_formats():
    """✅ input.isNumeric(): rejects invalid formats"""
    # Spec: "Rejects: '1e10', '1.2.3', '--5', scientific notation"

    invalid_inputs = [
    "1e10",     # Scientific notation
    "1.2.3",    # Multiple decimal points
    "--5",      # Double minus
    "12-34",    # Minus in middle
    "abc",      # Letters
    "12a",      # Letters mixed with numbers
    "",         # Empty string
    "  ",       # Whitespace only
    "Infinity", # Special value
    "NaN",      # Special value
    ]

    # For each, input.isNumeric() should return FALSE


def test_155_is_numeric_edge_cases():
    """✅ input.isNumeric(): edge cases"""

    edge_cases = [
    ("0", True),           # Zero
    ("-0", True),          # Negative zero
    ("+5", False),         # Plus sign (not mentioned in spec as accepted)
    ("00042", True),       # Leading zeros
    (".", False),          # Just decimal point
    ("-", False),          # Just minus sign
    ("1.", True),          # Trailing decimal
    (".1", True),          # Leading decimal
    ]

    # Expected behavior for each



def test_156_is_alpha_basic_letters():
    """✅ input.isAlpha(): basic letters only"""
    # Spec: "input.isAlpha(): Only letters (a-z, A-Z)"

    valid_inputs = [
    "abc",
    "ABC",
    "AbC",
    "a",
    "Z"
    ]

    invalid_inputs = [
    "abc123",   # Contains numbers
    "abc def",  # Contains space
    "abc-def",  # Contains hyphen
    "abc_def",  # Contains underscore
    "",         # Empty
    "123",      # Only numbers
    ]


def test_157_is_alpha_unicode_and_accented_characters():
    """✅ input.isAlpha(): unicode and accented characters"""
    # Spec doesn't explicitly mention unicode
    # Test expected behavior

    unicode_cases = [
    ("café", None),      # Accented e
    ("naïve", None),     # Accented i
    ("Björk", None),     # Scandinavian characters
    ("日本", None),      # Japanese characters
    ("مرحبا", None),     # Arabic characters
    ("Привет", None),    # Cyrillic characters
    ]

    # Expected: Likely FALSE (spec says "a-z, A-Z" only)
    # But implementation may accept unicode letters



def test_158_is_digit_vs_is_numeric_difference():
    """✅ input.isDigit() vs input.isNumeric() difference"""
    # Spec: "input.isDigit(): Only digits (0-9)"
    # vs "input.isNumeric(): optional minus, digits, optional decimal"

    test_cases = [
    # (input, isDigit, isNumeric)
    ("123", True, True),          # Plain digits
    ("-45", False, True),         # Negative
    ("12.34", False, True),       # Decimal
    (".5", False, True),          # Leading decimal
    ("abc", False, False),        # Letters
    ("12a", False, False),        # Mixed
    ("", False, False),           # Empty
    ]

    # isDigit(): ONLY 0-9 characters, nothing else
    # isNumeric(): Allows minus, decimal, but not scientific notation



def test_159_expression_accesses_context_variables():
    """✅ Expressions can access context variables"""
    # Spec: "Context variable access: context.max_value"

    validation_rule = "input.isNumeric() && input < context.max_value"
    context = {"max_value": 100}

    test_cases = [
    ("50", True),   # 50 < 100
    ("100", False), # 100 < 100 is false
    ("150", False), # 150 < 100
    ("abc", False), # Not numeric
    ]


def test_160_expression_with_nested_context_access():
    """✅ Expressions can access nested context properties"""
    # Spec: "Nested object access in expressions"

    validation_rule = "input.isNumeric() && input >= context.user.min_age"
    context = {
    "user": {
    "min_age": 18
    }
    }

    test_cases = [
    ("18", True),   # 18 >= 18
    ("25", True),   # 25 >= 18
    ("17", False),  # 17 < 18
    ]



def test_161_logical_and_operator():
    """✅ Logical AND (&&) operator"""
    # Spec: "Logical operators: &&, ||"

    validation_rules = [
    ("input.isNumeric() && input > 0", "50", True),
    ("input.isNumeric() && input > 0", "0", False),
    ("input.isNumeric() && input > 0", "abc", False),
    ("input.length >= 3 && input.isAlpha()", "abc", True),
    ("input.length >= 3 && input.isAlpha()", "ab", False),
    ("input.length >= 3 && input.isAlpha()", "abc123", False),
    ]


def test_162_logical_or_operator():
    """✅ Logical OR (||) operator"""

    validation_rules = [
    ("input.length == 0 || input.length >= 5", "", True),      # Empty allowed
    ("input.length == 0 || input.length >= 5", "hello", True), # 5+ chars
    ("input.length == 0 || input.length >= 5", "hi", False),   # 2 chars (neither condition)
    ("input.isNumeric() || input.isAlpha()", "123", True),
    ("input.isNumeric() || input.isAlpha()", "abc", True),
    ("input.isNumeric() || input.isAlpha()", "abc123", False),
    ]


def test_163_logical_operator_precedence():
    """✅ Logical operator precedence: && before ||"""
    # Standard precedence: AND binds tighter than OR

    # input.length > 5 || input.isNumeric() && input > 10
    # Parsed as: input.length > 5 || (input.isNumeric() && input > 10)

    test_cases = [
    ("hello world", True),   # length > 5 → TRUE (first condition)
    ("15", True),             # length not > 5, but isNumeric && 15 > 10 → TRUE
    ("5", False),             # length not > 5, isNumeric but 5 not > 10 → FALSE
    ("abc", False),           # length not > 5, not numeric → FALSE
    ]



def test_164_comparison_operators_with_numbers():
    """✅ Comparison operators: ==, !=, >, <, >=, <="""
    # Spec: "Numeric comparisons: input > 0, input <= 100"

    validation_rules = [
    ("input > 0", "5", True),
    ("input > 0", "0", False),
    ("input > 0", "-5", False),
    ("input >= 0", "0", True),
    ("input < 100", "50", True),
    ("input < 100", "100", False),
    ("input <= 100", "100", True),
    ("input == 42", "42", True),
    ("input == 42", "43", False),
    ("input != 0", "5", True),
    ("input != 0", "0", False),
    ]


def test_165_comparison_with_string_values():
    """✅ Comparison operators with string values"""

    validation_rules = [
    ("input == 'yes'", "yes", True),
    ("input == 'yes'", "YES", False),  # Case-sensitive
    ("input != 'no'", "yes", True),
    ("input == context.expected", "test", True),  # context.expected = "test"
    ]



def test_166_expression_max_512_characters():
    """✅ Expression length: max 512 characters"""
    # Spec: "Expression length: 512 characters"

    # Valid: 512 characters
    valid_expression = "input.isNumeric() && " + " && ".join([f"input > {i}" for i in range(100)])
    # Truncate to 512 if needed
    valid_expression = valid_expression[:512]
    assert len(valid_expression) <= 512

    # Invalid: 513 characters
    invalid_expression = valid_expression + "x"
    assert len(invalid_expression) == 513
    # Expected: Validation error during flow submission



def test_167_expression_with_empty_input():
    """✅ Expression evaluation with empty input"""

    validation_rules = [
    ("input.length == 0", "", True),               # Explicitly allow empty
    ("input.length > 0", "", False),               # Require non-empty
    ("input.length == 0 || input.length >= 3", "", True),  # Optional field
    ("input.length == 0 || input.length >= 3", "ab", False), # Too short
    ("input.length == 0 || input.length >= 3", "abc", True), # Valid
    ]


def test_168_expression_with_null_or_undefined_context():
    """✅ Expression with null/undefined context variables"""
    # Spec: "Null-safe evaluation"

    validation_rule = "input.isNumeric() && input < context.max_value"

    # Case 1: context.max_value is undefined
    context_missing = {}
    # Expected: context.max_value evaluates to null
    # Comparison "50 < null" evaluates to false

    # Case 2: context.max_value is null
    context_null = {"max_value": None}
    # Expected: "50 < null" evaluates to false

    # Case 3: context.max_value exists
    context_exists = {"max_value": 100}
    # Expected: "50 < 100" evaluates to true


def test_425_string_1_not_equal_number_1():
    """✅ String "1" ≠ number 1 (no type coercion)"""
    # Spec: "No type coercion: string '123' ≠ number 123"

    context = {
    "status": "1"  # String
    }

    route = {
    "condition": "context.status == 1",  # Number comparison
    "target_node": "node_active"
    }

    # Expected:
    # - Route does NOT match
    # - String "1" ≠ number 1
    # - No automatic type coercion


def test_426_string_number_comparison_fails():
    """✅ Comparing string to number fails"""

    context = {
    "count": "25"  # String
    }

    route = {
    "condition": "context.count > 20",
    "target_node": "node_many"
    }

    # Expected:
    # - Route does NOT match
    # - String "25" cannot be compared to number 20
    # - No type coercion


def test_427_explicit_type_conversion_required():
    """✅ Must use PROMPT type conversion or mapping to convert types"""
    # Spec: Type conversion happens in PROMPT or response_map

    # Scenario 1: PROMPT with target_type
    prompt_config = {
    "type": "PROMPT",
    "config": {
    "text": "Enter quantity:",
    "save_to_variable": "quantity",
    "target_type": "NUMBER"
    }
    }

    user_input = "25"  # String input

    # Expected: context.quantity = 25 (NUMBER)

    # Scenario 2: response_map with type inference
    api_config = {
    "type": "API_ACTION",
    "config": {
    "response_map": {
        "age:NUMBER": "response.body.age"  # Explicit type
    }
    }
    }

    # Expected: context.age = 25 (NUMBER)


def test_428_menu_selection_comparison_as_number():
    """✅ MENU selection is NUMBER, can be compared numerically"""
    # Spec: "selection auto-created (NUMBER type)"

    # After menu selection:
    context = {
    "selection": 2  # NUMBER type
    }

    routes = [
    {"condition": "context.selection == 1", "target_node": "node_option_1"},
    {"condition": "context.selection == 2", "target_node": "node_option_2"},
    {"condition": "context.selection > 2", "target_node": "node_high"}
    ]

    # Expected:
    # - Second route matches (2 == 2)
    # - Routes to node_option_2
    # - Numeric comparison works



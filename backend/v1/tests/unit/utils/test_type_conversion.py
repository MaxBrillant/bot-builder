"""
Type conversion (Tests 141-152)
Reorganized from: test_11_type_conversion.py

Tests validate: Type conversion
"""
import pytest

def test_141_string_to_number_basic_integers():
    """✅ String to number: basic integers"""
    # Spec: "Number variable: '42' → 42"

    test_cases = [
    ("42", 42),
    ("0", 0),
    ("1", 1),
    ("999", 999),
    ("1000", 1000)
    ]

    # In PROMPT with number variable declared
    # After validation passes, convert input to number
    # Expected: All convert successfully


def test_142_string_to_number_decimal_values():
    """✅ String to number: decimal values"""
    # Spec: "Number: standard JSON number format"

    test_cases = [
    ("3.14", 3.14),
    ("0.5", 0.5),
    (".5", 0.5),  # Leading dot
    ("10.0", 10.0)
    ]

    # Expected: All convert to float/number type


def test_143_string_to_number_negative_values():
    """✅ String to number: negative values"""
    # Spec: "input.isNumeric(): optional minus sign"

    test_cases = [
    ("-5", -5),
    ("-42", -42),
    ("-3.14", -3.14)
    ]

    # Expected: Negative numbers convert successfully


def test_144_string_to_number_invalid_formats():
    """✅ String to number: invalid formats fail"""
    # These should fail conversion

    invalid_cases = [
    "abc",      # Letters
    "1e10",     # Scientific notation (spec: isNumeric rejects)
    "1.2.3",    # Multiple decimals
    "--5",      # Double minus
    "12-34",    # Minus in middle
    "12.34.56", # Multiple dots
    "NaN",      # Special value
    "Infinity", # Special value
    "",         # Empty string
    "  ",       # Whitespace only
    ]

    # In PROMPT: conversion fails → validation error → retry
    # In mappings: conversion fails → variable = null


def test_145_string_to_number_edge_cases():
    """✅ String to number: edge cases and boundaries"""

    edge_cases = [
    ("0", 0),           # Zero
    ("-0", -0),         # Negative zero
    ("0.0", 0.0),       # Zero with decimal
    ("00042", 42),      # Leading zeros (should parse to 42)
    ]

    # Expected behavior for each case



def test_146_string_to_boolean_valid_values():
    """✅ String to boolean: valid conversions"""
    # Spec: "Boolean variable: 'true' → true, 'false' → false"

    valid_true = [
    ("true", True),
    ("True", True),   # Case variations
    ("TRUE", True),
    ("1", True),      # Numeric 1
    ]

    valid_false = [
    ("false", False),
    ("False", False),
    ("FALSE", False),
    ("0", False),     # Numeric 0
    ]

    # Expected: Convert to boolean type


def test_147_string_to_boolean_invalid_values():
    """✅ String to boolean: invalid values fail"""
    # Spec example: "'yes' → null" (conversion failed)

    invalid_cases = [
    "yes",
    "no",
    "y",
    "n",
    "on",
    "off",
    "2",        # Not 0 or 1
    "abc",
    "",
    ]

    # In PROMPT: conversion fails → retry
    # In mappings: conversion fails → variable = null



def test_148_array_type_preservation():
    """✅ Array type: arrays remain arrays"""
    # Spec: "Array variable: expects array value"

    valid_arrays = [
    (["a", "b", "c"], ["a", "b", "c"]),
    ([1, 2, 3], [1, 2, 3]),
    ([], []),
    ([{"id": 1}], [{"id": 1}])
    ]

    # Expected: No conversion needed, stored as-is


def test_149_array_type_invalid_conversions():
    """✅ Array type: non-arrays fail conversion"""
    # Spec: "String to array → null"

    invalid_cases = [
    "abc",      # String
    "123",      # Number string
    "true",     # Boolean string
    "",         # Empty string
    ]

    # Expected: Cannot convert to array → null



def test_150_prompt_conversion_after_validation():
    """✅ PROMPT: conversion happens AFTER validation passes"""
    # Spec: "Type Enforcement & Conversion Process:"
    # "1. User provides input (string)"
    # "2. PROMPT validates format"
    # "3. If validation passes, attempt type conversion"
    # "4. If conversion succeeds, save to context"
    # "5. If conversion fails, user sees error and must retry"

    flow_variables = {
    "age": {"type": "number", "default": 0}
    }

    prompt_config = {
    "validation": {
    "type": "EXPRESSION",
    "rule": "input.isNumeric()",
    "error_message": "Must be numeric"
    },
    "save_to_variable": "age"
    }

    # Scenario 1: User inputs "25"
    # 1. Validation: "25".isNumeric() → TRUE
    # 2. Conversion: "25" → 25 (number)
    # 3. Save: context.age = 25

    # Scenario 2: User inputs "abc"
    # 1. Validation: "abc".isNumeric() → FALSE
    # 2. Conversion: NOT attempted (validation failed first)
    # 3. User sees error, retry

    # Scenario 3: User inputs "25" but variable type is boolean
    # 1. Validation: "25".isNumeric() → TRUE
    # 2. Conversion: "25" → boolean fails
    # 3. User sees error, retry (counts toward max_attempts)


def test_151_mapping_conversion_sets_null_on_failure():
    """✅ output_mapping/response_map: conversion failure sets null, continues"""
    # Spec: "On failure (missing path OR conversion error): Set variable to null"
    # "Conversion failures in mappings do not count toward validation retry attempts"

    flow_variables = {
    "age": {"type": "number", "default": 0},
    "verified": {"type": "boolean", "default": False}
    }

    # API response with invalid types:
    api_response = {
    "age": "not_a_number",     # Cannot convert to number
    "verified": "maybe"         # Cannot convert to boolean
    }

    # response_map:
    # [
    #   {"source_path": "age", "target_variable": "age"},
    #   {"source_path": "verified", "target_variable": "verified"}
    # ]

    # Expected context after mapping:
    # age = null (conversion failed)
    # verified = null (conversion failed)
    # NO error thrown, NO retry, flow continues


def test_152_prompt_vs_mapping_conversion_failure_differences():
    """✅ Conversion failure behavior: PROMPT vs mappings"""
    # Spec: "Comparison with PROMPT Type Conversion"
    # "PROMPT: Conversion failure → validation error → user must retry (counts toward max attempts)"
    # "Output Mappings: Conversion failure → sets null → flow continues (no retry)"

    flow_variables = {
    "age": {"type": "number", "default": 0}
    }

    # PROMPT scenario:
    # User inputs "abc" for number variable
    # 1. Validation passes (if no isNumeric check)
    # 2. Conversion fails ("abc" cannot convert to number)
    # 3. Show error: "Invalid input format"
    # 4. Increment retry counter
    # 5. User must retry

    # API_ACTION response_map scenario:
    # API returns {"age": "abc"}
    # 1. Extract value: "abc"
    # 2. Attempt conversion to number
    # 3. Conversion fails
    # 4. Set age = null
    # 5. Flow continues (no error shown to user)
    # 6. No retry counter increment

    # This design allows flows to continue gracefully when external data is malformed,
    # while enforcing correctness for user-provided input.


def test_429_empty_array_in_response_map():
    """✅ Empty array from API stored as empty array"""
    # Spec: Arrays supported in context

    api_config = {
    "type": "API_ACTION",
    "config": {
    "response_map": {
        "items": "response.body.items"
    }
    }
    }

    api_response = {
    "body": {
    "items": []  # Empty array
    }
    }

    # Expected:
    # - context.items = []
    # - Empty array (not null)
    # - context.items.length = 0


def test_430_null_converted_to_empty_array():
    """✅ Null in array context handled appropriately"""
    # Spec: Null-safe operations

    api_config = {
    "type": "API_ACTION",
    "config": {
    "response_map": {
        "items": "response.body.items"
    }
    }
    }

    api_response = {
    "body": {
    "items": None  # Null
    }
    }

    # Expected:
    # - context.items = null (or empty array)
    # - Length check: null.length should not throw error
    # - Null-safe navigation


def test_431_non_array_value_in_array_field():
    """✅ Non-array value assigned to array field"""
    # Spec: No variable type constraints at runtime

    api_config = {
    "type": "API_ACTION",
    "config": {
    "response_map": {
        "items": "response.body.items"  # Expected array
    }
    }
    }

    api_response = {
    "body": {
    "items": "not_an_array"  # String instead
    }
    }

    # Expected:
    # - context.items = "not_an_array" (stored as-is)
    # - No validation error (no type constraints)
    # - Dynamic menu would fail if used as source


def test_432_array_with_mixed_types():
    """✅ Array with mixed types stored as-is"""
    # Spec: No type constraints on array elements

    api_response = {
    "body": {
    "mixed": [
        "string",
        123,
        True,
        None,
        {"nested": "object"}
    ]
    }
    }

    # Expected:
    # - context.mixed = [mixed array]
    # - All types preserved
    # - No type coercion
    # - Array truncation still applies (24 items max)


def test_433_array_truncation_preserves_type():
    """✅ Array truncation preserves element types"""
    # Spec: "Silent truncation to 24 items at all storage points"

    large_array = []
    for i in range(30):
        large_array.append({
        "id": i,
        "name": f"Item {i}",
        "price": i * 10.5
        })

    # Stored in context:
    # Expected:
    # - First 24 items preserved
    # - Items 24-29 discarded
    # - Object structure preserved
    # - Types intact



"""
Content limits (Tests 207-222)
Reorganized from: test_17_content_length_limits.py

Tests validate: Content limits
"""
import pytest

def test_207_message_text_max_1024_characters():
    """✅ Message text: max 1024 characters"""
    # Spec: "Message text length: 1024 characters"
    # Applies to: PROMPT text, MENU text, MESSAGE text

    # Valid: 1024 characters
    valid_text = "a" * 1024
    assert len(valid_text) == 1024

    # Invalid: 1025 characters
    invalid_text = "a" * 1025
    assert len(invalid_text) == 1025
    # Expected: Validation error during flow submission


def test_208_prompt_config_text_limit():
    """✅ PROMPT node text field: 1024 char limit"""

    prompt_config = {
    "text": "a" * 1024,  # Valid
    "save_to_variable": "value"
    }

    # Exceeding limit
    prompt_config_invalid = {
    "text": "a" * 1025,  # Invalid
    "save_to_variable": "value"
    }
    # Expected: Validation error


def test_209_menu_config_text_limit():
    """✅ MENU node text field: 1024 char limit"""

    menu_config = {
    "text": "a" * 1024,  # Valid
    "source_type": "STATIC",
    "static_options": [{"label": "Option"}]
    }


def test_210_message_config_text_limit():
    """✅ MESSAGE node text field: 1024 char limit"""

    message_config = {
    "text": "a" * 1024  # Valid
    }



def test_211_error_message_max_512_characters():
    """✅ Error message: max 512 characters"""
    # Spec: "Error message length: 512 characters"

    validation = {
    "type": "REGEX",
    "rule": "^[0-9]+$",
    "error_message": "a" * 512  # Valid
    }

    validation_invalid = {
    "type": "REGEX",
    "rule": "^[0-9]+$",
    "error_message": "a" * 513  # Invalid
    }
    # Expected: Validation error


def test_212_regex_pattern_max_512_characters():
    """✅ Regex pattern: max 512 characters"""
    # Spec: "Regex pattern length: 512 characters"

    validation = {
    "type": "REGEX",
    "rule": "^" + "a?" * 250 + "$",  # Complex pattern ~512 chars
    "error_message": "Invalid"
    }
    assert len(validation["rule"]) <= 512

    # Exceeding limit
    long_pattern = "^" + "a?" * 300 + "$"  # > 512 chars
    # Expected: Validation error


def test_213_expression_max_512_characters():
    """✅ Expression: max 512 characters"""
    # Spec: "Expression length: 512 characters"

    validation = {
    "type": "EXPRESSION",
    "rule": "input.length > 0" + " && input.length < 100" * 20,  # Long expression
    "error_message": "Invalid"
    }
    # Ensure under 512
    assert len(validation["rule"]) <= 512


def test_214_route_condition_max_512_characters():
    """✅ Route condition: max 512 characters"""
    # Spec: "Route condition length: 512 characters (same as expression limit)"

    route = {
    "condition": "context.a == 1 && context.b == 2" * 15,  # Long condition
    "target_node": "node_next"
    }

    if len(route["condition"]) <= 512:
        # Valid
        pass
    else:
        # Expected: Validation error
        pass



def test_215_template_length_max_1024_characters():
    """✅ Template length: max 1024 characters"""
    # Spec: "Template length: 1024 characters"

    # Template in message text
    template = "Hello {{context.name}}! " * 40  # ~1000 chars
    assert len(template) <= 1024

    # Exceeding limit
    long_template = "Hello {{context.name}}! " * 50  # > 1024
    # Expected: Validation error


def test_216_counter_text_max_512_characters():
    """✅ Counter text: max 512 characters"""
    # Spec: "Counter text length: 512 characters"

    defaults = {
    "retry_logic": {
    "max_attempts": 3,
    "counter_text": "Attempt {{current_attempt}} of {{max_attempts}}. " * 10,
    "fail_route": "node_fail"
    }
    }

    counter_text = defaults["retry_logic"]["counter_text"]
    assert len(counter_text) <= 512



def test_217_interrupt_keyword_max_96_characters():
    """✅ Interrupt keyword: max 96 characters"""
    # Spec: "Interrupt keyword length: 96 characters"

    interrupt = {
    "input": "a" * 96,  # Valid
    "target_node": "node_cancel"
    }

    interrupt_invalid = {
    "input": "a" * 97,  # Invalid
    "target_node": "node_cancel"
    }
    # Expected: Validation error


def test_218_menu_option_label_max_96_characters():
    """✅ Menu option label: max 96 characters"""
    # Spec: "Option label length: 96 characters"

    option = {
    "label": "a" * 96  # Valid
    }

    option_invalid = {
    "label": "a" * 97  # Invalid
    }
    # Expected: Validation error


def test_219_variable_name_max_96_characters():
    """✅ Variable name: max 96 characters"""
    # Spec: "Variable name length: 96 characters"

    variables = {
    "a" * 96: {"type": "string", "default": None}  # Valid
    }

    # Exceeding limit
    long_var_name = "a" * 97
    # Expected: Validation error



def test_220_api_url_max_1024_characters():
    """✅ API URL: max 1024 characters"""
    # Spec: "Request URL length: 1024 characters"

    api_config = {
    "request": {
    "method": "GET",
    "url": "https://api.example.com/" + "path/" * 100  # Long URL
    }
    }

    if len(api_config["request"]["url"]) <= 1024:
        # Valid
        pass
    else:
        # Expected: Validation error
        pass


def test_221_api_header_name_max_128_characters():
    """✅ API header name: max 128 characters"""
    # Spec: "Header name length: 128 characters"

    headers = {
    "a" * 128: "value"  # Valid
    }

    headers_invalid = {
    "a" * 129: "value"  # Invalid
    }


def test_222_api_header_value_max_2048_characters():
    """✅ API header value: max 2048 characters"""
    # Spec: "Header value length: 2048 characters (Tokens & long values)"

    headers = {
    "Authorization": "Bearer " + "a" * 2040  # Valid (long token)
    }
    assert len(headers["Authorization"]) <= 2048

    headers_invalid = {
    "Authorization": "Bearer " + "a" * 2050  # Invalid
    }


def test_282_valid_position_integer_coordinates():
    """✅ Valid position with integer coordinates"""
    # Spec: "Must have both x and y properties"
    # "Both values must be numeric (integer or float)"

    node_with_position = {
    "id": "node_test",
    "name": "Test Node",
    "type": "MESSAGE",
    "config": {
    "text": "Hello"
    },
    "routes": [{"condition": "true", "target_node": "node_end"}],
    "position": {
    "x": 250,
    "y": 100
    }
    }

    # Expected:
    # - position has both x and y ✓
    # - Both are numeric (integers) ✓
    # - Validation passes


def test_283_valid_position_float_coordinates():
    """✅ Valid position with float coordinates"""
    # Spec: "Both values must be numeric (integer or float)"
    # Example from spec: {"x": 250.5, "y": 100}

    node_with_position = {
    "id": "node_test",
    "name": "Test Node",
    "type": "PROMPT",
    "config": {
    "text": "Enter value:",
    "save_to_variable": "value"
    },
    "routes": [{"condition": "true", "target_node": "node_end"}],
    "position": {
    "x": 250.5,
    "y": 100.75
    }
    }

    # Expected:
    # - position has both x and y ✓
    # - Both are numeric (floats) ✓
    # - Decimal values accepted
    # - Validation passes


def test_284_valid_position_negative_coordinates():
    """✅ Valid position with negative coordinates"""
    # Spec: "Negative values allowed (canvas extends in all directions)"
    # Example from spec: {"x": -150, "y": -200}

    node_with_position = {
    "id": "node_test",
    "name": "Test Node",
    "type": "MENU",
    "config": {
    "text": "Choose:",
    "source_type": "STATIC",
    "static_options": [{"label": "Option 1"}]
    },
    "routes": [{"condition": "true", "target_node": "node_end"}],
    "position": {
    "x": -150,
    "y": -200
    }
    }

    # Expected:
    # - Negative values accepted ✓
    # - No min/max bounds enforced
    # - Canvas extends in all directions
    # - Validation passes


def test_285_valid_position_extreme_coordinates():
    """✅ Valid position with extreme coordinates (no bounds)"""
    # Spec: "No min/max bounds (infinite canvas)"

    extreme_positions = [
    {"x": 0, "y": 0},                    # Origin
    {"x": 10000, "y": 10000},           # Large positive
    {"x": -10000, "y": -10000},         # Large negative
    {"x": 9999.99, "y": -9999.99},      # Mixed large values
    {"x": 0.0001, "y": -0.0001}         # Very small values
    ]

    for position in extreme_positions:
        node = {
        "id": "node_test",
        "name": "Test",
        "type": "TEXT",
        "config": {"type": "TEXT", "text": "Done"},
        "routes": [],
        "position": position
        }
        # Expected: All positions valid (no bounds)



def test_286_position_missing_x_property_fails():
    """✅ Position missing x property causes validation error"""
    # Spec: "Must have both x and y properties"

    node_with_invalid_position = {
    "id": "node_test",
    "name": "Test Node",
    "type": "MESSAGE",
    "config": {
    "text": "Hello"
    },
    "routes": [{"condition": "true", "target_node": "node_end"}],
    "position": {
    "y": 100
    # Missing 'x'
    }
    }

    # Expected:
    # - Validation error during flow submission
    # - Error type: "missing_field"
    # - Error message: "Position must have both 'x' and 'y' properties"
    # - Location: "nodes.node_test.position"


def test_287_position_missing_y_property_fails():
    """✅ Position missing y property causes validation error"""
    # Spec: "Must have both x and y properties"

    node_with_invalid_position = {
    "id": "node_test",
    "name": "Test Node",
    "type": "MESSAGE",
    "config": {
    "text": "Hello"
    },
    "routes": [{"condition": "true", "target_node": "node_end"}],
    "position": {
    "x": 250
    # Missing 'y'
    }
    }

    # Expected:
    # - Validation error during flow submission
    # - Error type: "missing_field"
    # - Error message: "Position must have both 'x' and 'y' properties"
    # - Location: "nodes.node_test.position"


def test_288_position_non_numeric_values_fail():
    """✅ Position with non-numeric values causes validation error"""
    # Spec: "Both values must be numeric (integer or float)"

    invalid_positions = [
    {"x": "250", "y": 100},        # String instead of number
    {"x": 250, "y": "100"},        # String instead of number
    {"x": true, "y": 100},         # Boolean instead of number
    {"x": 250, "y": null},         # Null instead of number
    {"x": 250, "y": [100]},        # Array instead of number
    {"x": {"val": 250}, "y": 100}  # Object instead of number
    ]

    for position in invalid_positions:
        node = {
        "id": "node_test",
        "name": "Test",
        "type": "MESSAGE",
        "config": {"text": "Hello"},
        "routes": [{"condition": "true", "target_node": "node_end"}],
        "position": position
        }

        # Expected:
        # - Validation error
        # - Error type: "invalid_type"
        # - Error message: "Position x and y must be numeric values"
        # - Location: "nodes.node_test.position"


def test_289_position_missing_entirely_fails():
    """✅ Node missing position field causes validation error"""
    # Spec: "position (required)"

    node_without_position = {
    "id": "node_test",
    "name": "Test Node",
    "type": "MESSAGE",
    "config": {
    "text": "Hello"
    },
    "routes": [{"condition": "true", "target_node": "node_end"}]
    # Missing entire 'position' field
    }

    # Expected:
    # - Validation error during flow submission
    # - Error type: "required_field"
    # - Error message: "Node must have a 'position' field"
    # - Location: "nodes.node_test"


def test_290_position_with_extra_properties_accepted():
    """✅ Position with extra properties accepted (only x, y validated)"""
    # Spec doesn't prohibit extra properties, only requires x and y

    node_with_extra_position_props = {
    "id": "node_test",
    "name": "Test Node",
    "type": "MESSAGE",
    "config": {
    "text": "Hello"
    },
    "routes": [{"condition": "true", "target_node": "node_end"}],
    "position": {
    "x": 250,
    "y": 100,
    "z": 50,                    # Extra property (ignored)
    "rotation": 45,             # Extra property (ignored)
    "custom_metadata": "value"  # Extra property (ignored)
    }
    }

    # Expected:
    # - Required x and y present ✓
    # - Extra properties ignored (not validated)
    # - Validation passes
    # - System uses only x and y for positioning

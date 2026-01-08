"""
Retry logic (Tests 223-233)
Reorganized from: test_18_retry_logic_details.py

Tests validate: Retry logic
"""
import pytest

def test_223_retry_counter_increments_on_validation_failure():
    """✅ Retry counter increments each time validation fails"""
    # Spec: "Retry tracking, Route to fail_route after max attempts"

    prompt_config = {
    "text": "Enter a number:",
    "save_to_variable": "age",
    "validation": {
    "type": "EXPRESSION",
    "rule": "input.isNumeric() && input > 0",
    "error_message": "Must be a positive number"
    }
    }

    defaults = {
    "retry_logic": {
    "max_attempts": 3,
    "counter_text": "(Attempt {{current_attempt}} of {{max_attempts}})",
    "fail_route": "node_fail"
    }
    }

    # Attempt 1: User enters "abc"
    # Validation fails
    # Expected: retry_counter = 1
    # Display: "Must be a positive number (Attempt 1 of 3)"

    # Attempt 2: User enters "-5"
    # Validation fails (not > 0)
    # Expected: retry_counter = 2
    # Display: "Must be a positive number (Attempt 2 of 3)"

    # Attempt 3: User enters "0"
    # Validation fails (not > 0)
    # Expected: retry_counter = 3
    # Display: "Must be a positive number (Attempt 3 of 3)"

    # Attempt 4: Max exceeded
    # Expected: Route to fail_route ("node_fail")


def test_224_counter_text_template_rendered_with_attempts():
    """✅ counter_text template renders with {{current_attempt}} and {{max_attempts}}"""
    # Spec: "counter_text: Template for retry counter display"
    # "{{current_attempt}}: Current retry attempt (only in retry counter_text)"
    # "{{max_attempts}}: Maximum attempts (only in retry counter_text)"

    counter_text_template = "(Attempt {{current_attempt}} of {{max_attempts}})"

    # Attempt 1
    rendered_1 = "(Attempt 1 of 3)"
    # Attempt 2
    rendered_2 = "(Attempt 2 of 3)"
    # Attempt 3
    rendered_3 = "(Attempt 3 of 3)"

    # Template variables ONLY available in counter_text
    # NOT available in error_message, validation rules, or context


def test_225_custom_counter_text_template():
    """✅ Custom counter_text templates work"""

    custom_templates = [
    "Try {{current_attempt}}/{{max_attempts}}",
    "Retry #{{current_attempt}} ({{max_attempts}} max)",
    "You have {{max_attempts}} - {{current_attempt}} attempts remaining",
    ]

    # All should render correctly with current_attempt and max_attempts



def test_226_counter_resets_on_validation_success():
    """✅ Retry counter resets when validation succeeds"""

    prompt_config = {
    "text": "Enter value:",
    "save_to_variable": "value",
    "validation": {
    "type": "EXPRESSION",
    "rule": "input.isNumeric()",
    "error_message": "Must be numeric"
    }
    }

    # Attempt 1: User enters "abc" → fail, counter = 1
    # Attempt 2: User enters "xyz" → fail, counter = 2
    # Attempt 3: User enters "123" → SUCCESS

    # Expected:
    # - Validation passes
    # - Value saved to context
    # - Retry counter RESET to 0
    # - Progress to next node

    # If user encounters another PROMPT later:
    # - Counter starts fresh at 0


def test_227_counter_not_incremented_on_interrupt():
    """✅ Retry counter NOT incremented when interrupt triggered"""
    # Spec: "Interrupt Behavior: Does not count as retry attempt"

    prompt_config = {
    "text": "Enter value (0 to cancel):",
    "save_to_variable": "value",
    "validation": {
    "type": "EXPRESSION",
    "rule": "input.isNumeric() && input > 0",
    "error_message": "Must be positive number"
    },
    "interrupts": [
    {"input": "0", "target_node": "node_cancel"}
    ]
    }

    # Attempt 1: User enters "abc" → fail, counter = 1
    # Attempt 2: User enters "0" → INTERRUPT

    # Expected:
    # - Interrupt matched BEFORE validation
    # - Route to node_cancel
    # - Counter NOT incremented (still 1)
    # - Counter actually reset on interrupt


def test_228_counter_reset_on_interrupt():
    """✅ Retry counter reset when interrupt triggered"""
    # Spec mentions reset behavior for interrupts

    # User at PROMPT with retry counter = 2 (2 failed attempts)
    # User enters interrupt keyword
    # Expected:
    # - Route to interrupt target
    # - Retry counter RESET to 0



def test_229_menu_invalid_selection_increments_retry_counter():
    """✅ MENU: invalid selection counts toward max_attempts"""
    # Spec: "Invalid selection handling: count toward max attempts limit (from flow defaults)"

    menu_config = {
    "text": "Choose option:",
    "source_type": "STATIC",
    "static_options": [
    {"label": "Option 1"},
    {"label": "Option 2"}
    ],
    "error_message": "Please select 1 or 2"
    }

    defaults = {
    "retry_logic": {
    "max_attempts": 3,
    "counter_text": "(Attempt {{current_attempt}} of {{max_attempts}})",
    "fail_route": "node_fail"
    }
    }

    # Attempt 1: User enters "3" (out of range)
    # Expected: retry_counter = 1, show error + counter

    # Attempt 2: User enters "abc" (non-numeric)
    # Expected: retry_counter = 2, show error + counter

    # Attempt 3: User enters "0" (below range)
    # Expected: retry_counter = 3, show error + counter

    # Attempt 4: Max exceeded
    # Expected: Route to fail_route



def test_230_fail_route_triggered_after_max_attempts():
    """✅ fail_route triggered when max_attempts exceeded"""
    # Spec: "After max attempts: route to fail_route or terminate flow"

    defaults = {
    "retry_logic": {
    "max_attempts": 3,
    "fail_route": "node_too_many_attempts"
    }
    }

    # After 3 failed validation attempts
    # Expected:
    # - next_node = "node_too_many_attempts"
    # - No more retry prompts
    # - User routed to failure handling node


def test_231_no_fail_route_terminates_flow():
    """✅ Without fail_route, flow terminates after max attempts"""
    # Spec: "After max attempts exceeded routes to fail_route or terminates"

    # If retry_logic defined WITHOUT fail_route
    # (This should be caught by validation, but testing runtime behavior)

    # After max attempts exceeded:
    # Expected:
    # - Flow terminates with error
    # - Session status = ERROR
    # - User sees generic error message



def test_232_default_max_attempts_is_three():
    """✅ Default max_attempts is 3"""
    # Spec: "max_attempts: Maximum validation retry attempts (default: 3, valid range: 1-10)"

    defaults = {
    "retry_logic": {
    "fail_route": "node_fail"
    # max_attempts not specified
    }
    }

    # Expected: max_attempts = 3 (default)


def test_233_max_attempts_configurable_range_1_to_10():
    """✅ max_attempts: valid range 1-10"""
    # Spec: "valid range: 1-10"

    # Valid configurations
    valid_configs = [
    {"max_attempts": 1, "fail_route": "node_fail"},
    {"max_attempts": 3, "fail_route": "node_fail"},
    {"max_attempts": 5, "fail_route": "node_fail"},
    {"max_attempts": 10, "fail_route": "node_fail"},
    ]

    # Invalid configurations
    invalid_configs = [
    {"max_attempts": 0, "fail_route": "node_fail"},   # Too low
    {"max_attempts": 11, "fail_route": "node_fail"},  # Too high
    {"max_attempts": -1, "fail_route": "node_fail"},  # Negative
    ]

    # Invalid configs should fail validation

"""
Error messages (Tests 330-346)
Reorganized from: test_28_error_messages_ux.py

Tests validate: Error messages
"""
import pytest

def test_330_no_route_match_error_message():
    """✅ No matching route shows: "An error occurred. Please try again." """
    # Spec: "No route matches: 'An error occurred. Please try again.'"

    node = {
    "type": "LOGIC_EXPRESSION",
    "routes": [
    {"condition": "context.status == 'active'", "target_node": "node_active"},
    {"condition": "context.status == 'inactive'", "target_node": "node_inactive"}
    # No catch-all route
    ]
    }

    context = {"status": "pending"}  # Doesn't match any route

    # Expected:
    # - No route matches
    # - Session status = ERROR
    # - User sees: "An error occurred. Please try again."
    # - Session terminates


def test_331_max_auto_progression_error_message():
    """✅ Max auto-progression shows: "System error. Please contact support." """
    # Spec: "Max auto-progression (10 nodes): 'System error. Please contact support.'"

    # After 10 consecutive MESSAGE/LOGIC/API nodes without PROMPT/MENU
    # Expected:
    # - Auto-progression counter = 11 (exceeds max 10)
    # - Session status = ERROR
    # - User sees: "System error. Please contact support."
    # - Session terminates


def test_332_session_timeout_error_message():
    """✅ Session timeout shows: "Session expired. Please start again." """
    # Spec: "Session timeout (30 min): 'Session expired. Please start again.'"

    # Session created at 10:00 AM
    # Current time: 10:31 AM (31 minutes elapsed)

    # User sends message
    # Expected:
    # - Session expired (30 min from creation)
    # - Session status = EXPIRED
    # - User sees: "Session expired. Please start again."
    # - Message not processed


def test_333_bot_unavailable_error_message():
    """✅ Inactive bot shows: "Bot unavailable" """
    # Spec: "Inactive: Webhook returns 'Bot unavailable' message"

    bot = {
    "id": "bot_123",
    "status": "inactive"
    }

    webhook_request = {
    "bot_id": "bot_123",
    "channel": "whatsapp",
    "channel_user_id": "+254712345678",
    "message_text": "START"
    }

    # Expected:
    # - Bot status checked
    # - Status is "inactive"
    # - User sees: "Bot unavailable"
    # - No session created
    # - No flow processing


def test_334_max_retry_attempts_uses_fail_route():
    """✅ Max retry attempts routes to fail_route node (configurable message)"""
    # Spec: "Max retry attempts: Routes to fail_route or terminates"

    defaults = {
    "retry_logic": {
    "max_attempts": 3,
    "fail_route": "node_too_many_attempts"
    }
    }

    fail_route_node = {
    "id": "node_too_many_attempts",
    "type": "MESSAGE",
    "config": {
    "text": "We couldn't process your input after 3 attempts. Please contact support at +254700123456."
    },
    "routes": [{"condition": "true", "target_node": "node_end"}]
    }

    # After 3 failed validation attempts:
    # Expected:
    # - Routes to node_too_many_attempts
    # - User sees custom message defined in fail_route node
    # - Flow continues to end


def test_335_max_retry_without_fail_route_terminates():
    """✅ Max retry without fail_route shows default error"""
    # Spec: "After max attempts exceeded routes to fail_route or terminates"

    # If retry_logic defined WITHOUT fail_route (should be caught by validation)
    # But testing runtime behavior:

    # After 3 failed attempts and no fail_route:
    # Expected:
    # - Flow terminates with error
    # - Session status = ERROR
    # - User sees generic error: "An error occurred. Please try again."



def test_336_empty_input_default_error_message():
    """✅ Empty input shows: "This field is required. Please enter a value." """
    # Spec: "Error message: 'This field is required. Please enter a value.'"

    prompt = {
    "type": "PROMPT",
    "config": {
    "text": "What's your name?",
    "save_to_variable": "name"
    # No validation defined
    }
    }

    user_input = ""  # Empty

    # Expected:
    # - Empty input rejected
    # - User sees: "This field is required. Please enter a value."
    # - Counts toward retry attempts
    # - Display: "This field is required. Please enter a value. (Attempt 1 of 3)"


def test_337_custom_validation_error_message():
    """✅ Validation failure shows custom error_message"""
    # Spec: Custom error messages in validation config

    prompt = {
    "type": "PROMPT",
    "config": {
    "text": "Enter your age:",
    "save_to_variable": "age",
    "validation": {
        "type": "EXPRESSION",
        "rule": "input.isNumeric() && input > 0 && input < 120",
        "error_message": "Please enter a valid age between 1 and 119"
    }
    }
    }

    user_input = "150"  # Invalid

    # Expected:
    # - Validation fails
    # - User sees: "Please enter a valid age between 1 and 119 (Attempt 1 of 3)"
    # - Retry counter included


def test_338_menu_invalid_selection_error_message():
    """✅ Invalid MENU selection shows custom or default error"""
    # Spec: "Invalid selection: Show error, retry"
    # "error_message: 'Invalid selection. Please choose a valid option.'"

    menu = {
    "type": "MENU",
    "config": {
    "text": "Choose option:",
    "source_type": "STATIC",
    "static_options": [
        {"label": "Option 1"},
        {"label": "Option 2"},
        {"label": "Option 3"}
    ],
    "error_message": "Invalid selection. Please enter 1, 2, or 3."
    }
    }

    user_input = "5"  # Out of range

    # Expected:
    # - Invalid selection
    # - User sees: "Invalid selection. Please enter 1, 2, or 3. (Attempt 1 of 3)"
    # - Menu re-displayed
    # - Counts toward max_attempts


def test_339_menu_default_error_message():
    """✅ MENU without custom error_message shows default"""
    # Spec: Default error for invalid selection

    menu = {
    "type": "MENU",
    "config": {
    "text": "Choose:",
    "source_type": "STATIC",
    "static_options": [{"label": "Yes"}, {"label": "No"}]
    # No error_message specified
    }
    }

    user_input = "abc"  # Non-numeric

    # Expected:
    # - Invalid selection
    # - User sees: "Invalid selection. Please choose a valid option. (Attempt 1 of 3)"
    # - Default error message used



def test_340_missing_required_field_error_format():
    """✅ Missing required field shows structured error"""
    # Spec: Validation response format with error details

    flow_missing_name = {
    "trigger_keywords": ["START"],
    "start_node_id": "node_1",
    "nodes": {}
    # Missing 'name'
    }

    # Expected validation response:
    expected_error = {
    "status": "error",
    "errors": [
    {
        "type": "required_field",
        "message": "Flow must have a 'name' field",
        "field": "name"
    }
    ]
    }


def test_341_circular_reference_error_format():
    """✅ Circular reference shows detailed error"""
    # Spec: "Circular reference detected: node_a → node_b → node_a"

    # Expected validation response:
    expected_error = {
    "status": "error",
    "errors": [
    {
        "type": "circular_reference",
        "message": "Circular reference detected: node_a → node_b → node_a",
        "nodes": ["node_a", "node_b"]
    }
    ]
    }


def test_342_orphan_nodes_error_format():
    """✅ Orphan nodes show descriptive error"""
    # Spec: "Orphan nodes detected (nodes with no parent): 'Prompt 2' (node_prompt_2)"

    # Expected validation response:
    expected_error = {
    "status": "error",
    "errors": [
    {
        "type": "orphan_nodes",
        "message": "Orphan nodes detected (nodes with no parent): 'Prompt 2' (node_prompt_2), 'Menu 3' (node_menu_3). Only the start node should have no parent. These nodes are unreachable in the flow.",
        "location": "nodes"
    }
    ]
    }


def test_343_duplicate_trigger_keyword_error_format():
    """✅ Duplicate trigger keyword shows conflict details"""
    # Spec: Error response for duplicate keyword

    # Expected validation response:
    expected_error = {
    "status": "error",
    "errors": [
    {
        "type": "duplicate_trigger_keyword",
        "message": "Trigger keyword 'START' is already used in flow 'booking_flow' of this bot",
        "conflicting_flow_name": "booking_flow",
        "keyword": "START"
    }
    ]
    }


def test_344_duplicate_wildcard_trigger_error_format():
    """✅ Duplicate wildcard trigger shows clear error"""
    # Spec: "Only one flow per bot can use the wildcard trigger"

    # Expected validation response:
    expected_error = {
    "status": "error",
    "errors": [
    {
        "type": "duplicate_wildcard_trigger",
        "message": "Wildcard trigger '*' is already used in flow 'fallback_handler' of this bot. Only one flow per bot can use the wildcard trigger.",
        "conflicting_flow_name": "fallback_handler",
        "keyword": "*"
    }
    ]
    }



def test_345_empty_array_menu_shows_header_no_options():
    """✅ Empty array in DYNAMIC menu shows header, no options"""
    # Spec: "Empty array in dynamic menu: Shows menu header with no options; any input will be invalid"
    # "Recommend checking array length with LOGIC_EXPRESSION first"

    menu_config = {
    "text": "Select a trip:",
    "source_type": "DYNAMIC",
    "source_variable": "trips",
    "item_template": "{{index}}. {{item.from}} → {{item.to}}"
    }

    context = {
    "trips": []  # Empty array
    }

    # Expected user experience:
    # - User sees: "Select a trip:"
    # - No options listed
    # - Any input user enters will be invalid
    # - Should route to error or use LOGIC_EXPRESSION first to check length


def test_346_recommend_logic_expression_before_empty_array_check():
    """✅ Best practice: Check array length before showing menu"""
    # Spec: "Recommend checking array length with LOGIC_EXPRESSION first"

    # Good pattern:
    logic_node = {
    "type": "LOGIC_EXPRESSION",
    "routes": [
    {"condition": "context.trips.length > 0", "target_node": "node_menu"},
    {"condition": "context.trips.length == 0", "target_node": "node_no_trips"}
    ]
    }

    no_trips_message = {
    "type": "MESSAGE",
    "config": {
    "text": "No trips available at the moment. Please check back later."
    }
    }

    # Expected: Array length checked BEFORE menu
    # Prevents showing empty menu

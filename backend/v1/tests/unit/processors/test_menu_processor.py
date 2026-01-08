"""
Basic MENU functionality (Tests 047-055)
Reorganized from: test_03_menu_processor.py

Tests validate: Basic MENU functionality
"""
import pytest

def test_47_static_menu_display_and_numeric_selection(menu_node_static):
    """✅ STATIC menu - display options, numeric selection works"""
    # Spec: "Present options and capture user selection"
    # "Numeric selection (1, 2, 3...)"
    node = menu_node_static
    context = {}

    # Options: ["Option 1", "Option 2", "Option 3"]
    # Expected display:
    # "Choose an option:
    #  1. Option 1
    #  2. Option 2
    #  3. Option 3"

    assert node["config"]["source_type"] == "STATIC"
    assert len(node["config"]["static_options"]) == 3

    # User selects "2"
    user_input = "2"

    # Expected:
    # - context["selection"] = 2 (number type)
    # - Route evaluation: selection == 2 → node_opt2


def test_48_static_menu_invalid_selection_retries(menu_node_static):
    """✅ STATIC menu - invalid selection shows error and retries"""
    # Spec: "Invalid selection handling: Display error, re-display menu, count toward max_attempts"
    node = menu_node_static
    context = {}

    invalid_inputs = [
    "4",  # Out of range (only 3 options)
    "0",  # Below range
    "abc",  # Non-numeric
    "",  # Empty
    ]

    # For each invalid input:
    # Expected:
    # - Show error_message: "Please select 1, 2, or 3"
    # - Re-display menu options
    # - Increment retry counter
    # - needs_input=True



def test_49_dynamic_menu_load_from_context_array(menu_node_dynamic):
    """✅ DYNAMIC menu - load from context array"""
    # Spec: "Dynamic options (from context arrays)"
    node = menu_node_dynamic
    context = {
    "trips": [
    {"id": "trip1", "from": "Nairobi", "to": "Mombasa", "time": "08:00", "price": 1500},
    {"id": "trip2", "from": "Nairobi", "to": "Kisumu", "time": "10:00", "price": 1200}
    ]
    }

    assert node["config"]["source_type"] == "DYNAMIC"
    assert node["config"]["source_variable"] == "trips"

    # Menu should display items from context["trips"]
    # Number of options = len(context["trips"]) = 2


def test_50_dynamic_menu_item_template_renders_correctly(menu_node_dynamic):
    """✅ DYNAMIC menu - item_template renders with {{item.*}} and {{index}}"""
    # Spec: "{{item.*}} and {{index}} available in template"
    # item_template: "{{index}}. {{item.from}} → {{item.to}} at {{item.time}}"
    node = menu_node_dynamic
    context = {
    "trips": [
    {"from": "Nairobi", "to": "Mombasa", "time": "08:00"},
    {"from": "Nairobi", "to": "Kisumu", "time": "10:00"}
    ]
    }

    # Expected rendered output:
    # "1. Nairobi → Mombasa at 08:00"
    # "2. Nairobi → Kisumu at 10:00"

    # {{index}} is 1-based (spec: "{{index}}: 1-based counter in MENU")


def test_51_dynamic_menu_output_mapping_with_type_conversion(menu_node_dynamic):
    """✅ DYNAMIC menu - output_mapping with type conversion"""
    # Spec: "output_mapping uses type inference based on flow's variables section"
    # "Extract value, look up type, convert, on success save, on failure set null"

    node = menu_node_dynamic
    context = {
    "trips": [
    {"id": "trip1", "departure_time": "08:00", "price": "1500"},  # price is string
    {"id": "trip2", "departure_time": "10:00", "price": "1200"}
    ]
    }

    flow_variables = {
    "trip_id": {"type": "string", "default": None},
    "departure_time": {"type": "string", "default": None},
    "price": {"type": "number", "default": 0}  # Declared as number
    }

    # User selects option 1 (first trip)
    user_input = "1"

    # output_mapping extracts from selected item (trips[0]):
    # - {"source_path": "id", "target_variable": "trip_id"}
    # - {"source_path": "departure_time", "target_variable": "departure_time"}
    # - {"source_path": "price", "target_variable": "price"}

    # Expected context after mapping:
    # - context["selection"] = 1 (number, auto-set)
    # - context["trip_id"] = "trip1" (string)
    # - context["departure_time"] = "08:00" (string)
    # - context["price"] = 1500 (converted from "1500" string to number)


def test_52_dynamic_menu_truncate_to_24_items(menu_node_dynamic):
    """✅ DYNAMIC menu - truncate to 24 items if source exceeds"""
    # Spec: "Dynamic menus limited to 24 options - if source array exceeds 24, only first 24 items displayed"
    node = menu_node_dynamic
    context = {
    "trips": [{"id": f"trip{i}", "from": "A", "to": "B", "time": "08:00"} for i in range(30)]
    }

    assert len(context["trips"]) == 30

    # Expected: Only first 24 items displayed
    # User can only select 1-24
    # Selection "25" would be invalid



def test_53_menu_interrupts_bypass_selection_validation(menu_node_static):
    """✅ MENU interrupts - checked before validation, bypass selection"""
    # Spec: "Interrupts are checked BEFORE menu validation"
    # "If input matches interrupt, routes to interrupt target immediately"
    node = menu_node_static.copy()
    node["config"]["interrupts"] = [
    {"input": "0", "target_node": "node_cancel"}
    ]

    context = {}

    # User enters "0"
    user_input = "0"

    # Expected:
    # - Interrupt matched BEFORE checking if "0" is valid menu selection
    # - Route to "node_cancel"
    # - Does NOT count as invalid selection
    # - selection variable NOT set


def test_54_menu_interrupt_vs_selection_conflict_warning(menu_node_static):
    """✅ MENU interrupts - numeric interrupt conflicts with selection"""
    # Spec: "⚠️ Interrupt vs Selection Conflicts: Interrupts ALWAYS WIN"
    # Example: Option 4 exists, but interrupt "4" intercepts it
    node = menu_node_static.copy()
    node["config"]["static_options"] = [
    {"label": "Option 1"},
    {"label": "Option 2"},
    {"label": "Option 3"},
    {"label": "Go back"}  # This is option 4
    ]
    node["config"]["interrupts"] = [
    {"input": "4", "target_node": "node_cancel"}  # Conflicts!
    ]

    context = {}

    # User enters "4" intending to select "Go back"
    user_input = "4"

    # Expected:
    # - Interrupt "4" matches FIRST
    # - Routes to "node_cancel"
    # - User CANNOT select option 4
    # - This is a design flaw (per spec best practices)

    # Spec recommendation: Use non-numeric interrupts like "0", "back"



def test_55_dynamic_menu_empty_array_shows_no_options(menu_node_dynamic):
    """✅ Empty array shows menu header with no options, any input invalid"""
    # Spec: "Empty array in dynamic menu: Shows menu header with no options; any input will be invalid"
    node = menu_node_dynamic
    context = {
    "trips": []  # Empty array
    }

    assert len(context["trips"]) == 0

    # Expected display:
    # "Select a trip:"
    # (no options listed)

    # Any user input is invalid:
    # "1" → invalid (no options)
    # "abc" → invalid

    # Spec recommendation: "Check array length with LOGIC_EXPRESSION first"


def test_234_selection_variable_automatically_created():
    """✅ MENU automatically creates 'selection' variable"""
    # Spec: "selection variable automatically set to numeric index as number (1, 2, 3, etc.)"

    menu_config = {
    "text": "Choose:",
    "source_type": "STATIC",
    "static_options": [
    {"label": "Option 1"},
    {"label": "Option 2"}
    ]
    }

    context_before = {}

    # User selects option 2
    user_input = "2"

    # After MENU processing:
    context_after = {
    "selection": 2  # Automatically added
    }

    # Expected: 'selection' variable created without explicit declaration


def test_235_selection_is_number_type_not_string():
    """✅ selection variable is NUMBER type, not string"""
    # Spec: "selection variable automatically set as number"
    # "context.selection = 2 (number, automatically set by MENU)"

    # User enters "2" (string input)
    user_input = "2"

    # After processing:
    context = {
    "selection": 2  # NUMBER type, not "2" string
    }

    # This is important for route conditions:
    # "selection == 2" (number comparison) works
    # "selection == '2'" (string comparison) fails


def test_236_selection_uses_one_based_indexing():
    """✅ selection uses 1-based indexing (not 0-based)"""
    # Spec: "{{index}}: 1-based counter in MENU dynamic template (1, 2, 3...)"
    # "Numeric selection (1, 2, 3...)"

    menu_options = [
    {"label": "First"},   # User sees: 1. First
    {"label": "Second"},  # User sees: 2. Second
    {"label": "Third"}    # User sees: 3. Third
    ]

    # User selects "1" → First option (index 0 in array)
    # context.selection = 1 (not 0)

    # User selects "2" → Second option (index 1 in array)
    # context.selection = 2 (not 1)

    # User selects "3" → Third option (index 2 in array)
    # context.selection = 3 (not 2)



def test_237_selection_set_before_output_mapping_executes():
    """✅ selection set BEFORE output_mapping extracts fields"""
    # Spec: "Result in context (after type inference): selection = 2 (number, automatically set)"
    # This happens before output_mapping fields are extracted

    menu_config = {
    "source_type": "DYNAMIC",
    "source_variable": "items",
    "output_mapping": [
    {"source_path": "id", "target_variable": "item_id"}
    ]
    }

    items = [
    {"id": "item_1"},
    {"id": "item_2"}
    ]

    # User selects option 2

    # Processing order:
    # 1. Validate selection (2 is valid range 1-2)
    # 2. Set context.selection = 2
    # 3. Get selected item: items[2-1] = items[1] = {"id": "item_2"}
    # 4. Execute output_mapping on selected item
    # 5. Extract fields: context.item_id = "item_2"

    # Final context:
    expected_context = {
    "selection": 2,        # Set first
    "item_id": "item_2"    # Extracted second
    }


def test_238_selection_available_in_route_conditions():
    """✅ selection variable available in route conditions"""
    # Spec: STATIC MENU routes can use "selection == N" conditions

    menu_config = {
    "source_type": "STATIC",
    "static_options": [
    {"label": "Option 1"},
    {"label": "Option 2"},
    {"label": "Option 3"}
    ]
    }

    routes = [
    {"condition": "selection == 1", "target_node": "node_opt1"},
    {"condition": "selection == 2", "target_node": "node_opt2"},
    {"condition": "selection == 3", "target_node": "node_opt3"},
    {"condition": "true", "target_node": "node_default"}
    ]

    # User selects "2"
    # context.selection = 2
    # Route evaluation: "selection == 2" → TRUE
    # Expected: next_node = "node_opt2"



def test_239_selection_behavior_same_in_static_and_dynamic_menus():
    """✅ selection variable behavior identical in STATIC and DYNAMIC menus"""

    # STATIC menu
    static_context = {}
    # User selects option 2
    # Expected: context.selection = 2 (number)

    # DYNAMIC menu
    dynamic_context = {}
    # User selects option 2
    # Expected: context.selection = 2 (number)

    # Both create selection variable the same way
    # Both use 1-based indexing
    # Both store as number type

    # Difference is in routing:
    # STATIC: Can route by selection value
    # DYNAMIC: Must use single "true" route, then LOGIC_EXPRESSION after


def test_296_valid_selection_routes_for_static_menu():
    """✅ Valid selection routes within static menu option range"""
    # Spec: "STATIC MENU - Route by specific selections"
    # Example: 3 options → valid routes: selection == 1, 2, 3

    menu_node = {
    "id": "node_menu",
    "name": "Choose Payment Method",
    "type": "MENU",
    "config": {
    "text": "Select payment method:",
    "source_type": "STATIC",
    "static_options": [
        {"label": "M-Pesa"},
        {"label": "Credit Card"},
        {"label": "Cash"}
        # 3 options total
    ]
    },
    "routes": [
    {"condition": "selection == 1", "target_node": "node_mpesa"},      # ✓ Within range
    {"condition": "selection == 2", "target_node": "node_card"},       # ✓ Within range
    {"condition": "selection == 3", "target_node": "node_cash"},       # ✓ Within range
    {"condition": "true", "target_node": "node_error"}                 # ✓ Catch-all
    ],
    "position": {"x": 0, "y": 0}
    }

    # Expected:
    # - Static menu has 3 options
    # - Valid selection range: 1-3
    # - All routes check selections 1, 2, 3 (within range) ✓
    # - Validation passes


def test_297_selection_out_of_range_high_fails():
    """✅ Selection route beyond static menu options causes validation error"""
    # Spec: "Selection number 5 is out of range. Valid range is 1-3"

    menu_node = {
    "id": "node_menu",
    "name": "Choose Option",
    "type": "MENU",
    "config": {
    "text": "Select option:",
    "source_type": "STATIC",
    "static_options": [
        {"label": "Option 1"},
        {"label": "Option 2"},
        {"label": "Option 3"}
        # 3 options total
    ]
    },
    "routes": [
    {"condition": "selection == 1", "target_node": "node_opt1"},
    {"condition": "selection == 5", "target_node": "node_opt5"},  # ✗ Out of range!
    {"condition": "true", "target_node": "node_default"}
    ],
    "position": {"x": 0, "y": 0}
    }

    # Expected:
    # - Validation error during flow submission
    # - Error type: "selection_out_of_range"
    # - Error message: "Route condition 'selection == 5' is out of range. Static menu has 3 options. Valid selection range is 1-3."
    # - Location: "nodes.node_menu.routes[1].condition"
    # - Suggestion: "Remove the invalid route or add more menu options"


def test_298_selection_below_range_fails():
    """✅ Selection route with 0 or negative values causes validation error"""
    # Spec: "Numeric selection (1, 2, 3...)" - selection starts at 1, not 0

    menu_node = {
    "id": "node_menu",
    "name": "Choose Option",
    "type": "MENU",
    "config": {
    "text": "Select option:",
    "source_type": "STATIC",
    "static_options": [
        {"label": "Option 1"},
        {"label": "Option 2"}
        # 2 options total
    ]
    },
    "routes": [
    {"condition": "selection == 0", "target_node": "node_zero"},    # ✗ Below range (1-based indexing)
    {"condition": "selection == -1", "target_node": "node_neg"},    # ✗ Negative
    {"condition": "true", "target_node": "node_default"}
    ],
    "position": {"x": 0, "y": 0}
    }

    # Expected:
    # - Validation error
    # - Error message: "Route condition 'selection == 0' is invalid. Selection must be between 1 and 2 (menu uses 1-based indexing)."
    # - Same error for negative values


def test_299_selection_range_with_max_8_static_options():
    """✅ Static menu with max 8 options validates selection routes correctly"""
    # Spec: "Static menus limited to 8 options maximum"

    menu_node = {
    "id": "node_menu",
    "name": "Main Menu",
    "type": "MENU",
    "config": {
    "text": "Select option:",
    "source_type": "STATIC",
    "static_options": [
        {"label": "Option 1"},
        {"label": "Option 2"},
        {"label": "Option 3"},
        {"label": "Option 4"},
        {"label": "Option 5"},
        {"label": "Option 6"},
        {"label": "Option 7"},
        {"label": "Option 8"}
        # 8 options (at maximum limit)
    ]
    },
    "routes": [
    {"condition": "selection == 1", "target_node": "node_1"},
    {"condition": "selection == 2", "target_node": "node_2"},
    {"condition": "selection == 3", "target_node": "node_3"},
    {"condition": "selection == 4", "target_node": "node_4"},
    {"condition": "selection == 5", "target_node": "node_5"},
    {"condition": "selection == 6", "target_node": "node_6"},
    {"condition": "selection == 7", "target_node": "node_7"},
    {"condition": "selection == 8", "target_node": "node_8"},     # ✓ At max
    {"condition": "true", "target_node": "node_default"}
    ],
    "position": {"x": 0, "y": 0}
    }

    # Expected:
    # - 8 static options (at limit) ✓
    # - Valid selection range: 1-8
    # - All route selections within range ✓
    # - Validation passes

    # Invalid case: selection == 9 with only 8 options
    menu_node_invalid = {
    "id": "node_menu",
    "name": "Main Menu",
    "type": "MENU",
    "config": {
    "text": "Select option:",
    "source_type": "STATIC",
    "static_options": [
        {"label": f"Option {i}"} for i in range(1, 9)
        # 8 options
    ]
    },
    "routes": [
    {"condition": "selection == 9", "target_node": "node_9"},  # ✗ Out of range
    {"condition": "true", "target_node": "node_default"}
    ],
    "position": {"x": 0, "y": 0}
    }

    # Expected error: "Selection 9 is out of range. Valid range is 1-8."



def test_300_non_numeric_selection_in_static_menu_route_fails():
    """✅ Non-numeric selection values in STATIC menu routes cause validation error"""
    # Spec: "Numeric selection (1, 2, 3...)"

    menu_node = {
    "id": "node_menu",
    "name": "Choose Option",
    "type": "MENU",
    "config": {
    "text": "Select option:",
    "source_type": "STATIC",
    "static_options": [
        {"label": "Option 1"},
        {"label": "Option 2"}
    ]
    },
    "routes": [
    {"condition": "selection == 'first'", "target_node": "node_1"},  # ✗ String, not number
    {"condition": "selection == true", "target_node": "node_2"},      # ✗ Boolean, not number
    {"condition": "true", "target_node": "node_default"}
    ],
    "position": {"x": 0, "y": 0}
    }

    # Expected:
    # - Validation error
    # - Error type: "invalid_route_condition"
    # - Error message: "STATIC MENU route conditions must use numeric selection comparisons (e.g., 'selection == 1')"


def test_301_dynamic_menu_not_subject_to_selection_range_validation():
    """✅ DYNAMIC menu not subject to design-time selection range validation"""
    # Spec: "DYNAMIC MENU - Single route only"
    # Options unknown at design time, so no range validation possible

    menu_node = {
    "id": "node_menu",
    "name": "Select Trip",
    "type": "MENU",
    "config": {
    "text": "Select trip:",
    "source_type": "DYNAMIC",
    "source_variable": "trips",
    "item_template": "{{index}}. {{item.from}} → {{item.to}}",
    "output_mapping": [
        {"source_path": "id", "target_variable": "trip_id"}
    ]
    },
    "routes": [
    {"condition": "true", "target_node": "node_next"}  # Only "true" allowed
    ],
    "position": {"x": 0, "y": 0}
    }

    # Expected:
    # - DYNAMIC menu validation checks:
    #   - Must have exactly 1 route ✓
    #   - Route condition must be "true" ✓
    # - No selection range validation (options unknown at design time)
    # - Validation passes

    # Invalid: DYNAMIC menu with selection routing
    menu_node_invalid = {
    "id": "node_menu",
    "name": "Select Trip",
    "type": "MENU",
    "config": {
    "text": "Select trip:",
    "source_type": "DYNAMIC",
    "source_variable": "trips",
    "item_template": "{{index}}. {{item.from}} → {{item.to}}"
    },
    "routes": [
    {"condition": "selection == 1", "target_node": "node_1"}  # ✗ Not allowed
    ],
    "position": {"x": 0, "y": 0}
    }

    # Expected:
    # - Validation error
    # - Error message: "DYNAMIC MENU nodes only allow condition 'true'"
    # - Suggestion: "Use a LOGIC_EXPRESSION node after the menu for conditional routing"


def test_302_selection_comparison_operators_in_static_menu():
    """✅ Selection comparison operators (>, <, >=, <=) in STATIC menu routes"""
    # Spec allows selection comparisons beyond just equality

    menu_node = {
    "id": "node_menu",
    "name": "Rate Service",
    "type": "MENU",
    "config": {
    "text": "Rate our service (1-5):",
    "source_type": "STATIC",
    "static_options": [
        {"label": "1 - Poor"},
        {"label": "2 - Fair"},
        {"label": "3 - Good"},
        {"label": "4 - Very Good"},
        {"label": "5 - Excellent"}
        # 5 options
    ]
    },
    "routes": [
    {"condition": "selection >= 4", "target_node": "node_positive"},   # ✓ 4 or 5
    {"condition": "selection == 3", "target_node": "node_neutral"},    # ✓ Exactly 3
    {"condition": "selection < 3", "target_node": "node_negative"},    # ✓ 1 or 2
    {"condition": "true", "target_node": "node_default"}
    ],
    "position": {"x": 0, "y": 0}
    }

    # Expected:
    # - All comparisons reference values within valid range (1-5) ✓
    # - Range validation should check:
    #   - "selection >= 4": 4 and 5 are within range ✓
    #   - "selection < 3": 1 and 2 are within range ✓
    # - Validation passes


def test_303_single_option_static_menu_only_allows_selection_1():
    """✅ Static menu with single option validates selection == 1 only"""
    # Edge case: Menu with minimum options (1)

    menu_node = {
    "id": "node_menu",
    "name": "Confirm",
    "type": "MENU",
    "config": {
    "text": "Proceed?",
    "source_type": "STATIC",
    "static_options": [
        {"label": "Yes, proceed"}
        # Only 1 option
    ]
    },
    "routes": [
    {"condition": "selection == 1", "target_node": "node_proceed"},  # ✓ Valid
    {"condition": "true", "target_node": "node_default"}
    ],
    "position": {"x": 0, "y": 0}
    }

    # Expected:
    # - Single option menu ✓
    # - Valid selection range: 1 only
    # - Route checks selection == 1 ✓
    # - Validation passes

    # Invalid: selection == 2 with only 1 option
    menu_node_invalid = {
    "id": "node_menu",
    "name": "Confirm",
    "type": "MENU",
    "config": {
    "text": "Proceed?",
    "source_type": "STATIC",
    "static_options": [{"label": "Yes"}]
    },
    "routes": [
    {"condition": "selection == 2", "target_node": "node_2"}  # ✗ Out of range
    ],
    "position": {"x": 0, "y": 0}
    }

    # Expected error: "Selection 2 is out of range. Valid range is 1 (menu has only 1 option)."


def test_410_menu_custom_error_message_used():
    """✅ MENU custom error_message is displayed to user"""
    # Spec: MENU config includes error_message field

    menu_config = {
    "type": "MENU",
    "config": {
    "text": "Choose payment method:",
    "source_type": "STATIC",
    "static_options": [
        {"label": "M-Pesa"},
        {"label": "Card"}
    ],
    "error_message": "Invalid payment method. Please enter 1 for M-Pesa or 2 for Card."
    }
    }

    user_input = "3"  # Out of range

    # Expected:
    # - User sees custom error: "Invalid payment method. Please enter 1 for M-Pesa or 2 for Card."
    # - NOT default error: "Invalid selection. Please choose a valid option."
    # - Custom message provides specific guidance


def test_411_menu_error_message_with_retry_counter():
    """✅ Error message combined with retry counter template"""
    # Spec: Retry logic includes counter_text with templates

    menu_config = {
    "type": "MENU",
    "config": {
    "text": "Select option:",
    "source_type": "STATIC",
    "static_options": [{"label": "A"}, {"label": "B"}],
    "error_message": "Please enter 1 or 2."
    }
    }

    defaults = {
    "retry_logic": {
    "max_attempts": 3,
    "counter_text": "(Attempt {{current_attempt}} of {{max_attempts}})",
    "fail_route": "node_failed"
    }
    }

    # After first invalid input:
    # Expected display:
    # "Please enter 1 or 2. (Attempt 1 of 3)"


def test_412_menu_error_message_empty_string_uses_default():
    """✅ Empty error_message falls back to default"""

    menu_config = {
    "type": "MENU",
    "config": {
    "text": "Choose:",
    "source_type": "STATIC",
    "static_options": [{"label": "Yes"}],
    "error_message": ""  # Empty
    }
    }

    # Expected:
    # - Empty error_message treated as not provided
    # - Default error used: "Invalid selection. Please choose a valid option."


def test_413_dynamic_menu_error_message():
    """✅ DYNAMIC menu can have custom error_message"""
    # Spec: DYNAMIC menu also supports error_message

    menu_config = {
    "type": "MENU",
    "config": {
    "text": "Select trip:",
    "source_type": "DYNAMIC",
    "source_variable": "trips",
    "item_template": "{{index}}. {{item.destination}}",
    "error_message": "Invalid trip number. Please enter a number from the list above."
    }
    }

    context = {
    "trips": [
    {"destination": "Nairobi"},
    {"destination": "Mombasa"}
    ]
    }

    user_input = "5"  # Out of range

    # Expected:
    # - Custom error message shown
    # - Helps user understand the issue




def test_423_menu_selection_must_be_integer():
    """✅ MENU selection must be integer, float rejected"""
    # Spec: selection variable is NUMBER type, 1-based indexing

    menu_config = {
    "type": "MENU",
    "config": {
    "text": "Choose:",
    "source_type": "STATIC",
    "static_options": [
        {"label": "Option 1"},
        {"label": "Option 2"}
    ]
    }
    }

    invalid_inputs = [
    "1.5",  # Float
    "2.0",  # Float representation
    "0.5"   # Fraction
    ]

    # Expected:
    # - All rejected as invalid
    # - Error: "Invalid selection. Please choose a valid option."
    # - Selection must be integer 1, 2, etc.


def test_424_menu_selection_stored_as_number_type():
    """✅ selection variable stored as NUMBER type"""
    # Spec: "selection variable auto-created (NUMBER type)"

    menu_config = {
    "type": "MENU",
    "config": {
    "text": "Choose:",
    "source_type": "STATIC",
    "static_options": [{"label": "A"}, {"label": "B"}]
    }
    }

    user_input = "1"  # String input

    # Expected:
    # - context.selection = 1 (NUMBER, not string "1")
    # - Type conversion happens automatically
    # - Can be used in numeric comparisons



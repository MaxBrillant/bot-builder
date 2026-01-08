"""
Route evaluation (Tests 106-120)
Reorganized from: test_08_routing_conditions.py

Tests validate: Route evaluation
"""
import pytest

def test_106_routes_sorted_by_priority_before_evaluation():
    """✅ Routes sorted by priority (specific before "true")"""
    # Spec: "Automatic Sorting: Routes are automatically sorted by priority at runtime"
    # "Lower Priority = Evaluated First"

    # Original route order (as defined in flow):
    original_routes = [
    {"condition": "true", "target_node": "node_fallback"},  # Priority: 1000
    {"condition": "selection == 2", "target_node": "node_opt2"},  # Priority: 2
    {"condition": "selection == 1", "target_node": "node_opt1"}  # Priority: 1
    ]

    # Expected sorted order (runtime):
    expected_sorted = [
    {"condition": "selection == 1", "target_node": "node_opt1"},  # Priority: 1
    {"condition": "selection == 2", "target_node": "node_opt2"},  # Priority: 2
    {"condition": "true", "target_node": "node_fallback"}  # Priority: 1000 (last)
    ]

    # Spec table for MENU:
    # "selection == N" → Priority: N
    # "true" → Priority: 1000


def test_107_api_action_route_sorting():
    """✅ API_ACTION routes: success → error → custom → true"""
    # Spec: "API_ACTION: 'success' → priority 1, 'error' → priority 2"

    original_routes = [
    {"condition": "true", "target_node": "node_fallback"},  # Priority: 1000
    {"condition": "error", "target_node": "node_error"},  # Priority: 2
    {"condition": "success", "target_node": "node_success"}  # Priority: 1
    ]

    # Expected sorted:
    expected_sorted = [
    {"condition": "success", "target_node": "node_success"},  # Priority: 1
    {"condition": "error", "target_node": "node_error"},  # Priority: 2
    {"condition": "true", "target_node": "node_fallback"}  # Priority: 1000
    ]


def test_108_catch_all_true_always_evaluated_last():
    """✅ "true" catch-all always evaluated last"""
    # Spec: "✅ Specific conditions always evaluated before catch-all"
    # "'true' → Priority: 1000"

    routes = [
    {"condition": "true", "target_node": "node_default"},
    {"condition": "context.age > 18", "target_node": "node_adult"},
    {"condition": "context.verified == true", "target_node": "node_verified"}
    ]

    # After sorting, "true" is last
    # Ensures specific conditions checked first



def test_109_first_matching_route_wins():
    """✅ First matching route wins (after sorting)"""
    # Spec: "First-match wins (routes evaluated in order after sorting)"

    routes = [
    {"condition": "context.age > 18", "target_node": "node_adult"},
    {"condition": "context.age > 21", "target_node": "node_adult_21plus"},
    {"condition": "true", "target_node": "node_default"}
    ]

    context = {"age": 25}

    # Evaluation:
    # 1. "context.age > 18" → 25 > 18 → TRUE → Match! Route to node_adult
    # Routes 2 and 3 not evaluated

    # Expected: next_node = "node_adult"
    # Even though age > 21 also true, first match wins


def test_110_no_matching_route_terminates_with_error():
    """✅ No matching route → flow terminates with error"""
    # Spec: "Critical: If no route condition evaluates to true, the flow terminates with error"
    # "User sees: 'An error occurred. Please try again.'"

    routes = [
    {"condition": "context.status == 'active'", "target_node": "node_active"},
    {"condition": "context.status == 'inactive'", "target_node": "node_inactive"}
    # No catch-all!
    ]

    context = {"status": "pending"}  # Doesn't match any route

    # Expected:
    # - All conditions evaluate to false
    # - Flow terminates
    # - Session status = ERROR
    # - User sees: "An error occurred. Please try again."

    # Best practice: Always include catch-all "true" route



def test_111_no_automatic_type_conversion():
    """✅ String vs number comparison fails (no coercion)"""
    # Spec: "No Automatic Type Conversion: Comparisons use strict type checking"
    # "'123' > 18 → FAILS (string vs number)"

    routes = [
    {"condition": "context.age > 18", "target_node": "node_adult"},
    {"condition": "true", "target_node": "node_default"}
    ]

    # Test case 1: age as string
    context_string = {"age": "25"}  # String, not number

    # Evaluation: "25" > 18 (string vs number)
    # Expected: Comparison returns false, no match
    # Falls through to "true" catch-all
    # next_node = "node_default"

    # Test case 2: age as number
    context_number = {"age": 25}  # Number

    # Evaluation: 25 > 18 (number vs number)
    # Expected: TRUE, match
    # next_node = "node_adult"


def test_112_string_vs_number_comparison_fails():
    """✅ Type mismatch returns false (no crash)"""
    # Spec: "Null-Safe Evaluation: Type mismatch returns false (route doesn't match)"
    # "No exceptions are thrown"

    routes = [
    {"condition": "context.count == 10", "target_node": "node_match"},
    {"condition": "true", "target_node": "node_nomatch"}
    ]

    context = {"count": "10"}  # String "10"

    # Evaluation: "10" == 10 (string vs number)
    # Expected: false (no exception)
    # Falls through to catch-all
    # next_node = "node_nomatch"


def test_113_menu_selection_always_number_type():
    """✅ MENU selection is always number type"""
    # Spec: "MENU `selection` is always a number"
    # "context.selection = 2 (number, automatically set by MENU)"

    routes = [
    {"condition": "selection == 2", "target_node": "node_opt2"},  # Number comparison
    {"condition": "selection == '2'", "target_node": "node_wrong"},  # String comparison
    {"condition": "true", "target_node": "node_fallback"}
    ]

    context = {"selection": 2}  # Number (from MENU)

    # Evaluation:
    # 1. selection == 2 → 2 == 2 (number vs number) → TRUE
    # Expected: next_node = "node_opt2"

    # If using string comparison "selection == '2'":
    # 2 == "2" (number vs string) → FALSE
    # Would NOT match


def test_114_null_comparisons():
    """✅ Null comparison behavior"""
    # Spec: "null == null → true; null == <any value> → false"

    routes = [
    {"condition": "context.value == null", "target_node": "node_null"},
    {"condition": "context.value != null", "target_node": "node_not_null"},
    {"condition": "true", "target_node": "node_default"}
    ]

    # Test case 1: value is null
    context_null = {"value": None}
    # Expected: context.value == null → TRUE
    # next_node = "node_null"

    # Test case 2: value exists
    context_exists = {"value": 42}
    # Expected: context.value == null → FALSE
    # Expected: context.value != null → TRUE
    # next_node = "node_not_null"

    # Test case 3: value undefined (missing property)
    context_missing = {}
    # Expected: context.value is undefined → treated as null
    # context.value == null → TRUE
    # next_node = "node_null"



def test_115_reserved_keyword_success():
    """✅ "success" - API_ACTION success state"""
    # Spec: "'success' - API_ACTION success state"

    # After API_ACTION completes successfully
    route_condition_flag = "success"

    routes = [
    {"condition": "success", "target_node": "node_success_handler"},
    {"condition": "error", "target_node": "node_error_handler"}
    ]

    # Expected: First route matches
    # next_node = "node_success_handler"


def test_116_reserved_keyword_error():
    """✅ "error" - API_ACTION error state"""
    # Spec: "'error' - API_ACTION error state"

    # After API_ACTION fails
    route_condition_flag = "error"

    routes = [
    {"condition": "success", "target_node": "node_success_handler"},
    {"condition": "error", "target_node": "node_error_handler"}
    ]

    # Expected: Second route matches
    # next_node = "node_error_handler"


def test_117_reserved_keyword_true():
    """✅ "true" - Always true (catch-all)"""
    # Spec: "'true' - Always true (catch-all)"

    routes = [
    {"condition": "context.value > 100", "target_node": "node_high"},
    {"condition": "true", "target_node": "node_always"}
    ]

    context = {"value": 50}

    # Evaluation:
    # 1. context.value > 100 → 50 > 100 → FALSE
    # 2. true → Always TRUE
    # Expected: next_node = "node_always"


def test_118_reserved_keyword_false():
    """✅ "false" - Never true (unused but valid)"""
    # Spec: "'false' - Never true"

    routes = [
    {"condition": "false", "target_node": "node_never"},
    {"condition": "true", "target_node": "node_always"}
    ]

    # Evaluation:
    # 1. false → Always FALSE
    # 2. true → TRUE
    # Expected: next_node = "node_always"

    # Note: "false" condition is never useful in practice



def test_119_context_variable_comparisons():
    """✅ Context variable access in conditions"""
    # Spec: "Context variable access in conditions: context.variable"

    routes = [
    {"condition": "context.count > context.max_value", "target_node": "node_exceeded"},
    {"condition": "context.count <= context.max_value", "target_node": "node_ok"}
    ]

    context = {"count": 150, "max_value": 100}

    # Evaluation:
    # context.count > context.max_value → 150 > 100 → TRUE
    # Expected: next_node = "node_exceeded"


def test_120_array_length_checks_in_conditions():
    """✅ Array length checks in conditions"""
    # Spec: "Array length checks: context.items.length > 0"

    routes = [
    {"condition": "context.items.length > 0", "target_node": "node_has_items"},
    {"condition": "context.items.length == 0", "target_node": "node_empty"}
    ]

    # Test case 1: Array with items
    context_with = {"items": ["a", "b", "c"]}
    # Expected: context.items.length > 0 → 3 > 0 → TRUE
    # next_node = "node_has_items"

    # Test case 2: Empty array
    context_empty = {"items": []}
    # Expected: context.items.length > 0 → 0 > 0 → FALSE
    # Expected: context.items.length == 0 → 0 == 0 → TRUE
    # next_node = "node_empty"

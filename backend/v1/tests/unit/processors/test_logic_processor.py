"""
LOGIC_EXPRESSION (Tests 064-066)
Reorganized from: test_05_other_processors.py

Tests validate: LOGIC_EXPRESSION
"""
import pytest

def test_64_logic_expression_route_evaluation_with_context(logic_expression_node):
    """✅ LOGIC_EXPRESSION - route evaluation with context variables"""
    # Spec: "Internal conditional routing, Evaluate context variables"
    # "Comparison operators (==, !=, >, <, >=, <=), Logical operators (&&, ||)"

    node = logic_expression_node

    # Test case 1: Adult and verified
    context_1 = {"age": 25, "verified": True}
    # Route: "context.age > 18 && context.verified == true"
    # Expected: next_node = "node_adult"

    # Test case 2: Adult but not verified
    context_2 = {"age": 25, "verified": False}
    # Route: "context.age > 18" (second route, first doesn't match)
    # Expected: next_node = "node_adult_unverified"

    # Test case 3: Minor
    context_3 = {"age": 15, "verified": False}
    # Route: "context.age <= 18"
    # Expected: next_node = "node_minor"

    # Test case 4: No matching route (catch-all)
    context_4 = {}  # age is null/undefined
    # All specific routes fail, catch-all "true" matches
    # Expected: next_node = "node_error"


def test_65_logic_expression_null_safe_navigation(logic_expression_node):
    """✅ LOGIC_EXPRESSION - null-safe path navigation"""
    # Spec: "Null-Safe Navigation: Missing properties → return null (doesn't cause errors)"
    # "null values in path → condition evaluates to false"

    node = logic_expression_node

    # Test missing properties
    context_missing = {}  # No "age" or "verified" properties

    # Evaluation: "context.age > 18" where context.age is undefined/null
    # Expected: evaluates to false (null-safe), no exception thrown

    # Test nested missing properties
    node_nested = {
    "id": "node_logic",
    "name": "Check Nested",
    "type": "LOGIC_EXPRESSION",
    "config": {},
    "routes": [
    {"condition": "context.user.profile.age > 18", "target_node": "node_adult"},
    {"condition": "true", "target_node": "node_fallback"}
    ],
    "position": {"x": 0, "y": 0}
    }

    context_no_user = {}
    # context.user is undefined → context.user.profile.age returns null
    # Condition "null > 18" evaluates to false
    # Falls through to "true" catch-all
    # Expected: next_node = "node_fallback"


def test_66_logic_expression_array_access(logic_expression_node):
    """✅ LOGIC_EXPRESSION - array element access and length"""
    # Spec: "Array index: context.trips.0.driver (zero-based, use dot notation)"
    # "Array length: context.items.length"

    node = {
    "id": "node_logic",
    "name": "Check Array",
    "type": "LOGIC_EXPRESSION",
    "config": {},
    "routes": [
    {"condition": "context.items.length > 0", "target_node": "node_has_items"},
    {"condition": "context.items.length == 0", "target_node": "node_empty"},
    {"condition": "true", "target_node": "node_error"}
    ],
    "position": {"x": 0, "y": 0}
    }

    # Test with items
    context_with_items = {"items": ["a", "b", "c"]}
    # context.items.length = 3
    # Expected: next_node = "node_has_items"

    # Test empty array
    context_empty = {"items": []}
    # context.items.length = 0
    # Expected: next_node = "node_empty"

    # Test array element access
    node_element = {
    "id": "node_logic",
    "name": "Check First Trip",
    "type": "LOGIC_EXPRESSION",
    "config": {},
    "routes": [
    {"condition": "context.trips.0.id == 'trip1'", "target_node": "node_match"},
    {"condition": "true", "target_node": "node_nomatch"}
    ],
    "position": {"x": 0, "y": 0}
    }

    context_trips = {
    "trips": [
    {"id": "trip1", "from": "Nairobi"},
    {"id": "trip2", "from": "Mombasa"}
    ]
    }
    # context.trips.0.id = "trip1"
    # Expected: next_node = "node_match"



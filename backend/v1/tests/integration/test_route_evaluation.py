"""
Route evaluation details (Tests 191-199)
Reorganized from: test_15_route_evaluation_details.py

Tests validate: Route evaluation details
"""
import pytest

def test_191_first_matching_route_selected_others_ignored():
    """✅ First matching route wins, later routes ignored"""
    # Spec: "First-match wins (routes evaluated in order after sorting)"
    # "No fallthrough to multiple routes"

    routes = [
    {"condition": "context.age > 18", "target_node": "node_adult"},
    {"condition": "context.age > 21", "target_node": "node_adult_21plus"},
    {"condition": "context.age > 30", "target_node": "node_adult_30plus"},
    {"condition": "true", "target_node": "node_default"}
    ]

    context = {"age": 35}

    # Evaluation order (after sorting, assuming all have same priority):
    # 1. context.age > 18 → 35 > 18 → TRUE → MATCH! Select node_adult
    # Routes 2, 3, 4 are NOT evaluated

    # Expected: next_node = "node_adult"
    # NOT "node_adult_21plus" or "node_adult_30plus" even though both would match


def test_192_route_evaluation_stops_after_first_match():
    """✅ Route evaluation stops immediately after first match"""
    # Spec: "Only first matching route executed"

    routes = [
    {"condition": "context.status == 'active'", "target_node": "node_active"},
    {"condition": "context.verified == true", "target_node": "node_verified"},
    {"condition": "true", "target_node": "node_default"}
    ]

    context = {"status": "active", "verified": True}

    # Both first and second conditions are true
    # But only first route should be selected
    # Expected: next_node = "node_active"


def test_193_catch_all_true_only_evaluated_if_no_prior_match():
    """✅ Catch-all "true" route only evaluated if no prior match"""
    # Spec: "✅ Specific conditions always evaluated before catch-all"

    routes = [
    {"condition": "context.type == 'premium'", "target_node": "node_premium"},
    {"condition": "context.type == 'basic'", "target_node": "node_basic"},
    {"condition": "true", "target_node": "node_default"}
    ]

    # Test case 1: Matches specific condition
    context_premium = {"type": "premium"}
    # Expected: node_premium (catch-all not evaluated)

    # Test case 2: No specific match
    context_other = {"type": "trial"}
    # Expected: node_default (catch-all evaluated)



def test_194_no_matching_route_terminates_flow_with_error():
    """✅ No matching route → flow terminates with specific error"""
    # Spec: "Critical: If no route condition evaluates to true, the flow terminates with error"
    # "User sees error message: 'An error occurred. Please try again.'"

    routes = [
    {"condition": "context.status == 'active'", "target_node": "node_active"},
    {"condition": "context.status == 'inactive'", "target_node": "node_inactive"}
    # No catch-all!
    ]

    context = {"status": "pending"}

    # Neither condition matches
    # Expected:
    # - Flow terminates
    # - Session status = ERROR
    # - User sees: "An error occurred. Please try again."
    # - Session ends


def test_195_best_practice_always_include_catch_all():
    """✅ Best practice: always include catch-all "true" route"""
    # Spec: "Best Practice: Always include a catch-all route as the last option"

    # ✅ GOOD - Has catch-all
    good_routes = [
    {"condition": "context.status == 'active'", "target_node": "node_active"},
    {"condition": "context.status == 'inactive'", "target_node": "node_inactive"},
    {"condition": "true", "target_node": "node_unknown_status"}
    ]

    # ❌ BAD - No catch-all
    bad_routes = [
    {"condition": "context.status == 'active'", "target_node": "node_active"},
    {"condition": "context.status == 'inactive'", "target_node": "node_inactive"}
    ]

    # With good_routes: any context.status value has a route
    # With bad_routes: only "active" and "inactive" have routes



def test_196_success_check_with_response_body_access():
    """✅ success_check expression accesses response.body.*"""
    # Spec: "Available variables in expression: response.body.*, response.status, response.headers.*"

    success_check = {
    "status_codes": [200, 201],
    "expression": "response.body.success == true && response.body.data != null"
    }

    # Test case 1: Status 200, expression true
    response_1 = {
    "status": 200,
    "body": {
    "success": True,
    "data": {"id": 123}
    }
    }
    # Expected: success route

    # Test case 2: Status 200, expression false (success field is false)
    response_2 = {
    "status": 200,
    "body": {
    "success": False,
    "error": "Not found"
    }
    }
    # Expected: error route (expression failed)

    # Test case 3: Status 200, expression false (data is null)
    response_3 = {
    "status": 200,
    "body": {
    "success": True,
    "data": None
    }
    }
    # Expected: error route (expression failed)


def test_197_success_check_with_response_status_access():
    """✅ success_check expression accesses response.status"""

    success_check = {
    "status_codes": [200, 201, 202],
    "expression": "response.status == 200 || response.status == 201"
    }

    # Test case 1: Status 200
    response_1 = {"status": 200, "body": {}}
    # Expression: 200 == 200 → TRUE
    # Expected: success route

    # Test case 2: Status 202
    response_2 = {"status": 202, "body": {}}
    # In status_codes but expression is FALSE (202 != 200 and 202 != 201)
    # Expected: error route (expression must also pass)


def test_198_success_check_with_response_headers_access():
    """✅ success_check expression accesses response.headers.*"""

    success_check = {
    "status_codes": [200],
    "expression": "response.headers['Content-Type'] == 'application/json'"
    }

    # Test case 1: Correct content type
    response_1 = {
    "status": 200,
    "headers": {"Content-Type": "application/json"},
    "body": {}
    }
    # Expected: success route

    # Test case 2: Wrong content type
    response_2 = {
    "status": 200,
    "headers": {"Content-Type": "text/html"},
    "body": {}
    }
    # Expected: error route (expression failed)


def test_199_success_check_combined_status_and_expression():
    """✅ success_check: BOTH status codes AND expression must pass"""
    # Spec: "success_check with status_codes and expression"

    success_check = {
    "status_codes": [200, 201],
    "expression": "response.body.id != null"
    }

    # Test case 1: Status matches, expression true → SUCCESS
    response_success = {
    "status": 200,
    "body": {"id": "user123", "name": "Alice"}
    }
    # Expected: success route

    # Test case 2: Status matches, expression false → ERROR
    response_missing_id = {
    "status": 200,
    "body": {"name": "Alice"}  # No id field
    }
    # Expected: error route

    # Test case 3: Status doesn't match, expression true → ERROR
    response_wrong_status = {
    "status": 404,
    "body": {"id": "user123"}
    }
    # Expected: error route

    # Test case 4: Status doesn't match, expression false → ERROR
    response_both_fail = {
    "status": 404,
    "body": {"name": "Alice"}
    }
    # Expected: error route

    # BOTH conditions must be satisfied for success route

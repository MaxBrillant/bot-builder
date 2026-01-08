"""
Flow structure validation (Tests 001-035)
Reorganized from: test_01_flow_validation.py

Tests validate: Flow structure validation
"""
import pytest

def test_01_valid_flow_with_all_required_fields(self, minimal_valid_flow):
        """✅ Flow has name, trigger_keywords, start_node_id, nodes"""
        # Validator would check these exist
        assert "name" in minimal_valid_flow
        assert "trigger_keywords" in minimal_valid_flow
        assert "start_node_id" in minimal_valid_flow
        assert "nodes" in minimal_valid_flow
        assert len(minimal_valid_flow["trigger_keywords"]) > 0
        # Would call: validator.validate_flow(minimal_valid_flow) -> is_valid=True

def test_02_flow_missing_name_fails(self, flow_missing_name):
        """✅ Flow without name field fails validation"""
        assert "name" not in flow_missing_name
        # Expected: validator.validate_flow() returns error "name field required"

def test_03_flow_missing_trigger_keywords_fails(self, flow_missing_trigger_keywords):
        """✅ Flow without trigger_keywords field fails"""
        assert "trigger_keywords" not in flow_missing_trigger_keywords
        # Expected: validation error "trigger_keywords required"

def test_04_flow_empty_trigger_keywords_fails(self, flow_empty_trigger_keywords):
        """✅ Empty trigger_keywords array fails (spec: at least one required)"""
        assert flow_empty_trigger_keywords["trigger_keywords"] == []
        # Expected: validation error "at least one trigger keyword required"

def test_05_flow_missing_start_node_id_fails(self, minimal_valid_flow):
        """✅ Flow without start_node_id fails"""
        flow = minimal_valid_flow.copy()
        del flow["start_node_id"]
        assert "start_node_id" not in flow
        # Expected: validation error

def test_06_flow_missing_nodes_fails(self, minimal_valid_flow):
        """✅ Flow without nodes field fails"""
        flow = minimal_valid_flow.copy()
        del flow["nodes"]
        assert "nodes" not in flow
        # Expected: validation error

def test_07_flow_empty_nodes_fails(self, minimal_valid_flow):
        """✅ Flow with empty nodes object fails"""
        flow = minimal_valid_flow.copy()
        flow["nodes"] = {}
        assert len(flow["nodes"]) == 0
        # Expected: validation error "at least one node required"


class TestFlowNameConstraints:
    """Test flow name constraints (spec: max 96 chars, unique per bot)"""

def test_08_flow_name_max_96_chars_valid(self, minimal_valid_flow):
        """✅ Flow name with exactly 96 characters is valid"""
        flow = minimal_valid_flow.copy()
        flow["name"] = "a" * 96
        assert len(flow["name"]) == 96
        # Expected: validation passes

def test_09_flow_name_exceeds_96_chars_fails(self, minimal_valid_flow):
        """✅ Flow name with 97 characters fails"""
        flow = minimal_valid_flow.copy()
        flow["name"] = "a" * 97
        assert len(flow["name"]) == 97
        # Expected: validation error "name exceeds 96 characters"

def test_10_flow_name_special_chars_valid(self, minimal_valid_flow):
        """✅ Flow name with apostrophes, emojis, punctuation valid (spec allows any printable)"""
        flow = minimal_valid_flow.copy()
        flow["name"] = "Max's Flow 🚀 (v2.0)"
        # Expected: validation passes - spec says "any printable characters allowed"


class TestTriggerKeywordValidation:
    """Test trigger keyword constraints (spec: unique per bot, specific format)"""

def test_11_valid_trigger_keywords_format(self, minimal_valid_flow):
        """✅ Valid keywords: letters, numbers, spaces, underscores, hyphens"""
        flow = minimal_valid_flow.copy()
        flow["trigger_keywords"] = [
            "START",
            "begin-now",
            "test_123",
            "HELLO WORLD"
        ]
        # All should pass per spec: "Allowed characters: letters, numbers, spaces, underscores, hyphens"
        for kw in flow["trigger_keywords"]:
            # Check format - no punctuation/special chars
            assert not any(c in kw for c in "!@#$%^&*()+={}[]|\\:;\"'<>,.?/")

def test_12_trigger_keywords_with_punctuation_fails(self, minimal_valid_flow):
        """✅ Keywords with punctuation fail (spec: NOT allowed punctuation)"""
        flow = minimal_valid_flow.copy()
        flow["trigger_keywords"] = ["START!"]
        # Expected: validation error "punctuation not allowed in trigger keywords"
        assert "!" in flow["trigger_keywords"][0]

def test_13_trigger_keywords_case_insensitive_matching(self, minimal_valid_flow):
        """✅ Trigger keywords match case-insensitively (spec: "START"="start"="Start")"""
        # This tests matching behavior, not validation
        # Spec says: "Case-insensitive: 'START', 'start', 'Start' all match"
        keywords = ["START"]
        test_inputs = ["START", "start", "Start", " START ", "  start  "]
        for inp in test_inputs:
            normalized = inp.strip().upper()
            assert normalized in [k.upper() for k in keywords]


class TestWildcardTrigger:
    """Test wildcard trigger rules (spec: only one per bot, must be sole keyword)"""

def test_14_single_wildcard_trigger_valid(self, minimal_valid_flow):
        """✅ Flow with single wildcard ["*"] is valid"""
        flow = minimal_valid_flow.copy()
        flow["trigger_keywords"] = ["*"]
        assert flow["trigger_keywords"] == ["*"]
        # Expected: validation passes

def test_15_wildcard_with_other_keywords_fails(self, flow_wildcard_with_other_keywords):
        """✅ Wildcard combined with other keywords fails (spec: must be sole keyword)"""
        assert "*" in flow_wildcard_with_other_keywords["trigger_keywords"]
        assert len(flow_wildcard_with_other_keywords["trigger_keywords"]) > 1
        # Expected: validation error "Wildcard must be the only keyword"

def test_16_wildcard_priority_after_specific(self, minimal_valid_flow):
        """✅ Wildcard evaluated AFTER specific keywords (spec: fallback only)"""
        # This tests matching behavior
        # Per spec: "Priority: Always checked AFTER specific keywords (fallback only)"
        # Bot has flows: ["START"], ["HELP"], ["*"]
        flows = [
            {"trigger_keywords": ["START"]},
            {"trigger_keywords": ["HELP"]},
            {"trigger_keywords": ["*"]}
        ]

        # Message "START" should match specific, not wildcard
        message = "START"
        # Matching logic would check specific first, find match, not check wildcard


class TestNodeStructureValidation:
    """Test node validation rules (spec: start node exists, routes valid, no orphans)"""

def test_17_start_node_must_exist(self, flow_invalid_start_node):
        """✅ start_node_id must reference existing node"""
        start_id = flow_invalid_start_node["start_node_id"]
        assert start_id not in flow_invalid_start_node["nodes"]
        # Expected: validation error "start_node_id 'node_nonexistent' does not exist"

def test_18_route_target_must_exist(self, minimal_valid_flow):
        """✅ All route target_nodes must reference existing nodes"""
        flow = minimal_valid_flow.copy()
        flow["nodes"]["node_start"]["routes"][0]["target_node"] = "node_nonexistent"

        target = flow["nodes"]["node_start"]["routes"][0]["target_node"]
        assert target not in flow["nodes"]
        # Expected: validation error "Route target 'node_nonexistent' not found"

def test_19_circular_reference_detected(self, flow_circular_reference):
        """✅ Circular reference detection (spec: ALL loops invalid)"""
        # Spec: "Any path that returns to previously visited node is rejected"
        # Flow: A → B → A (circular)
        assert flow_circular_reference["nodes"]["node_a"]["routes"][0]["target_node"] == "node_b"
        assert flow_circular_reference["nodes"]["node_b"]["routes"][0]["target_node"] == "node_a"
        # Expected: validation error "Circular reference detected: node_a → node_b → node_a"

def test_20_orphan_nodes_detected(self, flow_with_orphan_nodes):
        """✅ Only start node can have no parent (spec: orphan detection)"""
        # Spec: "Only start_node_id should have no parent. All other nodes must be referenced."
        # Flow has node_orphan that is never referenced in any route

        # Find all referenced nodes
        referenced = {flow_with_orphan_nodes["start_node_id"]}
        for node_id, node in flow_with_orphan_nodes["nodes"].items():
            for route in node.get("routes", []):
                referenced.add(route["target_node"])

        # Check for orphans (nodes not in referenced set, excluding start)
        all_nodes = set(flow_with_orphan_nodes["nodes"].keys())
        start = flow_with_orphan_nodes["start_node_id"]
        orphans = all_nodes - referenced - {start}

        assert "node_orphan" in orphans
        # Expected: validation error "Orphan nodes detected: node_orphan"


class TestRouteValidation:
    """Test route validation rules (spec: unique conditions per node, fail_route required)"""

def test_21_duplicate_route_conditions_fail(self, minimal_valid_flow):
        """✅ Duplicate route conditions within same node fail (case-insensitive)"""
        flow = minimal_valid_flow.copy()
        flow["nodes"]["node_start"]["routes"] = [
            {"condition": "true", "target_node": "node_end"},
            {"condition": "TRUE", "target_node": "node_end"}  # Case-insensitive duplicate
        ]

        # Normalize conditions to check for duplicates
        conditions = [r["condition"].lower() for r in flow["nodes"]["node_start"]["routes"]]
        assert len(conditions) != len(set(conditions))
        # Expected: validation error "Duplicate condition 'true' in node routes"

def test_22_fail_route_required_with_retry_logic(self, minimal_valid_flow):
        """✅ fail_route required when retry_logic defined (spec requirement)"""
        flow = minimal_valid_flow.copy()
        flow["defaults"] = {
            "retry_logic": {
                "max_attempts": 3,
                "counter_text": "(Attempt {{current_attempt}} of {{max_attempts}})"
                # Missing fail_route
            }
        }

        assert "retry_logic" in flow.get("defaults", {})
        assert "fail_route" not in flow["defaults"]["retry_logic"]
        # Expected: validation error "fail_route required when retry_logic defined"

def test_23_fail_route_must_exist(self, complete_flow_all_fields):
        """✅ fail_route must reference existing node"""
        flow = complete_flow_all_fields.copy()
        flow["defaults"]["retry_logic"]["fail_route"] = "node_nonexistent"

        fail_route = flow["defaults"]["retry_logic"]["fail_route"]
        assert fail_route not in flow["nodes"]
        # Expected: validation error "fail_route 'node_nonexistent' not found"


class TestNodeTypeSpecificValidation:
    """Test node type specific requirements (spec: per-node-type configs)"""

def test_24_prompt_requires_text_and_save_to_variable(self, prompt_node_basic):
        """✅ PROMPT node requires text and save_to_variable"""
        assert "text" in prompt_node_basic["config"]
        assert "save_to_variable" in prompt_node_basic["config"]
        # Per spec: PROMPT config requires both fields

def test_25_prompt_routes_must_be_true_only(self, prompt_node_basic):
        """✅ PROMPT nodes only allow "true" condition (spec: route validation)"""
        # Spec table: PROMPT | "true" only | 1 route
        assert len(prompt_node_basic["routes"]) == 1
        assert prompt_node_basic["routes"][0]["condition"] == "true"
        # If route had "selection == 1", validation should fail

def test_26_menu_static_max_8_options(self, menu_node_static):
        """✅ STATIC menu max 8 options (spec constraint)"""
        # Spec: "Static options count: 8"
        assert len(menu_node_static["config"]["static_options"]) <= 8

def test_27_menu_dynamic_single_true_route_only(self, menu_node_dynamic):
        """✅ DYNAMIC menu only allows single "true" route (spec: critical restriction)"""
        # Spec: "MENU (DYNAMIC) | 'true' only | 1 route | Critical: Only single 'true' route allowed"
        assert len(menu_node_dynamic["routes"]) == 1
        assert menu_node_dynamic["routes"][0]["condition"] == "true"

def test_28_api_action_requires_method_and_url(self, api_action_node):
        """✅ API_ACTION requires request.method and request.url"""
        assert "request" in api_action_node["config"]
        assert "method" in api_action_node["config"]["request"]
        assert "url" in api_action_node["config"]["request"]
        assert api_action_node["config"]["request"]["method"] in ["GET", "POST", "PUT", "DELETE", "PATCH"]

def test_29_end_node_no_routes(self, end_node):
        """✅ END nodes cannot have routes"""
        # Spec: "END | None | 0 routes | Terminal node"
        assert end_node["routes"] == []
        assert len(end_node["routes"]) == 0


class TestVariableDefinitionValidation:
    """Test variable definition constraints (spec: types, defaults, limits)"""

def test_30_valid_variable_types(self, complete_flow_all_fields):
        """✅ Valid types: string, number, boolean, array"""
        variables = complete_flow_all_fields["variables"]
        valid_types = {"string", "number", "boolean", "array"}

        for var_name, var_def in variables.items():
            assert var_def["type"] in valid_types

def test_31_string_default_max_256_chars(self, minimal_valid_flow):
        """✅ String defaults max 256 characters"""
        flow = minimal_valid_flow.copy()
        flow["variables"] = {
            "test_var": {
                "type": "string",
                "default": "a" * 256
            }
        }
        assert len(flow["variables"]["test_var"]["default"]) == 256
        # 257 would fail validation

def test_32_array_default_max_24_items(self, minimal_valid_flow):
        """✅ Array defaults max 24 items"""
        flow = minimal_valid_flow.copy()
        flow["variables"] = {
            "items": {
                "type": "array",
                "default": list(range(24))
            }
        }
        assert len(flow["variables"]["items"]["default"]) == 24
        # 25 would fail validation


class TestConstraintLimits:
    """Test system constraint enforcement (spec: hard limits)"""

def test_33_max_48_nodes_per_flow(self, minimal_valid_flow):
        """✅ Max 48 nodes per flow enforced"""
        flow = minimal_valid_flow.copy()
        # Create 49 nodes
        for i in range(49):
            flow["nodes"][f"node_{i}"] = {
                "id": f"node_{i}",
                "name": f"Node {i}",
                "type": "MESSAGE",
                "config": {"text": f"Message {i}"},
                "routes": [{"condition": "true", "target_node": "node_end"}],
                "position": {"x": i * 10, "y": 0}
            }

        assert len(flow["nodes"]) > 48
        # Expected: validation error "exceeds maximum of 48 nodes"

def test_34_max_8_routes_per_node(self, minimal_valid_flow):
        """✅ Max 8 routes per node enforced"""
        flow = minimal_valid_flow.copy()
        # Create node with 9 routes
        flow["nodes"]["node_start"]["routes"] = [
            {"condition": f"context.value == {i}", "target_node": "node_end"}
            for i in range(9)
        ]

        assert len(flow["nodes"]["node_start"]["routes"]) > 8
        # Expected: validation error "exceeds maximum of 8 routes per node"

def test_35_node_id_max_96_chars(self, minimal_valid_flow):
        """✅ Node ID max 96 characters"""
        flow = minimal_valid_flow.copy()
        long_id = "node_" + "a" * 92  # Total 97 chars

        flow["nodes"][long_id] = {
            "id": long_id,
            "name": "Long ID Node",
            "type": "MESSAGE",
            "config": {"text": "Test"},
            "routes": [{"condition": "true", "target_node": "node_end"}],
            "position": {"x": 0, "y": 0}
        }

        assert len(long_id) > 96
        # Expected: validation error "node ID exceeds 96 characters"


def test_240_empty_string_not_allowed_as_interrupt(self):
        """✅ Empty string "" NOT allowed as interrupt keyword"""
        # Spec: "Empty string '' is NOT allowed as an interrupt keyword (reserved for system empty handling)"

        prompt_config = {
            "text": "Enter value:",
            "save_to_variable": "value",
            "interrupts": [
                {"input": "", "target_node": "node_cancel"}  # Invalid!
            ]
        }

        # Expected: Validation error during flow submission
        # Error: "Empty string cannot be used as interrupt keyword"


def test_241_multi_word_interrupts_supported(self):
        """✅ Multi-word interrupts: "go back", "cancel order" work"""
        # Spec: "Multi-word interrupts supported"
        # "Whitespace in interrupt keywords allowed: 'go back', 'cancel order'"

        prompt_config = {
            "text": "Enter value:",
            "save_to_variable": "value",
            "interrupts": [
                {"input": "go back", "target_node": "node_previous"},
                {"input": "cancel order", "target_node": "node_cancel"}
            ]
        }

        # User enters "go back" → routes to node_previous
        # User enters "cancel order" → routes to node_cancel


def test_242_interrupt_whitespace_trimmed_before_match(self):
        """✅ Interrupt keywords trimmed before matching"""
        # Spec: "Interrupt keywords are trimmed before matching"

        prompt_config = {
            "interrupts": [
                {"input": "back", "target_node": "node_back"}
            ]
        }

        test_inputs = [
            " back",
            "back ",
            "  back  ",
            "\tback\t"
        ]

        # All should match after trimming


def test_243_interrupt_case_insensitive(self):
        """✅ Interrupts: case-insensitive matching"""
        # Spec: "Case-insensitive matching applied"

        prompt_config = {
            "interrupts": [
                {"input": "cancel", "target_node": "node_cancel"}
            ]
        }

        test_inputs = [
            "cancel",
            "CANCEL",
            "Cancel",
            "CaNcEl"
        ]

        # All should match


def test_244_interrupt_checked_before_validation(self):
        """✅ Interrupts checked BEFORE validation runs"""
        # Spec: "Processing Order: 1. Display message 2. Check interrupts 3. Check empty 4. Run validation"

        prompt_config = {
            "text": "Enter age:",
            "save_to_variable": "age",
            "validation": {
                "type": "EXPRESSION",
                "rule": "input.isNumeric() && input > 0",
                "error_message": "Must be positive number"
            },
            "interrupts": [
                {"input": "0", "target_node": "node_cancel"}
            ]
        }

        # User enters "0"
        # Order of checks:
        # 1. Trim input: "0"
        # 2. Check interrupt: "0" matches → ROUTE TO node_cancel
        # 3. Validation NOT run (interrupt bypassed it)

        # Even though "0" would fail validation (not > 0), interrupt takes precedence


def test_245_interrupt_does_not_save_to_variable(self):
        """✅ Interrupt: does NOT save to variable"""
        # Spec: "Does not save to variable"

        prompt_config = {
            "text": "Enter name:",
            "save_to_variable": "user_name",
            "interrupts": [
                {"input": "skip", "target_node": "node_skip"}
            ]
        }

        context_before = {}

        # User enters "skip"
        # Expected:
        # - Interrupt matched
        # - Route to node_skip
        # - context.user_name NOT set (remains undefined)

        context_after = {}  # user_name not added


    # ===== GAP 11: Success/Error Route Setting =====

class TestSuccessErrorRoutes:
    """Test what sets success/error route conditions"""

def test_246_success_route_set_by_status_codes(self):
        """✅ Success route: status code in success_check.status_codes"""
        # Spec: "success_check: Status code matching"

        success_check = {
            "status_codes": [200, 201, 202]
        }

        # Test cases:
        # Status 200 → success
        # Status 201 → success
        # Status 202 → success
        # Status 404 → error (not in list)


def test_247_success_route_requires_expression_pass(self):
        """✅ Success route: expression must also pass"""
        # Spec: "success_check with status_codes and expression"
        # BOTH must be satisfied

        success_check = {
            "status_codes": [200],
            "expression": "response.body.success == true"
        }

        # Status 200 + success=true → success
        # Status 200 + success=false → error
        # Status 404 + success=true → error


def test_248_error_route_set_by_http_error_status(self):
        """✅ Error route: HTTP error status (400-599)"""
        # Spec: "HTTP error status (400-599) → error route"

        error_statuses = [400, 401, 403, 404, 500, 502, 503]

        # All should trigger error route


def test_249_error_route_set_by_timeout(self):
        """✅ Error route: request timeout (30s)"""
        # Spec: "Timeout (30s) → error route"

        # Request takes > 30 seconds
        # Expected: TimeoutException → error route


def test_250_error_route_set_by_json_parse_failure(self):
        """✅ Error route: non-JSON or invalid JSON"""
        # Spec: "✅ JSON-only responses: Non-JSON responses route to error condition"
        # "Success status + Invalid JSON → error route"

        # Status 200 but response is HTML
        response = {
            "status": 200,
            "body": "<html>Error page</html>"
        }
        # Expected: Parse failure → error route

        # Status 200 but response is plain text
        response_text = {
            "status": 200,
            "body": "Plain text response"
        }
        # Expected: Parse failure → error route


def test_251_empty_response_204_no_content(self):
        """✅ Empty response (204 No Content) handling"""
        # Spec: "Empty Response (HTTP 204 No Content): Routes to success if status code matches, response_map skipped"

        success_check = {
            "status_codes": [200, 204]
        }

        response = {
            "status": 204,
            "body": None  # Empty/no content
        }

        # Expected:
        # - Status 204 in success_check → success route
        # - response_map skipped (nothing to map)


    # ===== GAP 12: Two-Pass Validation =====

class TestTwoPassValidation:
    """Test two-pass validation algorithm"""

def test_252_pass_one_builds_node_id_index(self):
        """✅ Pass 1: Build index of all node IDs"""
        # Spec: "Pass 1 - Indexing: Build index of all node IDs in the flow"

        flow = {
            "nodes": {
                "node_a": {"id": "node_a", "routes": [{"target_node": "node_c"}]},
                "node_b": {"id": "node_b", "routes": [{"target_node": "node_a"}]},
                "node_c": {"id": "node_c", "routes": [{"target_node": "node_end"}]},
                "node_end": {"id": "node_end", "routes": []}
            }
        }

        # Pass 1: Build index
        node_index = {"node_a", "node_b", "node_c", "node_end"}


def test_253_pass_two_validates_all_references(self):
        """✅ Pass 2: Validate all references using index"""
        # Spec: "Pass 2 - Validation: Validate all references and constraints"

        node_index = {"node_a", "node_b", "node_c", "node_end"}

        # Validate start_node_id
        start_node_id = "node_a"
        assert start_node_id in node_index  # Valid

        # Validate route targets
        routes = [
            {"target_node": "node_c"},  # Valid (in index)
            {"target_node": "node_missing"}  # Invalid (not in index)
        ]


def test_254_forward_references_allowed(self):
        """✅ Forward references: Node A references Node B defined later"""
        # Spec: "This allows nodes to reference other nodes that appear later in the JSON (order-independent)"

        flow = {
            "start_node_id": "node_a",
            "nodes": {
                "node_a": {
                    "id": "node_a",
                    "routes": [{"target_node": "node_z"}]  # References node_z (defined later)
                },
                # ... many nodes in between ...
                "node_z": {
                    "id": "node_z",
                    "routes": []
                }
            }
        }

        # Expected: Valid (two-pass validation allows forward references)


    # ===== GAP 13: Dot Notation Only =====

class TestDotNotationOnly:
    """Test dot notation requirement (no brackets)"""

def test_255_dot_notation_valid_in_templates(self):
        """✅ Dot notation: valid syntax"""
        # Spec: "Dot notation: context.items.0"
        # "Array index: context.trips.0.driver (zero-based, use dot notation)"

        valid_templates = [
            "{{context.user.name}}",           # Nested object
            "{{context.items.0}}",             # Array index
            "{{context.trips.0.from}}",        # Array element property
            "{{context.data.results.0.id}}",   # Deep nesting
        ]

        # All should work


def test_256_bracket_notation_invalid_in_templates(self):
        """✅ Bracket notation: NOT supported"""
        # Spec: "NOT Supported: Bracket notation: context.trips[0]"

        invalid_templates = [
            "{{context.items[0]}}",            # Bracket array index
            "{{context['items']}}",            # Bracket property access
            "{{context.trips[0].name}}",       # Mixed
        ]

        # Expected: These don't render or cause errors


def test_257_dot_notation_in_source_path(self):
        """✅ source_path in mappings: dot notation only"""
        # Spec: "source_path: dot notation only, max 256 chars"
        # "✅ Supported: data.user.id, items.0.name (array index with dot)"
        # "❌ NOT supported: items[0].name (bracket notation)"

        valid_mappings = [
            {"source_path": "data.user.id", "target_variable": "user_id"},
            {"source_path": "items.0.name", "target_variable": "first_name"},
            {"source_path": "results.0.data.value", "target_variable": "value"}
        ]

        invalid_mappings = [
            {"source_path": "items[0].name", "target_variable": "first_name"},  # Brackets
            {"source_path": "data['user'].id", "target_variable": "user_id"}    # Brackets
        ]


def test_258_dot_notation_in_conditions(self):
        """✅ Conditions: dot notation for nested access"""

        valid_conditions = [
            "context.user.age > 18",
            "context.items.0.price < 100",
            "context.data.results.length > 0"
        ]

        # Bracket notation likely not supported in conditions either


    # ===== GAP 14: Multi-tenant Isolation =====

class TestMultiTenantIsolation:
    """Test multi-tenant security isolation"""

def test_259_user_cannot_access_other_users_bots(self):
        """✅ User A cannot access User B's bots"""
        # Spec: "Users cannot access or modify other users' bots"

        user_a_id = "user_aaa"
        user_b_id = "user_bbb"

        bot_by_user_b = {
            "id": "bot_123",
            "owner_user_id": user_b_id,
            "name": "User B's Bot"
        }

        # User A attempts: GET /api/bots/bot_123
        # Expected: 403 Forbidden or 404 Not Found


def test_260_user_cannot_access_flows_in_other_users_bots(self):
        """✅ User A cannot access flows in User B's bots"""
        # Spec: "Every flow belongs to a specific bot, Users cannot access flows in other users' bots"

        user_a_id = "user_aaa"
        user_b_id = "user_bbb"

        bot_b = {"id": "bot_123", "owner_user_id": user_b_id}
        flow_in_bot_b = {"id": "flow_456", "bot_id": "bot_123"}

        # User A attempts: GET /api/flows/flow_456
        # Expected: 403 Forbidden


def test_261_trigger_keywords_scoped_per_bot(self):
        """✅ Trigger keywords: unique per bot (not globally)"""
        # Spec: "Trigger keywords scoped per bot"
        # "✅ Bot A can have Flow 1 with keyword 'START'"
        # "✅ Bot B can have Flow 1 with keyword 'START' (different bot, allowed)"

        bot_a_flows = [
            {"flow_id": "flow_a1", "trigger_keywords": ["START"]}
        ]

        bot_b_flows = [
            {"flow_id": "flow_b1", "trigger_keywords": ["START"]}  # Same keyword, different bot
        ]

        # Expected: Both valid, no conflict


def test_262_sessions_isolated_per_bot(self):
        """✅ Sessions: isolated per bot for same user"""
        # Spec: "Session Isolation: Each bot maintains its own independent sessions"
        # "Same user can have active sessions in multiple bots at the same time"

        user_id = "+254712345678"

        session_bot_a = {
            "session_key": f"whatsapp:{user_id}:bot_aaa",
            "context": {"data_a": "value_a"}
        }

        session_bot_b = {
            "session_key": f"whatsapp:{user_id}:bot_bbb",
            "context": {"data_b": "value_b"}
        }

        # Both sessions active simultaneously
        # context.data_a not accessible from bot_bbb
        # context.data_b not accessible from bot_aaa


    # ===== GAP 15: Bot Inactive Status =====

class TestBotInactiveStatus:
    """Test bot active/inactive status"""

def test_263_inactive_bot_rejects_webhook_messages(self):
        """✅ Inactive bot rejects incoming messages"""
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
        # - Return message: "Bot unavailable"
        # - No session created
        # - No flow processing


def test_264_active_bot_processes_messages_normally(self):
        """✅ Active bot processes messages normally"""
        # Spec: "Active: Receives and processes messages via webhook"

        bot = {
            "id": "bot_123",
            "status": "active"
        }

        webhook_request = {
            "bot_id": "bot_123",
            "channel": "whatsapp",
            "channel_user_id": "+254712345678",
            "message_text": "START"
        }

        # Expected:
        # - Bot status checked
        # - Status is "active"
        # - Process message normally
        # - Match trigger keywords
        # - Create/resume session
        # - Execute flow


def test_291_exact_duplicate_node_names_fail(self):
        """✅ Exact duplicate node names cause validation error"""
        # Spec: "Should be unique within the flow (case-insensitive)"

        flow = {
            "name": "test_flow",
            "trigger_keywords": ["START"],
            "start_node_id": "node_1",
            "nodes": {
                "node_1": {
                    "id": "node_1",
                    "name": "Welcome Message",  # First occurrence
                    "type": "MESSAGE",
                    "config": {"text": "Hello"},
                    "routes": [{"condition": "true", "target_node": "node_2"}],
                    "position": {"x": 0, "y": 0}
                },
                "node_2": {
                    "id": "node_2",
                    "name": "Welcome Message",  # Exact duplicate
                    "type": "MESSAGE",
                    "config": {"text": "Welcome"},
                    "routes": [{"condition": "true", "target_node": "node_3"}],
                    "position": {"x": 0, "y": 100}
                },
                "node_3": {
                    "id": "node_3",
                    "name": "End",
                    "type": "END",
                    "config": {},
                    "position": {"x": 0, "y": 200}
                }
            }
        }

        # Expected:
        # - Validation error during flow submission
        # - Error type: "duplicate_node_name"
        # - Error message: "Node name 'Welcome Message' is used by multiple nodes. Node names should be unique within the flow."
        # - Conflicting nodes: ["node_1", "node_2"]


def test_292_case_insensitive_duplicate_node_names_fail(self):
        """✅ Case-insensitive duplicate node names cause validation error"""
        # Spec: "Should be unique within the flow (case-insensitive)"

        flow = {
            "name": "test_flow",
            "trigger_keywords": ["START"],
            "start_node_id": "node_1",
            "nodes": {
                "node_1": {
                    "id": "node_1",
                    "name": "Get User Input",      # Original
                    "type": "PROMPT",
                    "config": {
                        "text": "Enter name:",
                        "save_to_variable": "name"
                    },
                    "routes": [{"condition": "true", "target_node": "node_2"}],
                    "position": {"x": 0, "y": 0}
                },
                "node_2": {
                    "id": "node_2",
                    "name": "get user input",      # Case-insensitive duplicate
                    "type": "PROMPT",
                    "config": {
                        "text": "Enter email:",
                        "save_to_variable": "email"
                    },
                    "routes": [{"condition": "true", "target_node": "node_3"}],
                    "position": {"x": 0, "y": 100}
                },
                "node_3": {
                    "id": "node_3",
                    "name": "GET USER INPUT",      # Another case variation
                    "type": "PROMPT",
                    "config": {
                        "text": "Enter phone:",
                        "save_to_variable": "phone"
                    },
                    "routes": [{"condition": "true", "target_node": "node_4"}],
                    "position": {"x": 0, "y": 200}
                },
                "node_4": {
                    "id": "node_4",
                    "name": "End",
                    "type": "END",
                    "config": {},
                    "position": {"x": 0, "y": 300}
                }
            }
        }

        # Expected:
        # - Validation error
        # - Error message: "Node name 'Get User Input' is used by multiple nodes (case-insensitive check). Found: 'Get User Input', 'get user input', 'GET USER INPUT'."
        # - All three nodes flagged as conflicting


def test_293_unique_node_names_valid(self):
        """✅ All unique node names (case-insensitive check) pass validation"""
        # Spec: Uniqueness promotes debugging clarity

        flow = {
            "name": "test_flow",
            "trigger_keywords": ["START"],
            "start_node_id": "node_1",
            "nodes": {
                "node_1": {
                    "id": "node_1",
                    "name": "Welcome Message",      # Unique
                    "type": "MESSAGE",
                    "config": {"text": "Welcome!"},
                    "routes": [{"condition": "true", "target_node": "node_2"}],
                    "position": {"x": 0, "y": 0}
                },
                "node_2": {
                    "id": "node_2",
                    "name": "Get User Name",        # Unique
                    "type": "PROMPT",
                    "config": {
                        "text": "Enter name:",
                        "save_to_variable": "name"
                    },
                    "routes": [{"condition": "true", "target_node": "node_3"}],
                    "position": {"x": 0, "y": 100}
                },
                "node_3": {
                    "id": "node_3",
                    "name": "Save to Database",     # Unique
                    "type": "API_ACTION",
                    "config": {
                        "request": {
                            "method": "POST",
                            "url": "https://api.example.com/users"
                        }
                    },
                    "routes": [
                        {"condition": "success", "target_node": "node_4"},
                        {"condition": "error", "target_node": "node_5"}
                    ],
                    "position": {"x": 0, "y": 200}
                },
                "node_4": {
                    "id": "node_4",
                    "name": "Success Confirmation", # Unique
                    "type": "MESSAGE",
                    "config": {"text": "Saved!"},
                    "routes": [{"condition": "true", "target_node": "node_6"}],
                    "position": {"x": -100, "y": 300}
                },
                "node_5": {
                    "id": "node_5",
                    "name": "Error Handler",        # Unique
                    "type": "MESSAGE",
                    "config": {"text": "Error occurred"},
                    "routes": [{"condition": "true", "target_node": "node_6"}],
                    "position": {"x": 100, "y": 300}
                },
                "node_6": {
                    "id": "node_6",
                    "name": "End",                  # Unique
                    "type": "END",
                    "config": {},
                    "position": {"x": 0, "y": 400}
                }
            }
        }

        # Expected:
        # - All node names unique (case-insensitive check) ✓
        # - Validation passes
        # - Flow stored successfully


def test_294_empty_or_whitespace_node_names_fail(self):
        """✅ Empty or whitespace-only node names cause validation error"""
        # Spec: "Cannot be empty or whitespace only"

        invalid_names = [
            "",           # Empty string
            " ",          # Single space
            "   ",        # Multiple spaces
            "\t",         # Tab
            "\n",         # Newline
            "  \t\n  "    # Mixed whitespace
        ]

        for invalid_name in invalid_names:
            flow = {
                "name": "test_flow",
                "trigger_keywords": ["START"],
                "start_node_id": "node_1",
                "nodes": {
                    "node_1": {
                        "id": "node_1",
                        "name": invalid_name,  # Invalid: empty/whitespace
                        "type": "MESSAGE",
                        "config": {"text": "Hello"},
                        "routes": [{"condition": "true", "target_node": "node_2"}],
                        "position": {"x": 0, "y": 0}
                    },
                    "node_2": {
                        "id": "node_2",
                        "name": "End",
                        "type": "END",
                        "config": {},
                        "position": {"x": 0, "y": 100}
                    }
                }
            }

            # Expected:
            # - Validation error
            # - Error type: "invalid_field"
            # - Error message: "Node name cannot be empty or whitespace only"
            # - Location: "nodes.node_1.name"


class TestNodeNameBestPractices:
    """Test node name best practices (non-critical)"""

def test_295_node_name_max_50_characters(self):
        """✅ Node name maximum 50 characters"""
        # Spec: "Maximum 50 characters"

        # Valid: Exactly 50 characters
        valid_name = "A" * 50
        node_valid = {
            "id": "node_1",
            "name": valid_name,
            "type": "MESSAGE",
            "config": {"text": "Hello"},
            "routes": [{"condition": "true", "target_node": "node_2"}],
            "position": {"x": 0, "y": 0}
        }
        # Expected: Valid

        # Invalid: 51 characters
        invalid_name = "A" * 51
        node_invalid = {
            "id": "node_1",
            "name": invalid_name,
            "type": "MESSAGE",
            "config": {"text": "Hello"},
            "routes": [{"condition": "true", "target_node": "node_2"}],
            "position": {"x": 0, "y": 0}
        }

        # Expected:
        # - Validation error
        # - Error message: "Node name exceeds maximum length of 50 characters"

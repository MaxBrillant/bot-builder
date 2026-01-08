"""
Shared pytest fixtures
All fixtures designed based on BOT_BUILDER_SPECIFICATIONS.md
"""
import pytest
from typing import Dict, Any, List
from uuid import uuid4


# ===== Flow Fixtures =====

@pytest.fixture
def minimal_valid_flow() -> Dict[str, Any]:
    """Minimal valid flow per spec: MESSAGE → END"""
    return {
        "name": "minimal_flow",
        "trigger_keywords": ["START"],
        "start_node_id": "node_start",
        "nodes": {
            "node_start": {
                "id": "node_start",
                "name": "Start Message",
                "type": "MESSAGE",
                "config": {
                    "text": "Welcome!"
                },
                "routes": [
                    {"condition": "true", "target_node": "node_end"}
                ],
                "position": {"x": 0, "y": 0}
            },
            "node_end": {
                "id": "node_end",
                "name": "End",
                "type": "END",
                "config": {},
                "routes": [],
                "position": {"x": 0, "y": 100}
            }
        }
    }


@pytest.fixture
def complete_flow_all_fields() -> Dict[str, Any]:
    """Flow with all optional fields defined"""
    return {
        "name": "complete_flow",
        "trigger_keywords": ["BEGIN", "START"],
        "variables": {
            "user_name": {"type": "string", "default": None},
            "age": {"type": "number", "default": 0},
            "is_verified": {"type": "boolean", "default": False},
            "items": {"type": "array", "default": []}
        },
        "defaults": {
            "retry_logic": {
                "max_attempts": 3,
                "counter_text": "(Attempt {{current_attempt}} of {{max_attempts}})",
                "fail_route": "node_fail"
            }
        },
        "start_node_id": "node_start",
        "nodes": {
            "node_start": {
                "id": "node_start",
                "name": "Start",
                "type": "MESSAGE",
                "config": {"text": "Starting..."},
                "routes": [{"condition": "true", "target_node": "node_end"}],
                "position": {"x": 0, "y": 0}
            },
            "node_end": {
                "id": "node_end",
                "name": "End",
                "type": "END",
                "config": {},
                "routes": [],
                "position": {"x": 0, "y": 100}
            },
            "node_fail": {
                "id": "node_fail",
                "name": "Fail Handler",
                "type": "MESSAGE",
                "config": {"text": "Too many attempts"},
                "routes": [{"condition": "true", "target_node": "node_end"}],
                "position": {"x": 100, "y": 50}
            }
        }
    }


@pytest.fixture
def prompt_node_basic() -> Dict[str, Any]:
    """Basic PROMPT node"""
    return {
        "id": "node_prompt",
        "name": "Get Name",
        "type": "PROMPT",
        "config": {
            "text": "What is your name?",
            "save_to_variable": "user_name"
        },
        "routes": [{"condition": "true", "target_node": "node_next"}],
        "position": {"x": 0, "y": 0}
    }


@pytest.fixture
def prompt_node_with_regex_validation() -> Dict[str, Any]:
    """PROMPT with REGEX validation"""
    return {
        "id": "node_prompt",
        "name": "Get Phone",
        "type": "PROMPT",
        "config": {
            "text": "Enter phone number:",
            "save_to_variable": "phone",
            "validation": {
                "type": "REGEX",
                "rule": "^\\+?[0-9]{10,15}$",
                "error_message": "Invalid phone format"
            }
        },
        "routes": [{"condition": "true", "target_node": "node_next"}],
        "position": {"x": 0, "y": 0}
    }


@pytest.fixture
def prompt_node_with_expression_validation() -> Dict[str, Any]:
    """PROMPT with EXPRESSION validation"""
    return {
        "id": "node_prompt",
        "name": "Get Age",
        "type": "PROMPT",
        "config": {
            "text": "Enter your age:",
            "save_to_variable": "age",
            "validation": {
                "type": "EXPRESSION",
                "rule": "input.isNumeric() && input > 0 && input <= 120",
                "error_message": "Age must be between 1 and 120"
            }
        },
        "routes": [{"condition": "true", "target_node": "node_next"}],
        "position": {"x": 0, "y": 0}
    }


@pytest.fixture
def prompt_node_with_interrupts() -> Dict[str, Any]:
    """PROMPT with interrupt keywords"""
    return {
        "id": "node_prompt",
        "name": "Get Input",
        "type": "PROMPT",
        "config": {
            "text": "Enter value (0 to cancel):",
            "save_to_variable": "value",
            "interrupts": [
                {"input": "0", "target_node": "node_cancel"},
                {"input": "back", "target_node": "node_previous"}
            ]
        },
        "routes": [{"condition": "true", "target_node": "node_next"}],
        "position": {"x": 0, "y": 0}
    }


@pytest.fixture
def menu_node_static() -> Dict[str, Any]:
    """MENU node with static options"""
    return {
        "id": "node_menu",
        "name": "Select Option",
        "type": "MENU",
        "config": {
            "text": "Choose an option:",
            "source_type": "STATIC",
            "static_options": [
                {"label": "Option 1"},
                {"label": "Option 2"},
                {"label": "Option 3"}
            ],
            "error_message": "Please select 1, 2, or 3"
        },
        "routes": [
            {"condition": "selection == 1", "target_node": "node_opt1"},
            {"condition": "selection == 2", "target_node": "node_opt2"},
            {"condition": "selection == 3", "target_node": "node_opt3"},
            {"condition": "true", "target_node": "node_error"}
        ],
        "position": {"x": 0, "y": 0}
    }


@pytest.fixture
def menu_node_dynamic() -> Dict[str, Any]:
    """MENU node with dynamic options"""
    return {
        "id": "node_menu",
        "name": "Select Trip",
        "type": "MENU",
        "config": {
            "text": "Select a trip:",
            "source_type": "DYNAMIC",
            "source_variable": "trips",
            "item_template": "{{index}}. {{item.from}} → {{item.to}} at {{item.time}}",
            "output_mapping": [
                {"source_path": "id", "target_variable": "trip_id"},
                {"source_path": "departure_time", "target_variable": "departure_time"},
                {"source_path": "price", "target_variable": "price"}
            ]
        },
        "routes": [
            {"condition": "true", "target_node": "node_next"}
        ],
        "position": {"x": 0, "y": 0}
    }


@pytest.fixture
def api_action_node() -> Dict[str, Any]:
    """API_ACTION node"""
    return {
        "id": "node_api",
        "name": "Fetch Data",
        "type": "API_ACTION",
        "config": {
            "request": {
                "method": "GET",
                "url": "https://api.example.com/users/{{user.channel_id}}",
                "headers": {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer {{context.token}}"
                }
            },
            "response_map": [
                {"source_path": "data.user_id", "target_variable": "user_id"},
                {"source_path": "data.name", "target_variable": "user_name"},
                {"source_path": "data.age", "target_variable": "age"}
            ],
            "success_check": {
                "status_codes": [200, 201],
                "expression": "response.body.success == true"
            }
        },
        "routes": [
            {"condition": "success", "target_node": "node_success"},
            {"condition": "error", "target_node": "node_error"},
            {"condition": "true", "target_node": "node_fallback"}
        ],
        "position": {"x": 0, "y": 0}
    }


@pytest.fixture
def logic_expression_node() -> Dict[str, Any]:
    """LOGIC_EXPRESSION node"""
    return {
        "id": "node_logic",
        "name": "Check Status",
        "type": "LOGIC_EXPRESSION",
        "config": {},
        "routes": [
            {"condition": "context.age > 18 && context.verified == true", "target_node": "node_adult"},
            {"condition": "context.age > 18", "target_node": "node_adult_unverified"},
            {"condition": "context.age <= 18", "target_node": "node_minor"},
            {"condition": "true", "target_node": "node_error"}
        ],
        "position": {"x": 0, "y": 0}
    }


@pytest.fixture
def message_node() -> Dict[str, Any]:
    """MESSAGE node"""
    return {
        "id": "node_message",
        "name": "Display Info",
        "type": "MESSAGE",
        "config": {
            "text": "Hello {{context.user_name}}, your age is {{context.age}}"
        },
        "routes": [
            {"condition": "true", "target_node": "node_next"}
        ],
        "position": {"x": 0, "y": 0}
    }


@pytest.fixture
def end_node() -> Dict[str, Any]:
    """END node"""
    return {
        "id": "node_end",
        "name": "End",
        "type": "END",
        "config": {},
        "routes": [],
        "position": {"x": 0, "y": 0}
    }


# ===== Invalid Flow Fixtures =====

@pytest.fixture
def flow_missing_name(minimal_valid_flow) -> Dict[str, Any]:
    """Flow without name field"""
    flow = minimal_valid_flow.copy()
    del flow["name"]
    return flow


@pytest.fixture
def flow_missing_trigger_keywords(minimal_valid_flow) -> Dict[str, Any]:
    """Flow without trigger_keywords"""
    flow = minimal_valid_flow.copy()
    del flow["trigger_keywords"]
    return flow


@pytest.fixture
def flow_empty_trigger_keywords(minimal_valid_flow) -> Dict[str, Any]:
    """Flow with empty trigger_keywords array"""
    flow = minimal_valid_flow.copy()
    flow["trigger_keywords"] = []
    return flow


@pytest.fixture
def flow_invalid_start_node(minimal_valid_flow) -> Dict[str, Any]:
    """Flow with start_node_id that doesn't exist"""
    flow = minimal_valid_flow.copy()
    flow["start_node_id"] = "node_nonexistent"
    return flow


@pytest.fixture
def flow_circular_reference() -> Dict[str, Any]:
    """Flow with circular reference"""
    return {
        "name": "circular",
        "trigger_keywords": ["CIRCLE"],
        "start_node_id": "node_a",
        "nodes": {
            "node_a": {
                "id": "node_a",
                "name": "Node A",
                "type": "MESSAGE",
                "config": {"text": "A"},
                "routes": [{"condition": "true", "target_node": "node_b"}],
                "position": {"x": 0, "y": 0}
            },
            "node_b": {
                "id": "node_b",
                "name": "Node B",
                "type": "MESSAGE",
                "config": {"text": "B"},
                "routes": [{"condition": "true", "target_node": "node_a"}],
                "position": {"x": 0, "y": 100}
            }
        }
    }


@pytest.fixture
def flow_with_orphan_nodes(minimal_valid_flow) -> Dict[str, Any]:
    """Flow with orphan node (not start, not referenced)"""
    flow = minimal_valid_flow.copy()
    flow["nodes"]["node_orphan"] = {
        "id": "node_orphan",
        "name": "Orphan",
        "type": "MESSAGE",
        "config": {"text": "Orphan"},
        "routes": [{"condition": "true", "target_node": "node_end"}],
        "position": {"x": 200, "y": 0}
    }
    return flow


@pytest.fixture
def flow_wildcard_with_other_keywords(minimal_valid_flow) -> Dict[str, Any]:
    """Flow with wildcard combined with other keywords"""
    flow = minimal_valid_flow.copy()
    flow["trigger_keywords"] = ["*", "START"]
    return flow


# ===== Session & Context Fixtures =====

@pytest.fixture
def session_context_empty() -> Dict[str, Any]:
    """Empty session context"""
    return {}


@pytest.fixture
def session_context_with_variables() -> Dict[str, Any]:
    """Session context with variables"""
    return {
        "user_name": "Alice",
        "age": 25,
        "is_verified": True,
        "items": ["item1", "item2", "item3"]
    }


@pytest.fixture
def session_context_with_nested() -> Dict[str, Any]:
    """Session context with nested objects"""
    return {
        "user": {
            "profile": {
                "name": "Alice",
                "age": 25
            }
        },
        "trips": [
            {"id": "trip1", "from": "Nairobi", "to": "Mombasa", "price": 1500},
            {"id": "trip2", "from": "Nairobi", "to": "Kisumu", "price": 1200}
        ]
    }


# ===== API Response Fixtures =====

@pytest.fixture
def api_response_success() -> Dict[str, Any]:
    """Successful API response"""
    return {
        "status_code": 200,
        "headers": {"Content-Type": "application/json"},
        "body": {
            "success": True,
            "data": {
                "user_id": "user123",
                "name": "Alice",
                "age": "25",  # String that needs conversion
                "verified": "true",  # String that needs conversion
                "tags": ["active", "premium"]
            }
        }
    }


@pytest.fixture
def api_response_error() -> Dict[str, Any]:
    """Error API response"""
    return {
        "status_code": 404,
        "headers": {"Content-Type": "application/json"},
        "body": {
            "success": False,
            "error": "User not found"
        }
    }


@pytest.fixture
def api_response_invalid_json() -> Dict[str, Any]:
    """Response with invalid JSON"""
    return {
        "status_code": 200,
        "headers": {"Content-Type": "text/html"},
        "body": "<html>Error page</html>"
    }

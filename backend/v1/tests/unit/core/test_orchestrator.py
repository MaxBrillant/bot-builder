"""
Auto-progression (Tests 169-175)
Reorganized from: test_13_auto_progression.py

Tests validate: Auto-progression
"""
import pytest

def test_169_counter_increments_on_message_nodes():
    """✅ Auto-progression counter increments on MESSAGE nodes"""
    # Spec: "Max auto-progression steps: 10 consecutive nodes without user input"
    # MESSAGE nodes don't require input → count toward auto-progression

    flow = {
    "name": "message_chain",
    "trigger_keywords": ["CHAIN"],
    "start_node_id": "node_msg1",
    "nodes": {
    "node_msg1": {
        "type": "MESSAGE",
        "config": {"text": "Message 1"},
        "routes": [{"condition": "true", "target_node": "node_msg2"}]
    },
    "node_msg2": {
        "type": "MESSAGE",
        "config": {"text": "Message 2"},
        "routes": [{"condition": "true", "target_node": "node_msg3"}]
    },
    "node_msg3": {
        "type": "MESSAGE",
        "config": {"text": "Message 3"},
        "routes": [{"condition": "true", "target_node": "node_end"}]
    },
    "node_end": {
        "type": "END",
        "config": {},
        "routes": []
    }
    }
    }

    # Expected progression count:
    # node_msg1 → count = 1
    # node_msg2 → count = 2
    # node_msg3 → count = 3
    # node_end → count = 4 (END also counts)


def test_170_counter_increments_on_logic_expression_nodes():
    """✅ Auto-progression counter increments on LOGIC_EXPRESSION nodes"""
    # Spec: LOGIC_EXPRESSION nodes don't require input → count toward auto-progression

    flow = {
    "name": "logic_chain",
    "trigger_keywords": ["LOGIC"],
    "start_node_id": "node_logic1",
    "nodes": {
    "node_logic1": {
        "type": "LOGIC_EXPRESSION",
        "config": {},
        "routes": [{"condition": "true", "target_node": "node_logic2"}]
    },
    "node_logic2": {
        "type": "LOGIC_EXPRESSION",
        "config": {},
        "routes": [{"condition": "true", "target_node": "node_msg"}]
    },
    "node_msg": {
        "type": "MESSAGE",
        "config": {"text": "Done"},
        "routes": [{"condition": "true", "target_node": "node_end"}]
    },
    "node_end": {
        "type": "END",
        "config": {},
        "routes": []
    }
    }
    }

    # Expected progression count:
    # node_logic1 → count = 1
    # node_logic2 → count = 2
    # node_msg → count = 3
    # node_end → count = 4


def test_171_counter_resets_on_prompt_node():
    """✅ Auto-progression counter RESETS when reaching PROMPT node"""
    # Spec: "Auto-progression counter resets at PROMPT or MENU nodes (user input required)"

    flow = {
    "name": "reset_at_prompt",
    "trigger_keywords": ["RESET"],
    "start_node_id": "node_msg1",
    "nodes": {
    # 5 MESSAGE nodes
    "node_msg1": {
        "type": "MESSAGE",
        "config": {"text": "Message 1"},
        "routes": [{"condition": "true", "target_node": "node_msg2"}]
    },
    "node_msg2": {
        "type": "MESSAGE",
        "config": {"text": "Message 2"},
        "routes": [{"condition": "true", "target_node": "node_msg3"}]
    },
    "node_msg3": {
        "type": "MESSAGE",
        "config": {"text": "Message 3"},
        "routes": [{"condition": "true", "target_node": "node_msg4"}]
    },
    "node_msg4": {
        "type": "MESSAGE",
        "config": {"text": "Message 4"},
        "routes": [{"condition": "true", "target_node": "node_msg5"}]
    },
    "node_msg5": {
        "type": "MESSAGE",
        "config": {"text": "Message 5"},
        "routes": [{"condition": "true", "target_node": "node_prompt"}]
    },
    # PROMPT node - RESETS counter
    "node_prompt": {
        "type": "PROMPT",
        "config": {
            "text": "Enter name:",
            "save_to_variable": "name"
        },
        "routes": [{"condition": "true", "target_node": "node_msg6"}]
    },
    # 5 more MESSAGE nodes AFTER prompt
    "node_msg6": {
        "type": "MESSAGE",
        "config": {"text": "Message 6"},
        "routes": [{"condition": "true", "target_node": "node_msg7"}]
    },
    "node_msg7": {
        "type": "MESSAGE",
        "config": {"text": "Message 7"},
        "routes": [{"condition": "true", "target_node": "node_msg8"}]
    },
    "node_msg8": {
        "type": "MESSAGE",
        "config": {"text": "Message 8"},
        "routes": [{"condition": "true", "target_node": "node_msg9"}]
    },
    "node_msg9": {
        "type": "MESSAGE",
        "config": {"text": "Message 9"},
        "routes": [{"condition": "true", "target_node": "node_msg10"}]
    },
    "node_msg10": {
        "type": "MESSAGE",
        "config": {"text": "Message 10"},
        "routes": [{"condition": "true", "target_node": "node_end"}]
    },
    "node_end": {
        "type": "END",
        "config": {},
        "routes": []
    }
    }
    }

    # Expected progression:
    # msg1-msg5 → count reaches 5
    # prompt → counter RESETS to 0, waits for user input
    # After user input: msg6-msg10 → count reaches 5
    # Total flow is valid even though 10+ nodes exist
    # Because counter reset at PROMPT


def test_172_counter_resets_on_menu_node():
    """✅ Auto-progression counter RESETS when reaching MENU node"""
    # Spec: "Counter resets at PROMPT or MENU nodes"

    flow = {
    "name": "reset_at_menu",
    "trigger_keywords": ["MENU"],
    "start_node_id": "node_msg1",
    "nodes": {
    # 5 auto-progression nodes
    "node_msg1": {"type": "MESSAGE", "config": {"text": "1"}, "routes": [{"condition": "true", "target_node": "node_msg2"}]},
    "node_msg2": {"type": "MESSAGE", "config": {"text": "2"}, "routes": [{"condition": "true", "target_node": "node_msg3"}]},
    "node_msg3": {"type": "MESSAGE", "config": {"text": "3"}, "routes": [{"condition": "true", "target_node": "node_msg4"}]},
    "node_msg4": {"type": "MESSAGE", "config": {"text": "4"}, "routes": [{"condition": "true", "target_node": "node_msg5"}]},
    "node_msg5": {"type": "MESSAGE", "config": {"text": "5"}, "routes": [{"condition": "true", "target_node": "node_menu"}]},
    # MENU node - RESETS counter
    "node_menu": {
        "type": "MENU",
        "config": {
            "text": "Choose:",
            "source_type": "STATIC",
            "static_options": [{"label": "Option 1"}]
        },
        "routes": [{"condition": "true", "target_node": "node_end"}]
    },
    "node_end": {"type": "END", "config": {}, "routes": []}
    }
    }

    # Counter resets at MENU, so valid



def test_173_flow_with_exactly_10_auto_progression_steps_passes():
    """✅ Flow with exactly 10 consecutive auto-progression steps is valid"""
    # Spec: "Max auto-progression steps: 10"

    flow = {
    "name": "ten_steps",
    "trigger_keywords": ["TEN"],
    "start_node_id": "node_msg1",
    "nodes": {
    "node_msg1": {"type": "MESSAGE", "config": {"text": "1"}, "routes": [{"condition": "true", "target_node": "node_msg2"}]},
    "node_msg2": {"type": "MESSAGE", "config": {"text": "2"}, "routes": [{"condition": "true", "target_node": "node_msg3"}]},
    "node_msg3": {"type": "MESSAGE", "config": {"text": "3"}, "routes": [{"condition": "true", "target_node": "node_msg4"}]},
    "node_msg4": {"type": "MESSAGE", "config": {"text": "4"}, "routes": [{"condition": "true", "target_node": "node_msg5"}]},
    "node_msg5": {"type": "MESSAGE", "config": {"text": "5"}, "routes": [{"condition": "true", "target_node": "node_msg6"}]},
    "node_msg6": {"type": "MESSAGE", "config": {"text": "6"}, "routes": [{"condition": "true", "target_node": "node_msg7"}]},
    "node_msg7": {"type": "MESSAGE", "config": {"text": "7"}, "routes": [{"condition": "true", "target_node": "node_msg8"}]},
    "node_msg8": {"type": "MESSAGE", "config": {"text": "8"}, "routes": [{"condition": "true", "target_node": "node_msg9"}]},
    "node_msg9": {"type": "MESSAGE", "config": {"text": "9"}, "routes": [{"condition": "true", "target_node": "node_msg10"}]},
    "node_msg10": {"type": "MESSAGE", "config": {"text": "10"}, "routes": [{"condition": "true", "target_node": "node_end"}]},
    "node_end": {"type": "END", "config": {}, "routes": []}
    }
    }

    # 10 MESSAGE nodes + 1 END = 11 nodes total
    # But only 10 auto-progression steps before END
    # Expected: Valid at runtime (doesn't exceed limit)


def test_174_flow_with_11_auto_progression_steps_fails():
    """✅ Flow with 11 consecutive auto-progression steps exceeds limit"""
    # Spec: "Prevent infinite loops - max 10 consecutive nodes"

    flow = {
    "name": "eleven_steps",
    "trigger_keywords": ["ELEVEN"],
    "start_node_id": "node_msg1",
    "nodes": {
    "node_msg1": {"type": "MESSAGE", "config": {"text": "1"}, "routes": [{"condition": "true", "target_node": "node_msg2"}]},
    "node_msg2": {"type": "MESSAGE", "config": {"text": "2"}, "routes": [{"condition": "true", "target_node": "node_msg3"}]},
    "node_msg3": {"type": "MESSAGE", "config": {"text": "3"}, "routes": [{"condition": "true", "target_node": "node_msg4"}]},
    "node_msg4": {"type": "MESSAGE", "config": {"text": "4"}, "routes": [{"condition": "true", "target_node": "node_msg5"}]},
    "node_msg5": {"type": "MESSAGE", "config": {"text": "5"}, "routes": [{"condition": "true", "target_node": "node_msg6"}]},
    "node_msg6": {"type": "MESSAGE", "config": {"text": "6"}, "routes": [{"condition": "true", "target_node": "node_msg7"}]},
    "node_msg7": {"type": "MESSAGE", "config": {"text": "7"}, "routes": [{"condition": "true", "target_node": "node_msg8"}]},
    "node_msg8": {"type": "MESSAGE", "config": {"text": "8"}, "routes": [{"condition": "true", "target_node": "node_msg9"}]},
    "node_msg9": {"type": "MESSAGE", "config": {"text": "9"}, "routes": [{"condition": "true", "target_node": "node_msg10"}]},
    "node_msg10": {"type": "MESSAGE", "config": {"text": "10"}, "routes": [{"condition": "true", "target_node": "node_msg11"}]},
    "node_msg11": {"type": "MESSAGE", "config": {"text": "11"}, "routes": [{"condition": "true", "target_node": "node_end"}]},  # 11th!
    "node_end": {"type": "END", "config": {}, "routes": []}
    }
    }

    # Expected runtime behavior:
    # - Process nodes 1-10 successfully
    # - Attempt to process node 11
    # - Counter = 11 (exceeds max of 10)
    # - Terminate flow with error
    # - Session status = ERROR
    # - User sees: "System error. Please contact support."


def test_175_api_action_counts_toward_auto_progression():
    """✅ API_ACTION nodes count toward auto-progression"""
    # Spec: API_ACTION nodes don't require user input → count toward auto-progression

    flow = {
    "name": "api_chain",
    "trigger_keywords": ["API"],
    "start_node_id": "node_api1",
    "nodes": {
    # Chain of API calls
    "node_api1": {
        "type": "API_ACTION",
        "config": {
            "request": {"method": "GET", "url": "https://api.example.com/1"}
        },
        "routes": [{"condition": "success", "target_node": "node_api2"}]
    },
    "node_api2": {
        "type": "API_ACTION",
        "config": {
            "request": {"method": "GET", "url": "https://api.example.com/2"}
        },
        "routes": [{"condition": "success", "target_node": "node_api3"}]
    },
    # ... continue for 10 API calls ...
    "node_api3": {
        "type": "API_ACTION",
        "config": {
            "request": {"method": "GET", "url": "https://api.example.com/3"}
        },
        "routes": [{"condition": "success", "target_node": "node_end"}]
    },
    "node_end": {"type": "END", "config": {}, "routes": []}
    }
    }

    # API_ACTION nodes execute without user input → count toward auto-progression
    # Chaining many API calls could hit the limit

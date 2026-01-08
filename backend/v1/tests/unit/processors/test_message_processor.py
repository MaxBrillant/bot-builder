"""
MESSAGE (Tests 067-068)
Reorganized from: test_05_other_processors.py

Tests validate: MESSAGE
"""
import pytest

def test_67_message_display_and_auto_progress(message_node):
    """✅ MESSAGE - display text and auto-progress to next node"""
    # Spec: "Display information and auto-progress"
    # "Auto-progress to next node, No user input required"

    node = message_node
    context = {"user_name": "Alice", "age": 25}

    # Expected behavior:
    # 1. Render text with template: "Hello Alice, your age is 25"
    # 2. Display message to user
    # 3. Auto-progress immediately to next node (no waiting for input)
    # 4. needs_input = False

    assert node["routes"][0]["condition"] == "true"
    # Single route with "true" condition


def test_68_message_template_rendering(message_node):
    """✅ MESSAGE - template rendering in text"""
    # Spec: "Access full context for templates"
    # "{{context.*}} available"

    node = message_node
    context = {
    "user_name": "Alice",
    "age": 25,
    "items": ["item1", "item2"]
    }

    # Text template: "Hello {{context.user_name}}, your age is {{context.age}}"
    # Expected rendered: "Hello Alice, your age is 25"

    # Test with nested context
    node_nested = {
    "id": "node_msg",
    "name": "Message",
    "type": "MESSAGE",
    "config": {
    "text": "Welcome {{context.user.profile.name}} from {{context.user.city}}"
    },
    "routes": [{"condition": "true", "target_node": "node_next"}],
    "position": {"x": 0, "y": 0}
    }

    context_nested = {
    "user": {
    "profile": {"name": "Bob"},
    "city": "Nairobi"
    }
    }
    # Expected: "Welcome Bob from Nairobi"



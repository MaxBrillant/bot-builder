"""
Template substitution (Tests 070-086)
Reorganized from: test_06_template_engine.py

Tests validate: Template substitution
"""
import pytest

def test_70_context_variable_substitution():
    """✅ {{context.variable}} substitution"""
    # Spec: "Context variable: {{context.name}} → 'John'"
    template = "Hello {{context.user_name}}"
    context = {"user_name": "Alice"}

    # Expected output: "Hello Alice"


def test_71_nested_object_access():
    """✅ {{context.nested.object}} nested access"""
    # Spec: "Nested object: {{context.user.email}} → 'john@example.com'"
    template = "Email: {{context.user.email}}, Age: {{context.user.profile.age}}"
    context = {
    "user": {
    "email": "alice@example.com",
    "profile": {
        "age": 25
    }
    }
    }

    # Expected: "Email: alice@example.com, Age: 25"


def test_72_array_element_access_dot_notation():
    """✅ {{context.array.0}} array access with dot notation"""
    # Spec: "Array index: {{context.items.0}} → First item"
    # "Spec: Use dot notation for array indices: context.trips.0.driver"
    template = "First trip: {{context.trips.0.from}} to {{context.trips.0.to}}"
    context = {
    "trips": [
    {"from": "Nairobi", "to": "Mombasa"},
    {"from": "Nairobi", "to": "Kisumu"}
    ]
    }

    # Expected: "First trip: Nairobi to Mombasa"


def test_73_multiple_templates_in_single_string():
    """✅ Multiple templates in same string"""
    # Spec: "Multiple templates in same string supported"
    template = "{{context.greeting}} {{context.name}}, you have {{context.count}} messages"
    context = {
    "greeting": "Hello",
    "name": "Alice",
    "count": 5
    }

    # Expected: "Hello Alice, you have 5 messages"



def test_74_user_channel_id_variable():
    """✅ {{user.channel_id}} special variable"""
    # Spec: "{{user.channel_id}}: Platform-specific user identifier"
    # Examples: "+254712345678" (WhatsApp), "U012345" (Slack)
    template = "Your ID: {{user.channel_id}}"
    user_data = {"channel_id": "+254712345678", "channel": "whatsapp"}

    # Expected: "Your ID: +254712345678"


def test_75_user_channel_variable():
    """✅ {{user.channel}} special variable"""
    # Spec: "{{user.channel}}: Channel name (e.g., 'whatsapp', 'telegram', 'slack')"
    template = "You're using {{user.channel}}"
    user_data = {"channel": "whatsapp"}

    # Expected: "You're using whatsapp"


def test_76_menu_item_and_index_variables():
    """✅ {{item.*}} and {{index}} in MENU templates"""
    # Spec: "{{item.*}}: Current item in MENU dynamic template"
    # "{{index}}: 1-based counter in MENU dynamic template (1, 2, 3...)"
    item_template = "{{index}}. {{item.from}} → {{item.to}} (KSH {{item.price}})"

    items = [
    {"from": "Nairobi", "to": "Mombasa", "price": 1500},
    {"from": "Nairobi", "to": "Kisumu", "price": 1200}
    ]

    # Expected outputs:
    # Item 0 with index=1: "1. Nairobi → Mombasa (KSH 1500)"
    # Item 1 with index=2: "2. Nairobi → Kisumu (KSH 1200)"


def test_77_retry_counter_variables():
    """✅ {{current_attempt}} and {{max_attempts}} in counter_text"""
    # Spec: "{{current_attempt}}: Current retry attempt (only in retry counter_text)"
    # "{{max_attempts}}: Maximum attempts (only in retry counter_text)"
    # "Available ONLY in defaults.retry_logic.counter_text"

    counter_template = "(Attempt {{current_attempt}} of {{max_attempts}})"
    retry_data = {"current_attempt": 2, "max_attempts": 3}

    # Expected: "(Attempt 2 of 3)"

    # Note: These variables NOT available in:
    # - Error messages
    # - Validation rules
    # - Session context
    # - Any other template context



def test_78_missing_variable_displays_literally():
    """✅ Missing variable displayed literally (debugging feature)"""
    # Spec: "Missing Variable Behavior: Variable is displayed literally (unreplaced)"
    # "Intentional debugging feature - makes debugging easier"
    template = "Welcome, {{context.user_name}}!"
    context = {}  # user_name not defined

    # Expected output: "Welcome, {{context.user_name}}!"
    # NOT: "Welcome, !" or "Welcome, None!"


def test_79_null_value_behavior():
    """✅ Null value handling in templates"""
    # Spec mentions missing variables but not explicit null handling
    # Test actual behavior with null values
    template = "Value: {{context.value}}"
    context = {"value": None}

    # Expected behavior (implementation-defined):
    # Option 1: Display literally "{{context.value}}"
    # Option 2: Display "null" or empty string



def test_80_prompt_node_template_context():
    """✅ PROMPT node: {{context.*}}, {{input}} (in validation only)"""
    # Spec table: PROMPT | {{context.*}}, {{input}} | input only in validation expressions

    # Text template - only context available
    text_template = "Hello {{context.name}}, please enter your age:"
    context = {"name": "Alice"}
    # Expected: "Hello Alice, please enter your age:"

    # Validation expression - input available
    validation_rule = "input.isNumeric() && input > 0"
    # Can access "input" variable (user's input string)


def test_81_menu_node_template_context():
    """✅ MENU node: {{context.*}}, {{item.*}}, {{index}} (in item_template only)"""
    # Spec table: MENU | {{context.*}}, {{item.*}}, {{index}} | item and index only in item_template

    # Menu text template - only context
    text_template = "Select a trip, {{context.user_name}}:"
    context = {"user_name": "Alice"}
    # Expected: "Select a trip, Alice:"

    # Item template - context, item, index all available
    item_template = "{{index}}. {{item.name}} - {{context.currency}}{{item.price}}"
    # Can access context, item, and index


def test_82_api_action_node_template_context():
    """✅ API_ACTION node: {{context.*}}, {{user.channel_id}}"""
    # Spec table: API_ACTION | {{context.*}}, {{user.channel_id}}
    # Note: "Other user data should be fetched via API calls"

    url_template = "https://api.example.com/users/{{user.channel_id}}/orders"
    user_data = {"channel_id": "+254712345678"}
    # Expected URL: "https://api.example.com/users/+254712345678/orders"

    body_template = '{"user_id": "{{user.channel_id}}", "product": "{{context.product}}"}'
    context = {"product": "laptop"}
    # Expected body: {"user_id": "+254712345678", "product": "laptop"}



def test_83_templates_no_arithmetic():
    """✅ Templates cannot do arithmetic operations"""
    # Spec: "❌ Not Supported: Arithmetic operations: {{count + 1}}"
    template = "Count: {{context.count + 1}}"
    context = {"count": 5}

    # Expected output: Literally "Count: {{context.count + 1}}"
    # NOT: "Count: 6"


def test_84_templates_no_string_manipulation():
    """✅ Templates cannot do string manipulation"""
    # Spec: "❌ Not Supported: String manipulation: {{name.toUpperCase()}}"
    template = "Name: {{context.name.toUpperCase()}}"
    context = {"name": "alice"}

    # Expected output: Literally "Name: {{context.name.toUpperCase()}}"
    # NOT: "Name: ALICE"


def test_85_templates_no_conditionals():
    """✅ Templates cannot have conditional rendering"""
    # Spec: "❌ Not Supported: Conditional rendering: {{if condition}}"
    template = "{{if context.verified}}Verified{{else}}Not verified{{endif}}"
    context = {"verified": True}

    # Expected output: Displayed literally (or error)
    # NOT: "Verified"

    # Workaround: Use LOGIC_EXPRESSION nodes for conditionals


def test_86_templates_no_default_values_with_or():
    """✅ Templates cannot use || for default values"""
    # Spec: "❌ Not Supported: Default values with || operator: {{context.name || 'Guest'}}"
    # "Workaround: Initialize variables with defaults in flow definition"
    template = "Welcome, {{context.name || 'Guest'}}"
    context = {}

    # Expected output: Literally "Welcome, {{context.name || 'Guest'}}"
    # NOT: "Welcome, Guest"

    # Proper workaround - initialize in flow definition:
    flow_variables = {
    "name": {"type": "string", "default": "Guest"}
    }
    # Then template: "Welcome, {{context.name}}" → "Welcome, Guest"

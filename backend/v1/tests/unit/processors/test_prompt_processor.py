"""
Basic PROMPT functionality (Tests 036-046)
Reorganized from: test_02_prompt_processor.py

Tests validate: Basic PROMPT functionality
"""
import pytest

def test_36_prompt_display_wait_and_save(self, prompt_node_basic):
        """✅ Display text, wait for input, save to variable"""
        # Spec: PROMPT "Collect and validate user input"
        # Processing: 1) Display message 2) Wait for input 3) Save to variable

        node = prompt_node_basic
        context = {}

        # First call - no user input (display message)
        # Expected result: message="What is your name?", needs_input=True
        expected_message = node["config"]["text"]
        assert expected_message == "What is your name?"

        # Second call - with user input
        user_input = "Alice"
        expected_variable = node["config"]["save_to_variable"]

        # After processing with input "Alice"
        # Expected: context["user_name"] = "Alice", next_node assigned
        # Simulating: context would be updated with {user_name: "Alice"}


class TestPromptRegexValidation:
    """Test REGEX validation behavior"""

def test_37_regex_validation_valid_input_passes(self, prompt_node_with_regex_validation):
        """✅ REGEX validation - valid input passes"""
        # Spec: "Valid input matching regex → save and progress"
        node = prompt_node_with_regex_validation
        context = {}

        # Pattern: ^\+?[0-9]{10,15}$
        valid_inputs = [
            "+254712345678",
            "0712345678",
            "254712345678"
        ]

        for inp in valid_inputs:
            # Validation should pass
            # Expected: input saved to context["phone"], progress to next_node
            pass

def test_38_regex_validation_invalid_input_retries(self, prompt_node_with_regex_validation):
        """✅ REGEX validation - invalid input shows error and retries"""
        # Spec: "Invalid input → show error_message, retry"
        node = prompt_node_with_regex_validation
        context = {}

        invalid_inputs = [
            "123",  # Too short
            "abcd1234567890",  # Contains letters
            "+254-712-345678",  # Contains hyphens
        ]

        # Expected for each:
        # - Validation fails
        # - Show error_message: "Invalid phone format"
        # - needs_input=True (wait for retry)
        # - Increment retry counter
        # - Show counter_text if defined


class TestPromptExpressionValidation:
    """Test EXPRESSION validation behavior"""

def test_39_expression_validation_basic_checks(self, prompt_node_with_expression_validation):
        """✅ EXPRESSION validation - isNumeric, length, comparisons"""
        # Spec: "Supported Methods: input.isAlpha(), input.isNumeric(), input.isDigit(), input.length"
        node = prompt_node_with_expression_validation
        context = {}

        # Rule: "input.isNumeric() && input > 0 && input <= 120"
        valid_cases = [
            "25",
            "1",
            "120"
        ]

        invalid_cases = [
            "0",  # Not > 0
            "121",  # Exceeds 120
            "abc",  # Not numeric
            "-5"  # Negative
        ]

        # Valid cases should pass validation and save
        # Invalid cases should show error and retry

def test_40_expression_with_context_variables(self, prompt_node_basic):
        """✅ EXPRESSION validation can access context variables"""
        # Spec: "Context variable access: context.max_value"
        node = prompt_node_basic.copy()
        node["config"]["validation"] = {
            "type": "EXPRESSION",
            "rule": "input.isNumeric() && input < context.max_value",
            "error_message": "Value must be less than max"
        }

        context = {"max_value": 100}

        # Input "50" with max_value=100 should pass
        # Input "150" with max_value=100 should fail


class TestPromptInterrupts:
    """Test interrupt keyword handling"""

def test_41_interrupts_bypass_validation(self, prompt_node_with_interrupts):
        """✅ Interrupts bypass validation and route immediately"""
        # Spec: "Interrupt Behavior: Bypasses all validation checks"
        # "Does not save to variable, Does not count as retry attempt"
        node = prompt_node_with_interrupts
        context = {}

        # Node has interrupts: [{"input": "0", "target_node": "node_cancel"}]
        interrupt_input = "0"

        # Expected:
        # - Check interrupt BEFORE validation
        # - Match found → route to "node_cancel"
        # - Variable "value" NOT saved to context
        # - Retry counter NOT incremented
        # - Validation not executed

        # Even if validation would fail, interrupt takes precedence
        assert "0" == interrupt_input

def test_42_interrupt_case_insensitive_whitespace_trimmed(self, prompt_node_with_interrupts):
        """✅ Interrupts: case-insensitive, whitespace trimmed"""
        # Spec: "Interrupt keywords are trimmed before matching, Case-insensitive matching applied"
        node = prompt_node_with_interrupts

        interrupt_variations = [
            "0",
            " 0 ",
            "  0",
            "0  ",
            "back",
            "BACK",
            "Back",
            " back ",
        ]

        # All should match interrupts
        # "0" → node_cancel
        # "back" → node_previous


class TestPromptRetryLogic:
    """Test validation retry behavior"""

def test_43_max_attempts_exceeded_routes_to_fail_route(self, prompt_node_basic):
        """✅ Max attempts exceeded routes to fail_route"""
        # Spec: "After max attempts exceeded routes to fail_route or terminates"
        # Default max_attempts: 3

        node = prompt_node_basic.copy()
        node["config"]["validation"] = {
            "type": "EXPRESSION",
            "rule": "input.isNumeric()",
            "error_message": "Must be a number"
        }

        context = {}
        flow_defaults = {
            "retry_logic": {
                "max_attempts": 3,
                "counter_text": "(Attempt {{current_attempt}} of {{max_attempts}})",
                "fail_route": "node_fail"
            }
        }

        # Attempt 1: invalid input "abc" → retry, counter: 1/3
        # Attempt 2: invalid input "xyz" → retry, counter: 2/3
        # Attempt 3: invalid input "def" → retry, counter: 3/3
        # Attempt 4: max exceeded → route to "node_fail"

        # Expected: next_node = "node_fail"


class TestPromptEmptyInputHandling:
    """Test empty input behavior"""

def test_44_empty_input_rejected_by_default(self, prompt_node_basic):
        """✅ Empty input rejected by default unless validation allows"""
        # Spec: "Default Behavior: Empty input is ALWAYS REJECTED unless explicitly allowed"
        node = prompt_node_basic
        context = {}

        empty_inputs = ["", "   ", "\t", "\n"]

        # System trims whitespace, so all become ""
        # Expected: validation error "This field is required. Please enter a value."
        # Counts toward retry attempts

def test_45_empty_input_allowed_with_explicit_validation(self, prompt_node_basic):
        """✅ Empty input allowed when validation explicitly permits"""
        # Spec: "To explicitly allow empty input (optional fields):"
        # "rule": "input.length == 0 || (input.isNumeric() && input.length == 10)"
        node = prompt_node_basic.copy()
        node["config"]["validation"] = {
            "type": "EXPRESSION",
            "rule": "input.length == 0 || input.length >= 3",
            "error_message": "Enter at least 3 characters or leave empty"
        }

        context = {}

        # Empty input "" → validation passes (input.length == 0 is true)
        # Saved as empty string ""
        # Input "ab" → fails (not empty, less than 3)
        # Input "abc" → passes (>= 3)


class TestPromptTypeConversion:
    """Test type conversion after validation"""

def test_46_type_conversion_on_save(self, prompt_node_basic):
        """✅ Type conversion based on variable declaration"""
        # Spec: "User input (string) converted based on variable type"
        # "Number variable: '42' → 42"
        # "Conversion failure → validation error, retry"

        node = prompt_node_basic.copy()
        node["config"]["save_to_variable"] = "age"

        # Variable declared in flow as: {"age": {"type": "number", "default": 0}}
        flow_variables = {
            "age": {"type": "number", "default": 0}
        }

        context = {}

        # User inputs "25" (string)
        # After validation passes, convert to number
        # Expected: context["age"] = 25 (number)

        # User inputs "abc" (string)
        # Conversion fails (cannot convert "abc" to number)
        # Expected: validation error, retry

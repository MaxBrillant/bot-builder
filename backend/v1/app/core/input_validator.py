"""
Input Validator
Validates user input in PROMPT nodes (REGEX, EXPRESSION validation types).
"""
import re
from typing import Any, Dict
from app.utils.shared import PathResolver, TypeConverter
from app.utils.logger import get_logger
from app.utils.exceptions import InputValidationError
from app.utils.constants import VariableType, SystemConstraints, RegexPatterns

logger = get_logger(__name__)


# ===== Class 1: InputValidator (~150 lines) =====
class InputValidator:
    """
    Input validation system for PROMPT nodes

    Features:
    - REGEX validation (full string match)
    - EXPRESSION validation (custom methods via string replacement and evaluation)
    - Type conversion (using TypeConverter)
    - Safe evaluation (no arbitrary code execution)

    Supported Expression Methods:
    - input.isAlpha() - Only letters (a-z, A-Z)
    - input.isNumeric() - Numeric format (digits, optional decimal, optional minus)
    - input.isDigit() - Only digits (0-9)
    - input.length - String length property
    - Context variable access (including array indices like context.items.0)
    - Comparison operators
    - Logical operators (&&, ||)
    """

    def __init__(self):
        self.path_resolver = PathResolver()
        self.type_converter = TypeConverter()

    def validate_regex(self, input_value: str, pattern: str) -> bool:
        """
        Validate input against regex pattern (full match)

        Args:
            input_value: User input to validate
            pattern: Regex pattern

        Returns:
            True if input matches pattern, False otherwise

        Note:
            Full string matching is enforced automatically.
            Anchors (^, $) are implicit but can be added for clarity.

        Unsupported Features (per spec section 6):
            - Lookahead/lookbehind assertions
            - Named groups
        """
        if not pattern:
            return True  # No pattern means no validation

        try:
            # Check for unsupported regex features BEFORE compilation
            unsupported_features = [
                (r'\(\?[=!]', 'lookahead assertions (?= or ?!)'),
                (r'\(\?<[=!]', 'lookbehind assertions (?<= or ?<!)'),
                (r'\(\?P<\w+>', 'named groups (?P<name>...)'),
            ]

            for feature_pattern, feature_name in unsupported_features:
                if re.search(feature_pattern, pattern):
                    logger.error(
                        f"Unsupported regex feature: {feature_name}",
                        pattern=pattern,
                        feature=feature_name
                    )
                    return False

            # Compile pattern
            regex = re.compile(pattern)

            # Full match required (match entire string)
            match = regex.fullmatch(input_value)

            return match is not None

        except re.error as e:
            logger.error(f"Invalid regex pattern: {str(e)}", pattern=pattern)
            return False
        except Exception as e:
            logger.error(f"Regex validation error: {str(e)}")
            return False

    def validate_expression(self, input_value: str, rule: str, context: Dict[str, Any]) -> bool:
        """
        Validate input using expression rule

        Args:
            input_value: User input to validate
            rule: Expression rule (e.g., "input.isAlpha() && input.length >= 3")
            context: Session context for variable access

        Returns:
            True if expression evaluates to true, False otherwise

        Supported Methods (per spec section 6):
            - input.isAlpha() - Only letters (a-z, A-Z)
            - input.isNumeric() - Numeric format
            - input.isDigit() - Only digits (0-9)
            - input.length - String length property
            - Context variable access (context.*)
            - Logical operators (&&, ||)

        Unsupported (will return False):
            - Custom functions (parseInt, etc.)
            - String methods beyond isAlpha/isNumeric/isDigit
            - Array/object methods
            - Date/time operations
        """
        if not rule:
            return True

        try:
            # Validate expression syntax BEFORE evaluation
            self._validate_expression_syntax(rule)

            # Create evaluation context with input methods
            eval_context = {
                'input': input_value,
                'context': context
            }

            return self._evaluate_expression(rule, eval_context)

        except ValueError as e:
            # Syntax validation errors
            logger.error(f"Expression syntax error: {str(e)}", rule=rule)
            return False
        except Exception as e:
            logger.error(f"Expression validation error: {str(e)}", rule=rule)
            return False

    def _validate_expression_syntax(self, expr: str) -> None:
        """
        Validate that expression uses only supported syntax

        Raises:
            ValueError: If expression contains unsupported features

        Per spec section 6, supported features:
            - input.isAlpha(), input.isNumeric(), input.isDigit()
            - input.length
            - context.* (variable access)
            - Comparison operators (==, !=, >, <, >=, <=)
            - Logical operators (&&, ||)

        Unsupported features:
            - Custom functions (parseInt, toUpperCase, includes, etc.)
            - String methods beyond isAlpha/isNumeric/isDigit
            - Array/object methods
            - Date/time operations
        """
        from app.utils.constants import SystemConstraints

        # Check expression length (spec: MAX_EXPRESSION_LENGTH = 512)
        if len(expr) > SystemConstraints.MAX_EXPRESSION_LENGTH:
            raise ValueError(
                f"Expression exceeds maximum length of {SystemConstraints.MAX_EXPRESSION_LENGTH} characters "
                f"(current: {len(expr)} characters)"
            )
        # Check for unsupported input methods (method calls with parentheses)
        input_methods = re.findall(r'input\.(\w+)\s*\(', expr)
        supported_input_methods = ['isAlpha', 'isNumeric', 'isDigit']

        for method in input_methods:
            if method not in supported_input_methods:
                raise ValueError(
                    f"Unsupported method: input.{method}(). "
                    f"Supported methods: {', '.join(['input.' + m + '()' for m in supported_input_methods])}"
                )

        # Check for unsupported input properties (beyond 'length')
        # Find all input.xxx references, then exclude methods to get only properties
        all_input_refs = re.findall(r'input\.(\w+)', expr)
        input_properties = [ref for ref in all_input_refs if ref not in input_methods]
        supported_properties = ['length']

        for prop in input_properties:
            if prop not in supported_properties:
                raise ValueError(
                    f"Unsupported property: input.{prop}. "
                    f"Only 'input.length' is supported as a property."
                )

        # Check for standalone functions (e.g., parseInt, toUpperCase called on input)
        # This catches things like: parseInt(input), input.toUpperCase(), etc.
        # Pattern: word followed by parentheses that's NOT input.method() or context.
        standalone_functions = re.findall(r'\b(\w+)\s*\([^)]*\)', expr)

        # Filter out supported methods and keywords
        allowed_in_functions = supported_input_methods + ['input', 'context']
        unsupported_functions = [
            f for f in standalone_functions
            if f not in allowed_in_functions
        ]

        if unsupported_functions:
            raise ValueError(
                f"Unsupported functions: {', '.join(unsupported_functions)}. "
                f"Only input.isAlpha(), input.isNumeric(), and input.isDigit() are supported. "
                f"Functions like parseInt(), toUpperCase(), includes() are not supported."
            )

    def _evaluate_expression(self, expr: str, eval_context: Dict[str, Any]) -> bool:
        """Evaluate custom expression with input context"""
        expr = expr.strip()
        input_value = eval_context.get('input', '')
        context = eval_context.get('context', {})

        # Replace input methods
        expr = self._replace_input_methods(expr, input_value)

        # Replace context variable references using PathResolver
        expr = self._replace_context_variables(expr, context)

        # Handle logical operators
        # Check || first (lower precedence) to ensure correct parsing order
        # Expression "a && b || c" should parse as "(a && b) || c"
        if '||' in expr:
            parts = [p.strip() for p in expr.split('||')]
            return any(self._evaluate_simple(part) for part in parts)

        if '&&' in expr:
            parts = [p.strip() for p in expr.split('&&')]
            return all(self._evaluate_simple(part) for part in parts)

        return self._evaluate_simple(expr)

    def _replace_input_methods(self, expr: str, input_value: str) -> str:
        """Replace input methods with their evaluated results"""
        # input.isAlpha() - only letters
        if 'input.isAlpha()' in expr:
            result = input_value.isalpha() if input_value else False
            expr = expr.replace('input.isAlpha()', str(result))

        # input.isNumeric() - numeric format
        if 'input.isNumeric()' in expr:
            result = self._is_numeric(input_value)
            expr = expr.replace('input.isNumeric()', str(result))

        # input.isDigit() - only digits
        if 'input.isDigit()' in expr:
            result = input_value.isdigit() if input_value else False
            expr = expr.replace('input.isDigit()', str(result))

        # input.length - string length
        if 'input.length' in expr:
            length = len(input_value) if input_value else 0
            expr = expr.replace('input.length', str(length))

        return expr

    def _is_numeric(self, value: str) -> bool:
        """
        Check if string is numeric format

        Per spec section 6, accepts:
            - "123" (integer)
            - "-45" (negative integer)
            - "12.34" (decimal)
            - ".5" (leading decimal point)
            - "1." (trailing decimal point)

        Rejects:
            - "1e10" (scientific notation)
            - "1.2.3" (multiple decimals)
            - "--5" (multiple minus signs)
            - "+5" (plus sign not supported)
        """
        from app.utils.constants import RegexPatterns

        if not value:
            return False

        # Pattern: optional minus, then either:
        #   - digits with optional trailing decimal: \d+\.?
        #   - optional digits with decimal and required trailing digits: \d*\.\d+
        # This accepts both "1." and ".5" for consistency
        return bool(re.match(RegexPatterns.NUMERIC_INPUT, value))

    def _replace_context_variables(self, expr: str, context: Dict[str, Any]) -> str:
        """Replace context variables with their values using PathResolver"""
        # Find context.variable patterns (supports array indices like context.items.0.name)
        # Pattern matches: identifier OR numeric, then (dot + identifier OR numeric) repeated
        pattern = r'context\.((?:[a-zA-Z_][a-zA-Z0-9_]*|\d+)(?:\.(?:[a-zA-Z_][a-zA-Z0-9_]*|\d+))*)'

        def replace_var(match):
            var_path = match.group(1)
            value = self.path_resolver.resolve(f"context.{var_path}", {'context': context})

            if value is None:
                return 'None'
            elif isinstance(value, bool):
                return str(value)
            elif isinstance(value, str):
                return f'"{value}"'
            else:
                return str(value)

        return re.sub(pattern, replace_var, expr)

    def _evaluate_simple(self, expr: str) -> bool:
        """Evaluate simple boolean expression"""
        expr = expr.strip()

        # Handle boolean literals
        if expr in ['True', 'true']:
            return True
        if expr in ['False', 'false']:
            return False

        # Handle comparisons
        for op in ['>=', '<=', '==', '!=', '>', '<']:
            if op in expr:
                parts = expr.split(op, 1)
                if len(parts) == 2:
                    left = self._parse_value(parts[0].strip())
                    right = self._parse_value(parts[1].strip())
                    return self._compare(left, op, right)

        # Single value (truthy check)
        return self._parse_value(expr) not in [False, None, 0, '']

    def _parse_value(self, value_str: str) -> Any:
        """Parse string value to appropriate type"""
        value_str = value_str.strip()

        if value_str == 'None':
            return None
        if value_str in ['True', 'true']:
            return True
        if value_str in ['False', 'false']:
            return False
        if value_str.startswith('"') and value_str.endswith('"'):
            return value_str[1:-1]

        try:
            if '.' in value_str:
                return float(value_str)
            return int(value_str)
        except ValueError:
            return value_str

    def _compare(self, left: Any, op: str, right: Any) -> bool:
        """Perform comparison"""
        try:
            if op == '==':
                return left == right
            elif op == '!=':
                return left != right
            elif op == '>':
                return left > right
            elif op == '<':
                return left < right
            elif op == '>=':
                return left >= right
            elif op == '<=':
                return left <= right
            return False
        except Exception:
            return False

    def convert_type(self, value: Any, target_type: str) -> Any:
        """
        Convert value to target variable type using TypeConverter

        Args:
            value: Input value
            target_type: Target type (STRING, NUMBER, BOOLEAN, ARRAY)

        Returns:
            Converted value

        Raises:
            InputValidationError: If conversion fails
        """
        try:
            if target_type == VariableType.STRING.value:
                result = self.type_converter.to_string(value)
                # to_string returns None only if value is None, which is valid
                return result
            elif target_type == VariableType.NUMBER.value:
                result = self.type_converter.to_number(value)
                if result is None and value is not None:
                    raise InputValidationError(
                        message=f"Cannot convert '{value}' to number",
                        error_code="TYPE_CONVERSION_ERROR",
                        value=str(value),
                        target_type=target_type
                    )
                return result
            elif target_type == VariableType.BOOLEAN.value:
                result = self.type_converter.to_boolean(value)
                if result is None and value is not None:
                    raise InputValidationError(
                        message=f"Cannot convert '{value}' to boolean",
                        error_code="TYPE_CONVERSION_ERROR",
                        value=str(value),
                        target_type=target_type
                    )
                return result
            elif target_type == VariableType.ARRAY.value:
                result = self.type_converter.to_array(value)
                if result is None and value is not None:
                    raise InputValidationError(
                        message=f"Cannot convert '{value}' to array",
                        error_code="TYPE_CONVERSION_ERROR",
                        value=str(value),
                        target_type=target_type
                    )
                return result
            else:
                return value
        except Exception as e:
            raise InputValidationError(
                message=str(e),
                error_code="TYPE_CONVERSION_ERROR",
                value=str(value),
                target_type=target_type
            )

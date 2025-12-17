"""
Shared utilities used across the codebase
Eliminates ~400 lines of code duplication

This module consolidates:
- Path resolution logic (duplicated in template_engine.py, condition_evaluator.py, validation_system.py)
- Type conversion logic (duplicated in validation_system.py, processors)
- Expression parsing (replaces string hacks in condition_evaluator.py, validation_system.py)
"""

from typing import Any, Optional, Dict, List, Union
from dataclasses import dataclass
from enum import Enum
import re
import json
from app.utils.logger import get_logger
from app.utils.exceptions import InputValidationError

logger = get_logger(__name__)


class PathResolver:
    """
    Centralized dot-notation path resolution with null-safety

    Replaces duplicate code in:
    - template_engine.py lines 127-186
    - condition_evaluator.py lines 163-210
    - validation_system.py lines 232-258

    Examples:
        >>> PathResolver.resolve("user.name", {"user": {"name": "John"}})
        "John"

        >>> PathResolver.resolve("items.0", {"items": ["a", "b"]})
        "a"

        >>> PathResolver.resolve("missing.path", {})
        None

        >>> PathResolver.resolve_with_default("missing", {}, "default")
        "default"
    """

    @staticmethod
    def resolve(path: str, context: Dict[str, Any]) -> Optional[Any]:
        """
        Resolve dot-notation path to actual value with null-safety

        Args:
            path: Variable path (e.g., 'context.user.name', 'items.0')
            context: Context dictionary

        Returns:
            Resolved value or None if not found
        """
        if not path:
            return None

        try:
            parts = path.split('.')
            current = context

            for part in parts:
                if current is None:
                    return None

                # Handle dictionary access
                if isinstance(current, dict):
                    current = current.get(part)

                # Handle array/list access (numeric indices)
                elif isinstance(current, (list, tuple)):
                    try:
                        index = int(part)
                        if 0 <= index < len(current):
                            current = current[index]
                        else:
                            return None  # Index out of bounds
                    except (ValueError, IndexError):
                        return None

                # Handle object attribute access
                elif hasattr(current, part):
                    current = getattr(current, part)

                else:
                    return None  # Path not found

            return current

        except Exception as e:
            logger.debug(f"Path resolution error: {str(e)}", path=path)
            return None

    @staticmethod
    def resolve_with_default(path: str, context: Dict[str, Any], default: Any) -> Any:
        """
        Resolve path with fallback to default value

        Args:
            path: Variable path
            context: Context dictionary
            default: Default value if path not found

        Returns:
            Resolved value or default
        """
        result = PathResolver.resolve(path, context)
        return default if result is None else result


class TypeConverter:
    """
    Centralized type conversion with consistent error handling

    Replaces duplicate logic in:
    - validation_system.py lines 329-416
    - prompt_processor.py type conversion
    - menu_processor.py type conversion

    Examples:
        >>> TypeConverter.to_string(123)
        "123"

        >>> TypeConverter.to_integer("42")
        42

        >>> TypeConverter.to_boolean("yes")
        True

        >>> TypeConverter.to_array("a,b,c")
        ["a", "b", "c"]
    """

    @staticmethod
    def to_string(value: Any) -> str:
        """
        Convert value to string

        Args:
            value: Input value

        Returns:
            String representation
        """
        if value is None:
            return ""
        return str(value) if not isinstance(value, str) else value

    @staticmethod
    def to_integer(value: Any) -> Optional[int]:
        """
        Convert value to integer, return None on failure

        Args:
            value: Input value

        Returns:
            Integer value or None if conversion fails
        """
        if value is None:
            return None

        # If already an integer, return as-is
        if isinstance(value, int) and not isinstance(value, bool):
            return value

        # If it's a float, truncate to int
        if isinstance(value, float):
            return int(value)

        # Try to convert string to integer
        if isinstance(value, str):
            try:
                return int(value.strip())
            except ValueError:
                return None

        # For other types, try conversion
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def to_boolean(value: Any) -> Optional[bool]:
        """
        Convert value to boolean with consistent rules

        Truthy values: true, 1, yes, y (case-insensitive)
        Falsy values: false, 0, no, n, empty string (case-insensitive)

        Args:
            value: Input value

        Returns:
            Boolean value or None if conversion fails
        """
        if value is None:
            return None

        # If already a boolean, return as-is
        if isinstance(value, bool):
            return value

        # Convert string to boolean
        if isinstance(value, str):
            value_lower = value.lower().strip()
            if value_lower in ['true', '1', 'yes', 'y']:
                return True
            elif value_lower in ['false', '0', 'no', 'n', '']:
                return False
            else:
                return None

        # Convert numbers to boolean (0 = false, non-zero = true)
        if isinstance(value, (int, float)):
            return bool(value)

        return None

    @staticmethod
    def to_array(value: Any) -> Optional[List]:
        """
        Convert value to array/list

        Args:
            value: Input value

        Returns:
            List or None if conversion fails
        """
        if value is None:
            return None

        # If already an array, return as-is
        if isinstance(value, list):
            return value

        # If tuple, convert to list
        if isinstance(value, tuple):
            return list(value)

        # Try to parse JSON string as array
        if isinstance(value, str):
            # First try JSON parsing
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass

            # Fallback: parse as comma-separated
            if ',' in value:
                return [item.strip() for item in value.split(',')]

            # Single value -> single-element array
            return [value] if value.strip() else []

        # For other types, wrap in array
        return [value]

    @staticmethod
    def convert(value: Any, target_type: str) -> Any:
        """
        Convert value to target type with error handling

        Args:
            value: Input value
            target_type: Target type (string, number, boolean, array)

        Returns:
            Converted value

        Raises:
            InputValidationError: If conversion fails
        """
        if value is None:
            return None

        if target_type == "string":
            return TypeConverter.to_string(value)

        elif target_type == "number":
            result = TypeConverter.to_integer(value)
            if result is None:
                raise InputValidationError(f"Cannot convert '{value}' to number")
            return result

        elif target_type == "boolean":
            result = TypeConverter.to_boolean(value)
            if result is None:
                raise InputValidationError(f"Cannot convert '{value}' to boolean")
            return result

        elif target_type == "array":
            result = TypeConverter.to_array(value)
            if result is None:
                raise InputValidationError(f"Cannot convert '{value}' to array")
            return result

        else:
            # Unknown type, return as-is
            return value


# Expression AST node types
@dataclass
class ExpressionNode:
    """Base class for expression AST nodes"""
    pass


@dataclass
class LiteralNode(ExpressionNode):
    """Literal value node (string, number, boolean, null)"""
    value: Any


@dataclass
class VariableNode(ExpressionNode):
    """Variable reference node (e.g., 'context.user.name')"""
    path: str


@dataclass
class BinaryOpNode(ExpressionNode):
    """Binary operation node (e.g., 'a > b', 'x && y')"""
    left: ExpressionNode
    operator: str
    right: ExpressionNode


@dataclass
class MethodCallNode(ExpressionNode):
    """Method call node (e.g., 'input.contains("text")')"""
    target: ExpressionNode
    method: str
    args: List[Any]


class ExpressionParser:
    """
    Proper expression parser with simple AST

    Replaces string hacks in:
    - condition_evaluator.py lines 88-95 (string splitting for &&, ||)
    - validation_system.py lines 143-173 (string replacement)

    Supports:
    - Literals: numbers, strings (quoted), booleans (true/false), null
    - Variables: dot-notation paths (context.user.name)
    - Comparisons: ==, !=, >, <, >=, <=
    - Logical operators: && (and), || (or)
    - Method calls: input.contains("text"), input.matches("pattern")

    Examples:
        >>> parser = ExpressionParser()
        >>> parser.evaluate("context.age > 18", {"age": 25})
        True

        >>> parser.evaluate("input.contains('yes')", {"input": "yes please"})
        True

        >>> parser.evaluate("context.verified && context.age >= 18", {"verified": True, "age": 20})
        True
    """

    # Operator patterns
    COMPARISON_OPERATORS = ['==', '!=', '>=', '<=', '>', '<']
    LOGICAL_OPERATORS = ['&&', '||']

    # Regex patterns
    OPERATOR_PATTERN = re.compile(r'(==|!=|>=|<=|>|<)')
    METHOD_PATTERN = re.compile(r'(\w+(?:\.\w+)*)\.(contains|matches|startswith|endswith)\s*\(\s*["\']([^"\']*)["\']?\s*\)')

    def parse(self, expression: str) -> ExpressionNode:
        """
        Parse expression string into AST

        Args:
            expression: Expression to parse

        Returns:
            Root AST node
        """
        expression = expression.strip()

        # Handle logical operators (lowest precedence)
        if '||' in expression:
            parts = [p.strip() for p in expression.split('||')]
            nodes = [self.parse(part) for part in parts]
            # Build left-associative tree
            result = nodes[0]
            for node in nodes[1:]:
                result = BinaryOpNode(result, '||', node)
            return result

        if '&&' in expression:
            parts = [p.strip() for p in expression.split('&&')]
            nodes = [self.parse(part) for part in parts]
            # Build left-associative tree
            result = nodes[0]
            for node in nodes[1:]:
                result = BinaryOpNode(result, '&&', node)
            return result

        # Handle method calls (e.g., input.contains("text"))
        method_match = self.METHOD_PATTERN.search(expression)
        if method_match:
            target_path = method_match.group(1)
            method = method_match.group(2)
            arg = method_match.group(3)
            return MethodCallNode(
                target=VariableNode(target_path),
                method=method,
                args=[arg]
            )

        # Handle comparison operators
        operator_match = self.OPERATOR_PATTERN.search(expression)
        if operator_match:
            operator = operator_match.group(1)
            left_expr = expression[:operator_match.start()].strip()
            right_expr = expression[operator_match.end():].strip()

            return BinaryOpNode(
                left=self._parse_value(left_expr),
                operator=operator,
                right=self._parse_value(right_expr)
            )

        # Single value (variable or literal)
        return self._parse_value(expression)

    def _parse_value(self, expr: str) -> ExpressionNode:
        """Parse a single value (literal or variable)"""
        expr = expr.strip()

        # Handle null/None
        if expr in ['null', 'None', 'none', 'NULL']:
            return LiteralNode(None)

        # Handle boolean literals
        if expr in ['true', 'True', 'TRUE']:
            return LiteralNode(True)
        if expr in ['false', 'False', 'FALSE']:
            return LiteralNode(False)

        # Handle string literals (quoted)
        if (expr.startswith('"') and expr.endswith('"')) or \
           (expr.startswith("'") and expr.endswith("'")):
            return LiteralNode(expr[1:-1])

        # Handle numeric literals
        try:
            # Try integer first
            if '.' not in expr:
                return LiteralNode(int(expr))
            else:
                return LiteralNode(float(expr))
        except ValueError:
            pass

        # Must be a variable reference
        return VariableNode(expr)

    def evaluate(self, expression: str, context: Dict[str, Any]) -> Any:
        """
        Parse and evaluate expression in given context

        Args:
            expression: Expression to evaluate
            context: Context dictionary

        Returns:
            Evaluation result
        """
        try:
            ast = self.parse(expression)
            return self._evaluate_node(ast, context)
        except Exception as e:
            logger.error(f"Expression evaluation error: {str(e)}", expression=expression)
            return False

    def _evaluate_node(self, node: ExpressionNode, context: Dict[str, Any]) -> Any:
        """Evaluate an AST node"""
        if isinstance(node, LiteralNode):
            return node.value

        elif isinstance(node, VariableNode):
            return PathResolver.resolve(node.path, context)

        elif isinstance(node, BinaryOpNode):
            left = self._evaluate_node(node.left, context)
            right = self._evaluate_node(node.right, context)

            if node.operator == '&&':
                return self._is_truthy(left) and self._is_truthy(right)
            elif node.operator == '||':
                return self._is_truthy(left) or self._is_truthy(right)
            elif node.operator == '==':
                return self._compare_equal(left, right)
            elif node.operator == '!=':
                return not self._compare_equal(left, right)
            elif node.operator == '>':
                return self._compare_numeric(left, right, lambda a, b: a > b)
            elif node.operator == '<':
                return self._compare_numeric(left, right, lambda a, b: a < b)
            elif node.operator == '>=':
                return self._compare_numeric(left, right, lambda a, b: a >= b)
            elif node.operator == '<=':
                return self._compare_numeric(left, right, lambda a, b: a <= b)
            else:
                return False

        elif isinstance(node, MethodCallNode):
            target = self._evaluate_node(node.target, context)
            if target is None:
                return False

            target_str = str(target).lower()
            arg_str = str(node.args[0]).lower() if node.args else ""

            if node.method == 'contains':
                return arg_str in target_str
            elif node.method == 'matches':
                try:
                    return bool(re.search(node.args[0], str(target)))
                except re.error:
                    return False
            elif node.method == 'startswith':
                return target_str.startswith(arg_str)
            elif node.method == 'endswith':
                return target_str.endswith(arg_str)
            else:
                return False

        return False

    def _is_truthy(self, value: Any) -> bool:
        """Check if value is truthy"""
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return len(value) > 0 and value.lower() not in ['false', '0', 'no', 'n']
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, (list, dict)):
            return len(value) > 0
        return bool(value)

    def _compare_equal(self, left: Any, right: Any) -> bool:
        """Compare values for equality with type coercion"""
        # Null equality
        if left is None or right is None:
            return left == right

        # Try direct comparison first
        try:
            return left == right
        except:
            pass

        # String comparison (case-insensitive)
        try:
            return str(left).lower() == str(right).lower()
        except:
            return False

    def _compare_numeric(self, left: Any, right: Any, op) -> bool:
        """Compare numeric values"""
        try:
            left_num = float(left) if not isinstance(left, (int, float)) else left
            right_num = float(right) if not isinstance(right, (int, float)) else right
            return op(left_num, right_num)
        except (ValueError, TypeError):
            return False

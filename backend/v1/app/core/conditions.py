"""
Route Evaluation System
Consolidates: condition_evaluator.py + route_sorter.py

Two focused classes:
- ConditionEvaluator: Evaluates route conditions for node routing
- RouteSorter: Sorts routes by condition priority
"""

import re
from typing import Any, Dict, List

from app.utils.shared import PathResolver
from app.utils.logger import get_logger
from app.utils.exceptions import ConditionEvaluationError

logger = get_logger(__name__)


# ===== Class 1: ConditionEvaluator (~200 lines) =====
class ConditionEvaluator:
    """
    Evaluate routing conditions against context

    Supported:
    - Keywords: success, error, true, false
    - Comparison: ==, !=, >, <, >=, <=
    - Logical: &&, ||
    - Context access: context.variable
    - Null-safe navigation (using PathResolver)
    - Strict type checking (no coercion)

    Not supported:
    - Arithmetic operations
    - String manipulation
    - Function calls
    - Complex expressions
    """

    # Comparison operators
    OPERATORS = {
        '==': lambda a, b: a == b,
        '!=': lambda a, b: a != b,
        '>': lambda a, b: (a > b if isinstance(a, (int, float)) and not isinstance(a, bool)
                           and isinstance(b, (int, float)) and not isinstance(b, bool) else False),
        '<': lambda a, b: (a < b if isinstance(a, (int, float)) and not isinstance(a, bool)
                           and isinstance(b, (int, float)) and not isinstance(b, bool) else False),
        '>=': lambda a, b: (a >= b if isinstance(a, (int, float)) and not isinstance(a, bool)
                            and isinstance(b, (int, float)) and not isinstance(b, bool) else False),
        '<=': lambda a, b: (a <= b if isinstance(a, (int, float)) and not isinstance(a, bool)
                            and isinstance(b, (int, float)) and not isinstance(b, bool) else False),
    }

    # Operator regex pattern (order matters - longer operators first)
    OPERATOR_PATTERN = re.compile(r'(==|!=|>=|<=|>|<)')

    def __init__(self):
        self.path_resolver = PathResolver()

    def evaluate(self, condition: str, context: Dict[str, Any]) -> bool:
        """
        Evaluate condition against context

        Args:
            condition: Condition string to evaluate
            context: Context dictionary with variables

        Returns:
            True if condition evaluates to true, False otherwise

        Examples:
            >>> evaluator = ConditionEvaluator()
            >>> evaluator.evaluate("success", {"_api_result": "success"})
            True

            >>> evaluator.evaluate("context.age > 18", {"age": 25})
            True

            >>> evaluator.evaluate("true", {})
            True
        """
        if not condition:
            return False

        condition = condition.strip()

        try:
            # Handle keyword conditions
            if condition in ['true', 'True', 'TRUE']:
                return True

            if condition in ['false', 'False', 'FALSE']:
                return False

            if condition == 'success':
                return context.get('_api_result') == 'success'

            if condition == 'error':
                return context.get('_api_result') == 'error'

            # Handle logical operators (||, &&)
            # Check || first (lower precedence) to ensure correct parsing order
            # Expression "a && b || c" should parse as "(a && b) || c"
            if '||' in condition:
                parts = [p.strip() for p in condition.split('||')]
                return any(self.evaluate(part, context) for part in parts)

            if '&&' in condition:
                parts = [p.strip() for p in condition.split('&&')]
                return all(self.evaluate(part, context) for part in parts)

            # Handle comparison expressions
            match = self.OPERATOR_PATTERN.search(condition)
            if match:
                operator = match.group(1)
                left_expr = condition[:match.start()].strip()
                right_expr = condition[match.end():].strip()

                left_value = self._resolve_value(left_expr, context)
                right_value = self._resolve_value(right_expr, context)

                return self._compare(left_value, operator, right_value)

            # Single variable reference (truthy check)
            value = self._resolve_value(condition, context)
            return self._is_truthy(value)

        except Exception as e:
            logger.error(f"Condition evaluation error: {str(e)}", condition=condition, exc_info=True)
            raise ConditionEvaluationError(
                message="Condition evaluation failed",
                error_code="CONDITION_EVALUATION_ERROR",
                condition=condition
            )

    def _resolve_value(self, expr: str, context: Dict[str, Any]) -> Any:
        """
        Resolve expression to actual value

        Args:
            expr: Expression to resolve (e.g., 'context.user.age', '18', '"text"', 'null')
            context: Context dictionary

        Returns:
            Resolved value
        """
        expr = expr.strip()

        # Handle null/None
        if expr in ['null', 'None', 'none', 'NULL']:
            return None

        # Handle boolean literals
        if expr in ['true', 'True', 'TRUE']:
            return True
        if expr in ['false', 'False', 'FALSE']:
            return False

        # Handle string literals (quoted)
        if (expr.startswith('"') and expr.endswith('"')) or \
           (expr.startswith("'") and expr.endswith("'")):
            return expr[1:-1]

        # Handle numeric literals
        try:
            # Try integer
            if '.' not in expr:
                return int(expr)
            # Try float
            return float(expr)
        except ValueError:
            pass

        # Handle context variable access (dot notation) using PathResolver
        if expr.startswith('context.'):
            # Use PathResolver for consistent null-safe navigation
            return self.path_resolver.resolve(expr, {'context': context})

        # Handle direct variable access
        return self.path_resolver.resolve(expr, context)

    def _compare(self, left: Any, operator: str, right: Any) -> bool:
        """
        Perform type-aware comparison

        Args:
            left: Left operand
            operator: Comparison operator
            right: Right operand

        Returns:
            Comparison result

        Note:
            - No automatic type coercion
            - Type mismatch in comparisons returns False
        """
        try:
            # Handle None comparisons
            if operator == '==' and (left is None or right is None):
                return left == right

            if operator == '!=' and (left is None or right is None):
                return left != right

            # Get comparison function (lambdas handle type checking including boolean exclusion)
            compare_fn = self.OPERATORS.get(operator)
            if not compare_fn:
                return False

            return compare_fn(left, right)

        except Exception:
            return False

    def _is_truthy(self, value: Any) -> bool:
        """
        Check if value is truthy

        Args:
            value: Value to check

        Returns:
            True if value is truthy
        """
        if value is None:
            return False

        if isinstance(value, bool):
            return value

        if isinstance(value, (int, float)):
            return value != 0

        if isinstance(value, str):
            return len(value) > 0 and value.lower() not in ['false', '0', 'null', 'none']

        if isinstance(value, (list, dict)):
            return len(value) > 0

        return bool(value)


# ===== Class 2: RouteSorter (~80 lines) =====
class RouteSorter:
    """
    Sorts routes by condition priority to ensure optimal evaluation order

    Mirrors frontend logic from routeConditionUtils.ts
    """

    @staticmethod
    def get_condition_priority(condition: str, node_type: str) -> int:
        """
        Get priority for route condition sorting

        Lower numbers = higher priority (evaluated first)
        Higher numbers = lower priority (evaluated last)

        Args:
            condition: Route condition string (e.g., "selection == 1", "success", "true")
            node_type: Type of node (MENU, API_ACTION, LOGIC_EXPRESSION, etc.)

        Returns:
            Priority value (lower = higher priority)

        Priority Rules:
            - Catch-all "true": 1000 (always last)
            - MENU: Extract number from "selection == N", use as priority
            - API_ACTION: "success"=1, "error"=2, others=500
            - LOGIC_EXPRESSION: 500 (maintain order)
            - Default: 500
        """
        # Catch-all "true" always goes last
        if condition.strip().lower() == "true":
            return 1000

        if node_type == "MENU":
            # Extract selection number from "selection == N" pattern
            match = re.search(r'selection\s*==\s*(\d+)', condition)
            if match:
                return int(match.group(1))
            return 500

        elif node_type == "API_ACTION":
            # "success" before "error" before others
            if condition == "success":
                return 1
            if condition == "error":
                return 2
            return 500

        elif node_type == "LOGIC_EXPRESSION":
            # Custom expressions maintain their order (medium priority)
            return 500

        else:
            # Default: medium priority
            return 500

    @staticmethod
    def sort_routes(routes: List[Dict[str, Any]], node_type: str) -> List[Dict[str, Any]]:
        """
        Sort routes by condition priority

        Specific conditions evaluated first, catch-all "true" last.
        Returns a new sorted list without mutating the original.

        Args:
            routes: List of route dictionaries with 'condition' and 'target_node' keys
            node_type: Type of node (MENU, API_ACTION, LOGIC_EXPRESSION, etc.)

        Returns:
            New sorted list of routes

        Note:
            - Does NOT modify the original routes list
            - Creates a shallow copy before sorting
            - Stable sort maintains relative order for equal priorities
        """
        # Create a shallow copy to avoid modifying original
        routes_copy = list(routes)

        # Sort by priority (lower priority number = evaluated first)
        routes_copy.sort(key=lambda route: RouteSorter.get_condition_priority(
            route.get('condition', 'false'),
            node_type
        ))

        logger.debug(
            f"Sorted {len(routes_copy)} routes for {node_type}",
            node_type=node_type,
            route_count=len(routes_copy),
            conditions=[r.get('condition') for r in routes_copy]
        )

        return routes_copy


# ===== Backward Compatibility =====
# Export standalone function for existing code
def sort_routes(routes: List[Dict[str, Any]], node_type: str) -> List[Dict[str, Any]]:
    """
    Standalone function for backward compatibility

    Args:
        routes: List of route dictionaries
        node_type: Type of node

    Returns:
        Sorted list of routes
    """
    return RouteSorter.sort_routes(routes, node_type)

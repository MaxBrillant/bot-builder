"""
Condition Evaluator
Evaluates route conditions for node routing
Supports comparison operators, logical operators, and null-safe navigation
"""

import re
from typing import Any, Dict, Optional
from app.utils.logger import get_logger
from app.utils.exceptions import ConditionEvaluationError

logger = get_logger(__name__)


class ConditionEvaluator:
    """
    Evaluate routing conditions against context
    
    Supported:
    - Keywords: success, error, true, false
    - Comparison: ==, !=, >, <, >=, <=
    - Logical: &&, ||
    - Context access: context.variable
    - Null-safe navigation
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
        '>': lambda a, b: a > b if isinstance(a, (int, float)) and isinstance(b, (int, float)) else False,
        '<': lambda a, b: a < b if isinstance(a, (int, float)) and isinstance(b, (int, float)) else False,
        '>=': lambda a, b: a >= b if isinstance(a, (int, float)) and isinstance(b, (int, float)) else False,
        '<=': lambda a, b: a <= b if isinstance(a, (int, float)) and isinstance(b, (int, float)) else False,
    }
    
    # Operator regex pattern (order matters - longer operators first)
    OPERATOR_PATTERN = re.compile(r'(==|!=|>=|<=|>|<)')
    
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
            
            # Handle logical operators (&&, ||)
            if '&&' in condition:
                parts = [p.strip() for p in condition.split('&&')]
                return all(self.evaluate(part, context) for part in parts)
            
            if '||' in condition:
                parts = [p.strip() for p in condition.split('||')]
                return any(self.evaluate(part, context) for part in parts)
            
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
            logger.error(f"Condition evaluation error: {str(e)}", condition=condition)
            raise ConditionEvaluationError(f"Failed to evaluate condition: {str(e)}", condition=condition)
    
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
        
        # Handle context variable access (dot notation)
        if expr.startswith('context.'):
            path = expr[8:]  # Remove 'context.' prefix
            return self._resolve_path(path, context)
        
        # Handle direct variable access
        return self._resolve_path(expr, context)
    
    def _resolve_path(self, path: str, context: Dict[str, Any]) -> Any:
        """
        Resolve dot-notation path to value (null-safe)
        
        Args:
            path: Variable path (e.g., 'user.name', 'items.0')
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
                            return None
                    except (ValueError, IndexError):
                        return None
                
                # Handle object attribute access
                elif hasattr(current, part):
                    current = getattr(current, part)
                
                else:
                    return None
            
            return current
            
        except Exception:
            return None
    
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
            
            # Get comparison function
            compare_fn = self.OPERATORS.get(operator)
            if not compare_fn:
                return False
            
            # Type check for numeric comparisons
            if operator in ['>', '<', '>=', '<=']:
                if not (isinstance(left, (int, float)) and isinstance(right, (int, float))):
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
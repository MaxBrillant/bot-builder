"""
Validation System
Validates user input in PROMPT nodes
Supports REGEX and EXPRESSION validation types
"""

import re
from typing import Any, Dict, Optional
from app.utils.logger import get_logger
from app.utils.exceptions import InvalidInputError
from app.utils.constants import ValidationType, VariableType

logger = get_logger(__name__)


class ValidationSystem:
    """
    Input validation system for PROMPT nodes
    
    Features:
    - REGEX validation (full string match)
    - EXPRESSION validation (custom methods)
    - Type conversion (string, integer, boolean, array)
    - Safe evaluation (no arbitrary code execution)
    
    Supported Expression Methods:
    - input.isAlpha() - Only letters (a-z, A-Z)
    - input.isNumeric() - Numeric format (digits, optional decimal, optional minus)
    - input.isDigit() - Only digits (0-9)
    - input.length - String length property
    - Context variable access
    - Comparison operators
    - Logical operators (&&, ||)
    """
    
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
        
        Examples:
            >>> validator = ValidationSystem()
            >>> validator.validate_regex("123", r"^\d+$")
            True
            >>> validator.validate_regex("abc123", r"^\d+$")
            False
        """
        if not pattern:
            return True  # No pattern means no validation
        
        try:
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
        
        Examples:
            >>> validator.validate_expression("John", "input.isAlpha()", {})
            True
            >>> validator.validate_expression("123", "input.isNumeric()", {})
            True
        """
        if not rule:
            return True
        
        try:
            # Create evaluation context with input methods
            eval_context = {
                'input': input_value,
                'context': context
            }
            
            return self._evaluate_expression(rule, eval_context)
            
        except Exception as e:
            logger.error(f"Expression validation error: {str(e)}", rule=rule)
            return False
    
    def _evaluate_expression(self, expr: str, eval_context: Dict[str, Any]) -> bool:
        """
        Evaluate custom expression with input context
        
        Args:
            expr: Expression to evaluate
            eval_context: Context with input and variables
        
        Returns:
            Boolean result of expression
        """
        expr = expr.strip()
        input_value = eval_context.get('input', '')
        context = eval_context.get('context', {})
        
        # Replace input methods
        expr = self._replace_input_methods(expr, input_value)
        
        # Replace context variable references
        expr = self._replace_context_variables(expr, context)
        
        # Handle logical operators
        if '&&' in expr:
            parts = [p.strip() for p in expr.split('&&')]
            return all(self._evaluate_simple(part) for part in parts)
        
        if '||' in expr:
            parts = [p.strip() for p in expr.split('||')]
            return any(self._evaluate_simple(part) for part in parts)
        
        return self._evaluate_simple(expr)
    
    def _replace_input_methods(self, expr: str, input_value: str) -> str:
        """
        Replace input methods with their evaluated results
        
        Args:
            expr: Expression containing input methods
            input_value: Actual input string
        
        Returns:
            Expression with methods replaced by boolean values
        """
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
        Check if string is numeric
        
        Accepts:
        - Integers: "123"
        - Negative: "-45"
        - Decimals: "12.34", ".5"
        
        Rejects:
        - Scientific notation: "1e10"
        - Multiple decimals: "1.2.3"
        - Multiple signs: "--5"
        
        Args:
            value: String to check
        
        Returns:
            True if numeric format
        """
        if not value:
            return False
        
        # Pattern: optional minus, digits, optional decimal point + digits
        pattern = r'^-?\d*\.?\d+$'
        return bool(re.match(pattern, value))
    
    def _replace_context_variables(self, expr: str, context: Dict[str, Any]) -> str:
        """
        Replace context variables with their values
        
        Args:
            expr: Expression with context variables
            context: Session context
        
        Returns:
            Expression with variables replaced
        """
        # Find context.variable patterns
        pattern = r'context\.([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)'
        
        def replace_var(match):
            var_path = match.group(1)
            value = self._resolve_path(var_path, context)
            
            if value is None:
                return 'None'
            elif isinstance(value, bool):
                return str(value)
            elif isinstance(value, str):
                return f'"{value}"'
            else:
                return str(value)
        
        return re.sub(pattern, replace_var, expr)
    
    def _resolve_path(self, path: str, context: Dict[str, Any]) -> Any:
        """
        Resolve dot-notation path in context
        
        Args:
            path: Variable path
            context: Context dictionary
        
        Returns:
            Resolved value or None
        """
        try:
            parts = path.split('.')
            current = context
            
            for part in parts:
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    return None
                
                if current is None:
                    return None
            
            return current
        except Exception:
            return None
    
    def _evaluate_simple(self, expr: str) -> bool:
        """
        Evaluate simple boolean expression
        
        Args:
            expr: Simple expression (no logical operators)
        
        Returns:
            Boolean result
        """
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
    
    def convert_type(self, value: str, target_type: str) -> Any:
        """
        Convert input string to target variable type
        
        Args:
            value: Input string
            target_type: Target type (string, integer, boolean, array)
        
        Returns:
            Converted value
        
        Raises:
            InvalidInputError: If conversion fails
        """
        if target_type == VariableType.STRING.value:
            return value
        
        elif target_type == VariableType.INTEGER.value:
            try:
                return int(value)
            except ValueError:
                raise InvalidInputError(f"Cannot convert '{value}' to integer")
        
        elif target_type == VariableType.BOOLEAN.value:
            value_lower = value.lower()
            if value_lower in ['true', '1', 'yes', 'y']:
                return True
            elif value_lower in ['false', '0', 'no', 'n']:
                return False
            else:
                raise InvalidInputError(f"Cannot convert '{value}' to boolean")
        
        elif target_type == VariableType.ARRAY.value:
            # Arrays typically come from API responses, not user input
            # If needed, parse as comma-separated
            if ',' in value:
                return [item.strip() for item in value.split(',')]
            return [value]
        
        else:
            return value
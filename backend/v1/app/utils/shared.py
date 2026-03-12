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

        Supports:
        - Dot notation: 'user.name', 'items.0.id'
        - Array length: 'items.length', 'context.trips.length'
        - Wildcard for array/primitive root: '*', '*.0', '*.0.id'

        Args:
            path: Variable path (e.g., 'context.user.name', 'items.0', '*.0.id')
            context: Context dictionary

        Returns:
            Resolved value or None if not found
        """
        if not path:
            return None

        try:
            # Handle wildcard for root array/primitive access
            if path.startswith('*'):
                if path == '*':
                    # Return entire root (array or primitive)
                    return context
                elif path.startswith('*.'):
                    # Strip "*." and continue with remaining path on context
                    path = path[2:]  # Remove "*."
                    # Continue with normal resolution
                else:
                    # Invalid wildcard usage
                    return None

            parts = path.split('.')
            current = context

            for part in parts:
                if current is None:
                    return None

                # Handle dictionary access first
                # Dictionaries can have actual keys named "length", which take precedence
                # over the special .length property for arrays/strings
                if isinstance(current, dict):
                    # For dicts, always try normal key access (no special .length handling)
                    # Example: {"length": 5} should return 5, not len(dict)
                    current = current.get(part)

                # Special case: .length property for arrays/strings (but NOT dicts)
                # Example: [1,2,3].length returns 3, "hello".length returns 5
                elif part == "length" and isinstance(current, (list, tuple, str)):
                    current = len(current)
                    continue

                # Handle array/list access (numeric indices)
                elif isinstance(current, (list, tuple)):
                    try:
                        index = int(part)
                        if 0 <= index < len(current):
                            current = current[index]
                        else:
                            logger.debug(f"Array index out of bounds: {index} (length: {len(current)})", path=path)
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
    def to_string(value: Any) -> Optional[str]:
        """
        Convert value to string

        Args:
            value: Input value

        Returns:
            String representation, or None if value is None

        Note:
            Returns None for None input to maintain consistency with other
            type converter methods. Use empty string default at call site if needed.
        """
        if value is None:
            return None
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
    def to_number(value: Any) -> Optional[Union[int, float]]:
        """
        Convert value to number (supports both integers and decimals)

        Per spec, NUMBER type supports: "integers and decimals, standard JSON number"

        Returns int for whole numbers, float for decimals, to preserve correct
        JSON serialization (3 not 3.0).

        Args:
            value: Input value

        Returns:
            int or float value, or None if conversion fails
        """
        if value is None:
            return None

        # Preserve int as int
        if isinstance(value, int) and not isinstance(value, bool):
            return value

        # Float: demote whole floats to int (3.0 → 3), preserve decimals (3.5 → 3.5)
        if isinstance(value, float):
            return int(value) if value.is_integer() else value

        # Try to convert string to number
        if isinstance(value, str):
            stripped = value.strip()
            try:
                return int(stripped)
            except ValueError:
                try:
                    f = float(stripped)
                    return int(f) if f.is_integer() else f
                except ValueError:
                    logger.debug(f"Failed to convert string '{value}' to number")
                    return None

        # For other types, try float conversion then demote if whole
        try:
            f = float(value)
            return int(f) if f.is_integer() else f
        except (ValueError, TypeError):
            logger.debug(f"Failed to convert {type(value).__name__} '{value}' to number")
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
                logger.debug(f"Failed to convert string '{value}' to boolean (not a recognized truthy/falsy value)")
                return None

        # Convert numbers to boolean (0 = false, non-zero = true)
        if isinstance(value, (int, float)):
            return bool(value)

        logger.debug(f"Failed to convert {type(value).__name__} to boolean")
        return None

    @staticmethod
    def to_array(value: Any) -> Optional[List]:
        """
        Convert value to array/list with automatic truncation to 24 items

        Args:
            value: Input value

        Returns:
            List (truncated to 24 items if needed) or None if conversion fails

        Note:
            Per spec: Arrays are enforced to 24 items max and truncated if exceeded
        """
        from app.utils.constants import SystemConstraints

        if value is None:
            return None

        result = None

        # If already an array, use as-is
        if isinstance(value, list):
            result = value

        # If tuple, convert to list
        elif isinstance(value, tuple):
            result = list(value)

        # Try to parse JSON string as array
        elif isinstance(value, str):
            # First try JSON parsing
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    result = parsed
            except (json.JSONDecodeError, ValueError):
                pass

            if result is None:
                # Fallback: parse as comma-separated
                if ',' in value:
                    result = [item.strip() for item in value.split(',')]
                else:
                    # Single value -> single-element array
                    result = [value] if value.strip() else []

        # For other types, wrap in array
        else:
            result = [value]

        # Truncate to MAX_ARRAY_LENGTH if needed
        if result and len(result) > SystemConstraints.MAX_ARRAY_LENGTH:
            original_length = len(result)
            result = result[:SystemConstraints.MAX_ARRAY_LENGTH]
            logger.debug(
                f"Array truncated from {original_length} to {SystemConstraints.MAX_ARRAY_LENGTH} items (spec limit)"
            )

        return result

    @staticmethod
    def convert(value: Any, target_type: str) -> Any:
        """
        Convert value to target type with error handling

        Args:
            value: Input value
            target_type: Target type (STRING, NUMBER, BOOLEAN, ARRAY)

        Returns:
            Converted value

        Raises:
            InputValidationError: If conversion fails
        """
        if value is None:
            return None

        if target_type == "STRING":
            return TypeConverter.to_string(value)

        elif target_type == "NUMBER":
            result = TypeConverter.to_number(value)
            if result is None:
                raise InputValidationError(f"Cannot convert '{value}' to number")
            return result

        elif target_type == "BOOLEAN":
            result = TypeConverter.to_boolean(value)
            if result is None:
                raise InputValidationError(f"Cannot convert '{value}' to boolean")
            return result

        elif target_type == "ARRAY":
            result = TypeConverter.to_array(value)
            if result is None:
                raise InputValidationError(f"Cannot convert '{value}' to array")
            return result

        else:
            # Unknown type, return as-is
            return value
"""
Template Engine
Handles variable substitution in messages, URLs, and other text fields
Supports {{variable}} syntax with dot notation and array indexing
"""

import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote
from app.utils.logger import get_logger
from app.utils.exceptions import TemplateRenderError
from app.utils.security import escape_html
from app.utils.shared import PathResolver, TypeConverter

logger = get_logger(__name__)


class TemplateEngine:
    """
    Template rendering engine with variable substitution

    Features:
    - Simple variable substitution: {{variable_name}}
    - Dot notation for nested values: {{user.name}}, {{items.0}}
    - Special variables (with restrictions - see below)
    - Missing variables displayed literally (debugging feature)
    - Null-safe navigation

    Special Variable Restrictions (per BOT_BUILDER_SPECIFICATIONS.md Section 5):
    - {{user.channel_id}}, {{user.channel}}: ONLY in API_ACTION nodes
    - {{item.*}}, {{index}}: ONLY in MENU item_template
    - {{input}}: ONLY in PROMPT validation expressions (not template syntax)
    - {{current_attempt}}, {{max_attempts}}: ONLY in retry_logic counter_text

    No support for:
    - Complex expressions
    - Arithmetic operations
    - Function calls
    - Conditionals
    - Default value operator (||)
    """
    
    # Regex pattern for template variables: {{variable}}
    VARIABLE_PATTERN = re.compile(r'\{\{([^}]+)\}\}')

    def _render_internal(
        self,
        template: str,
        context: Dict[str, Any],
        formatter: callable,
        skip_validation: bool = False
    ) -> str:
        """
        Internal rendering logic shared across all render methods

        Args:
            template: Template string with {{variable}} placeholders
            context: Dictionary containing variable values
            formatter: Callable that transforms resolved value to string
            skip_validation: If True, skip template validation (used for render_counter)

        Returns:
            Rendered string with variables substituted

        Raises:
            TemplateRenderError: If template contains unsupported syntax
        """
        if not template:
            return ""

        # Validate template syntax before rendering (unless skipped for counter_text)
        if not skip_validation:
            self.validate_template(template)

        try:
            def replace_variable(match):
                variable_path = match.group(1).strip()
                value = self._resolve_path(variable_path, context)

                # If value is None or not found, return literal template (debugging feature)
                if value is None:
                    return match.group(0)  # Return {{variable}} as-is

                return formatter(value)

            rendered = self.VARIABLE_PATTERN.sub(replace_variable, template)
            return rendered

        except TemplateRenderError:
            # Re-raise validation errors as-is
            raise
        except Exception as e:
            logger.error(f"Template render error: {str(e)}", template=template)
            raise TemplateRenderError(f"Failed to render template: {str(e)}", template=template)

    def render(self, template: str, context: Dict[str, Any]) -> str:
        """
        Render template with context variables (Plain text output - no HTML escaping)

        Args:
            template: Template string with {{variable}} placeholders
            context: Dictionary containing variable values

        Returns:
            Rendered string with variables substituted

        Note:
            Use this for WhatsApp/SMS/plain text output.
            For HTML output (web UIs), use render_html() to prevent XSS.
            For URLs, use render_url() for proper encoding.

        Examples:
            >>> engine = TemplateEngine()
            >>> engine.render("Hello {{name}}!", {"name": "John"})
            "Hello John!"

            >>> engine.render("Item: {{item.id}}", {"item": {"id": "123"}})
            "Item: 123"

            >>> engine.render("Missing: {{missing}}", {})
            "Missing: {{missing}}"

        Raises:
            TemplateRenderError: If template contains unsupported syntax
        """
        return self._render_internal(template, context, formatter=self._format_value)
    
    def render_counter(self, template: str, context: Dict[str, Any]) -> str:
        """
        Render retry counter text with special variables

        This is the ONLY method that allows {{current_attempt}} and {{max_attempts}}.
        Per specification, these variables are restricted to counter_text only.

        Args:
            template: Counter text template with {{current_attempt}} and {{max_attempts}}
            context: Context containing current_attempt and max_attempts

        Returns:
            Rendered counter text

        Raises:
            TemplateRenderError: If template contains unsupported syntax
        """
        return self._render_internal(template, context, formatter=self._format_value, skip_validation=True)

    def render_url(self, template: str, context: Dict[str, Any]) -> str:
        """
        Render template with URL encoding for variable values
        Use this for URLs to properly encode special characters

        Args:
            template: Template string with {{variable}} placeholders
            context: Dictionary containing variable values

        Returns:
            Rendered string with variables substituted and URL-encoded

        Examples:
            >>> engine = TemplateEngine()
            >>> engine.render_url("https://api.example.com/user/{{phone}}", {"phone": "+254712345678"})
            "https://api.example.com/user/%2B254712345678"

            >>> engine.render_url("https://example.com/search?q={{query}}", {"query": "hello world"})
            "https://example.com/search?q=hello%20world"

            >>> engine.render_url("https://example.com/path/{{id}}", {"id": "user@example.com"})
            "https://example.com/path/user%40example.com"

        Raises:
            TemplateRenderError: If template contains unsupported syntax
        """
        return self._render_internal(template, context, formatter=lambda v: quote(str(v), safe=''))

    def render_html(self, template: str, context: Dict[str, Any]) -> str:
        """
        Render template with HTML escaping for variable values (Layer 2: Context-Aware Escaping)

        Use this when rendering templates for HTML output to prevent XSS attacks.

        Args:
            template: Template string with {{variable}} placeholders
            context: Dictionary containing variable values

        Returns:
            Rendered string with variables substituted and HTML-escaped

        Examples:
            >>> engine = TemplateEngine()
            >>> engine.render_html("Hello {{name}}!", {"name": "<script>alert('xss')</script>"})
            "Hello &lt;script&gt;alert('xss')&lt;/script&gt;!"

            >>> engine.render_html("Comment: {{comment}}", {"comment": "It's <great>"})
            "Comment: It&#x27;s &lt;great&gt;"

        Note:
            This implements Layer 2 (context-aware escaping) per spec Section 10.1.
            For WhatsApp/SMS, use render() instead (no HTML escaping needed).
            For web UIs, use this method to prevent XSS attacks.

        Raises:
            TemplateRenderError: If template contains unsupported syntax
        """
        return self._render_internal(template, context, formatter=lambda v: escape_html(str(v)))

    def _resolve_path(self, path: str, context: Dict[str, Any]) -> Any:
        """
        Resolve dot-notation path to actual value using PathResolver

        Args:
            path: Variable path (e.g., 'context.user.name', 'item.id', 'index')
            context: Context dictionary

        Returns:
            Resolved value or None if not found

        Examples:
            >>> engine._resolve_path("user.name", {"user": {"name": "John"}})
            "John"

            >>> engine._resolve_path("items.0", {"items": ["a", "b"]})
            "a"

            >>> engine._resolve_path("missing", {})
            None

        Note:
            Uses shared PathResolver for consistent behavior across the system,
            including support for .length property and wildcard paths.
        """
        return PathResolver.resolve(path, context)
    
    def _extract_variables(self, template: str) -> List[str]:
        """
        Extract all {{variable}} patterns from template
        
        Args:
            template: Template string
        
        Returns:
            List of variable paths found in template
        
        Examples:
            >>> engine._extract_variables("Hello {{name}}, you have {{count}} items")
            ['name', 'count']
        """
        if not template:
            return []
        
        matches = self.VARIABLE_PATTERN.findall(template)
        return [match.strip() for match in matches]
    
    def validate_template(self, template: str) -> bool:
        """
        Validate template syntax

        Checks for:
        - Balanced braces
        - No unsupported operators or expressions

        Args:
            template: Template string to validate

        Returns:
            True if template syntax is valid

        Raises:
            TemplateRenderError: If template contains unsupported syntax
        """
        if not template:
            return True

        # Check for balanced braces
        open_count = template.count('{{')
        close_count = template.count('}}')

        if open_count != close_count:
            raise TemplateRenderError(
                "Unbalanced template braces: mismatched {{ and }}",
                template=template
            )

        # Extract all variable expressions
        variable_expressions = self._extract_variables(template)

        # Validate each expression for unsupported features
        for expr in variable_expressions:
            self._validate_expression(expr, template)

        return True

    def _validate_expression(self, expression: str, original_template: str) -> None:
        """
        Validate a single template expression for unsupported syntax

        Rejects:
        - Arithmetic operators: +, -, *, /, %
        - Default value operator: ||
        - Ternary operator: ? :
        - Method calls with parentheses: .method()
        - Control flow keywords: if, for, while, function, return
        - Bracket notation: [0] (should use dot notation like .0)
        - Reserved variable {{input}} (only allowed in PROMPT validation expressions, not templates)

        Args:
            expression: The variable path expression (content between {{ and }})
            original_template: The full template string (for error messages)

        Raises:
            TemplateRenderError: If expression contains unsupported syntax
        """
        # Check for {{input}} usage - NOT allowed in templates
        # Note: 'input' is only available in validation EXPRESSIONS (not template syntax)
        if expression.strip() == 'input' or expression.strip().startswith('input.'):
            raise TemplateRenderError(
                f"Invalid template variable: {{{{{{expression}}}}}} is not allowed. "
                f"The 'input' variable is only available in PROMPT validation expressions "
                f"(which use plain 'input', not template syntax). "
                f"It cannot be used in prompt text, error messages, or templates.",
                template=original_template
            )

        # Check for retry counter variables - ONLY allowed in counter_text
        if expression.strip() in ('current_attempt', 'max_attempts'):
            raise TemplateRenderError(
                f"Invalid template variable: {{{{{{expression}}}}}} is not allowed. "
                f"Retry counter variables (current_attempt, max_attempts) are ONLY available "
                f"in retry_logic counter_text. They cannot be used in error messages, "
                f"validation rules, or any other templates.",
                template=original_template
            )

        # Patterns that are NOT allowed in templates
        unsupported_patterns = [
            # Arithmetic operators
            (r'[\+\-\*/%]', 'arithmetic operations', 'Use variables with pre-calculated values instead'),

            # Default value operator ||
            (r'\|\|', 'default value operator (||)', 'Initialize variables with defaults in flow definition'),

            # Ternary operator
            (r'\?.*:', 'ternary operator (? :)', 'Use LOGIC_EXPRESSION nodes for conditional logic'),

            # Method calls with parentheses
            (r'\.\w+\s*\(', 'method calls', 'Methods like .toUpperCase(), .includes() are not supported'),

            # Square bracket notation
            (r'\[', 'bracket notation', 'Use dot notation for array access (e.g., items.0 instead of items[0])'),

            # Control flow keywords
            (r'\b(if|for|while|function|return|class|new)\b', 'control flow keywords', 'Use node types for control flow'),
        ]

        for pattern, feature_name, suggestion in unsupported_patterns:
            if re.search(pattern, expression):
                raise TemplateRenderError(
                    f"Unsupported template syntax: {feature_name} not allowed in templates. "
                    f"{suggestion}. Found in expression: '{{{{{{expression}}}}}}'",
                    template=original_template
                )
    
    def render_json_value(
        self,
        template: str,
        context: Dict[str, Any],
        flow_variables: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> Any:
        """
        Render template value with type preservation for JSON bodies

        This method is specifically for rendering template variables in API request bodies.
        Unlike render() which always returns strings, this preserves native JSON types
        (numbers, booleans, arrays) based on variable declarations or value inference.

        Type Resolution Order:
        1. Check flow variable type definition (if variable declared and flow_variables provided)
        2. Infer from actual Python value type
        3. Preserve native types for JSON (number, boolean, array)

        Args:
            template: Template string with {{variable}} placeholder
            context: Dictionary containing variable values
            flow_variables: Optional flow variable definitions for type lookup

        Returns:
            Properly-typed value for JSON serialization (not stringified)
            - Numbers remain numbers
            - Booleans remain booleans
            - Arrays remain arrays
            - Strings remain strings
            - None if variable not found

        Examples:
            >>> engine = TemplateEngine()
            >>> flow_vars = {"amount": {"type": "NUMBER"}}
            >>> engine.render_json_value("{{amount}}", {"amount": 500}, flow_vars)
            500  # Returns int, not "500"

            >>> engine.render_json_value("{{active}}", {"active": True})
            True  # Returns bool, not "True"

            >>> engine.render_json_value("{{name}}", {"name": "Alice"})
            "Alice"  # Strings remain strings

        Raises:
            TemplateRenderError: If template contains unsupported syntax
        """
        if not template:
            return ""

        # Validate template syntax
        self.validate_template(template)

        # Check if this is a simple variable template (just {{variable}})
        match = self.VARIABLE_PATTERN.fullmatch(template.strip())
        if not match:
            # Not a simple variable template, fall back to string rendering
            return self.render(template, context)

        # Extract variable path
        variable_path = match.group(1).strip()

        # Resolve the value from context
        value = self._resolve_path(variable_path, context)

        # If value not found, return literal template for debugging
        if value is None:
            return template

        # Determine target type
        target_type = None

        # Step 1: Check flow variable type definition
        if flow_variables:
            # Extract the variable name from the path (e.g., "context.amount" -> "amount")
            var_name = self._extract_variable_name(variable_path)
            if var_name and var_name in flow_variables:
                var_def = flow_variables[var_name]
                target_type = var_def.get("type")

        # Step 2: Infer from actual value type if no declaration
        if not target_type:
            return self._preserve_native_type(value)

        # Step 3: Convert to declared type
        try:
            return self._convert_to_type(value, target_type)
        except Exception as e:
            logger.debug(f"Type conversion failed, preserving native type: {str(e)}")
            return self._preserve_native_type(value)

    def _extract_variable_name(self, variable_path: str) -> Optional[str]:
        """
        Extract base variable name from path

        Returns the LAST segment of the path to match against flow variable definitions.
        This ensures nested paths like "context.user.age" correctly extract "age" as the
        variable name to look up in the flow's variables section.

        Args:
            variable_path: Variable path like "context.amount" or "amount"

        Returns:
            Base variable name (e.g., "amount") or None

        Examples:
            >>> engine._extract_variable_name("context.amount")
            "amount"
            >>> engine._extract_variable_name("amount")
            "amount"
            >>> engine._extract_variable_name("context.user.name")
            "name"  # Fixed: now extracts last part, not second part
        """
        if not variable_path:
            return None

        parts = variable_path.split('.')

        # Return the last part of the path
        # This matches the actual variable name in flow definitions
        return parts[-1] if parts else None

    def _preserve_native_type(self, value: Any) -> Any:
        """
        Preserve native Python type for JSON serialization

        Args:
            value: Python value

        Returns:
            Value with native type preserved
        """
        # Preserve native JSON-compatible types
        if isinstance(value, (bool, int, float, list, dict)):
            return value

        # Convert everything else to string
        return str(value)

    def _convert_to_type(self, value: Any, target_type: str) -> Any:
        """
        Convert value to target type

        Args:
            value: Source value
            target_type: Target type (STRING, NUMBER, BOOLEAN, ARRAY)

        Returns:
            Converted value

        Raises:
            ValueError: If conversion fails
        """
        result = TypeConverter.convert(value, target_type)
        if result is None:
            return self._preserve_native_type(value)
        return result

    def _format_value(self, value: Any) -> str:
        """
        Format value for display in templates with smart number formatting

        Args:
            value: Value to format

        Returns:
            String representation

        Note:
            Numbers are formatted intelligently:
            - Integers display without decimals: 10.0 → "10"
            - Floats display with decimals: 10.5 → "10.5"
        """
        # Smart number formatting - remove unnecessary .0
        if isinstance(value, float):
            # Check if it's a whole number
            if value.is_integer():
                return str(int(value))
            else:
                return str(value)

        # Everything else: standard string conversion
        return str(value)

    def has_variables(self, template: str) -> bool:
        """
        Check if template contains any variables

        Args:
            template: Template string

        Returns:
            True if template contains {{variable}} patterns
        """
        return bool(self.VARIABLE_PATTERN.search(template))
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

logger = get_logger(__name__)


class TemplateEngine:
    """
    Template rendering engine with variable substitution

    Features:
    - Simple variable substitution: {{variable}}
    - Dot notation: {{context.user.name}}
    - Array indexing: {{context.items.0}}
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
            >>> engine.render("Hello {{context.name}}!", {"name": "John"})
            "Hello John!"

            >>> engine.render("Item: {{item.id}}", {"item": {"id": "123"}})
            "Item: 123"

            >>> engine.render("Missing: {{context.missing}}", {})
            "Missing: {{context.missing}}"

        Raises:
            TemplateRenderError: If template contains unsupported syntax
        """
        if not template:
            return ""

        # Validate template syntax before rendering
        self.validate_template(template)

        try:
            def replace_variable(match):
                variable_path = match.group(1).strip()
                value = self._resolve_path(variable_path, context)

                # If value is None or not found, return literal template (debugging feature)
                if value is None:
                    return match.group(0)  # Return {{variable}} as-is

                return str(value)

            rendered = self.VARIABLE_PATTERN.sub(replace_variable, template)
            return rendered

        except TemplateRenderError:
            # Re-raise validation errors as-is
            raise
        except Exception as e:
            logger.error(f"Template render error: {str(e)}", template=template)
            raise TemplateRenderError(f"Failed to render template: {str(e)}", template=template)
    
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
        if not template:
            return ""

        # For counter text, we skip the standard validation and use a permissive approach
        # Only current_attempt and max_attempts are allowed as special variables here
        try:
            def replace_variable(match):
                variable_path = match.group(1).strip()
                value = self._resolve_path(variable_path, context)

                # If value is None or not found, return literal template (debugging feature)
                if value is None:
                    return match.group(0)  # Return {{variable}} as-is

                return str(value)

            rendered = self.VARIABLE_PATTERN.sub(replace_variable, template)
            return rendered

        except Exception as e:
            logger.error(f"Template render error: {str(e)}", template=template)
            raise TemplateRenderError(f"Failed to render template: {str(e)}", template=template)

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
        if not template:
            return ""

        # Validate template syntax before rendering
        self.validate_template(template)

        try:
            def replace_variable(match):
                variable_path = match.group(1).strip()
                value = self._resolve_path(variable_path, context)

                # If value is None or not found, return literal template (debugging feature)
                if value is None:
                    return match.group(0)  # Return {{variable}} as-is

                # URL-encode the value using quote with safe='' to encode everything
                # except unreserved characters (A-Z, a-z, 0-9, -, _, ., ~)
                return quote(str(value), safe='')

            rendered = self.VARIABLE_PATTERN.sub(replace_variable, template)
            return rendered

        except TemplateRenderError:
            # Re-raise validation errors as-is
            raise
        except Exception as e:
            logger.error(f"Template render error: {str(e)}", template=template)
            raise TemplateRenderError(f"Failed to render template: {str(e)}", template=template)

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
        if not template:
            return ""

        # Validate template syntax before rendering
        self.validate_template(template)

        try:
            def replace_variable(match):
                variable_path = match.group(1).strip()
                value = self._resolve_path(variable_path, context)

                # If value is None or not found, return literal template (debugging feature)
                if value is None:
                    return match.group(0)  # Return {{variable}} as-is

                # HTML-escape the value to prevent XSS
                return escape_html(str(value))

            rendered = self.VARIABLE_PATTERN.sub(replace_variable, template)
            return rendered

        except TemplateRenderError:
            # Re-raise validation errors as-is
            raise
        except Exception as e:
            logger.error(f"Template render error: {str(e)}", template=template)
            raise TemplateRenderError(f"Failed to render template: {str(e)}", template=template)

    def _resolve_path(self, path: str, context: Dict[str, Any]) -> Any:
        """
        Resolve dot-notation path to actual value
        
        Args:
            path: Variable path (e.g., 'context.user.name', 'item.id', 'index')
            context: Context dictionary
        
        Returns:
            Resolved value or None if not found
        
        Examples:
            >>> engine._resolve_path("context.user.name", {"user": {"name": "John"}})
            "John"
            
            >>> engine._resolve_path("context.items.0", {"items": ["a", "b"]})
            "a"
            
            >>> engine._resolve_path("context.missing", {})
            None
        """
        if not path:
            return None
        
        try:
            # Split path by dots
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
    
    def has_variables(self, template: str) -> bool:
        """
        Check if template contains any variables
        
        Args:
            template: Template string
        
        Returns:
            True if template contains {{variable}} patterns
        """
        return bool(self.VARIABLE_PATTERN.search(template))
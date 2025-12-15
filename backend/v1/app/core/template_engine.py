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

logger = get_logger(__name__)


class TemplateEngine:
    """
    Template rendering engine with variable substitution
    
    Features:
    - Simple variable substitution: {{variable}}
    - Dot notation: {{context.user.name}}
    - Array indexing: {{context.items.0}}
    - Special variables: {{user.channel_id}}, {{item.*}}, {{index}}, {{input}}
    - Missing variables displayed literally (debugging feature)
    - Null-safe navigation
    
    No support for:
    - Complex expressions
    - Arithmetic operations
    - Function calls
    - Conditionals
    """
    
    # Regex pattern for template variables: {{variable}}
    VARIABLE_PATTERN = re.compile(r'\{\{([^}]+)\}\}')
    
    def render(self, template: str, context: Dict[str, Any]) -> str:
        """
        Render template with context variables
        
        Args:
            template: Template string with {{variable}} placeholders
            context: Dictionary containing variable values
        
        Returns:
            Rendered string with variables substituted
        
        Examples:
            >>> engine = TemplateEngine()
            >>> engine.render("Hello {{context.name}}!", {"name": "John"})
            "Hello John!"
            
            >>> engine.render("Item: {{item.id}}", {"item": {"id": "123"}})
            "Item: 123"
            
            >>> engine.render("Missing: {{context.missing}}", {})
            "Missing: {{context.missing}}"
        """
        if not template:
            return ""
        
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
        """
        if not template:
            return ""
        
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
        Validate template syntax (basic check)
        
        Args:
            template: Template string to validate
        
        Returns:
            True if template syntax is valid
        """
        if not template:
            return True
        
        # Check for balanced braces
        open_count = template.count('{{')
        close_count = template.count('}}')
        
        return open_count == close_count
    
    def has_variables(self, template: str) -> bool:
        """
        Check if template contains any variables
        
        Args:
            template: Template string
        
        Returns:
            True if template contains {{variable}} patterns
        """
        return bool(self.VARIABLE_PATTERN.search(template))
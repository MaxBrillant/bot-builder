"""
Route Condition Validator
Validates route conditions and counts based on node types
Mirrors frontend logic from routeConditionUtils.ts
"""

import re
from typing import Dict, List, Any, Optional
from app.utils.constants import NodeType, MenuSourceType
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RouteConditionValidator:
    """
    Validates route conditions and route counts for different node types.
    
    This validator mirrors the frontend logic in routeConditionUtils.ts to ensure
    that backend validation matches frontend behavior exactly.
    """
    
    # Regex pattern for MENU selection condition (e.g., "selection == 1")
    MENU_SELECTION_PATTERN = r'^selection == \d+$'
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def validate_node_routes(
        self,
        node_id: str,
        node_type: str,
        node_config: Dict[str, Any],
        routes: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """
        Main validation entry point for node routes.
        
        Args:
            node_id: Node identifier
            node_type: Node type (PROMPT, MENU, API_ACTION, etc.)
            node_config: Node configuration dictionary
            routes: List of route dictionaries
            
        Returns:
            List of error dictionaries with keys: type, message, location, suggestion
        """
        errors = []
        
        # Validate route count
        count_errors = self._validate_route_count(node_id, node_type, node_config, routes)
        errors.extend(count_errors)
        
        # Validate each route condition
        for i, route in enumerate(routes):
            condition = route.get('condition', '')
            condition_errors = self._validate_route_condition(
                node_id, node_type, node_config, condition, i
            )
            errors.extend(condition_errors)
        
        return errors
    
    def _validate_route_count(
        self,
        node_id: str,
        node_type: str,
        node_config: Dict[str, Any],
        routes: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """
        Validate that the number of routes does not exceed the maximum allowed.
        
        Args:
            node_id: Node identifier
            node_type: Node type
            node_config: Node configuration
            routes: List of routes
            
        Returns:
            List of error dictionaries
        """
        errors = []
        max_routes = self._get_max_routes(node_type, node_config)
        route_count = len(routes)
        
        if route_count > max_routes:
            error_msg = self._get_max_routes_error_message(node_type, node_config, max_routes, route_count)
            errors.append({
                "type": "route_count_exceeded",
                "message": error_msg,
                "location": f"nodes.{node_id}.routes",
                "suggestion": self._get_max_routes_suggestion(node_type, node_config, max_routes)
            })
        
        return errors
    
    def _validate_route_condition(
        self,
        node_id: str,
        node_type: str,
        node_config: Dict[str, Any],
        condition: str,
        route_index: int
    ) -> List[Dict[str, str]]:
        """
        Validate that a route condition is valid for the given node type.
        
        Args:
            node_id: Node identifier
            node_type: Node type
            node_config: Node configuration
            condition: Route condition string
            route_index: Index of the route in the routes list
            
        Returns:
            List of error dictionaries
        """
        errors = []
        allowed_conditions = self._get_allowed_conditions(node_type, node_config)
        
        # Check if condition is in allowed list
        if condition not in allowed_conditions:
            # Special handling for MENU static selection conditions
            if node_type == NodeType.MENU.value:
                source_type = node_config.get('source_type')
                if source_type == MenuSourceType.STATIC.value:
                    # Validate selection == N format and range
                    selection_errors = self._validate_static_menu_condition(
                        node_id, node_config, condition, route_index
                    )
                    if selection_errors:
                        errors.extend(selection_errors)
                        return errors
                    # If valid selection format and range, it's allowed
                    return errors
            
            # For non-MENU nodes or DYNAMIC menus, condition must be in allowed list
            error_msg = self._get_invalid_condition_error_message(node_type, node_config, condition)
            errors.append({
                "type": "invalid_route_condition",
                "message": error_msg,
                "location": f"nodes.{node_id}.routes[{route_index}].condition",
                "suggestion": self._get_condition_suggestion(node_type, node_config)
            })
        
        return errors
    
    def _validate_static_menu_condition(
        self,
        node_id: str,
        node_config: Dict[str, Any],
        condition: str,
        route_index: int
    ) -> List[Dict[str, str]]:
        """
        Validate MENU static selection condition format and range.
        
        Validates that:
        1. Condition matches "selection == N" pattern
        2. N is within valid range (1 to num_options)
        
        Args:
            node_id: Node identifier
            node_config: Node configuration
            condition: Route condition string
            route_index: Index of the route
            
        Returns:
            List of error dictionaries
        """
        errors = []
        
        # Check pattern match
        if not re.match(self.MENU_SELECTION_PATTERN, condition):
            errors.append({
                "type": "invalid_route_condition",
                "message": f"MENU node condition must be 'selection == N' (where N is 1-{len(node_config.get('static_options', []))}) or 'true'",
                "location": f"nodes.{node_id}.routes[{route_index}].condition",
                "suggestion": "Use format 'selection == 1', 'selection == 2', etc., or 'true' for fallback"
            })
            return errors
        
        # Extract selection number
        try:
            selection_num = int(condition.split('==')[1].strip())
        except (ValueError, IndexError):
            errors.append({
                "type": "invalid_route_condition",
                "message": f"Invalid selection number in condition '{condition}'",
                "location": f"nodes.{node_id}.routes[{route_index}].condition",
                "suggestion": "Use format 'selection == 1', 'selection == 2', etc."
            })
            return errors
        
        # Validate range
        static_options = node_config.get('static_options', [])
        num_options = len(static_options)
        
        if selection_num < 1 or selection_num > num_options:
            errors.append({
                "type": "invalid_route_condition",
                "message": f"Selection number {selection_num} is out of range. MENU has {num_options} option(s), valid range is 1-{num_options}",
                "location": f"nodes.{node_id}.routes[{route_index}].condition",
                "suggestion": f"Use 'selection == N' where N is between 1 and {num_options}, or 'true' for fallback"
            })
        
        return errors
    
    def _get_max_routes(self, node_type: str, node_config: Dict[str, Any]) -> int:
        """
        Calculate maximum allowed routes for a node type.
        
        Args:
            node_type: Node type
            node_config: Node configuration
            
        Returns:
            Maximum number of routes allowed
        """
        if node_type == NodeType.MENU.value:
            source_type = node_config.get('source_type')
            
            # DYNAMIC menus: Only 1 route (Next)
            if source_type == MenuSourceType.DYNAMIC.value:
                return 1
            
            # STATIC menus: number of options + 1 fallback
            static_options = node_config.get('static_options', [])
            return len(static_options) + 1
        
        elif node_type == NodeType.API_ACTION.value:
            # success, error, fallback
            return 3
        
        elif node_type == NodeType.LOGIC_EXPRESSION.value:
            # Up to system max (8)
            return 8
        
        elif node_type in [NodeType.PROMPT.value, NodeType.MESSAGE.value]:
            # Single route only
            return 1
        
        elif node_type == NodeType.END.value:
            return 0
        
        else:
            return 1
    
    def _get_allowed_conditions(self, node_type: str, node_config: Dict[str, Any]) -> List[str]:
        """
        Get list of allowed condition values for a node type.
        
        Note: For MENU STATIC nodes, this returns base conditions. 
        Selection conditions ("selection == N") are validated separately.
        
        Args:
            node_type: Node type
            node_config: Node configuration
            
        Returns:
            List of allowed condition strings
        """
        if node_type == NodeType.MENU.value:
            source_type = node_config.get('source_type')
            
            # DYNAMIC menus: Only "true" allowed
            if source_type == MenuSourceType.DYNAMIC.value:
                return ["true"]
            
            # STATIC menus: "true" + individual selections validated separately
            # Return only "true" here, selections are validated by pattern
            return ["true"]
        
        elif node_type == NodeType.API_ACTION.value:
            return ["success", "error", "true"]
        
        elif node_type in [NodeType.PROMPT.value, NodeType.MESSAGE.value]:
            return ["true"]
        
        elif node_type == NodeType.LOGIC_EXPRESSION.value:
            # Logic expressions accept any non-empty string
            # This is validated differently - not using allowed list
            return []
        
        elif node_type == NodeType.END.value:
            return []
        
        else:
            return ["true"]
    
    def _get_max_routes_error_message(
        self,
        node_type: str,
        node_config: Dict[str, Any],
        max_routes: int,
        current_count: int
    ) -> str:
        """Generate descriptive error message for exceeding max routes."""
        if node_type == NodeType.MENU.value:
            source_type = node_config.get('source_type')
            if source_type == MenuSourceType.DYNAMIC.value:
                return f"DYNAMIC MENU nodes can only have 1 route (for 'Next'). Currently has {current_count} routes"
            else:
                num_options = len(node_config.get('static_options', []))
                return f"STATIC MENU nodes can have at most {max_routes} routes ({num_options} options + 1 fallback). Currently has {current_count} routes"
        
        elif node_type == NodeType.API_ACTION.value:
            return f"API_ACTION nodes can have at most {max_routes} routes (success, error, fallback). Currently has {current_count} routes"
        
        elif node_type == NodeType.LOGIC_EXPRESSION.value:
            return f"LOGIC_EXPRESSION nodes can have at most {max_routes} routes. Currently has {current_count} routes"
        
        elif node_type in [NodeType.PROMPT.value, NodeType.MESSAGE.value]:
            return f"{node_type} nodes can only have 1 route. Currently has {current_count} routes"
        
        else:
            return f"Node type {node_type} can have at most {max_routes} routes. Currently has {current_count} routes"
    
    def _get_max_routes_suggestion(
        self,
        node_type: str,
        node_config: Dict[str, Any],
        max_routes: int
    ) -> str:
        """Generate helpful suggestion for fixing route count issues."""
        if node_type == NodeType.MENU.value:
            source_type = node_config.get('source_type')
            if source_type == MenuSourceType.DYNAMIC.value:
                return "DYNAMIC menus only support a single 'Next' route. Use a LOGIC_EXPRESSION node after the menu for conditional routing"
            else:
                return f"Remove extra routes or add more menu options. Maximum {max_routes} routes allowed"
        
        elif node_type == NodeType.API_ACTION.value:
            return "API_ACTION nodes support 'success', 'error', and 'true' (fallback) conditions only"
        
        elif node_type in [NodeType.PROMPT.value, NodeType.MESSAGE.value]:
            return f"{node_type} nodes only support a single route with condition 'true'"
        
        else:
            return f"Reduce the number of routes to {max_routes} or fewer"
    
    def _get_invalid_condition_error_message(
        self,
        node_type: str,
        node_config: Dict[str, Any],
        condition: str
    ) -> str:
        """Generate descriptive error message for invalid condition."""
        if node_type == NodeType.MENU.value:
            source_type = node_config.get('source_type')
            if source_type == MenuSourceType.DYNAMIC.value:
                return f"DYNAMIC MENU nodes only allow condition 'true'. Got: '{condition}'"
            else:
                num_options = len(node_config.get('static_options', []))
                return f"STATIC MENU nodes only allow 'selection == N' (where N is 1-{num_options}) or 'true'. Got: '{condition}'"
        
        elif node_type == NodeType.API_ACTION.value:
            return f"API_ACTION nodes only allow conditions: 'success', 'error', or 'true'. Got: '{condition}'"
        
        elif node_type in [NodeType.PROMPT.value, NodeType.MESSAGE.value]:
            return f"{node_type} nodes only allow condition 'true'. Got: '{condition}'"
        
        else:
            return f"Invalid condition '{condition}' for node type {node_type}"
    
    def _get_condition_suggestion(
        self,
        node_type: str,
        node_config: Dict[str, Any]
    ) -> str:
        """Generate helpful suggestion for fixing condition issues."""
        if node_type == NodeType.MENU.value:
            source_type = node_config.get('source_type')
            if source_type == MenuSourceType.DYNAMIC.value:
                return "Use condition 'true' for the Next route. For conditional routing, add a LOGIC_EXPRESSION node after this menu"
            else:
                num_options = len(node_config.get('static_options', []))
                return f"Use 'selection == 1' through 'selection == {num_options}' for specific options, or 'true' for fallback"
        
        elif node_type == NodeType.API_ACTION.value:
            return "Use 'success' for successful API calls, 'error' for failures, or 'true' for any outcome"
        
        elif node_type in [NodeType.PROMPT.value, NodeType.MESSAGE.value]:
            return "Use condition 'true' (the only valid condition for this node type)"
        
        elif node_type == NodeType.LOGIC_EXPRESSION.value:
            return "Use any valid expression as a condition (non-empty string)"
        
        else:
            return "Use a valid condition for this node type"
"""
Route Sorter
Sorts routes by condition priority to ensure optimal evaluation order
Mirrors frontend logic from routeConditionUtils.ts
"""

import re
from typing import List, Dict, Any
from app.utils.logger import get_logger

logger = get_logger(__name__)


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
    
    Examples:
        >>> get_condition_priority("true", "MENU")
        1000
        >>> get_condition_priority("selection == 1", "MENU")
        1
        >>> get_condition_priority("selection == 3", "MENU")
        3
        >>> get_condition_priority("success", "API_ACTION")
        1
        >>> get_condition_priority("error", "API_ACTION")
        2
    """
    # Catch-all "true" always goes last
    if condition.strip().lower() == "true":
        return 1000
    
    if node_type == "MENU":
        # Extract selection number from "selection == N" pattern
        match = re.search(r'selection\s*==\s*(\d+)', condition)
        if match:
            # Selection routes ordered by number (1, 2, 3, etc.)
            return int(match.group(1))
        # Other menu conditions
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
    
    Examples:
        >>> routes = [
        ...     {"condition": "true", "target_node": "n3"},
        ...     {"condition": "selection == 1", "target_node": "n1"},
        ...     {"condition": "selection == 2", "target_node": "n2"}
        ... ]
        >>> sorted_routes = sort_routes(routes, "MENU")
        >>> [r['condition'] for r in sorted_routes]
        ['selection == 1', 'selection == 2', 'true']
    """
    # Create a shallow copy to avoid modifying original
    routes_copy = list(routes)
    
    # Sort by priority (lower priority number = evaluated first)
    routes_copy.sort(key=lambda route: get_condition_priority(
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
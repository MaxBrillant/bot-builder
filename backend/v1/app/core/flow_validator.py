"""
Flow Validator
Validates flow structure on submission.
Contains: RouteConditionValidator, ValidationResult, FlowValidator
"""
import re
from typing import Any, Dict, Optional, List, Set
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import ValidationError
from app.utils.shared import PathResolver, TypeConverter
from app.utils.logger import get_logger
from app.utils.exceptions import InputValidationError
from app.utils.constants import (
    NodeType, VariableType, ValidationType, MenuSourceType,
    SystemConstraints, ReservedKeywords, RegexPatterns
)
from app.utils.security import validate_node_id_format
from app.models.node_configs import FlowNode

logger = get_logger(__name__)

# ===== Class 2: RouteConditionValidator (~200 lines) =====
class RouteConditionValidator:
    """
    Validates route conditions and route counts for different node types

    This validator mirrors the frontend logic in routeConditionUtils.ts to ensure
    that backend validation matches frontend behavior exactly.
    """

    # Regex pattern for MENU selection condition (e.g., "selection == 1")
    MENU_SELECTION_PATTERN = r'^selection == \d+$'

    def validate_node_routes(
        self,
        node_id: str,
        node_type: str,
        node_config: Dict[str, Any],
        routes: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """
        Main validation entry point for node routes

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
        """Validate that the number of routes does not exceed the maximum allowed"""
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
        """Validate that a route condition is valid for the given node type"""
        from app.utils.constants import SystemConstraints

        errors = []

        # Check route condition length (spec: MAX_ROUTE_CONDITION_LENGTH = 512)
        if len(condition) > SystemConstraints.MAX_ROUTE_CONDITION_LENGTH:
            errors.append({
                "type": "constraint_violation",
                "message": f"Route condition exceeds maximum length of {SystemConstraints.MAX_ROUTE_CONDITION_LENGTH} characters (current: {len(condition)} characters)",
                "location": f"nodes.{node_id}.routes[{route_index}].condition",
                "constraint": "MAX_ROUTE_CONDITION_LENGTH"
            })
            return errors

        # Special handling for LOGIC_EXPRESSION nodes
        if node_type == NodeType.LOGIC_EXPRESSION.value:
            if not condition or condition.strip() == "":
                errors.append({
                    "type": "invalid_route_condition",
                    "message": "Route condition cannot be empty",
                    "location": f"nodes.{node_id}.routes[{route_index}].condition",
                    "suggestion": "Use any valid expression as a condition (e.g., context.age > 18, true)"
                })
            return errors

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
        """Validate MENU static selection condition format and range"""
        errors = []

        # Check pattern match
        if not re.match(self.MENU_SELECTION_PATTERN, condition):
            errors.append({
                "type": "invalid_route_condition",
                "message": f"MENU node condition must be 'selection == N' (where N is 1-{len(node_config.get('static_options', []))})",
                "location": f"nodes.{node_id}.routes[{route_index}].condition",
                "suggestion": "Use format 'selection == 1', 'selection == 2', etc."
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
                "suggestion": f"Use 'selection == N' where N is between 1 and {num_options}"
            })

        return errors

    def _get_max_routes(self, node_type: str, node_config: Dict[str, Any]) -> int:
        """Calculate maximum allowed routes for a node type"""
        if node_type == NodeType.MENU.value:
            source_type = node_config.get('source_type')
            if source_type == MenuSourceType.DYNAMIC.value:
                return 1
            static_options = node_config.get('static_options', [])
            return len(static_options)
        elif node_type == NodeType.API_ACTION.value:
            return 2
        elif node_type == NodeType.LOGIC_EXPRESSION.value:
            return 8
        elif node_type in [NodeType.PROMPT.value, NodeType.TEXT.value, NodeType.SET_VARIABLE.value]:
            return 1
        else:
            return 1

    def _get_allowed_conditions(self, node_type: str, node_config: Dict[str, Any]) -> List[str]:
        """Get list of allowed condition values for a node type"""
        if node_type == NodeType.MENU.value:
            source_type = node_config.get('source_type')
            if source_type == MenuSourceType.DYNAMIC.value:
                return ["true"]
            # STATIC: no base allowed conditions — selection == N is validated separately
            return []
        elif node_type == NodeType.API_ACTION.value:
            return ["success", "error"]
        elif node_type in [NodeType.PROMPT.value, NodeType.TEXT.value, NodeType.SET_VARIABLE.value]:
            return ["true"]
        elif node_type == NodeType.LOGIC_EXPRESSION.value:
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
        """Generate descriptive error message for exceeding max routes"""
        if node_type == NodeType.MENU.value:
            source_type = node_config.get('source_type')
            if source_type == MenuSourceType.DYNAMIC.value:
                return f"DYNAMIC MENU nodes can have at most 1 route. Currently has {current_count} routes"
            else:
                num_options = len(node_config.get('static_options', []))
                return f"STATIC MENU nodes can have at most {max_routes} routes (one per option). Currently has {current_count} routes"
        elif node_type == NodeType.API_ACTION.value:
            return f"API_ACTION nodes can have at most {max_routes} routes (success, error). Currently has {current_count} routes"
        elif node_type == NodeType.LOGIC_EXPRESSION.value:
            return f"LOGIC_EXPRESSION nodes can have at most {max_routes} routes. Currently has {current_count} routes"
        elif node_type in [NodeType.PROMPT.value, NodeType.TEXT.value, NodeType.SET_VARIABLE.value]:
            return f"{node_type} nodes can have at most 1 route. Currently has {current_count} routes"
        else:
            return f"Node type {node_type} can have at most {max_routes} routes. Currently has {current_count} routes"

    def _get_max_routes_suggestion(
        self,
        node_type: str,
        node_config: Dict[str, Any],
        max_routes: int
    ) -> str:
        """Generate helpful suggestion for fixing route count issues"""
        if node_type == NodeType.MENU.value:
            source_type = node_config.get('source_type')
            if source_type == MenuSourceType.DYNAMIC.value:
                return "DYNAMIC menus only support a single 'Next' route. Use a LOGIC_EXPRESSION node after the menu for conditional routing"
            else:
                return f"Remove extra routes or add more menu options. Maximum {max_routes} routes allowed"
        elif node_type == NodeType.API_ACTION.value:
            return "API_ACTION nodes support 'success' and 'error' conditions only"
        elif node_type in [NodeType.PROMPT.value, NodeType.TEXT.value, NodeType.SET_VARIABLE.value]:
            return f"{node_type} nodes only support a single route with condition 'true'"
        else:
            return f"Reduce the number of routes to {max_routes} or fewer"

    def _get_invalid_condition_error_message(
        self,
        node_type: str,
        node_config: Dict[str, Any],
        condition: str
    ) -> str:
        """Generate descriptive error message for invalid condition"""
        if node_type == NodeType.MENU.value:
            source_type = node_config.get('source_type')
            if source_type == MenuSourceType.DYNAMIC.value:
                return f"DYNAMIC MENU nodes only allow condition 'true'. Got: '{condition}'"
            else:
                num_options = len(node_config.get('static_options', []))
                return f"STATIC MENU nodes only allow 'selection == N' (where N is 1-{num_options}). Got: '{condition}'"
        elif node_type == NodeType.API_ACTION.value:
            return f"API_ACTION nodes only allow conditions: 'success' or 'error'. Got: '{condition}'"
        elif node_type in [NodeType.PROMPT.value, NodeType.TEXT.value, NodeType.SET_VARIABLE.value]:
            return f"{node_type} nodes only allow condition 'true'. Got: '{condition}'"
        else:
            return f"Invalid condition '{condition}' for node type {node_type}"

    def _get_condition_suggestion(
        self,
        node_type: str,
        node_config: Dict[str, Any]
    ) -> str:
        """Generate helpful suggestion for fixing condition issues"""
        if node_type == NodeType.MENU.value:
            source_type = node_config.get('source_type')
            if source_type == MenuSourceType.DYNAMIC.value:
                return "Use condition 'true' for the Next route. For conditional routing, add a LOGIC_EXPRESSION node after this menu"
            else:
                num_options = len(node_config.get('static_options', []))
                return f"Use 'selection == 1' through 'selection == {num_options}', one route per option"
        elif node_type == NodeType.API_ACTION.value:
            return "Use 'success' for successful API calls, 'error' for failures"
        elif node_type in [NodeType.PROMPT.value, NodeType.TEXT.value, NodeType.SET_VARIABLE.value]:
            return "Use condition 'true' (the only valid condition for this node type)"
        elif node_type == NodeType.LOGIC_EXPRESSION.value:
            return "Use any valid expression as a condition (non-empty string)"
        else:
            return "Use a valid condition for this node type"


# ===== Class 3: ValidationResult (~50 lines) =====
class ValidationResult:
    """Result of flow validation"""

    def __init__(self):
        self.errors: List[Dict[str, str]] = []
        self.warnings: List[Dict[str, str]] = []

    def add_error(self, error_type: str, message: str, location: Optional[str] = None, suggestion: Optional[str] = None):
        """Add validation error"""
        error = {
            "type": error_type,
            "message": message
        }
        if location:
            error["location"] = location
        if suggestion:
            error["suggestion"] = suggestion
        self.errors.append(error)

    def add_warning(self, message: str, location: Optional[str] = None):
        """Add validation warning"""
        warning = {"message": message}
        if location:
            warning["location"] = location
        self.warnings.append(warning)

    def is_valid(self) -> bool:
        """Check if validation passed"""
        return len(self.errors) == 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "valid": self.is_valid(),
            "errors": self.errors,
            "warnings": self.warnings
        }


# ===== Class 4: FlowValidator (~400 lines) =====
class FlowValidator:
    """
    Comprehensive flow structure validator

    Validation Checks:
    1. JSON syntax valid
    2. Required fields present
    3. name unique per bot (not globally)
    4. trigger_keywords unique per bot
    5. Node IDs unique within flow
    6. start_node_id exists in nodes
    7. All route target_nodes exist
    8. No circular references without input nodes
    9. Variable types valid
    10. System constraints respected
    11. Node configs validated by Pydantic
    12. fail_route exists if defined
    13. Trigger keywords format
    """

    # Node types that collect user input (used to allow cycles that include these)
    INPUT_NODE_TYPES = {NodeType.PROMPT, NodeType.MENU}

    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
        self.route_validator = RouteConditionValidator()
        self.type_converter = TypeConverter()

    async def validate_flow(
        self,
        flow_data: Dict[str, Any],
        bot_id: UUID,
        current_flow_id: Optional[UUID] = None
    ) -> ValidationResult:
        """
        Comprehensive flow validation orchestrator

        Args:
            flow_data: Flow definition dictionary
            bot_id: Bot ID that owns the flow
            current_flow_id: Current flow UUID (for updates, to exclude self from duplicate checks)

        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult()

        # Step 1: Validate required fields (early return if missing)
        self._validate_required_fields(flow_data, result)
        if not result.is_valid():
            return result

        # Step 2: Validate flow name
        await self._validate_flow_name(
            flow_data.get('name'), bot_id, current_flow_id, result
        )

        # Step 3: Validate trigger keywords
        await self._validate_trigger_keywords_wrapper(flow_data, bot_id, current_flow_id, result)

        # Step 4: Validate flow variables
        self._validate_flow_variables(flow_data, result)

        # Step 5: Validate node structure
        nodes = self._validate_node_structure(flow_data, result)
        if not result.is_valid():
            return result

        # Step 6: Validate node graph
        start_node_id = flow_data.get('start_node_id')
        self._validate_node_graph(nodes, start_node_id, result)

        # Step 7: Validate routes
        self._validate_routes(nodes, result)

        # Step 8: Validate SET_VARIABLE assignments reference declared variables
        declared_variables = set(flow_data.get('variables', {}).keys())
        self._validate_set_variable_assignments(nodes, declared_variables, result)

        return result

    def _validate_required_fields(
        self,
        flow_data: Dict[str, Any],
        result: ValidationResult
    ):
        """Validate that all required top-level fields are present"""
        required_fields = ['name', 'trigger_keywords', 'start_node_id', 'nodes']
        for field in required_fields:
            if field not in flow_data:
                result.add_error(
                    "missing_field",
                    f"Required field '{field}' is missing",
                    field
                )

    async def _validate_trigger_keywords_wrapper(
        self,
        flow_data: Dict[str, Any],
        bot_id: UUID,
        current_flow_id: Optional[UUID],
        result: ValidationResult
    ):
        """Validate trigger keywords format and uniqueness"""
        keywords = flow_data.get('trigger_keywords', [])
        await self._validate_trigger_keywords(keywords, bot_id, current_flow_id, result)

    def _validate_flow_variables(self, flow_data: Dict[str, Any], result: ValidationResult):
        """Validate flow variables, defaults, and variable assignments"""
        # Validate variables
        variables = flow_data.get('variables', {})
        self._validate_variables(variables, result)

        # Validate defaults
        nodes_dict = flow_data.get('nodes', {})
        self._validate_defaults(flow_data.get('defaults', {}), nodes_dict, result)

    def _validate_node_structure(
        self,
        flow_data: Dict[str, Any],
        result: ValidationResult
    ) -> Dict[str, FlowNode]:
        """Validate node structure: count, parsing, and Pydantic validation"""
        nodes_dict = flow_data.get('nodes', {})

        # Check nodes structure
        if not nodes_dict or not isinstance(nodes_dict, dict):
            result.add_error(
                "invalid_structure",
                "Flow must contain at least one node",
                "nodes"
            )
            return {}

        # Validate node count constraint
        if len(nodes_dict) > SystemConstraints.MAX_NODES_PER_FLOW:
            result.add_error(
                "constraint_violation",
                f"Flow exceeds maximum of {SystemConstraints.MAX_NODES_PER_FLOW} nodes (has {len(nodes_dict)})",
                "nodes"
            )

        # Parse and validate all nodes with Pydantic
        nodes: Dict[str, FlowNode] = {}
        for node_id, node_data in nodes_dict.items():
            # Validate node ID format
            if not validate_node_id_format(node_id):
                result.add_error(
                    "invalid_format",
                    f"Node ID '{node_id}' must contain only alphanumeric characters and underscores",
                    f"nodes.{node_id}"
                )
                continue

            # Validate node ID matches key
            if node_data.get('id') != node_id:
                result.add_error(
                    "id_mismatch",
                    f"Node ID in config ('{node_data.get('id')}') does not match key ('{node_id}')",
                    f"nodes.{node_id}.id"
                )
                continue

            # Parse with Pydantic
            try:
                nodes[node_id] = FlowNode.model_validate(node_data)
            except ValidationError as e:
                for error in e.errors():
                    loc_parts = ['nodes', node_id] + [str(x) for x in error['loc']]
                    location = '.'.join(loc_parts)
                    msg = error['msg']
                    if 'ctx' in error and error['ctx']:
                        ctx = error['ctx']
                        if 'error' in ctx:
                            msg = str(ctx['error'])
                    result.add_error(
                        "validation_error",
                        f"Node '{node_id}': {msg}",
                        location
                    )

        return nodes

    def _validate_node_graph(
        self,
        nodes: Dict[str, FlowNode],
        start_node_id: str,
        result: ValidationResult
    ):
        """Validate node graph: start node, orphans, cycles, unreachable nodes"""
        if not nodes:
            return

        # Validate start_node_id exists
        if start_node_id not in nodes:
            result.add_error(
                "missing_node",
                f"start_node_id '{start_node_id}' does not exist in nodes",
                "start_node_id",
                f"Add node with id '{start_node_id}' or change start_node_id"
            )

        # Validate unique node names
        self._validate_unique_node_names(nodes, result)

        # Validate no orphan nodes
        self._validate_no_orphan_nodes(nodes, start_node_id, result)

        # Detect circular references
        self._detect_circular_references(nodes, start_node_id, result)

        # Check for unreachable nodes (warning only)
        self._check_unreachable_nodes(nodes, start_node_id, result)

    def _validate_routes(self, nodes: Dict[str, FlowNode], result: ValidationResult):
        """Validate routes and conditions"""
        if not nodes:
            return

        # Validate all routes and their conditions
        self._validate_all_routes(nodes, result)

    async def _validate_flow_name(
        self,
        flow_name: str,
        bot_id: UUID,
        current_flow_id: Optional[UUID],
        result: ValidationResult
    ):
        """Validate flow name format and uniqueness per bot"""
        if not flow_name or not flow_name.strip():
            result.add_error("invalid_name", "name cannot be empty or whitespace-only", "name")
            return

        if len(flow_name) > SystemConstraints.MAX_FLOW_NAME_LENGTH:
            result.add_error(
                "constraint_violation",
                f"name exceeds maximum length of {SystemConstraints.MAX_FLOW_NAME_LENGTH} characters",
                "name"
            )

        # Check uniqueness
        if not self.db:
            return

        from app.models.flow import Flow

        stmt = select(Flow).where(
            Flow.bot_id == bot_id,
            Flow.name == flow_name
        )

        if current_flow_id:
            stmt = stmt.where(Flow.id != current_flow_id)

        db_result = await self.db.execute(stmt)
        conflicting_flow = db_result.scalar_one_or_none()

        if conflicting_flow:
            result.add_error(
                "duplicate_flow_name",
                f"Flow name '{flow_name}' already exists in this bot",
                "name",
                "Use a different name or update the existing flow"
            )

    async def _validate_trigger_keywords(
        self,
        keywords: List[str],
        bot_id: UUID,
        current_flow_id: Optional[UUID],
        result: ValidationResult
    ):
        """Validate trigger keywords format and uniqueness per bot"""
        if not isinstance(keywords, list):
            result.add_error("invalid_type", "trigger_keywords must be an array", "trigger_keywords")
            return

        if not keywords or len(keywords) == 0:
            result.add_error(
                "missing_trigger_keywords",
                "At least one trigger keyword is required",
                "trigger_keywords",
                "Add at least one trigger keyword to activate this flow"
            )
            return

        # Validate format and character constraints
        # Allowed: letters (A-Z, a-z), numbers (0-9), spaces, underscores (_), hyphens (-)
        ALLOWED_PATTERN = re.compile(r'^[A-Za-z0-9 _-]+$')
        has_wildcard = False

        for i, keyword in enumerate(keywords):
            if not isinstance(keyword, str):
                result.add_error(
                    "invalid_type",
                    f"Keyword at index {i} must be a string",
                    f"trigger_keywords[{i}]"
                )
                continue

            if not keyword.strip():
                result.add_error(
                    "invalid_value",
                    f"Trigger keyword at index {i} cannot be empty or whitespace only",
                    f"trigger_keywords[{i}]"
                )
                continue

            # Check for wildcard
            if keyword.strip() == "*":
                has_wildcard = True
                continue

            # Check length
            if len(keyword) > SystemConstraints.MAX_INTERRUPT_KEYWORD_LENGTH:
                result.add_error(
                    "constraint_violation",
                    f"Trigger keyword '{keyword}' exceeds maximum length of {SystemConstraints.MAX_INTERRUPT_KEYWORD_LENGTH} characters (current: {len(keyword)})",
                    f"trigger_keywords[{i}]"
                )
                continue

            # Check for allowed characters (no punctuation, special characters, or emojis)
            if not ALLOWED_PATTERN.match(keyword):
                result.add_error(
                    "invalid_characters",
                    f"Trigger keyword '{keyword}' contains invalid characters. Only letters (A-Z, a-z), numbers (0-9), spaces, underscores (_), and hyphens (-) are allowed. No punctuation or special characters permitted.",
                    f"trigger_keywords[{i}]",
                    "Remove punctuation, special characters, and emojis from the keyword"
                )

        # Validate wildcard combination
        if has_wildcard and len(keywords) > 1:
            result.add_error(
                "wildcard_combination_error",
                "Wildcard trigger '*' cannot be combined with other keywords. The wildcard must be the only keyword in the array.",
                "trigger_keywords",
                "Remove other keywords or use a separate flow for the wildcard trigger"
            )

        if not result.is_valid() or not self.db or not keywords:
            return

        # Check for duplicate keywords (batched query)
        from app.models.flow import Flow
        from sqlalchemy import or_

        normalized_keywords = [kw.strip().upper() for kw in keywords if kw.strip()]

        if not normalized_keywords:
            return

        # Build a single query that checks all keywords at once
        keyword_conditions = [Flow.trigger_keywords.contains([kw]) for kw in normalized_keywords]

        stmt = select(Flow).where(
            Flow.bot_id == bot_id,
            or_(*keyword_conditions)
        )

        if current_flow_id:
            stmt = stmt.where(Flow.id != current_flow_id)

        db_result = await self.db.execute(stmt)
        conflicting_flows = db_result.scalars().all()

        # Check each keyword against conflicting flows
        for keyword in normalized_keywords:
            for conflicting_flow in conflicting_flows:
                # Check if this flow contains this specific keyword
                if any(kw.strip().upper() == keyword for kw in conflicting_flow.trigger_keywords):
                    result.add_error(
                        "duplicate_trigger_keyword",
                        f"Trigger keyword '{keyword}' is already used by flow '{conflicting_flow.name}' (ID: {conflicting_flow.id}) in this bot",
                        "trigger_keywords",
                        f"Use a different keyword or remove it from flow '{conflicting_flow.name}' first"
                    )
                    break  # Only report first conflict for each keyword

    def _validate_variables(self, variables: Dict[str, Any], result: ValidationResult):
        """Validate flow variables"""
        if not isinstance(variables, dict):
            result.add_error("invalid_type", "variables must be an object", "variables")
            return

        valid_types = [vt.value for vt in VariableType]

        for var_name, var_def in variables.items():
            if var_name in ReservedKeywords.RESERVED:
                result.add_error(
                    "reserved_keyword",
                    f"Variable name '{var_name}' is reserved and cannot be used. Reserved keywords: {', '.join(ReservedKeywords.RESERVED)}",
                    f"variables.{var_name}",
                    f"Choose a different variable name"
                )

            # Validate variable name format
            if not re.match(RegexPatterns.IDENTIFIER, var_name):
                result.add_error(
                    "invalid_format",
                    f"Variable name '{var_name}' must start with a letter or underscore and contain only letters, numbers, and underscores",
                    f"variables.{var_name}",
                    f"Use only letters, numbers, and underscores (e.g., 'user_name', 'age', '_temp')"
                )

            if len(var_name) > SystemConstraints.MAX_VARIABLE_NAME_LENGTH:
                result.add_error(
                    "constraint_violation",
                    f"Variable name '{var_name}' exceeds maximum length",
                    f"variables.{var_name}"
                )

            if not isinstance(var_def, dict):
                result.add_error(
                    "invalid_structure",
                    f"Variable '{var_name}' definition must be an object",
                    f"variables.{var_name}"
                )
                continue

            var_type = var_def.get('type')
            if var_type not in valid_types:
                result.add_error(
                    "invalid_type",
                    f"Variable '{var_name}' has invalid type '{var_type}'. Must be one of: {', '.join(valid_types)}",
                    f"variables.{var_name}.type"
                )
            else:
                self._validate_variable_default(var_name, var_type, var_def.get('default'), result)

    def _validate_variable_default(self, var_name: str, var_type: str, default_value: Any, result: ValidationResult):
        """Validate that a variable's default value matches its declared type"""
        if default_value is None:
            return

        location = f"variables.{var_name}.default"

        if var_type == VariableType.STRING.value:
            if not isinstance(default_value, str):
                result.add_error(
                    "invalid_default_value",
                    f"Variable '{var_name}' has type 'STRING' but default value is not a string. Got: {type(default_value).__name__}",
                    location,
                    "Provide a string value or null"
                )
        elif var_type == VariableType.NUMBER.value:
            if isinstance(default_value, bool):
                result.add_error(
                    "invalid_default_value",
                    f"Variable '{var_name}' has type 'NUMBER' but default value is a boolean",
                    location,
                    "Provide a number (e.g., 42, -10, 0, 3.14) or null"
                )
            elif isinstance(default_value, str):
                try:
                    float(default_value)
                except ValueError:
                    result.add_error(
                        "invalid_default_value",
                        f"Variable '{var_name}' has type 'NUMBER' but default value '{default_value}' cannot be converted to a number",
                        location,
                        "Provide a valid number (e.g., 42, -10, 0, 3.14) or null"
                    )
            elif not isinstance(default_value, (int, float)):
                result.add_error(
                    "invalid_default_value",
                    f"Variable '{var_name}' has type 'NUMBER' but default value is {type(default_value).__name__}",
                    location,
                    "Provide a number (e.g., 42, -10, 0, 3.14) or null"
                )
        elif var_type == VariableType.BOOLEAN.value:
            if isinstance(default_value, str):
                if default_value.lower() not in ['true', 'false', '1', '0', 'yes', 'no', 'y', 'n']:
                    result.add_error(
                        "invalid_default_value",
                        f"Variable '{var_name}' has type 'BOOLEAN' but default value '{default_value}' cannot be converted to boolean",
                        location,
                        "Provide true or false"
                    )
            elif not isinstance(default_value, bool):
                result.add_error(
                    "invalid_default_value",
                    f"Variable '{var_name}' has type 'BOOLEAN' but default value is {type(default_value).__name__}",
                    location,
                    "Provide true or false"
                )
        elif var_type == VariableType.ARRAY.value:
            if isinstance(default_value, str):
                import json
                try:
                    parsed = json.loads(default_value)
                    if not isinstance(parsed, list):
                        result.add_error(
                            "invalid_default_value",
                            f"Variable '{var_name}' has type 'ARRAY' but default value parses to {type(parsed).__name__}, not a list",
                            location,
                            "Provide a valid JSON array (e.g., [], [\"item1\", \"item2\"]) or null"
                        )
                except (json.JSONDecodeError, ValueError):
                    result.add_error(
                        "invalid_default_value",
                        f"Variable '{var_name}' has type 'ARRAY' but default value '{default_value}' is not valid JSON",
                        location,
                        "Provide a valid JSON array (e.g., [], [\"item1\", \"item2\"]) or null"
                    )
            elif not isinstance(default_value, list):
                result.add_error(
                    "invalid_default_value",
                    f"Variable '{var_name}' has type 'ARRAY' but default value is {type(default_value).__name__}",
                    location,
                    "Provide a valid JSON array (e.g., [], [\"item1\", \"item2\"]) or null"
                )

    def _validate_defaults(self, defaults: Dict[str, Any], nodes: Dict[str, Any], result: ValidationResult):
        """Validate flow defaults"""
        if not defaults:
            return

        if not isinstance(defaults, dict):
            result.add_error("invalid_type", "defaults must be an object", "defaults")
            return

        retry_logic = defaults.get('retry_logic')
        if retry_logic:
            if not isinstance(retry_logic, dict):
                result.add_error(
                    "invalid_type",
                    "retry_logic must be an object",
                    "defaults.retry_logic"
                )
                return

            max_attempts = retry_logic.get('max_attempts')
            if max_attempts is not None:
                if not isinstance(max_attempts, int) or max_attempts < 1 or max_attempts > SystemConstraints.MAX_VALIDATION_ATTEMPTS_MAX:
                    result.add_error(
                        "invalid_value",
                        f"max_attempts must be between 1 and {SystemConstraints.MAX_VALIDATION_ATTEMPTS_MAX}",
                        "defaults.retry_logic.max_attempts"
                    )

            fail_route = retry_logic.get('fail_route')
            # fail_route is optional - if not defined, session terminates on max attempts
            if fail_route and fail_route not in nodes:
                result.add_error(
                    "missing_node",
                    f"fail_route '{fail_route}' does not exist in nodes",
                    "defaults.retry_logic.fail_route",
                    f"Create a node with ID '{fail_route}' or use an existing node ID"
                )

    def _validate_unique_node_names(self, nodes: Dict[str, FlowNode], result: ValidationResult):
        """Validate that all node names are unique (case-insensitive)"""
        if not nodes:
            return

        name_to_nodes = {}
        for node_id, node in nodes.items():
            name_lower = node.name.lower().strip()
            if name_lower not in name_to_nodes:
                name_to_nodes[name_lower] = []
            name_to_nodes[name_lower].append(node_id)

        for name_lower, node_ids in name_to_nodes.items():
            if len(node_ids) > 1:
                original_name = nodes[node_ids[0]].name
                nodes_str = ', '.join(sorted(node_ids))
                result.add_error(
                    "duplicate_node_name",
                    f"Duplicate node name '{original_name}' found in nodes: {nodes_str}",
                    "nodes",
                    "Each node must have a unique name (case-insensitive)"
                )

    def _validate_no_orphan_nodes(self, nodes: Dict[str, FlowNode], start_node_id: str, result: ValidationResult):
        """Validate that only the start node has no parent"""
        if not nodes or not start_node_id:
            return

        nodes_with_parents = set()
        for node_id, node in nodes.items():
            if node.routes:
                for route in node.routes:
                    nodes_with_parents.add(route.target_node)

        orphan_nodes = []
        for node_id in nodes.keys():
            if node_id == start_node_id:
                continue
            if node_id not in nodes_with_parents:
                orphan_nodes.append(node_id)

        if orphan_nodes:
            node_names = []
            for node_id in orphan_nodes:
                node = nodes[node_id]
                node_names.append(f"'{node.name}' ({node_id})")

            nodes_str = ', '.join(node_names)
            result.add_error(
                "orphan_nodes",
                f"Orphan nodes detected (nodes with no parent): {nodes_str}. "
                f"Only the start node should have no parent. "
                f"These nodes are unreachable in the flow.",
                "nodes"
            )

    def _validate_all_routes(self, nodes: Dict[str, FlowNode], result: ValidationResult):
        """Validate all node routes including target existence and conditions"""
        node_ids = set(nodes.keys())

        for node_id, node in nodes.items():
            if not node.routes:
                continue

            if len(node.routes) > SystemConstraints.MAX_ROUTES_PER_NODE:
                result.add_error(
                    "constraint_violation",
                    f"Node has {len(node.routes)} routes, exceeds maximum of {SystemConstraints.MAX_ROUTES_PER_NODE}",
                    f"nodes.{node_id}.routes"
                )

            # Check for duplicate route conditions and validate condition length
            seen_conditions = {}
            for i, route in enumerate(node.routes):
                condition = route.condition
                if condition:
                    # Validate condition length (spec line 759, 1649)
                    if len(condition) > SystemConstraints.MAX_ROUTE_CONDITION_LENGTH:
                        result.add_error(
                            "constraint_violation",
                            f"Route condition exceeds maximum length of {SystemConstraints.MAX_ROUTE_CONDITION_LENGTH} characters (current: {len(condition)})",
                            f"nodes.{node_id}.routes[{i}].condition"
                        )

                    normalized_condition = condition.strip().lower()
                    if normalized_condition in seen_conditions:
                        result.add_error(
                            "duplicate_route_condition",
                            f"Node '{node_id}' has duplicate route condition: '{condition.strip()}'",
                            f"nodes.{node_id}.routes",
                            "Each route must have a unique condition"
                        )
                    else:
                        seen_conditions[normalized_condition] = i

            # Validate each route
            for i, route in enumerate(node.routes):
                route_location = f"nodes.{node_id}.routes[{i}]"

                if route.target_node not in node_ids:
                    result.add_error(
                        "missing_node",
                        f"Route target '{route.target_node}' does not exist in nodes",
                        f"{route_location}.target_node"
                    )

            # Validate route conditions using RouteConditionValidator
            node_config = node.config.model_dump()
            routes_list = [route.model_dump() for route in node.routes]

            route_errors = self.route_validator.validate_node_routes(
                node_id, node.type, node_config, routes_list
            )

            for error in route_errors:
                result.add_error(
                    error["type"],
                    error["message"],
                    error.get("location"),
                    error.get("suggestion")
                )

    def _validate_set_variable_assignments(
        self,
        nodes: Dict[str, FlowNode],
        declared_variables: Set[str],
        result: ValidationResult
    ):
        """Validate SET_VARIABLE node assignments: presence, uniqueness, and declared variables"""
        from app.models.node_configs import SetVariableNodeConfig

        for node_id, node in nodes.items():
            if node.type != NodeType.SET_VARIABLE.value:
                continue

            config: SetVariableNodeConfig = node.config

            # Check for duplicates, empty values, and undeclared variables
            seen_variables: Set[str] = set()
            for i, assignment in enumerate(config.assignments):
                if assignment.variable in seen_variables:
                    result.add_error(
                        "duplicate_variable_assignment",
                        f"SET_VARIABLE node '{node_id}': variable '{assignment.variable}' is assigned more than once",
                        f"nodes.{node_id}.config.assignments[{i}].variable",
                        "Each variable can only be assigned once per SET_VARIABLE node"
                    )
                else:
                    seen_variables.add(assignment.variable)

                if not assignment.value:
                    result.add_error(
                        "empty_assignment_value",
                        f"SET_VARIABLE node '{node_id}': assignment [{i}] value cannot be empty",
                        f"nodes.{node_id}.config.assignments[{i}].value",
                        "Provide a literal value or a template expression such as {{variable}}"
                    )

                if assignment.variable not in declared_variables:
                    result.add_error(
                        "undeclared_variable",
                        f"SET_VARIABLE node '{node_id}': assignment [{i}] references undeclared variable '{assignment.variable}'",
                        f"nodes.{node_id}.config.assignments[{i}].variable",
                        f"Declare variable '{assignment.variable}' in the flow's variables definition first"
                    )

    def _check_cycle_from_node(self, node_id: str, nodes: Dict[str, FlowNode], visited_in_path: Set[str]) -> Optional[List[str]]:
        """Check for cycle starting from a specific node using DFS"""
        if node_id in visited_in_path:
            return [node_id]

        node = nodes.get(node_id)
        if not node:
            return None

        visited_in_path.add(node_id)

        if node.routes:
            for route in node.routes:
                target = route.target_node
                if target in nodes:
                    cycle = self._check_cycle_from_node(target, nodes, visited_in_path)
                    if cycle:
                        cycle.insert(0, node_id)
                        return cycle

        visited_in_path.remove(node_id)
        return None

    def _detect_circular_references(self, nodes: Dict[str, FlowNode], start_node_id: str, result: ValidationResult):
        """Detect circular references - only reject cycles without input nodes.

        Cycles containing at least one PROMPT or MENU node are allowed since user input
        naturally breaks potential infinite loops. Cycles with only non-input nodes
        (TEXT, API_ACTION, LOGIC_EXPRESSION, SET_VARIABLE) are rejected.
        """
        checked_nodes = set()

        for node_id in nodes.keys():
            if node_id in checked_nodes:
                continue

            cycle = self._check_cycle_from_node(node_id, nodes, set())
            if cycle:
                # Check if cycle contains at least one input node
                has_input_node = any(
                    nodes[nid].type in self.INPUT_NODE_TYPES
                    for nid in cycle if nid in nodes
                )

                if not has_input_node:
                    cycle.append(cycle[0])
                    cycle_str = ' → '.join(cycle)
                    result.add_error(
                        "circular_reference",
                        f"Circular reference without input node detected: {cycle_str}",
                        "nodes",
                        "Add a PROMPT or MENU node to the cycle, or remove the circular routing"
                    )
                checked_nodes.update(cycle)
            else:
                checked_nodes.add(node_id)

    def _check_unreachable_nodes(self, nodes: Dict[str, FlowNode], start_node_id: str, result: ValidationResult):
        """Check for unreachable nodes (warning only)"""
        if not start_node_id or start_node_id not in nodes:
            return

        reachable = set()

        def mark_reachable(node_id: str):
            if node_id in reachable or node_id not in nodes:
                return

            reachable.add(node_id)
            node = nodes[node_id]
            if node.routes:
                for route in node.routes:
                    mark_reachable(route.target_node)

        mark_reachable(start_node_id)

        unreachable = set(nodes.keys()) - reachable
        for node_id in unreachable:
            result.add_warning(
                f"Node '{node_id}' is unreachable from start_node_id",
                f"nodes.{node_id}"
            )


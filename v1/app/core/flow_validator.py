"""
Flow Validator
Validates flow structure on submission
Performs comprehensive checks against all system constraints
"""

from typing import Dict, List, Any, Set, Tuple, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.utils.logger import get_logger
from app.utils.exceptions import FlowValidationError, DuplicateFlowError
from app.utils.constants import (
    NodeType, ValidationType, MenuSourceType, HTTPMethod, VariableType,
    SystemConstraints, ReservedKeywords
)
from app.utils.security import validate_flow_id_format, validate_node_id_format

logger = get_logger(__name__)


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
    8. No circular references
    9. Variable types valid
    10. System constraints respected
    11. Node configs match type requirements
    12. fail_route exists if defined
    13. Validation rules are valid
    14. Trigger keywords format
    """
    
    def __init__(self, db: Optional[AsyncSession] = None):
        self.logger = get_logger(__name__)
        self.db = db
    
    async def validate_flow(
        self,
        flow_data: Dict[str, Any],
        bot_id: UUID,
        current_flow_id: Optional[UUID] = None
    ) -> ValidationResult:
        """
        Comprehensive flow validation
        
        Args:
            flow_data: Flow definition dictionary
            bot_id: Bot ID that owns the flow
            current_flow_id: Current flow UUID (for updates, to exclude self from duplicate checks)
        
        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult()
        
        # 1. Check required top-level fields
        self._check_required_fields(flow_data, result)
        if not result.is_valid():
            return result
        
        # 2. Validate flow name format and uniqueness per bot
        flow_name = flow_data.get('name')
        await self._validate_flow_name(flow_name, bot_id, current_flow_id, result)
        
        # 3. Validate trigger keywords (format and uniqueness per bot)
        await self._validate_trigger_keywords(
            flow_data.get('trigger_keywords', []),
            bot_id,
            current_flow_id,
            result
        )
        
        # 4. Validate variables
        self._validate_variables(flow_data.get('variables', {}), result)
        
        # 5. Validate defaults
        self._validate_defaults(flow_data.get('defaults', {}), flow_data.get('nodes', {}), result)
        
        # 6. Check nodes structure
        nodes = flow_data.get('nodes', {})
        if not nodes or not isinstance(nodes, dict):
            result.add_error(
                "invalid_structure",
                "Flow must contain at least one node",
                "nodes"
            )
            return result
        
        # 7. Validate node count constraint
        if len(nodes) > SystemConstraints.MAX_NODES_PER_FLOW:
            result.add_error(
                "constraint_violation",
                f"Flow exceeds maximum of {SystemConstraints.MAX_NODES_PER_FLOW} nodes (has {len(nodes)})",
                "nodes"
            )
        
        # === PASS 1: INDEX ALL NODE IDs ===
        node_ids = set(nodes.keys())
        
        # 9. Check start_node_id exists (using node_ids index)
        start_node_id = flow_data.get('start_node_id')
        if start_node_id not in node_ids:
            result.add_error(
                "missing_node",
                f"start_node_id '{start_node_id}' does not exist in nodes",
                "start_node_id",
                f"Add node with id '{start_node_id}' or change start_node_id"
            )
        
        # === PASS 2: VALIDATE ALL REFERENCES ===
        # 8. Validate each node (using node_ids index for reference validation)
        for node_id, node in nodes.items():
            self._validate_node(node_id, node, node_ids, result)
        
        # 9. Validate unique node names (case-insensitive)
        self._validate_unique_node_names(nodes, result)
        
        # 10. Validate no orphan nodes (only start node should have no parent)
        self._validate_no_orphan_nodes(nodes, start_node_id, result)
        
        # 11. Check all route references (redundant check, already done in Pass 2)
        # self._check_node_references is no longer needed as validation happens in Pass 2
        
        # 12. Detect circular references
        self._detect_circular_references(nodes, start_node_id, result)
        
        # 13. Check for unreachable nodes (warning only)
        self._check_unreachable_nodes(nodes, start_node_id, result)
        
        return result
    
    def _check_required_fields(self, flow_data: Dict[str, Any], result: ValidationResult):
        """Validate required top-level fields"""
        required_fields = ['name', 'start_node_id', 'nodes']
        
        for field in required_fields:
            if field not in flow_data:
                result.add_error(
                    "missing_field",
                    f"Required field '{field}' is missing",
                    field
                )
    
    async def _validate_flow_name(
        self,
        flow_name: str,
        bot_id: UUID,
        current_flow_id: Optional[UUID],
        result: ValidationResult
    ):
        """Validate flow name format and uniqueness per bot"""
        if not flow_name:
            result.add_error("invalid_name", "name cannot be empty", "name")
            return
        
        # Check length
        if len(flow_name) > SystemConstraints.MAX_FLOW_ID_LENGTH:
            result.add_error(
                "constraint_violation",
                f"name exceeds maximum length of {SystemConstraints.MAX_FLOW_ID_LENGTH} characters",
                "name"
            )
        
        # Check format
        if not validate_flow_id_format(flow_name):
            result.add_error(
                "invalid_format",
                "name must contain only alphanumeric characters and underscores",
                "name"
            )
        
        # Check uniqueness (unique per bot, not globally)
        if not self.db:
            return
        
        from app.models.flow import Flow
        
        stmt = select(Flow).where(
            Flow.bot_id == bot_id,
            Flow.name == flow_name
        )
        
        # Exclude current flow if updating
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
        
        # Check minimum requirement: at least one trigger keyword
        if not keywords or len(keywords) == 0:
            result.add_error(
                "missing_trigger_keywords",
                "At least one trigger keyword is required",
                "trigger_keywords",
                "Add at least one trigger keyword to activate this flow"
            )
            return
        
        # Validate format
        for i, keyword in enumerate(keywords):
            if not isinstance(keyword, str):
                result.add_error(
                    "invalid_type",
                    f"Keyword at index {i} must be a string",
                    f"trigger_keywords[{i}]"
                )
            elif not keyword.strip():
                result.add_error(
                    "invalid_value",
                    f"Trigger keyword at index {i} cannot be empty or whitespace only",
                    f"trigger_keywords[{i}]"
                )
        
        # If format validation failed or no database access, stop here
        if not result.is_valid() or not self.db or not keywords:
            return
        
        # Check for duplicate keywords within same bot's flows
        # Import Flow model here to avoid circular dependency
        from app.models.flow import Flow
        
        # Normalize keywords to uppercase for comparison (matching storage format)
        normalized_keywords = [kw.strip().upper() for kw in keywords if kw.strip()]
        
        if not normalized_keywords:
            return
        
        # Query for flows with any of these keywords, owned by same bot
        for keyword in normalized_keywords:
            stmt = select(Flow).where(
                Flow.bot_id == bot_id,
                Flow.trigger_keywords.contains([keyword])
            )
            
            # Exclude current flow if updating (by UUID)
            if current_flow_id:
                stmt = stmt.where(Flow.id != current_flow_id)
            
            db_result = await self.db.execute(stmt)
            conflicting_flow = db_result.scalar_one_or_none()
            
            if conflicting_flow:
                result.add_error(
                    "duplicate_trigger_keyword",
                    f"Trigger keyword '{keyword}' is already used by flow '{conflicting_flow.name}' (ID: {conflicting_flow.id}) in this bot",
                    "trigger_keywords",
                    f"Use a different keyword or remove it from flow '{conflicting_flow.name}' first"
                )
    
    def _validate_variables(self, variables: Dict[str, Any], result: ValidationResult):
        """Validate flow variables"""
        if not isinstance(variables, dict):
            result.add_error("invalid_type", "variables must be an object", "variables")
            return
        
        valid_types = [vt.value for vt in VariableType]
        
        for var_name, var_def in variables.items():
            # Check if variable name is reserved
            if var_name in ReservedKeywords.RESERVED:
                result.add_error(
                    "reserved_keyword",
                    f"Variable name '{var_name}' is reserved and cannot be used. Reserved keywords: {', '.join(ReservedKeywords.RESERVED)}",
                    f"variables.{var_name}",
                    f"Choose a different variable name"
                )
            
            # Check variable name length
            if len(var_name) > SystemConstraints.MAX_VARIABLE_NAME_LENGTH:
                result.add_error(
                    "constraint_violation",
                    f"Variable name '{var_name}' exceeds maximum length",
                    f"variables.{var_name}"
                )
            
            # Check variable definition structure
            if not isinstance(var_def, dict):
                result.add_error(
                    "invalid_structure",
                    f"Variable '{var_name}' definition must be an object",
                    f"variables.{var_name}"
                )
                continue
            
            # Check type field
            var_type = var_def.get('type')
            if var_type not in valid_types:
                result.add_error(
                    "invalid_type",
                    f"Variable '{var_name}' has invalid type '{var_type}'. Must be one of: {', '.join(valid_types)}",
                    f"variables.{var_name}.type"
                )
            else:
                # Validate default value matches type
                self._validate_variable_default(var_name, var_type, var_def.get('default'), result)
    
    def _validate_variable_default(self, var_name: str, var_type: str, default_value: Any, result: ValidationResult):
        """
        Validate that a variable's default value matches its declared type
        
        Args:
            var_name: Variable name
            var_type: Variable type (string, integer, boolean, array)
            default_value: Default value to validate
            result: ValidationResult to add errors to
        """
        # null is always valid for any type
        if default_value is None:
            return
        
        location = f"variables.{var_name}.default"
        
        if var_type == VariableType.STRING.value:
            # String type: default must be a string
            if not isinstance(default_value, str):
                result.add_error(
                    "invalid_default_value",
                    f"Variable '{var_name}' has type 'string' but default value is not a string. Got: {type(default_value).__name__}",
                    location,
                    "Provide a string value or null"
                )
        
        elif var_type == VariableType.INTEGER.value:
            # Integer type: default must be an integer (or a string that can convert to integer)
            if isinstance(default_value, bool):
                # Boolean is technically an int subclass in Python, but we want to reject it
                result.add_error(
                    "invalid_default_value",
                    f"Variable '{var_name}' has type 'integer' but default value is a boolean",
                    location,
                    "Provide an integer (e.g., 42, -10, 0) or null"
                )
            elif isinstance(default_value, str):
                # Try to parse string as integer
                try:
                    int(default_value)
                except ValueError:
                    result.add_error(
                        "invalid_default_value",
                        f"Variable '{var_name}' has type 'integer' but default value '{default_value}' cannot be converted to an integer",
                        location,
                        "Provide a valid integer (e.g., 42, -10, 0) or null"
                    )
            elif not isinstance(default_value, int):
                result.add_error(
                    "invalid_default_value",
                    f"Variable '{var_name}' has type 'integer' but default value is {type(default_value).__name__}",
                    location,
                    "Provide an integer (e.g., 42, -10, 0) or null"
                )
        
        elif var_type == VariableType.BOOLEAN.value:
            # Boolean type: default must be a boolean (or a string that can convert)
            if isinstance(default_value, str):
                # Check if string is valid boolean representation
                if default_value.lower() not in ['true', 'false', '1', '0', 'yes', 'no', 'y', 'n']:
                    result.add_error(
                        "invalid_default_value",
                        f"Variable '{var_name}' has type 'boolean' but default value '{default_value}' cannot be converted to boolean",
                        location,
                        "Provide true or false"
                    )
            elif not isinstance(default_value, bool):
                result.add_error(
                    "invalid_default_value",
                    f"Variable '{var_name}' has type 'boolean' but default value is {type(default_value).__name__}",
                    location,
                    "Provide true or false"
                )
        
        elif var_type == VariableType.ARRAY.value:
            # Array type: default must be an array (or a string that can be parsed as JSON array)
            if isinstance(default_value, str):
                # Try to parse string as JSON array
                import json
                try:
                    parsed = json.loads(default_value)
                    if not isinstance(parsed, list):
                        result.add_error(
                            "invalid_default_value",
                            f"Variable '{var_name}' has type 'array' but default value parses to {type(parsed).__name__}, not a list",
                            location,
                            "Provide a valid JSON array (e.g., [], [\"item1\", \"item2\"]) or null"
                        )
                except (json.JSONDecodeError, ValueError):
                    result.add_error(
                        "invalid_default_value",
                        f"Variable '{var_name}' has type 'array' but default value '{default_value}' is not valid JSON",
                        location,
                        "Provide a valid JSON array (e.g., [], [\"item1\", \"item2\"]) or null"
                    )
            elif not isinstance(default_value, list):
                result.add_error(
                    "invalid_default_value",
                    f"Variable '{var_name}' has type 'array' but default value is {type(default_value).__name__}",
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
        
        # Validate retry_logic if present
        retry_logic = defaults.get('retry_logic')
        if retry_logic:
            if not isinstance(retry_logic, dict):
                result.add_error(
                    "invalid_type",
                    "retry_logic must be an object",
                    "defaults.retry_logic"
                )
                return
            
            # Check max_attempts
            max_attempts = retry_logic.get('max_attempts')
            if max_attempts is not None:
                if not isinstance(max_attempts, int) or max_attempts < 1 or max_attempts > SystemConstraints.MAX_VALIDATION_ATTEMPTS_MAX:
                    result.add_error(
                        "invalid_value",
                        f"max_attempts must be between 1 and {SystemConstraints.MAX_VALIDATION_ATTEMPTS_MAX}",
                        "defaults.retry_logic.max_attempts"
                    )
            
            # Check fail_route exists
            fail_route = retry_logic.get('fail_route')
            if fail_route and fail_route not in nodes:
                result.add_error(
                    "missing_node",
                    f"fail_route '{fail_route}' does not exist in nodes",
                    "defaults.retry_logic.fail_route"
                )
    
    def _validate_node(self, node_id: str, node: Dict[str, Any], node_ids: Set[str], result: ValidationResult):
        """Validate individual node"""
        location_prefix = f"nodes.{node_id}"
        
        # Check node ID format
        if not validate_node_id_format(node_id):
            result.add_error(
                "invalid_format",
                f"Node ID '{node_id}' must contain only alphanumeric characters and underscores",
                location_prefix
            )
        
        # Check node ID matches key
        if node.get('id') != node_id:
            result.add_error(
                "id_mismatch",
                f"Node ID in config ('{node.get('id')}') does not match key ('{node_id}')",
                f"{location_prefix}.id"
            )
        
        # Validate name field (required)
        if 'name' not in node:
            result.add_error(
                "missing_field",
                f"Node '{node_id}' is missing required field 'name'",
                f"{location_prefix}.name"
            )
            # Continue with other validations even if name is missing
        else:
            node_name = node['name']
            
            if not isinstance(node_name, str):
                result.add_error(
                    "invalid_type",
                    f"Node '{node_id}' name must be a string",
                    f"{location_prefix}.name"
                )
            elif not node_name or not node_name.strip():
                result.add_error(
                    "invalid_value",
                    f"Node '{node_id}' has an empty name",
                    f"{location_prefix}.name"
                )
            elif len(node_name) > 50:
                result.add_error(
                    "constraint_violation",
                    f"Node '{node_id}' name exceeds maximum length of 50 characters (current: {len(node_name)})",
                    f"{location_prefix}.name"
                )
        
        # Check required fields
        if 'type' not in node:
            result.add_error("missing_field", "Node missing required field 'type'", f"{location_prefix}.type")
            return
        
        if 'config' not in node:
            result.add_error("missing_field", "Node missing required field 'config'", f"{location_prefix}.config")
            return
        
        # Validate node type
        node_type = node.get('type')
        try:
            NodeType(node_type)
        except ValueError:
            result.add_error(
                "invalid_type",
                f"Invalid node type '{node_type}'. Must be one of: {', '.join([nt.value for nt in NodeType])}",
                f"{location_prefix}.type"
            )
            return
        
        # Get config for validation
        config = node.get('config', {})
        
        # Validate routes (required for all except END)
        if node_type != NodeType.END.value:
            routes = node.get('routes')
            if not routes:
                result.add_error(
                    "missing_field",
                    f"{node_type} node must have routes",
                    f"{location_prefix}.routes"
                )
            else:
                self._validate_routes(node_id, routes, node_ids, result)
                
                # Validate route conditions using RouteConditionValidator
                from app.core.route_validator import RouteConditionValidator
                
                route_validator = RouteConditionValidator()
                route_errors = route_validator.validate_node_routes(
                    node_id, node_type, config, routes
                )
                
                # Add route validation errors to result
                for error in route_errors:
                    result.add_error(
                        error["type"],
                        error["message"],
                        error.get("location"),
                        error.get("suggestion")
                    )
        
        # Validate node-specific config
        self._validate_node_config(node_id, node_type, config, result)
    
    def _validate_unique_node_names(self, nodes: Dict[str, Any], result: ValidationResult):
        """Validate that all node names are unique (case-insensitive)"""
        if not nodes:
            return
        
        name_to_nodes = {}  # Maps lowercase name to list of node IDs
        
        for node_id, node in nodes.items():
            node_name = node.get('name', '')
            if not node_name:
                continue  # Already caught by _validate_node
            
            # Skip if name is not a string (already caught by _validate_node)
            if not isinstance(node_name, str):
                continue
            
            name_lower = node_name.lower().strip()
            if not name_lower:
                continue  # Empty names already caught by _validate_node
            
            if name_lower not in name_to_nodes:
                name_to_nodes[name_lower] = []
            name_to_nodes[name_lower].append(node_id)
        
        # Check for duplicates
        for name_lower, node_ids in name_to_nodes.items():
            if len(node_ids) > 1:
                # Get original name (any will do, they're case-insensitive duplicates)
                original_name = nodes[node_ids[0]]['name']
                nodes_str = ', '.join(sorted(node_ids))
                result.add_error(
                    "duplicate_node_name",
                    f"Duplicate node name '{original_name}' found in nodes: {nodes_str}",
                    "nodes",
                    "Each node must have a unique name (case-insensitive)"
                )
    
    def _validate_no_orphan_nodes(self, nodes: Dict[str, Any], start_node_id: str, result: ValidationResult):
        """
        Validate that only the start node has no parent.
        All other nodes must be referenced in at least one route.
        """
        if not nodes:
            return
        
        if not start_node_id:
            return  # Already caught by other validation
        
        # Build set of all nodes that have parents (referenced in routes)
        nodes_with_parents = set()
        
        for node_id, node in nodes.items():
            routes = node.get('routes', [])
            for route in routes:
                target_node = route.get('target_node')
                if target_node:
                    nodes_with_parents.add(target_node)
        
        # Find orphan nodes (no parent and not start node)
        orphan_nodes = []
        
        for node_id in nodes.keys():
            if node_id == start_node_id:
                continue  # Start node is allowed to have no parent
            
            if node_id not in nodes_with_parents:
                orphan_nodes.append(node_id)
        
        # Report errors
        if orphan_nodes:
            node_names = []
            for node_id in orphan_nodes:
                node = nodes[node_id]
                node_name = node.get('name', node_id)
                node_names.append(f"'{node_name}' ({node_id})")
            
            nodes_str = ', '.join(node_names)
            result.add_error(
                "orphan_nodes",
                f"Orphan nodes detected (nodes with no parent): {nodes_str}. "
                f"Only the start node should have no parent. "
                f"These nodes are unreachable in the flow.",
                "nodes"
            )
    
    def _validate_routes(self, node_id: str, routes: List[Dict[str, Any]], node_ids: Set[str], result: ValidationResult):
        """Validate node routes using node_ids index"""
        location_prefix = f"nodes.{node_id}.routes"
        
        if not isinstance(routes, list):
            result.add_error("invalid_type", "routes must be an array", location_prefix)
            return
        
        if len(routes) > SystemConstraints.MAX_ROUTES_PER_NODE:
            result.add_error(
                "constraint_violation",
                f"Node has {len(routes)} routes, exceeds maximum of {SystemConstraints.MAX_ROUTES_PER_NODE}",
                location_prefix
            )
        
        # Check for duplicate route conditions (case-insensitive, whitespace-trimmed)
        seen_conditions = {}
        for i, route in enumerate(routes):
            if isinstance(route, dict) and 'condition' in route:
                condition = route['condition']
                if condition:
                    # Normalize: trim whitespace and convert to lowercase
                    normalized_condition = str(condition).strip().lower()
                    if normalized_condition in seen_conditions:
                        result.add_error(
                            "duplicate_route_condition",
                            f"Node '{node_id}' has duplicate route condition: '{condition.strip()}'",
                            location_prefix,
                            "Each route must have a unique condition"
                        )
                    else:
                        seen_conditions[normalized_condition] = i
        
        for i, route in enumerate(routes):
            route_location = f"{location_prefix}[{i}]"
            
            if not isinstance(route, dict):
                result.add_error("invalid_type", f"Route at index {i} must be an object", route_location)
                continue
            
            # Check required fields
            if 'condition' not in route:
                result.add_error("missing_field", "Route missing 'condition'", f"{route_location}.condition")
            
            if 'target_node' not in route:
                result.add_error("missing_field", "Route missing 'target_node'", f"{route_location}.target_node")
            else:
                target = route['target_node']
                if target not in node_ids:
                    result.add_error(
                        "missing_node",
                        f"Route target '{target}' does not exist in nodes",
                        f"{route_location}.target_node"
                    )
    
    def _validate_content_length(self, content: str, max_length: int, field_name: str, result: ValidationResult):
        """Validate content length against spec limits"""
        if content and len(content) > max_length:
            result.add_error(
                "constraint_violation",
                f"{field_name} exceeds maximum length of {max_length} characters (current: {len(content)})",
                field_name
            )
    
    def _validate_node_config(self, node_id: str, node_type: str, config: Dict[str, Any], result: ValidationResult):
        """Validate node configuration based on type"""
        location = f"nodes.{node_id}.config"
        
        if node_type == NodeType.PROMPT.value:
            self._validate_prompt_config(config, location, result)
        elif node_type == NodeType.MENU.value:
            self._validate_menu_config(config, location, result)
        elif node_type == NodeType.API_ACTION.value:
            self._validate_api_action_config(config, location, result)
        elif node_type == NodeType.MESSAGE.value:
            self._validate_message_config(config, location, result)
    
    def _validate_prompt_config(self, config: Dict[str, Any], location: str, result: ValidationResult):
        """Validate PROMPT node config"""
        if 'text' not in config:
            result.add_error("missing_field", "PROMPT node must have 'text'", f"{location}.text")
        else:
            # Validate text length
            self._validate_content_length(
                config['text'],
                SystemConstraints.MAX_MESSAGE_LENGTH,
                f"{location}.text",
                result
            )
        
        if 'save_to_variable' not in config:
            result.add_error("missing_field", "PROMPT node must have 'save_to_variable'", f"{location}.save_to_variable")
        
        # Validate validation if present
        validation = config.get('validation')
        if validation:
            if 'type' not in validation or 'rule' not in validation or 'error_message' not in validation:
                result.add_error(
                    "invalid_structure",
                    "validation must have 'type', 'rule', and 'error_message'",
                    f"{location}.validation"
                )
            else:
                # Validate error_message length
                self._validate_content_length(
                    validation.get('error_message', ''),
                    SystemConstraints.MAX_ERROR_MESSAGE_LENGTH,
                    f"{location}.validation.error_message",
                    result
                )
                
                # Validate rule length based on type
                rule = validation.get('rule', '')
                val_type = validation.get('type')
                if val_type == ValidationType.REGEX.value:
                    self._validate_content_length(
                        rule,
                        SystemConstraints.MAX_REGEX_LENGTH,
                        f"{location}.validation.rule",
                        result
                    )
                elif val_type == ValidationType.EXPRESSION.value:
                    self._validate_content_length(
                        rule,
                        SystemConstraints.MAX_EXPRESSION_LENGTH,
                        f"{location}.validation.rule",
                        result
                    )
    
    def _validate_menu_config(self, config: Dict[str, Any], location: str, result: ValidationResult):
        """Validate MENU node config"""
        if 'text' not in config:
            result.add_error("missing_field", "MENU node must have 'text'", f"{location}.text")
        else:
            # Validate text length
            self._validate_content_length(
                config['text'],
                SystemConstraints.MAX_MESSAGE_LENGTH,
                f"{location}.text",
                result
            )
        
        if 'source_type' not in config:
            result.add_error("missing_field", "MENU node must have 'source_type'", f"{location}.source_type")
            return
        
        source_type = config['source_type']
        
        if source_type == MenuSourceType.STATIC.value:
            if 'static_options' not in config:
                result.add_error(
                    "missing_field",
                    "STATIC menu must have 'static_options'",
                    f"{location}.static_options"
                )
            else:
                # Validate option labels length
                static_options = config.get('static_options', [])
                if isinstance(static_options, list):
                    for i, option in enumerate(static_options):
                        if isinstance(option, dict) and 'label' in option:
                            self._validate_content_length(
                                option['label'],
                                SystemConstraints.MAX_OPTION_LABEL_LENGTH,
                                f"{location}.static_options[{i}].label",
                                result
                            )
        elif source_type == MenuSourceType.DYNAMIC.value:
            if 'source_variable' not in config:
                result.add_error(
                    "missing_field",
                    "DYNAMIC menu must have 'source_variable'",
                    f"{location}.source_variable"
                )
            if 'item_template' not in config:
                result.add_error(
                    "missing_field",
                    "DYNAMIC menu must have 'item_template'",
                    f"{location}.item_template"
                )
            else:
                # Validate item_template length
                self._validate_content_length(
                    config['item_template'],
                    SystemConstraints.MAX_TEMPLATE_LENGTH,
                    f"{location}.item_template",
                    result
                )
        
        # Validate counter_text if present
        if 'counter_text' in config:
            self._validate_content_length(
                config['counter_text'],
                SystemConstraints.MAX_TEMPLATE_LENGTH,
                f"{location}.counter_text",
                result
            )
    
    def _validate_api_action_config(self, config: Dict[str, Any], location: str, result: ValidationResult):
        """Validate API_ACTION node config"""
        if 'request' not in config:
            result.add_error("missing_field", "API_ACTION node must have 'request'", f"{location}.request")
            return
        
        request = config['request']
        if 'method' not in request:
            result.add_error("missing_field", "request must have 'method'", f"{location}.request.method")
        
        if 'url' not in request:
            result.add_error("missing_field", "request must have 'url'", f"{location}.request.url")
    
    def _validate_message_config(self, config: Dict[str, Any], location: str, result: ValidationResult):
        """Validate MESSAGE node config"""
        if 'text' not in config:
            result.add_error("missing_field", "MESSAGE node must have 'text'", f"{location}.text")
        else:
            # Validate text length
            self._validate_content_length(
                config['text'],
                SystemConstraints.MAX_MESSAGE_LENGTH,
                f"{location}.text",
                result
            )
    
    def _check_node_references(self, nodes: Dict[str, Any], result: ValidationResult):
        """Check all route target_nodes exist"""
        for node_id, node in nodes.items():
            routes = node.get('routes', [])
            for route in routes:
                target = route.get('target_node')
                if target and target not in nodes:
                    result.add_error(
                        "missing_node",
                        f"Node '{node_id}' routes to non-existent node '{target}'",
                        f"nodes.{node_id}.routes"
                    )
    
    def _check_cycle_from_node(self, node_id: str, nodes: Dict[str, Any], visited_in_path: Set[str]) -> Optional[List[str]]:
        """Check for cycle starting from a specific node using DFS"""
        if node_id in visited_in_path:
            # Circular reference detected - return the cycle
            return [node_id]
        
        node = nodes.get(node_id)
        if not node:
            return None
        
        visited_in_path.add(node_id)
        
        routes = node.get('routes', [])
        for route in routes:
            target = route.get('target_node')
            if target and target in nodes:
                cycle = self._check_cycle_from_node(target, nodes, visited_in_path)
                if cycle:
                    # Build full cycle path
                    cycle.insert(0, node_id)
                    return cycle
        
        visited_in_path.remove(node_id)
        return None
    
    def _detect_circular_references(self, nodes: Dict[str, Any], start_node_id: str, result: ValidationResult):
        """Detect circular references in ALL nodes, not just reachable ones"""
        checked_nodes = set()
        
        # Check all nodes, not just those reachable from start
        for node_id in nodes.keys():
            if node_id in checked_nodes:
                continue
            
            # Run DFS from this node
            cycle = self._check_cycle_from_node(node_id, nodes, set())
            if cycle:
                # Add the closing node to complete the cycle visualization
                cycle.append(cycle[0])
                cycle_str = ' → '.join(cycle)
                result.add_error(
                    "circular_reference",
                    f"Circular reference detected: {cycle_str}",
                    "nodes",
                    "Remove circular routing or add exit conditions"
                )
                # Mark all nodes in cycle as checked
                checked_nodes.update(cycle)
            else:
                checked_nodes.add(node_id)
    
    def _check_unreachable_nodes(self, nodes: Dict[str, Any], start_node_id: str, result: ValidationResult):
        """Check for unreachable nodes (warning only)"""
        if not start_node_id or start_node_id not in nodes:
            return
        
        reachable = set()
        
        def mark_reachable(node_id: str):
            if node_id in reachable or node_id not in nodes:
                return
            
            reachable.add(node_id)
            node = nodes[node_id]
            routes = node.get('routes', [])
            for route in routes:
                target = route.get('target_node')
                if target:
                    mark_reachable(target)
        
        mark_reachable(start_node_id)
        
        unreachable = set(nodes.keys()) - reachable
        for node_id in unreachable:
            result.add_warning(
                f"Node '{node_id}' is unreachable from start_node_id",
                f"nodes.{node_id}"
            )
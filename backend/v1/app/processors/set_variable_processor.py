"""
SET_VARIABLE Processor
Sets flow variables to configured values, then auto-progresses
"""

from typing import Optional, Dict, Any
from app.models.node_configs import FlowNode, SetVariableNodeConfig
from app.processors.base_processor import BaseProcessor, ProcessResult
from app.utils.exceptions import InputValidationError


class SetVariableProcessor(BaseProcessor):
    """
    Process SET_VARIABLE nodes - assign values to flow variables

    Features:
    - Set one or more variables to configured values
    - Supports template syntax in values ({{variable}})
    - Type conversion based on variable's declared type
    - No message display
    - No user input required
    - Immediate auto-progression to next node
    """

    async def process(
        self,
        node: FlowNode,
        context: Dict[str, Any],
        user_input: Optional[str] = None,
        session: Optional[Any] = None,
        db: Optional[Any] = None
    ) -> ProcessResult:
        """
        Process SET_VARIABLE node

        Args:
            node: Typed FlowNode with SET_VARIABLE configuration
            context: Session context
            user_input: Not used (set_variable nodes don't require input)

        Returns:
            ProcessResult with next node (no message, immediate routing)

        Raises:
            NoMatchingRouteError: If routes exist but none match
        """
        config: SetVariableNodeConfig = node.config

        # Apply each assignment
        flow_variables = context.get('_flow_variables', {})
        for assignment in config.assignments:
            try:
                rendered_value = self.template_engine.render_json_value(
                    assignment.value, context, flow_variables
                )
            except Exception as e:
                self.logger.error(
                    f"SET_VARIABLE '{node.id}': template rendering failed for '{assignment.variable}': {str(e)}",
                    node_id=node.id,
                    variable=assignment.variable,
                    error=str(e)
                )
                rendered_value = assignment.value  # fall back to unrendered template string
            var_type = self._get_variable_type(assignment.variable, context)
            try:
                converted = self.validation_system.convert_type(rendered_value, var_type)
            except InputValidationError:
                # Fall back to storing the rendered string — don't crash the session
                self.logger.warning(
                    f"SET_VARIABLE '{node.id}': type conversion failed for '{assignment.variable}' "
                    f"(target type: {var_type}), storing rendered value as string",
                    node_id=node.id,
                    variable=assignment.variable,
                    target_type=var_type
                )
                converted = rendered_value
            context[assignment.variable] = converted

            self.logger.debug(
                f"SET_VARIABLE '{node.id}': set {assignment.variable} = {converted!r}",
                node_id=node.id,
                variable=assignment.variable
            )

        # Check if node is terminal (has no routes)
        terminal = self.check_terminal(node, context)
        if terminal:
            return terminal

        # Evaluate routes
        next_node = self.evaluate_routes(node.routes, context, node.type)

        if next_node is None:
            self.raise_no_matching_route(node)

        self.logger.debug(
            f"SET_VARIABLE routing to {next_node}",
            next_node=next_node
        )

        return ProcessResult(
            next_node=next_node,
            context=context
        )

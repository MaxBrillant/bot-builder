import type { NodeType, NodeConfig, Route, FlowNode } from "./types";

/**
 * Represents a route condition option that can be displayed in a dropdown
 */
export interface RouteConditionOption {
  value: string; // The actual condition value (e.g., "selection == 1", "success", "true")
  label: string; // User-friendly display label
  description?: string; // Optional tooltip/help text
  isDefault?: boolean; // Whether this is the default catch-all condition
}

/**
 * Determines whether a node type uses dropdown or text input for route conditions
 */
export function getConditionInputType(nodeType: NodeType): "dropdown" | "text" {
  switch (nodeType) {
    case "MENU":
    case "API_ACTION":
    case "PROMPT":
    case "TEXT":
      return "dropdown";
    case "LOGIC_EXPRESSION":
      return "text";
    default:
      return "text";
  }
}

/**
 * Gets the available route condition options for a given node type and configuration
 */
export function getRouteConditionOptions(
  nodeType: NodeType,
  nodeConfig?: NodeConfig
): RouteConditionOption[] {
  switch (nodeType) {
    case "MENU": {
      if (!nodeConfig) {
        return [
          {
            value: "true",
            label: "Next",
            description: "Continue to next node",
            isDefault: true,
          },
        ];
      }

      const menuConfig = nodeConfig as any;

      // DYNAMIC menus: Only allow "Next" route
      // Users must add LOGIC_EXPRESSION nodes for conditional routing
      if (menuConfig.source_type === "DYNAMIC") {
        return [
          {
            value: "true",
            label: "Next",
            description:
              "Continue to next node (use Logic Expression for conditional routing)",
            isDefault: true,
          },
        ];
      }

      // STATIC menus: Provide numbered options (no default catch-all)
      // Routes are auto-generated based on menu options
      const options: RouteConditionOption[] = [];
      const staticOptions = menuConfig.static_options || [];

      // Add options for each menu item
      staticOptions.forEach(
        (option: { label: string }, index: number) => {
          options.push({
            value: `selection == ${index + 1}`,
            label: `Option ${index + 1}: ${option.label}`,
            description: `User selects "${option.label}"`,
          });
        }
      );

      return options;
    }

    case "API_ACTION": {
      // Routes are auto-generated: success and error (no default catch-all)
      return [
        {
          value: "success",
          label: "Success",
          description: "API call succeeded",
        },
        {
          value: "error",
          label: "Error",
          description: "API call failed",
        },
      ];
    }

    case "PROMPT":
    case "TEXT": {
      return [
        {
          value: "true",
          label: "Next",
          description: "Continue to next node",
          isDefault: true,
        },
      ];
    }

    case "LOGIC_EXPRESSION": {
      // Logic expressions use text input, but we provide some common examples
      return [
        {
          value: "true",
          label: "Default",
          description: "Fallback when nothing else matches",
          isDefault: true,
        },
      ];
    }

    default:
      return [
        {
          value: "true",
          label: "Next",
          isDefault: true,
        },
      ];
  }
}

/**
 * Gets the unassigned route conditions for a node
 * Useful for determining what conditions are still available when adding new routes
 */
export function getUnassignedConditions(
  node: FlowNode,
  existingRoutes: Route[]
): RouteConditionOption[] {
  const allOptions = getRouteConditionOptions(node.type, node.config);
  const assignedConditions = new Set(
    existingRoutes.map((r) => r.condition.trim().toLowerCase())
  );

  return allOptions.filter(
    (opt) => !assignedConditions.has(opt.value.trim().toLowerCase())
  );
}

/**
 * Gets the default condition for a node type
 * Prefers first unassigned condition, falls back to first option (for route overtaking)
 */
export function getDefaultCondition(
  node: FlowNode,
  existingRoutes: Route[]
): string {
  const unassigned = getUnassignedConditions(node, existingRoutes);

  // Return first unassigned condition
  if (unassigned.length > 0) {
    return unassigned[0].value;
  }

  // All conditions assigned - return first option to allow route overtaking
  const allOptions = getRouteConditionOptions(node.type, node.config);
  if (allOptions.length > 0) {
    return allOptions[0].value;
  }

  return "";
}

/**
 * Validates if a condition is valid for a given node type
 */
export function isValidCondition(
  nodeType: NodeType,
  condition: string,
  nodeConfig?: NodeConfig
): boolean {
  const options = getRouteConditionOptions(nodeType, nodeConfig);

  // For dropdown types, condition must match one of the options
  if (getConditionInputType(nodeType) === "dropdown") {
    return options.some((opt) => opt.value === condition);
  }

  // For text input types (LOGIC_EXPRESSION), allow any non-empty string
  return condition.trim().length > 0;
}

/**
 * Gets a user-friendly label for a condition value
 */
export function getConditionLabel(
  nodeType: NodeType,
  condition: string,
  nodeConfig?: NodeConfig
): string {
  const options = getRouteConditionOptions(nodeType, nodeConfig);
  const option = options.find((opt) => opt.value === condition);

  if (option) {
    return option.label;
  }

  // For LOGIC_EXPRESSION, format the condition nicely
  if (nodeType === "LOGIC_EXPRESSION") {
    return formatLogicCondition(condition);
  }

  // For other custom conditions, return the condition itself
  return condition;
}

/**
 * Human-readable labels for comparison operators
 * Must match labels in ConditionRow.tsx for consistency
 */
const OPERATOR_LABELS: Record<string, string> = {
  "==": "is equal to",
  "!=": "is not equal to",
  ">": "is more than",
  "<": "is less than",
  ">=": "is at least",
  "<=": "is at most",
};

/**
 * Human-readable labels for boolean methods
 * Must match labels in expressionBuilderTypes.ts CONTEXT_CONFIGS for consistency
 */
const BOOLEAN_METHOD_LABELS: Record<string, string> = {
  "input.isAlpha()": "Input contains only letters",
  "input.isNumeric()": "Input is a number",
  "input.isDigit()": "Input contains only digits",
};

/**
 * Format a logic expression condition for display
 * Converts expressions like "context.age > 18" to "age greater than 18"
 */
function formatLogicCondition(condition: string): string {
  const trimmed = condition.trim();

  if (!trimmed) {
    return "";
  }

  // Split by logical operators while preserving them
  const parts: string[] = [];
  let current = "";
  let i = 0;

  while (i < trimmed.length) {
    if (trimmed[i] === "&" && trimmed[i + 1] === "&") {
      if (current.trim()) {
        parts.push(formatSingleCondition(current.trim()));
      }
      parts.push("AND");
      current = "";
      i += 2;
      continue;
    }
    if (trimmed[i] === "|" && trimmed[i + 1] === "|") {
      if (current.trim()) {
        parts.push(formatSingleCondition(current.trim()));
      }
      parts.push("OR");
      current = "";
      i += 2;
      continue;
    }
    current += trimmed[i];
    i++;
  }

  if (current.trim()) {
    parts.push(formatSingleCondition(current.trim()));
  }

  return parts.join(" ");
}

/**
 * Format a single condition (no logical operators)
 */
function formatSingleCondition(text: string): string {
  // Check for boolean methods
  if (BOOLEAN_METHOD_LABELS[text]) {
    return BOOLEAN_METHOD_LABELS[text];
  }

  // Parse comparison operators (check longer ones first)
  const operators = [">=", "<=", "==", "!=", ">", "<"];
  for (const op of operators) {
    const index = text.indexOf(op);
    if (index !== -1) {
      const left = text.substring(0, index).trim();
      const right = text.substring(index + op.length).trim();

      const leftFormatted = formatOperand(left);
      const rightFormatted = formatValue(right);
      const opLabel = OPERATOR_LABELS[op] || op;

      return `${leftFormatted} ${opLabel} ${rightFormatted}`;
    }
  }

  // No operator - treat as variable name
  return formatOperand(text);
}

/**
 * Human-readable labels for known properties
 * Must match labels in expressionBuilderTypes.ts CONTEXT_CONFIGS for consistency
 */
const PROPERTY_LABELS: Record<string, string> = {
  "input.length": "Input length",
  "response.status": "Response status code",
  "response.body.status": "Response body status",
  "response.body.data": "Response body data",
};

/**
 * Format a left operand (variable or property)
 */
function formatOperand(text: string): string {
  // Check for known properties first
  if (PROPERTY_LABELS[text]) {
    return PROPERTY_LABELS[text];
  }

  // Strip context. prefix for variables
  if (text.startsWith("context.")) {
    return text.replace(/^context\./, "");
  }

  // For other input/response properties, keep as-is but clean up
  return text;
}

/**
 * Format a right-side value
 */
function formatValue(text: string): string {
  // Remove quotes from strings
  if ((text.startsWith('"') && text.endsWith('"')) ||
      (text.startsWith("'") && text.endsWith("'"))) {
    return text.slice(1, -1);
  }
  // Format context variables
  if (text.startsWith("context.")) {
    return text.replace(/^context\./, "");
  }
  return text;
}

/**
 * Determines if a node is a branching node (supports multiple conditional routes).
 * MENU, API_ACTION, and LOGIC_EXPRESSION are branching nodes,
 * EXCEPT for DYNAMIC menus which only have a single "true" route.
 */
export function isBranchingNode(
  nodeType: NodeType,
  nodeConfig?: NodeConfig
): boolean {
  // Dynamic menus only have a single "true" route - not a branching node
  if (nodeType === "MENU") {
    const menuConfig = nodeConfig as any;
    if (menuConfig?.source_type === "DYNAMIC") {
      return false;
    }
  }

  return ["MENU", "API_ACTION", "LOGIC_EXPRESSION"].includes(nodeType);
}

/**
 * Gets the maximum number of routes allowed for a node type
 */
export function getMaxRoutes(
  nodeType: NodeType,
  nodeConfig?: NodeConfig
): number {
  switch (nodeType) {
    case "MENU": {
      const menuConfig = nodeConfig as any;

      // DYNAMIC menus: Only 1 route (Next)
      if (menuConfig?.source_type === "DYNAMIC") {
        return 1;
      }

      // STATIC menus: number of options
      const staticOptions = menuConfig?.static_options || [];
      return staticOptions.length;
    }
    case "API_ACTION": {
      // success and error
      return 2;
    }
    case "LOGIC_EXPRESSION": {
      // Up to system max (8)
      return 8;
    }
    case "PROMPT":
    case "TEXT": {
      // Single route only
      return 1;
    }
    default:
      return 1;
  }
}

/**
 * Gets the priority of a route condition for sorting
 * Lower numbers = higher priority (evaluated first)
 * Higher numbers = lower priority (evaluated last)
 */
export function getConditionPriority(
  condition: string,
  nodeType: NodeType
): number {
  // Catch-all "true" always goes last
  if (condition.trim().toLowerCase() === "true") {
    return 1000;
  }

  switch (nodeType) {
    case "MENU": {
      // Extract selection number from "selection == N" pattern
      const match = condition.match(/selection\s*==\s*(\d+)/);
      if (match) {
        // Selection routes ordered by number (1, 2, 3, etc.)
        return parseInt(match[1], 10);
      }
      // Other menu conditions
      return 500;
    }

    case "API_ACTION": {
      // "success" before "error" before others
      if (condition === "success") return 1;
      if (condition === "error") return 2;
      return 500;
    }

    case "LOGIC_EXPRESSION": {
      // Custom expressions maintain their order (medium priority)
      return 500;
    }

    default:
      // Default: medium priority
      return 500;
  }
}

/**
 * Sorts routes automatically based on condition priority
 * Specific conditions first, catch-all "true" last
 * Returns a new sorted array without mutating the original
 */
export function sortRoutes(routes: Route[], nodeType: NodeType): Route[] {
  return [...routes].sort((a, b) => {
    const priorityA = getConditionPriority(a.condition, nodeType);
    const priorityB = getConditionPriority(b.condition, nodeType);

    // Lower priority number = evaluated first
    return priorityA - priorityB;
  });
}

/**
 * Checks if a route is a catch-all/default route
 */
export function isFallbackRoute(condition: string): boolean {
  return condition.trim().toLowerCase() === "true";
}

/**
 * Determines if a node can accept another route based on its type and current routes.
 * Used by:
 * - Stub visibility (whether to show the "add route" stub)
 * - insertNodeInFlow (whether to allow adding a new branch)
 * - connectRouteToExistingNode (whether to allow connecting to existing node)
 *
 * @param node - The node to check
 * @returns true if a new route can be added, false otherwise
 */
export function canAddRoute(node: FlowNode): boolean {
  // LOGIC_EXPRESSION: Allow up to (MAX - 1) non-"true" routes, reserving 1 slot for fallback
  if (node.type === "LOGIC_EXPRESSION") {
    const nonTrueRouteCount =
      node.routes?.filter(
        (route) => route.condition.trim().toLowerCase() !== "true"
      ).length || 0;
    return nonTrueRouteCount < 7; // MAX_ROUTES_PER_NODE (8) - 1 for fallback
  }

  // For other nodes: count routes vs maxRoutes
  const maxRoutes = getMaxRoutes(node.type, node.config);
  const currentRoutes = node.routes?.length || 0;
  return currentRoutes < maxRoutes;
}

/**
 * Gets a descriptive label for route type (for visual indicators)
 */
export function getRouteTypeLabel(
  condition: string,
  nodeType: NodeType
): string {
  if (isFallbackRoute(condition)) {
    return "Default";
  }

  switch (nodeType) {
    case "MENU":
      if (condition.match(/selection\s*==\s*\d+/)) {
        return "Specific";
      }
      return "Condition";

    case "API_ACTION":
      if (condition === "success" || condition === "error") {
        return "Specific";
      }
      return "Condition";

    case "LOGIC_EXPRESSION":
      return "Expression";

    default:
      return "Condition";
  }
}


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
    case "MESSAGE":
      return "dropdown";
    case "LOGIC_EXPRESSION":
      return "text";
    case "END":
      return "dropdown"; // Not used, but consistent
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
    case "MESSAGE": {
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
          description: "Default catch-all route",
          isDefault: true,
        },
        {
          value: "false",
          label: "False (Never)",
          description: "Expression evaluates to false",
        },
      ];
    }

    case "END": {
      return []; // End nodes have no routes
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
  const assignedConditions = new Set(existingRoutes.map((r) => r.condition));

  return allOptions.filter((opt) => !assignedConditions.has(opt.value));
}

/**
 * Gets the default condition for a node type
 * This is typically the first unassigned condition, or "true" if none available
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

  // If all conditions are assigned, return "true" as default
  return "true";
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

  // For custom conditions (e.g., logic expressions), return the condition itself
  return condition;
}

/**
 * Determines if a node type supports multiple routes
 */
export function supportsMultipleRoutes(nodeType: NodeType): boolean {
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
    case "MESSAGE": {
      // Single route only
      return 1;
    }
    case "END": {
      return 0;
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


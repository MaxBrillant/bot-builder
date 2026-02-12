/**
 * Type definitions for the Expression Builder system
 *
 * The Expression Builder provides a visual, form-based interface for creating
 * logical expressions that are serialized to text for backend consumption.
 */

// Context types determine what options are available in the builder
export type ExpressionContext =
  | "validation_expression"  // Used in PROMPT nodes for input validation
  | "success_expression"     // Used in API_ACTION nodes for response validation
  | "route_logic";           // Used in LOGIC_EXPRESSION nodes for routing conditions

// Comparison operators supported by the backend
export type ComparisonOperator = "==" | "!=" | ">" | "<" | ">=" | "<=";

// Logical operators for combining conditions
export type LogicalOperator = "AND" | "OR";

/**
 * Root structure representing a complete expression
 * Consists of an array of conditions joined by logical operators
 */
export interface ExpressionDefinition {
  conditions: Condition[];
}

/**
 * A single condition in the expression
 * Can be a boolean method check or a comparison between two operands
 */
export interface Condition {
  left: LeftOperand;
  operator: ComparisonOperator;
  right: RightOperand;
  logicalOperator?: LogicalOperator; // How this connects to the next condition
}

/**
 * Left side of a condition
 * Can be a method call, property access, or variable reference
 */
export interface LeftOperand {
  type: "method" | "property" | "variable";
  path: string; // e.g., "input.isAlpha()", "input.length", "context.age", "response.status"
}

/**
 * Right side of a condition
 * Can be a literal value or a variable reference
 */
export interface RightOperand {
  type: "literal" | "variable";

  // For literal values
  literalType?: "string" | "number" | "boolean" | "null";
  literalValue?: any;

  // For variable references
  variablePath?: string; // e.g., "context.max_length"
}

/**
 * Boolean methods that don't require operator/right side in UI
 * These are rendered as standalone checks
 */
export const BOOLEAN_METHODS = [
  "input.isAlpha()",
  "input.isNumeric()",
  "input.isDigit()",
] as const;

/**
 * Check if a left operand path is a boolean method
 */
export function isBooleanMethod(path: string): boolean {
  return BOOLEAN_METHODS.includes(path as any);
}

/**
 * Configuration for each expression context
 * Defines what options are available in the left operand dropdown
 */
export interface ContextConfig {
  leftOptions: LeftOption[];
}

export interface LeftOption {
  value: string;           // The actual path value
  label: string;           // Display text
  type: "method" | "property" | "variable" | "separator" | "custom";
  group?: string;          // Optional grouping for organization
}

/**
 * Context-specific configurations
 */
export const CONTEXT_CONFIGS: Record<ExpressionContext, ContextConfig> = {
  validation_expression: {
    leftOptions: [
      { value: "input.isAlpha()", label: "Input contains only letters", type: "method", group: "Input Methods" },
      { value: "input.isNumeric()", label: "Input is a number", type: "method", group: "Input Methods" },
      { value: "input.isDigit()", label: "Input contains only digits", type: "method", group: "Input Methods" },
      { value: "__separator__", label: "", type: "separator" },
      { value: "input.length", label: "Input length", type: "property", group: "Input Properties" },
      { value: "__variables__", label: "Variables", type: "custom" },
      { value: "__custom__", label: "Custom field...", type: "custom" },
    ],
  },
  success_expression: {
    leftOptions: [
      { value: "response.status", label: "Response status code", type: "property", group: "Response" },
      { value: "response.body.status", label: "Response body status", type: "property", group: "Response Body" },
      { value: "response.body.data", label: "Response body data", type: "property", group: "Response Body" },
      { value: "__custom__", label: "Custom field...", type: "custom" },
    ],
  },
  route_logic: {
    leftOptions: [
      { value: "__variables__", label: "Variables", type: "custom" },
      { value: "__custom__", label: "Custom field...", type: "custom" },
    ],
  },
};

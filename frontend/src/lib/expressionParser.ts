/**
 * Expression Parser
 *
 * Converts text expressions into structured ExpressionDefinition format
 * for use in the visual Expression Builder
 */

import type {
  ExpressionDefinition,
  Condition,
  LeftOperand,
  RightOperand,
  ComparisonOperator,
  LogicalOperator,
} from "./expressionBuilderTypes";
import { BOOLEAN_METHODS } from "./expressionBuilderTypes";

/**
 * Parse a text expression into structured format
 *
 * @param text - Expression text (e.g., "context.age > 18 && input.isAlpha()")
 * @returns Structured expression definition
 */
export function parseExpression(text: string): ExpressionDefinition {
  if (!text || !text.trim()) {
    return { conditions: [] };
  }

  try {
    const conditions: Condition[] = [];
    const parts = splitByLogicalOperators(text);

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];

      if (part.type === "condition") {
        const condition = parseCondition(part.text);

        // Look ahead for logical operator
        if (i + 1 < parts.length && parts[i + 1].type === "operator") {
          condition.logicalOperator = parts[i + 1].text as LogicalOperator;
        }

        conditions.push(condition);
      }
    }

    return { conditions };
  } catch (error) {
    console.error("Failed to parse expression:", error);
    // Return empty on parse failure - component will show empty builder
    return { conditions: [] };
  }
}

/**
 * Split expression by logical operators while preserving them
 *
 * "a && b || c" => [
 *   { type: 'condition', text: 'a' },
 *   { type: 'operator', text: 'AND' },
 *   { type: 'condition', text: 'b' },
 *   { type: 'operator', text: 'OR' },
 *   { type: 'condition', text: 'c' }
 * ]
 */
function splitByLogicalOperators(text: string): Array<{ type: "condition" | "operator"; text: string }> {
  const result: Array<{ type: "condition" | "operator"; text: string }> = [];
  let current = "";
  let i = 0;

  while (i < text.length) {
    // Check for &&
    if (text[i] === "&" && text[i + 1] === "&") {
      if (current.trim()) {
        result.push({ type: "condition", text: current.trim() });
        current = "";
      }
      result.push({ type: "operator", text: "AND" });
      i += 2;
      continue;
    }

    // Check for ||
    if (text[i] === "|" && text[i + 1] === "|") {
      if (current.trim()) {
        result.push({ type: "condition", text: current.trim() });
        current = "";
      }
      result.push({ type: "operator", text: "OR" });
      i += 2;
      continue;
    }

    current += text[i];
    i++;
  }

  // Add remaining
  if (current.trim()) {
    result.push({ type: "condition", text: current.trim() });
  }

  return result;
}

/**
 * Parse a single condition
 *
 * Examples:
 *   "input.isAlpha()" => boolean method check
 *   "context.age > 18" => comparison
 *   "response.status == 200" => comparison
 */
function parseCondition(text: string): Condition {
  const trimmed = text.trim();

  // Check if it's a boolean method (standalone)
  if (BOOLEAN_METHODS.includes(trimmed as any)) {
    return {
      left: { type: "method", path: trimmed },
      operator: "==",
      right: { type: "literal", literalType: "boolean", literalValue: true },
    };
  }

  // Check if it's a variable truthy check (no operator)
  // e.g., "context.verified" with no comparison operator
  if (!hasComparisonOperator(trimmed)) {
    return {
      left: parseLeftOperand(trimmed),
      operator: "==",
      right: { type: "literal", literalType: "boolean", literalValue: true },
    };
  }

  // Parse as comparison
  return parseComparison(trimmed);
}

/**
 * Check if text contains a comparison operator
 */
function hasComparisonOperator(text: string): boolean {
  const operators = ["==", "!=", ">=", "<=", ">", "<"];
  return operators.some((op) => text.includes(op));
}

/**
 * Parse a comparison expression
 *
 * "context.age > 18" => { left: context.age, operator: >, right: 18 }
 */
function parseComparison(text: string): Condition {
  // Find operator (order matters - check longer operators first to avoid partial matches)
  const operators: ComparisonOperator[] = [">=", "<=", "==", "!=", ">", "<"];

  for (const op of operators) {
    const index = text.indexOf(op);
    if (index !== -1) {
      const leftText = text.substring(0, index).trim();
      const rightText = text.substring(index + op.length).trim();

      return {
        left: parseLeftOperand(leftText),
        operator: op,
        right: parseRightOperand(rightText),
      };
    }
  }

  // Fallback: treat as truthy check
  return {
    left: parseLeftOperand(text),
    operator: "==",
    right: { type: "literal", literalType: "boolean", literalValue: true },
  };
}

/**
 * Parse left side operand
 *
 * Can be: method, property, or variable
 */
function parseLeftOperand(text: string): LeftOperand {
  const trimmed = text.trim();

  // Check for method call (ends with ())
  if (trimmed.endsWith("()")) {
    return { type: "method", path: trimmed };
  }

  // Check for property (input.length, response.status, etc.)
  if (trimmed.startsWith("input.") || trimmed.startsWith("response.")) {
    if (trimmed === "input.length" || trimmed.startsWith("response.")) {
      return { type: "property", path: trimmed };
    }
  }

  // Check for context.variable - strip the "context." prefix
  if (trimmed.startsWith("context.")) {
    const varName = trimmed.replace("context.", "");
    return { type: "variable", path: varName };
  }

  // Default: variable (no prefix)
  return { type: "variable", path: trimmed };
}

/**
 * Parse right side operand
 *
 * Can be: literal value or variable reference
 * Variables are converted to {{variable}} template syntax
 */
function parseRightOperand(text: string): RightOperand {
  const trimmed = text.trim();

  // Check for variable reference - convert to {{variable}} syntax
  if (trimmed.startsWith("context.")) {
    const varName = trimmed.replace("context.", "");
    return {
      type: "literal",
      literalType: "string",
      literalValue: `{{${varName}}}`,
    };
  }

  if (trimmed.startsWith("response.")) {
    return {
      type: "literal",
      literalType: "string",
      literalValue: `{{${trimmed}}}`,
    };
  }

  // Check for null
  if (trimmed === "null" || trimmed === "None") {
    return { type: "literal", literalType: "string", literalValue: "null" };
  }

  // Check for boolean literals - convert to strings
  if (trimmed === "true" || trimmed === "True") {
    return { type: "literal", literalType: "string", literalValue: "true" };
  }
  if (trimmed === "false" || trimmed === "False") {
    return { type: "literal", literalType: "string", literalValue: "false" };
  }

  // Check for string literal (quoted) - remove quotes
  if (
    (trimmed.startsWith('"') && trimmed.endsWith('"')) ||
    (trimmed.startsWith("'") && trimmed.endsWith("'"))
  ) {
    return {
      type: "literal",
      literalType: "string",
      literalValue: trimmed.slice(1, -1), // Remove quotes
    };
  }

  // Check for number - keep as string
  const num = Number(trimmed);
  if (!isNaN(num) && trimmed !== "") {
    return { type: "literal", literalType: "string", literalValue: trimmed };
  }

  // Default: treat as string literal (unquoted)
  return { type: "literal", literalType: "string", literalValue: trimmed };
}

/**
 * Expression Serializer
 *
 * Converts structured ExpressionDefinition back to text expressions
 * that the backend can evaluate
 */

import type {
  ExpressionDefinition,
  Condition,
  LeftOperand,
  RightOperand,
} from "./expressionBuilderTypes";
import { isBooleanMethod } from "./expressionBuilderTypes";

/**
 * Serialize structured expression to text
 *
 * @param expression - Structured expression definition
 * @returns Text expression for backend
 */
export function serializeExpression(expression: ExpressionDefinition): string {
  if (!expression.conditions || expression.conditions.length === 0) {
    return "";
  }

  // Filter out incomplete conditions (empty left path or empty right value for non-boolean methods)
  const validConditions = expression.conditions.filter((condition) => {
    // Must have left operand
    if (!condition.left.path || condition.left.path.trim() === "") {
      return false;
    }
    // Boolean methods don't need right operand
    if (condition.left.path.endsWith("()")) {
      return true;
    }
    // Non-boolean conditions must have right operand value
    const rightValue = condition.right?.literalValue;
    if (rightValue === undefined || rightValue === null || String(rightValue).trim() === "") {
      return false;
    }
    return true;
  });

  if (validConditions.length === 0) {
    return "";
  }

  return validConditions
    .map((condition, index) => {
      const conditionText = serializeCondition(condition);

      // Add logical operator if not last condition
      // Default to AND if logicalOperator is not set (matches UI default)
      if (index < validConditions.length - 1) {
        const logicalOp = condition.logicalOperator || "AND";
        const operator = logicalOp === "AND" ? "&&" : "||";
        return `${conditionText} ${operator}`;
      }

      return conditionText;
    })
    .join(" ");
}

/**
 * Serialize a single condition
 *
 * Boolean methods are serialized as standalone (e.g., "input.isAlpha()")
 * Other conditions are serialized as comparisons (e.g., "context.age > 18")
 */
function serializeCondition(condition: Condition): string {
  const left = serializeLeftOperand(condition.left);

  // Boolean methods don't need operator and right side
  if (isBooleanMethod(condition.left.path)) {
    return left;
  }

  // Regular comparison
  const right = serializeRightOperand(condition.right);
  return `${left} ${condition.operator} ${right}`;
}

/**
 * Serialize left operand
 */
function serializeLeftOperand(operand: LeftOperand): string {
  // If it's a variable (just the name), add "context." prefix
  if (
    operand.type === "variable" &&
    !operand.path.startsWith("context.") &&
    !operand.path.startsWith("response.") &&
    !operand.path.startsWith("input.")
  ) {
    return `context.${operand.path}`;
  }
  return operand.path;
}

/**
 * Serialize right operand
 * Handles template variables {{variable}} and converts them to context.variable
 */
function serializeRightOperand(operand: RightOperand): string {
  if (operand.type === "variable") {
    return operand.variablePath || "";
  }

  // Literal value - check if it contains {{variable}} syntax
  const value = String(operand.literalValue || "");

  // Check for template variable syntax: {{variable}}
  const templateMatch = value.match(/^\{\{(.+?)\}\}$/);
  if (templateMatch) {
    const varName = templateMatch[1].trim();
    // If it's just a variable name (no dots), add context. prefix
    if (!varName.includes(".")) {
      return `context.${varName}`;
    }
    // If it already has a prefix (response.field), keep as-is
    return varName;
  }

  // Check if it looks like a number
  const num = Number(value);
  if (!isNaN(num) && value !== "" && value.trim() !== "") {
    return String(num);
  }

  // Check for boolean literals
  if (value.toLowerCase() === "true") {
    return "true";
  }
  if (value.toLowerCase() === "false") {
    return "false";
  }

  // Check for null
  if (value.toLowerCase() === "null") {
    return "null";
  }

  // Default: treat as string literal (escape internal quotes)
  const escaped = value.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
  return `"${escaped}"`;
}

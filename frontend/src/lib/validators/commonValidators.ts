import { RESERVED_KEYWORDS } from "../constants";

/**
 * Validates if a string is not empty after trimming
 */
export function isNonEmptyString(value: string | undefined | null): boolean {
  return typeof value === "string" && value.trim().length > 0;
}

/**
 * Validates string length
 */
export function isWithinMaxLength(value: string, maxLength: number): boolean {
  return value.length <= maxLength;
}

/**
 * Checks if a variable name is a reserved keyword
 */
export function isReservedKeyword(name: string): boolean {
  return RESERVED_KEYWORDS.includes(name.toLowerCase());
}

/**
 * Validates variable name format (alphanumeric and underscores, must start with letter or underscore)
 * Also checks against reserved keywords
 */
export function isValidVariableName(name: string): boolean {
  // Check format
  if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(name)) {
    return false;
  }
  // Check reserved keywords
  if (isReservedKeyword(name)) {
    return false;
  }
  return true;
}

/**
 * Gets error message for invalid variable name
 */
export function getVariableNameError(name: string): string | null {
  if (!name || name.trim() === "") {
    return "Variable name is required";
  }
  if (isReservedKeyword(name)) {
    return `Variable name '${name}' is reserved. Reserved keywords: ${RESERVED_KEYWORDS.join(", ")}`;
  }
  if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(name)) {
    return "Variable name must start with letter or underscore, contain only letters, numbers, and underscores";
  }
  return null;
}

/**
 * Validates URL format (basic check for http:// or https://)
 */
export function isValidURL(url: string): boolean {
  return /^https?:\/\/.+/.test(url);
}

/**
 * Validates template syntax (checks for balanced {{ }})
 */
export function hasValidTemplateSyntax(template: string): boolean {
  const openCount = (template.match(/\{\{/g) || []).length;
  const closeCount = (template.match(/\}\}/g) || []).length;
  return openCount === closeCount;
}

/**
 * Extracts template variables from a string
 */
export function extractTemplateVariables(template: string): string[] {
  const matches = template.match(/\{\{([^}]+)\}\}/g);
  if (!matches) return [];
  return matches.map((match) => match.slice(2, -2).trim());
}

/**
 * Validates that all template variables are defined
 */
export function areTemplateVariablesDefined(
  template: string,
  availableVariables: string[]
): { isValid: boolean; undefinedVars: string[] } {
  const usedVars = extractTemplateVariables(template);
  const undefinedVars = usedVars.filter(
    (varName) => !availableVariables.includes(varName)
  );
  return {
    isValid: undefinedVars.length === 0,
    undefinedVars,
  };
}

/**
 * Validates HTTP method
 */
export function isValidHTTPMethod(method: string): boolean {
  return ["GET", "POST", "PUT", "DELETE", "PATCH"].includes(method);
}

/**
 * Validates validation type
 */
export function isValidValidationType(type: string): boolean {
  return ["REGEX", "EXPRESSION"].includes(type);
}

/**
 * Validates menu source type
 */
export function isValidMenuSourceType(type: string): boolean {
  return ["STATIC", "DYNAMIC"].includes(type);
}

/**
 * Helper to create error message for max length validation
 */
export function getMaxLengthError(
  fieldName: string,
  maxLength: number
): string {
  return `${fieldName} must be ${maxLength} characters or less`;
}

/**
 * Helper to create error message for required field
 */
export function getRequiredFieldError(fieldName: string): string {
  return `${fieldName} is required`;
}

/**
 * Validates Success Expression syntax for API_ACTION nodes
 * Allowed: response.body.*, response.status, logical operators, comparisons
 */
export function validateSuccessExpression(expression: string): {
  isValid: boolean;
  error?: string;
} {
  if (!expression || expression.trim() === "") {
    return { isValid: true }; // Empty is valid (optional)
  }

  const trimmed = expression.trim();


  // Check for disallowed patterns
  if (trimmed.includes("context.")) {
    return {
      isValid: false,
      error:
        "Success expressions cannot access context variables. Use response.body.* or response.status instead.",
    };
  }

  if (trimmed.includes("input.")) {
    return {
      isValid: false,
      error:
        "Success expressions cannot use input methods. Use response.body.* or response.status instead.",
    };
  }

  // Check if it uses response. prefix
  if (!trimmed.includes("response.")) {
    // Allow simple keywords like status codes or boolean values
    if (!/^(true|false|\d+)$/.test(trimmed)) {
      return {
        isValid: false,
        error:
          "Success expressions must reference response.body.* or response.status.",
      };
    }
  }

  // Validate response.* usage
  if (trimmed.includes("response.")) {
    if (
      !trimmed.includes("response.body.") &&
      !trimmed.includes("response.status")
    ) {
      return {
        isValid: false,
        error:
          "Use response.body.field for body data or response.status for status code.",
      };
    }
  }

  return { isValid: true };
}

/**
 * Validates Route Condition syntax based on node type
 * Different node types allow different context variables
 */
export function validateRouteCondition(
  condition: string,
  nodeType?: string
): { isValid: boolean; error?: string } {
  if (!condition || condition.trim() === "") {
    return { isValid: false, error: "Condition is required" };
  }

  const trimmed = condition.trim().toLowerCase();

  // Check for standalone functions (parseInt, toUpperCase, etc.)
  const functionsCheck = validateExpressionFunctions(condition);
  if (!functionsCheck.isValid) {
    return functionsCheck;
  }

  // Keywords are always valid
  if (["true", "success", "error"].includes(trimmed)) {
    return { isValid: true };
  }

  // Check for common type mismatch: comparing selection to string
  if (nodeType === "MENU" && /selection\s*==\s*["']/.test(condition)) {
    return {
      isValid: false,
      error: 'Menu selection is a number. Use selection == 1 without quotes (not "1" with quotes).',
    };
  }

  // Check for disallowed patterns based on node type
  if (nodeType === "API_ACTION") {
    // API_ACTION should only use: response.*, context.*, or already validated keywords
    const hasResponseVar = condition.includes("response.");
    const hasContextVar = condition.includes("context.");
    const hasApiResult = condition.includes("_api_result");

    if (!hasResponseVar && !hasContextVar && !hasApiResult) {
      return {
        isValid: false,
        error:
          "API_ACTION routes must use response.* variables (e.g., response.body.status), context.*, or keywords (success/error).",
      };
    }

    // Disallow selection in API routes
    if (condition.includes("selection")) {
      return {
        isValid: false,
        error:
          '"selection" is only for MENU routes. Use response.* or context.* variables instead.',
      };
    }
  }

  if (nodeType === "MENU") {
    // MENU should use selection
    if (
      !condition.includes("selection") &&
      trimmed !== "true"
    ) {
      return {
        isValid: false,
        error:
          'Menu routes should use "selection" (e.g., selection == 1) or "true" for fallback.',
      };
    }
  }

  // Warn about input.* in route conditions (not typically valid)
  if (condition.includes("input.")) {
    return {
      isValid: false,
      error:
        "Route conditions cannot use input methods. Use context.* variables instead.",
    };
  }

  return { isValid: true };
}

/**
 * Validates Validation Expression syntax for PROMPT nodes
 * Allowed: input.*, context.*, logical operators, comparisons
 */
export function validateValidationExpression(expression: string): {
  isValid: boolean;
  error?: string;
} {
  if (!expression || expression.trim() === "") {
    return { isValid: true }; // Empty is valid (optional)
  }

  const trimmed = expression.trim();

  // Check for standalone functions (parseInt, toUpperCase, etc.)
  const functionsCheck = validateExpressionFunctions(trimmed);
  if (!functionsCheck.isValid) {
    return functionsCheck;
  }

  // Check for disallowed patterns
  if (trimmed.includes("response.")) {
    return {
      isValid: false,
      error:
        "Validation expressions cannot access response data. Use input.* methods or context.* variables.",
    };
  }

  if (trimmed.includes("selection")) {
    return {
      isValid: false,
      error:
        "Validation expressions cannot use 'selection'. This is for menu routing only.",
    };
  }

  // Must use input.* or context.*
  if (!trimmed.includes("input.") && !trimmed.includes("context.")) {
    return {
      isValid: false,
      error:
        "Validation expressions must use input methods (input.isAlpha(), input.length, etc.) or context variables.",
    };
  }

  // WHITELIST VALIDATION: Check that all 'input' usage follows allowed patterns
  // Allowed patterns: input.isAlpha(), input.isNumeric(), input.isDigit(), input.length
  const allowedInputPatterns = [
    /\binput\.isAlpha\(\)/,
    /\binput\.isNumeric\(\)/,
    /\binput\.isDigit\(\)/,
    /\binput\.length\b/,
  ];

  // Find all occurrences of 'input' as a word boundary
  const inputPattern = /\binput\b/g;
  const inputMatches = trimmed.match(inputPattern);

  if (inputMatches) {
    // Replace all valid patterns with a placeholder to check what remains
    let testExpression = trimmed;
    allowedInputPatterns.forEach((pattern) => {
      testExpression = testExpression.replace(pattern, "VALID_INPUT");
    });

    // If 'input' still exists as a word after removing valid patterns, it's invalid
    if (/\binput\b/.test(testExpression)) {
      return {
        isValid: false,
        error:
          "Direct comparisons with 'input' are not supported. Use 'input.length' for length checks, 'input.isDigit()' for type checks, or use REGEX validation type instead. For value range checks, use a LOGIC_EXPRESSION node after storing the input.",
      };
    }
  }

  // Additional validation: ensure context access is properly formatted if present
  const hasContextAccess = trimmed.includes("context.");

  // If neither valid input methods nor context are found, reject
  const hasValidInput = allowedInputPatterns.some((pattern) =>
    pattern.test(trimmed)
  );

  if (!hasValidInput && !hasContextAccess) {
    return {
      isValid: false,
      error:
        "Use valid input methods: input.isAlpha(), input.isNumeric(), input.isDigit(), or input.length.",
    };
  }

  return { isValid: true };
}

/**
 * Validates trigger keyword format per backend spec
 * Allowed: A-Z, a-z, 0-9, space, underscore (_), hyphen (-)
 * Not allowed: punctuation, special characters, emojis
 */
export function isValidTriggerKeyword(keyword: string): boolean {
  // Must match backend pattern: /^[A-Za-z0-9 _-]+$/
  return /^[A-Za-z0-9 _-]+$/.test(keyword);
}

/**
 * Validates trigger keywords array
 * Checks character validity and wildcard combination rules
 */
export function validateTriggerKeywords(keywords: string[]): {
  isValid: boolean;
  errors: Array<{ index: number; error: string }>;
} {
  const errors: Array<{ index: number; error: string }> = [];

  // Check for wildcard combination
  const hasWildcard = keywords.includes('*');
  if (hasWildcard && keywords.length > 1) {
    errors.push({
      index: -1,
      error: "Wildcard trigger '*' cannot be combined with other keywords. Remove other keywords or use a separate flow."
    });
  }

  // Check each keyword
  keywords.forEach((keyword, index) => {
    if (keyword !== '*' && !isValidTriggerKeyword(keyword)) {
      errors.push({
        index,
        error: "Keyword can only contain letters (A-Z, a-z), numbers (0-9), spaces, underscores (_), and hyphens (-). No punctuation or special characters."
      });
    }
  });

  return {
    isValid: errors.length === 0,
    errors
  };
}

/**
 * Validates regex pattern matches backend constraints
 * Checks for unsupported features: lookahead, lookbehind, named groups
 */
export function validateRegexFeatures(pattern: string): {
  isValid: boolean;
  error?: string;
} {
  // Check for lookahead
  if (/\(\?[=!]/.test(pattern)) {
    return {
      isValid: false,
      error: "Lookahead assertions (?= or ?!) are not supported. Use simple patterns."
    };
  }

  // Check for lookbehind
  if (/\(\?<[=!]/.test(pattern)) {
    return {
      isValid: false,
      error: "Lookbehind assertions (?<= or ?<!) are not supported. Use simple patterns."
    };
  }

  // Check for named groups
  if (/\(\?P<\w+>/.test(pattern)) {
    return {
      isValid: false,
      error: "Named groups (?P<name>) are not supported. Use unnamed groups."
    };
  }

  // Validate pattern compiles
  try {
    new RegExp(pattern);
  } catch (e) {
    return {
      isValid: false,
      error: `Invalid regex: ${(e as Error).message}`
    };
  }

  return { isValid: true };
}

/**
 * Validates that expression doesn't use standalone functions
 * Backend rejects functions like parseInt(), toUpperCase(), includes(), etc.
 * Only allowed methods are: input.isAlpha(), input.isNumeric(), input.isDigit()
 */
export function validateExpressionFunctions(expression: string): {
  isValid: boolean;
  error?: string;
} {
  // List of standalone functions that backend rejects
  const disallowedFunctions = [
    'parseInt', 'parseFloat', 'Number', 'String', 'Boolean',
    'toUpperCase', 'toLowerCase', 'trim', 'includes', 'startsWith',
    'endsWith', 'substring', 'substr', 'slice', 'split', 'replace',
    'match', 'search', 'indexOf', 'lastIndexOf', 'Math.', 'Date.',
    'Array.', 'Object.', 'JSON.', 'console.', 'eval', 'Function'
  ];

  // Check for each disallowed function
  for (const func of disallowedFunctions) {
    const pattern = new RegExp(`\\b${func.replace('.', '\\.')}`, 'i');
    if (pattern.test(expression)) {
      return {
        isValid: false,
        error: `Function '${func}' is not supported. Use only: input.isAlpha(), input.isNumeric(), input.isDigit(), input.length, context.*, and basic operators (==, !=, >, <, >=, <=, &&, ||).`
      };
    }
  }

  return { isValid: true };
}

/**
 * Validates template string for restricted variables based on context
 * Per backend spec: certain variables are only available in specific contexts
 */
export function validateTemplateVariables(
  template: string,
  nodeType?: "MESSAGE" | "PROMPT" | "MENU" | "API_ACTION" | "LOGIC_EXPRESSION" | "END",
  fieldContext?: "item_template" | "counter_text" | "default"
): {
  isValid: boolean;
  error?: string;
} {
  // Extract all template variables from {{variable}} syntax
  const variablePattern = /\{\{([^}]+)\}\}/g;
  const matches = template.matchAll(variablePattern);

  for (const match of matches) {
    const variable = match[1].trim();

    // Check for {{input}} - NEVER allowed in templates (only in expressions without {{}}))
    if (variable === 'input' || variable.startsWith('input.')) {
      return {
        isValid: false,
        error: `{{${variable}}} cannot be used in templates. The 'input' variable is only available in PROMPT validation expressions (use it directly without {{ }}, like: input.length > 5).`
      };
    }

    // Check for {{current_attempt}} and {{max_attempts}} - ONLY in counter_text
    if (variable === 'current_attempt' || variable === 'max_attempts') {
      if (fieldContext !== 'counter_text') {
        return {
          isValid: false,
          error: `{{${variable}}} is only available in retry_logic counter_text. It cannot be used in error messages, validation rules, or other templates.`
        };
      }
    }

    // Check for {{user.*}} - ONLY in API_ACTION nodes
    if (variable.startsWith('user.')) {
      if (nodeType !== 'API_ACTION') {
        return {
          isValid: false,
          error: `{{${variable}}} is only available in API_ACTION nodes. User variables (user.channel_id, user.channel) cannot be used in ${nodeType || 'this'} node type.`
        };
      }
    }

    // Check for {{item}} and {{index}} - ONLY in MENU item_template
    if (variable === 'item' || variable.startsWith('item.') || variable === 'index') {
      if (nodeType !== 'MENU' || fieldContext !== 'item_template') {
        return {
          isValid: false,
          error: `{{${variable}}} is only available in MENU item_template field. It cannot be used in other fields or node types.`
        };
      }
    }
  }

  return { isValid: true };
}

/**
 * Validates template string for unsupported syntax
 * Per backend spec: templates don't support arithmetic, ternary, methods, etc.
 */
export function validateTemplateSyntax(template: string): {
  isValid: boolean;
  error?: string;
} {
  // Extract template expressions (content within {{ }})
  const variablePattern = /\{\{([^}]+)\}\}/g;
  const matches = template.matchAll(variablePattern);

  for (const match of matches) {
    const expression = match[1].trim();

    // Check for arithmetic operators
    if (/[\+\-\*\/%]/.test(expression)) {
      return {
        isValid: false,
        error: `Arithmetic operators (+, -, *, /, %) are not supported in templates. Use variables with pre-calculated values instead.`
      };
    }

    // Check for default value operator ||
    if (/\|\|/.test(expression)) {
      return {
        isValid: false,
        error: `Default value operator (||) is not supported. Initialize variables with defaults in flow definition instead.`
      };
    }

    // Check for ternary operator
    if (/\?.*:/.test(expression)) {
      return {
        isValid: false,
        error: `Ternary operator (? :) is not supported. Use LOGIC_EXPRESSION nodes for conditional logic instead.`
      };
    }

    // Check for method calls with parentheses
    if (/\.\w+\s*\(/.test(expression)) {
      return {
        isValid: false,
        error: `Method calls like .toUpperCase(), .includes() are not supported in templates. Use pre-processed values instead.`
      };
    }

    // Check for square bracket notation
    if (/\[/.test(expression)) {
      return {
        isValid: false,
        error: `Bracket notation is not supported. Use dot notation for array access (e.g., items.0 instead of items[0]).`
      };
    }

    // Check for control flow keywords
    if (/\b(if|for|while|function|return|class|new)\b/.test(expression)) {
      return {
        isValid: false,
        error: `Control flow keywords (if, for, while, function, return, class, new) are not supported. Use node types for control flow instead.`
      };
    }
  }

  return { isValid: true };
}

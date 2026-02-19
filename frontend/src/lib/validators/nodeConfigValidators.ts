import type {
  NodeType,
  NodeConfig,
  TextNodeConfig,
  PromptNodeConfig,
  MenuNodeConfig,
  APIActionNodeConfig,
  LogicExpressionNodeConfig,
  ValidationError,
  ValidationRule,
} from "../types";
import { SystemConstraints } from "../types";
import {
  isNonEmptyString,
  isWithinMaxLength,
  isValidURL,
  isValidHTTPMethod,
  isValidValidationType,
  isValidMenuSourceType,
  getMaxLengthError,
  getRequiredFieldError,
  validateSuccessExpression,
  validateRouteCondition,
  validateValidationExpression,
  validateRegexFeatures,
  getVariableNameError,
  validateTemplateVariables,
  validateTemplateSyntax,
} from "./commonValidators";
import { isValidCondition, getMaxRoutes } from "../routeConditionUtils";

export interface ValidationResult {
  isValid: boolean;
  errors: ValidationError[];
}

/**
 * Main validator - routes to specific node type validator
 */
export function validateNodeConfig(
  config: NodeConfig,
  nodeType: NodeType
): ValidationResult {
  switch (nodeType) {
    case "TEXT":
      return validateTextConfig(config as TextNodeConfig);
    case "PROMPT":
      return validatePromptConfig(config as PromptNodeConfig);
    case "MENU":
      return validateMenuConfig(config as MenuNodeConfig);
    case "API_ACTION":
      return validateAPIActionConfig(config as APIActionNodeConfig);
    case "LOGIC_EXPRESSION":
      return validateLogicExpressionConfig(config as LogicExpressionNodeConfig);
    case "END":
      return { isValid: true, errors: [] };
    default:
      return {
        isValid: false,
        errors: [{ field: "type", message: "Invalid node type" }],
      };
  }
}

/**
 * TEXT node validation
 */
export function validateTextConfig(
  config: TextNodeConfig
): ValidationResult {
  const errors: ValidationError[] = [];

  // Required: text
  if (!isNonEmptyString(config.text)) {
    errors.push({
      field: "text",
      message: getRequiredFieldError("Text message"),
    });
  }

  // Length constraint: max 1024 chars
  if (
    config.text &&
    !isWithinMaxLength(config.text, SystemConstraints.MAX_MESSAGE_LENGTH)
  ) {
    errors.push({
      field: "text",
      message: getMaxLengthError(
        "Text message",
        SystemConstraints.MAX_MESSAGE_LENGTH
      ),
    });
  }

  // Validate template syntax and restricted variables
  if (config.text) {
    const syntaxValidation = validateTemplateSyntax(config.text);
    if (!syntaxValidation.isValid && syntaxValidation.error) {
      errors.push({
        field: "text",
        message: syntaxValidation.error,
      });
    }

    const variableValidation = validateTemplateVariables(config.text, "TEXT");
    if (!variableValidation.isValid && variableValidation.error) {
      errors.push({
        field: "text",
        message: variableValidation.error,
      });
    }
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

/**
 * PROMPT node validation
 */
export function validatePromptConfig(
  config: PromptNodeConfig
): ValidationResult {
  const errors: ValidationError[] = [];

  // Required: text
  if (!isNonEmptyString(config.text)) {
    errors.push({
      field: "text",
      message: getRequiredFieldError("Prompt text"),
    });
  }

  // Length: text max 1024
  if (
    config.text &&
    !isWithinMaxLength(config.text, SystemConstraints.MAX_MESSAGE_LENGTH)
  ) {
    errors.push({
      field: "text",
      message: getMaxLengthError(
        "Prompt text",
        SystemConstraints.MAX_MESSAGE_LENGTH
      ),
    });
  }

  // Validate template syntax and restricted variables
  if (config.text) {
    const syntaxValidation = validateTemplateSyntax(config.text);
    if (!syntaxValidation.isValid && syntaxValidation.error) {
      errors.push({
        field: "text",
        message: syntaxValidation.error,
      });
    }

    const variableValidation = validateTemplateVariables(config.text, "PROMPT");
    if (!variableValidation.isValid && variableValidation.error) {
      errors.push({
        field: "text",
        message: variableValidation.error,
      });
    }
  }

  // Required: save_to_variable
  if (!isNonEmptyString(config.save_to_variable)) {
    errors.push({
      field: "save_to_variable",
      message: getRequiredFieldError("Variable name"),
    });
  }

  // Length: save_to_variable max 96
  if (
    config.save_to_variable &&
    !isWithinMaxLength(
      config.save_to_variable,
      SystemConstraints.MAX_VARIABLE_NAME_LENGTH
    )
  ) {
    errors.push({
      field: "save_to_variable",
      message: getMaxLengthError(
        "Variable name",
        SystemConstraints.MAX_VARIABLE_NAME_LENGTH
      ),
    });
  }

  // Variable name format and reserved keywords check
  if (config.save_to_variable) {
    const varNameError = getVariableNameError(config.save_to_variable);
    if (varNameError) {
      errors.push({
        field: "save_to_variable",
        message: varNameError,
      });
    }
  }

  // Validation rule (if provided)
  if (config.validation) {
    const valErrors = validateValidationRule(config.validation);
    errors.push(...valErrors);
  }

  // Interrupts (if provided)
  if (config.interrupts) {
    config.interrupts.forEach((interrupt, index) => {
      // Interrupt keyword validation
      if (!interrupt.input || !interrupt.input.trim()) {
        errors.push({
          field: `interrupts[${index}].input`,
          message: "Interrupt keyword cannot be empty or whitespace-only. Empty string '' is not allowed as an interrupt keyword.",
        });
      } else if (!isWithinMaxLength(interrupt.input, SystemConstraints.MAX_INTERRUPT_KEYWORD_LENGTH)) {
        errors.push({
          field: `interrupts[${index}].input`,
          message: getMaxLengthError(
            "Interrupt keyword",
            SystemConstraints.MAX_INTERRUPT_KEYWORD_LENGTH
          ),
        });
      }

      // Target node validation
      if (!isNonEmptyString(interrupt.target_node)) {
        errors.push({
          field: `interrupts[${index}].target_node`,
          message: "Interrupt target node is required",
        });
      } else if (!isWithinMaxLength(interrupt.target_node, SystemConstraints.MAX_NODE_ID_LENGTH)) {
        errors.push({
          field: `interrupts[${index}].target_node`,
          message: getMaxLengthError("Target node ID", SystemConstraints.MAX_NODE_ID_LENGTH),
        });
      }
    });
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

/**
 * MENU node validation
 */
export function validateMenuConfig(config: MenuNodeConfig): ValidationResult {
  const errors: ValidationError[] = [];

  // Required: text
  if (!isNonEmptyString(config.text)) {
    errors.push({ field: "text", message: getRequiredFieldError("Menu text") });
  }

  // Length: text
  if (
    config.text &&
    !isWithinMaxLength(config.text, SystemConstraints.MAX_MESSAGE_LENGTH)
  ) {
    errors.push({
      field: "text",
      message: getMaxLengthError(
        "Menu text",
        SystemConstraints.MAX_MESSAGE_LENGTH
      ),
    });
  }

  // Validate template syntax and restricted variables in text
  if (config.text) {
    const syntaxValidation = validateTemplateSyntax(config.text);
    if (!syntaxValidation.isValid && syntaxValidation.error) {
      errors.push({
        field: "text",
        message: syntaxValidation.error,
      });
    }

    const variableValidation = validateTemplateVariables(config.text, "MENU");
    if (!variableValidation.isValid && variableValidation.error) {
      errors.push({
        field: "text",
        message: variableValidation.error,
      });
    }
  }

  // Required: source_type
  if (!config.source_type) {
    errors.push({
      field: "source_type",
      message: getRequiredFieldError("Source type"),
    });
  }

  // Validate source_type value
  if (config.source_type && !isValidMenuSourceType(config.source_type)) {
    errors.push({
      field: "source_type",
      message: "Source type must be STATIC or DYNAMIC",
    });
  }

  // Conditional validation based on source_type
  if (config.source_type === "STATIC") {
    // STATIC: must have static_options
    if (!config.static_options || config.static_options.length === 0) {
      errors.push({
        field: "static_options",
        message: "At least one option is required for static menus",
      });
    }

    // Max 8 options for static menus
    if (
      config.static_options &&
      config.static_options.length > SystemConstraints.MAX_STATIC_MENU_OPTIONS
    ) {
      errors.push({
        field: "static_options",
        message: `Maximum ${SystemConstraints.MAX_STATIC_MENU_OPTIONS} options allowed for static menus`,
      });
    }

    // STATIC menus cannot have output_mapping (backend spec line 858)
    if (config.output_mapping && config.output_mapping.length > 0) {
      errors.push({
        field: "output_mapping",
        message: "output_mapping only works with DYNAMIC source_type. Remove output_mapping from STATIC menu.",
      });
    }

    // Validate each option
    config.static_options?.forEach((option, index) => {
      if (!isNonEmptyString(option.label)) {
        errors.push({
          field: `static_options[${index}].label`,
          message: "Option label is required",
        });
      }
      if (
        option.label &&
        !isWithinMaxLength(
          option.label,
          SystemConstraints.MAX_OPTION_LABEL_LENGTH
        )
      ) {
        errors.push({
          field: `static_options[${index}].label`,
          message: getMaxLengthError(
            "Label",
            SystemConstraints.MAX_OPTION_LABEL_LENGTH
          ),
        });
      }
    });
  } else if (config.source_type === "DYNAMIC") {
    // DYNAMIC: must have source_variable and item_template
    if (!isNonEmptyString(config.source_variable)) {
      errors.push({
        field: "source_variable",
        message: "Source variable is required for dynamic menus",
      });
    }

    if (!isNonEmptyString(config.item_template)) {
      errors.push({
        field: "item_template",
        message: "Item template is required for dynamic menus",
      });
    }

    // Length constraints
    if (
      config.source_variable &&
      !isWithinMaxLength(
        config.source_variable,
        SystemConstraints.MAX_VARIABLE_NAME_LENGTH
      )
    ) {
      errors.push({
        field: "source_variable",
        message: getMaxLengthError(
          "Variable name",
          SystemConstraints.MAX_VARIABLE_NAME_LENGTH
        ),
      });
    }

    if (
      config.item_template &&
      !isWithinMaxLength(
        config.item_template,
        SystemConstraints.MAX_TEMPLATE_LENGTH
      )
    ) {
      errors.push({
        field: "item_template",
        message: getMaxLengthError(
          "Template",
          SystemConstraints.MAX_TEMPLATE_LENGTH
        ),
      });
    }

    // Validate template syntax and restricted variables in item_template
    if (config.item_template) {
      const syntaxValidation = validateTemplateSyntax(config.item_template);
      if (!syntaxValidation.isValid && syntaxValidation.error) {
        errors.push({
          field: "item_template",
          message: syntaxValidation.error,
        });
      }

      const variableValidation = validateTemplateVariables(config.item_template, "MENU", "item_template");
      if (!variableValidation.isValid && variableValidation.error) {
        errors.push({
          field: "item_template",
          message: variableValidation.error,
        });
      }
    }

    // Validate output_mapping (if provided)
    config.output_mapping?.forEach((mapping, index) => {
      // Source path is required and must be non-empty
      if (!isNonEmptyString(mapping.source_path)) {
        errors.push({
          field: `output_mapping[${index}].source_path`,
          message: "Source path is required",
        });
      } else {
        // Validate source_path length
        if (!isWithinMaxLength(mapping.source_path, SystemConstraints.MAX_SOURCE_PATH_LENGTH)) {
          errors.push({
            field: `output_mapping[${index}].source_path`,
            message: getMaxLengthError(
              "Source path",
              SystemConstraints.MAX_SOURCE_PATH_LENGTH
            ),
          });
        }
        // Validate no bracket notation
        if (mapping.source_path.includes('[') || mapping.source_path.includes(']')) {
          errors.push({
            field: `output_mapping[${index}].source_path`,
            message: "Bracket notation not supported in source_path. Use dot notation instead (e.g., 'items.0.name' not 'items[0].name')",
          });
        }
      }

      // Target variable is required
      if (!isNonEmptyString(mapping.target_variable)) {
        errors.push({
          field: `output_mapping[${index}].target_variable`,
          message: "Target variable is required",
        });
      } else {
        // Validate max length
        if (!isWithinMaxLength(mapping.target_variable, SystemConstraints.MAX_VARIABLE_NAME_LENGTH)) {
          errors.push({
            field: `output_mapping[${index}].target_variable`,
            message: getMaxLengthError("Variable name", SystemConstraints.MAX_VARIABLE_NAME_LENGTH),
          });
        }

        // Validate target_variable against reserved keywords
        const varNameError = getVariableNameError(mapping.target_variable);
        if (varNameError) {
          errors.push({
            field: `output_mapping[${index}].target_variable`,
            message: varNameError,
          });
        }
      }
    });
  }

  // Error message (optional)
  if (
    config.error_message &&
    !isWithinMaxLength(
      config.error_message,
      SystemConstraints.MAX_ERROR_MESSAGE_LENGTH
    )
  ) {
    errors.push({
      field: "error_message",
      message: getMaxLengthError(
        "Error message",
        SystemConstraints.MAX_ERROR_MESSAGE_LENGTH
      ),
    });
  }

  // Validate template syntax and restricted variables in error_message
  if (config.error_message) {
    const syntaxValidation = validateTemplateSyntax(config.error_message);
    if (!syntaxValidation.isValid && syntaxValidation.error) {
      errors.push({
        field: "error_message",
        message: syntaxValidation.error,
      });
    }

    const variableValidation = validateTemplateVariables(config.error_message, "MENU");
    if (!variableValidation.isValid && variableValidation.error) {
      errors.push({
        field: "error_message",
        message: variableValidation.error,
      });
    }
  }

  // Interrupts validation
  if (config.interrupts) {
    config.interrupts.forEach((interrupt, index) => {
      // Interrupt keyword validation
      if (!interrupt.input || !interrupt.input.trim()) {
        errors.push({
          field: `interrupts[${index}].input`,
          message: "Interrupt keyword cannot be empty or whitespace-only. Empty string '' is not allowed as an interrupt keyword.",
        });
      } else if (!isWithinMaxLength(interrupt.input, SystemConstraints.MAX_INTERRUPT_KEYWORD_LENGTH)) {
        errors.push({
          field: `interrupts[${index}].input`,
          message: getMaxLengthError(
            "Interrupt keyword",
            SystemConstraints.MAX_INTERRUPT_KEYWORD_LENGTH
          ),
        });
      }

      // Target node validation
      if (!isNonEmptyString(interrupt.target_node)) {
        errors.push({
          field: `interrupts[${index}].target_node`,
          message: "Interrupt target node is required",
        });
      } else if (!isWithinMaxLength(interrupt.target_node, SystemConstraints.MAX_NODE_ID_LENGTH)) {
        errors.push({
          field: `interrupts[${index}].target_node`,
          message: getMaxLengthError("Target node ID", SystemConstraints.MAX_NODE_ID_LENGTH),
        });
      }
    });
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

/**
 * API_ACTION node validation
 */
export function validateAPIActionConfig(
  config: APIActionNodeConfig
): ValidationResult {
  const errors: ValidationError[] = [];

  // Required: request
  if (!config.request) {
    errors.push({
      field: "request",
      message: "Request configuration is required",
    });
    return { isValid: false, errors };
  }

  // Required: method
  if (!config.request.method) {
    errors.push({
      field: "request.method",
      message: getRequiredFieldError("HTTP method"),
    });
  }

  // Valid method
  if (config.request.method && !isValidHTTPMethod(config.request.method)) {
    errors.push({
      field: "request.method",
      message: "Invalid HTTP method",
    });
  }

  // Required: url
  if (!isNonEmptyString(config.request.url)) {
    errors.push({
      field: "request.url",
      message: getRequiredFieldError("URL"),
    });
  }

  // Length: url
  if (
    config.request.url &&
    !isWithinMaxLength(
      config.request.url,
      SystemConstraints.MAX_REQUEST_URL_LENGTH
    )
  ) {
    errors.push({
      field: "request.url",
      message: getMaxLengthError(
        "URL",
        SystemConstraints.MAX_REQUEST_URL_LENGTH
      ),
    });
  }

  // URL format (basic)
  if (config.request.url && !isValidURL(config.request.url)) {
    errors.push({
      field: "request.url",
      message: "URL must start with http:// or https://",
    });
  }

  // Validate template syntax and restricted variables in URL
  if (config.request.url) {
    const syntaxValidation = validateTemplateSyntax(config.request.url);
    if (!syntaxValidation.isValid && syntaxValidation.error) {
      errors.push({
        field: "request.url",
        message: syntaxValidation.error,
      });
    }

    const variableValidation = validateTemplateVariables(config.request.url, "API_ACTION");
    if (!variableValidation.isValid && variableValidation.error) {
      errors.push({
        field: "request.url",
        message: variableValidation.error,
      });
    }
  }

  // Validate headers array (if provided)
  if (config.request.headers) {
    // Check max number of headers
    if (config.request.headers.length > SystemConstraints.MAX_HEADERS_PER_REQUEST) {
      errors.push({
        field: "request.headers",
        message: `Maximum ${SystemConstraints.MAX_HEADERS_PER_REQUEST} headers allowed`,
      });
    }

    // Validate each header
    config.request.headers.forEach((header, index) => {
      // Header name validation
      if (!isNonEmptyString(header.name)) {
        errors.push({
          field: `request.headers[${index}].name`,
          message: "Header name is required",
        });
      } else if (!isWithinMaxLength(header.name, SystemConstraints.MAX_HEADER_NAME_LENGTH)) {
        errors.push({
          field: `request.headers[${index}].name`,
          message: getMaxLengthError("Header name", SystemConstraints.MAX_HEADER_NAME_LENGTH),
        });
      }

      // Header value validation
      if (!isNonEmptyString(header.value)) {
        errors.push({
          field: `request.headers[${index}].value`,
          message: "Header value is required",
        });
      } else if (!isWithinMaxLength(header.value, SystemConstraints.MAX_HEADER_VALUE_LENGTH)) {
        errors.push({
          field: `request.headers[${index}].value`,
          message: getMaxLengthError("Header value", SystemConstraints.MAX_HEADER_VALUE_LENGTH),
        });
      }
    });
  }

  // Validate request body (if provided)
  if (config.request.body !== undefined && config.request.body !== null) {
    // Body must be a string (JSON string), not an object
    if (typeof config.request.body !== 'string') {
      errors.push({
        field: "request.body",
        message: "Request body must be a JSON string",
      });
    } else {
      // Validate it's valid JSON
      try {
        JSON.parse(config.request.body);
      } catch (e) {
        errors.push({
          field: "request.body",
          message: "Request body must be valid JSON",
        });
      }
    }
  }

  // Validate response_map (if provided)
  config.response_map?.forEach((mapping, index) => {
    // Both source_path and target_variable are required
    if (!isNonEmptyString(mapping.source_path)) {
      errors.push({
        field: `response_map[${index}].source_path`,
        message: "Source path is required",
      });
    } else {
      // Validate source_path length
      if (!isWithinMaxLength(mapping.source_path, SystemConstraints.MAX_SOURCE_PATH_LENGTH)) {
        errors.push({
          field: `response_map[${index}].source_path`,
          message: getMaxLengthError(
            "Source path",
            SystemConstraints.MAX_SOURCE_PATH_LENGTH
          ),
        });
      }
      // Validate no bracket notation
      if (mapping.source_path.includes('[') || mapping.source_path.includes(']')) {
        errors.push({
          field: `response_map[${index}].source_path`,
          message: "Bracket notation not supported in source_path. Use dot notation instead (e.g., 'data.items.0.name' not 'data.items[0].name'). For root arrays, use '*' prefix (e.g., '*.0.id').",
        });
      }
    }

    if (!isNonEmptyString(mapping.target_variable)) {
      errors.push({
        field: `response_map[${index}].target_variable`,
        message: "Target variable is required",
      });
    } else {
      // Validate max length
      if (!isWithinMaxLength(mapping.target_variable, SystemConstraints.MAX_VARIABLE_NAME_LENGTH)) {
        errors.push({
          field: `response_map[${index}].target_variable`,
          message: getMaxLengthError("Variable name", SystemConstraints.MAX_VARIABLE_NAME_LENGTH),
        });
      }

      // Validate target_variable
      const varNameError = getVariableNameError(mapping.target_variable);
      if (varNameError) {
        errors.push({
          field: `response_map[${index}].target_variable`,
          message: varNameError,
        });
      }
    }
  });

  // Validate success_check (if provided)
  if (config.success_check) {
    // At least one of status_codes or expression must be specified
    const hasStatusCodes = config.success_check.status_codes && config.success_check.status_codes.length > 0;
    const hasExpression = config.success_check.expression && config.success_check.expression.trim() !== "";

    if (!hasStatusCodes && !hasExpression) {
      errors.push({
        field: "success_check",
        message: "At least one of 'status_codes' or 'expression' must be specified",
      });
    }

    // Validate expression if provided
    if (config.success_check.expression) {
      if (
        !isWithinMaxLength(
          config.success_check.expression,
          SystemConstraints.MAX_EXPRESSION_LENGTH
        )
      ) {
        errors.push({
          field: "success_check.expression",
          message: getMaxLengthError(
            "Expression",
            SystemConstraints.MAX_EXPRESSION_LENGTH
          ),
        });
      }

      // Validate expression syntax
      const expressionValidation = validateSuccessExpression(
        config.success_check.expression
      );
      if (!expressionValidation.isValid && expressionValidation.error) {
        errors.push({
          field: "success_check.expression",
          message: expressionValidation.error,
        });
      }
    }
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

/**
 * LOGIC_EXPRESSION node validation
 */
export function validateLogicExpressionConfig(
  _config: LogicExpressionNodeConfig
): ValidationResult {
  // LOGIC_EXPRESSION has no config fields - routes are configured separately
  // No validation needed
  return { isValid: true, errors: [] };
}

/**
 * Helper: Validate validation rule
 */
function validateValidationRule(rule: ValidationRule): ValidationError[] {
  const errors: ValidationError[] = [];

  if (!rule.type) {
    errors.push({
      field: "validation.type",
      message: getRequiredFieldError("Validation type"),
    });
  }

  if (rule.type && !isValidValidationType(rule.type)) {
    errors.push({
      field: "validation.type",
      message: "Type must be REGEX or EXPRESSION",
    });
  }

  if (!isNonEmptyString(rule.rule)) {
    errors.push({
      field: "validation.rule",
      message: getRequiredFieldError("Validation rule"),
    });
  }

  if (
    rule.type === "REGEX" &&
    rule.rule &&
    !isWithinMaxLength(rule.rule, SystemConstraints.MAX_REGEX_LENGTH)
  ) {
    errors.push({
      field: "validation.rule",
      message: getMaxLengthError(
        "Regex pattern",
        SystemConstraints.MAX_REGEX_LENGTH
      ),
    });
  }

  // Validate REGEX features (lookahead, lookbehind, named groups)
  if (rule.type === "REGEX" && rule.rule) {
    const regexValidation = validateRegexFeatures(rule.rule);
    if (!regexValidation.isValid && regexValidation.error) {
      errors.push({
        field: "validation.rule",
        message: regexValidation.error,
      });
    }
  }

  if (
    rule.type === "EXPRESSION" &&
    rule.rule &&
    !isWithinMaxLength(rule.rule, SystemConstraints.MAX_EXPRESSION_LENGTH)
  ) {
    errors.push({
      field: "validation.rule",
      message: getMaxLengthError(
        "Expression",
        SystemConstraints.MAX_EXPRESSION_LENGTH
      ),
    });
  }

  // Validate EXPRESSION syntax
  if (rule.type === "EXPRESSION" && rule.rule) {
    const expressionValidation = validateValidationExpression(rule.rule);
    if (!expressionValidation.isValid && expressionValidation.error) {
      errors.push({
        field: "validation.rule",
        message: expressionValidation.error,
      });
    }
  }

  if (!isNonEmptyString(rule.error_message)) {
    errors.push({
      field: "validation.error_message",
      message: getRequiredFieldError("Error message"),
    });
  }

  if (
    rule.error_message &&
    !isWithinMaxLength(
      rule.error_message,
      SystemConstraints.MAX_ERROR_MESSAGE_LENGTH
    )
  ) {
    errors.push({
      field: "validation.error_message",
      message: getMaxLengthError(
        "Error message",
        SystemConstraints.MAX_ERROR_MESSAGE_LENGTH
      ),
    });
  }

  // Validate template syntax and restricted variables in error_message
  if (rule.error_message) {
    const syntaxValidation = validateTemplateSyntax(rule.error_message);
    if (!syntaxValidation.isValid && syntaxValidation.error) {
      errors.push({
        field: "validation.error_message",
        message: syntaxValidation.error,
      });
    }

    const variableValidation = validateTemplateVariables(rule.error_message, "PROMPT");
    if (!variableValidation.isValid && variableValidation.error) {
      errors.push({
        field: "validation.error_message",
        message: variableValidation.error,
      });
    }
  }

  return errors;
}

/**
 * Validate routes for a node
 * Enhanced with route condition type awareness
 */
export function validateRoutes(
  routes: Array<{ condition: string; target_node: string }> | undefined,
  nodeType: NodeType,
  availableNodes: string[],
  nodeConfig?: NodeConfig
): { isValid: boolean; errors: ValidationError[] } {
  const errors: ValidationError[] = [];

  // END nodes cannot have routes
  if (nodeType === "END" && routes && routes.length > 0) {
    errors.push({ field: "routes", message: "END nodes cannot have routes" });
    return { isValid: false, errors };
  }

  // All other nodes should have at least one route
  if (nodeType !== "END" && (!routes || routes.length === 0)) {
    errors.push({ field: "routes", message: "At least one route is required" });
    return { isValid: false, errors };
  }

  // Check for duplicate conditions (case-insensitive)
  const conditionMap = new Map<string, number>();
  routes?.forEach((route, index) => {
    const normalizedCondition = route.condition.trim().toLowerCase();
    if (conditionMap.has(normalizedCondition)) {
      errors.push({
        field: `routes[${index}].condition`,
        message: `Duplicate condition found (same as route ${
          conditionMap.get(normalizedCondition)! + 1
        })`,
      });
    } else {
      conditionMap.set(normalizedCondition, index);
    }
  });

  // Validate each route
  routes?.forEach((route, index) => {
    if (!route.condition || route.condition.trim() === "") {
      errors.push({
        field: `routes[${index}].condition`,
        message: "Condition is required",
      });
    } else {
      // Validate condition length
      if (!isWithinMaxLength(route.condition, SystemConstraints.MAX_ROUTE_CONDITION_LENGTH)) {
        errors.push({
          field: `routes[${index}].condition`,
          message: getMaxLengthError(
            "Route condition",
            SystemConstraints.MAX_ROUTE_CONDITION_LENGTH
          ),
        });
      }

      // Use new validation that's aware of node type and configuration
      // For MENU and API_ACTION, allow "true" as it's auto-generated internally as fallback to END
      const isTrueCondition = route.condition.trim().toLowerCase() === "true";
      const isAutoGeneratedFallback = isTrueCondition && (nodeType === "MENU" || nodeType === "API_ACTION");

      if (!isAutoGeneratedFallback && !isValidCondition(nodeType, route.condition, nodeConfig)) {
        // For dropdown types, give specific error about valid options
        if (["MENU", "API_ACTION", "PROMPT", "TEXT"].includes(nodeType)) {
          errors.push({
            field: `routes[${index}].condition`,
            message:
              "Invalid condition for this node type. Please select a valid option.",
          });
        } else {
          // For LOGIC_EXPRESSION, use the old validator
          const conditionValidation = validateRouteCondition(
            route.condition,
            nodeType
          );
          if (!conditionValidation.isValid && conditionValidation.error) {
            errors.push({
              field: `routes[${index}].condition`,
              message: conditionValidation.error,
            });
          }
        }
      }
    }

    if (!route.target_node || route.target_node.trim() === "") {
      errors.push({
        field: `routes[${index}].target_node`,
        message: "Target node is required",
      });
    } else {
      // Validate max length
      if (!isWithinMaxLength(route.target_node, SystemConstraints.MAX_NODE_ID_LENGTH)) {
        errors.push({
          field: `routes[${index}].target_node`,
          message: getMaxLengthError("Target node ID", SystemConstraints.MAX_NODE_ID_LENGTH),
        });
      }

      // Validate node exists
      if (!availableNodes.includes(route.target_node)) {
        errors.push({
          field: `routes[${index}].target_node`,
          message: "Target node does not exist",
        });
      }
    }
  });

  // Max routes based on node type and configuration
  const maxRoutes = getMaxRoutes(nodeType, nodeConfig);

  // For MENU and API_ACTION, exclude auto-generated fallback "true" routes from the count
  // These are added automatically to route to END and shouldn't count against the max
  const routesToCount = (nodeType === "MENU" || nodeType === "API_ACTION")
    ? routes?.filter(r => r.condition.trim().toLowerCase() !== "true") || []
    : routes || [];

  if (routesToCount.length > maxRoutes) {
    errors.push({
      field: "routes",
      message: `Maximum ${maxRoutes} routes allowed for this node type`,
    });
  }

  return { isValid: errors.length === 0, errors };
}

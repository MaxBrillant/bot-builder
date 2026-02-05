/**
 * Application constants
 * Matches backend constants for consistency
 */

/**
 * Reserved keywords that cannot be used as variable names
 * Must match backend: app.utils.constants.ReservedKeywords.RESERVED
 */
export const RESERVED_KEYWORDS = [
  "user",
  "item",
  "index",
  "input",
  "context",
  "response",
  "selection",
  "true",
  "false",
  "null",
  "success",
  "error",
];

/**
 * Variable name validation pattern
 * Must start with letter or underscore, contain only alphanumeric and underscores
 * Matches backend: app.utils.constants.RegexPatterns.IDENTIFIER
 */
export const IDENTIFIER_PATTERN = /^[A-Za-z_][A-Za-z0-9_]*$/;

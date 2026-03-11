/**
 * Simple cURL parser for basic curl commands
 * Handles common patterns: -X, -H, -d, --data, --header, --request
 */

interface ParsedCurl {
  method: string;
  url: string;
  headers: Record<string, string>;
  body?: string;
}

/**
 * Collapse runs of whitespace into a single space, but only outside quoted
 * strings, so that body/header values with intentional whitespace are preserved.
 * Single-quoted strings are treated as literals (no escape sequences, per bash).
 * Double-quoted strings honour \" escapes.
 */
function collapseOuterWhitespace(s: string): string {
  let result = "";
  let i = 0;
  while (i < s.length) {
    const ch = s[i];
    if (ch === "'") {
      result += ch;
      i++;
      while (i < s.length && s[i] !== "'") {
        result += s[i++];
      }
      if (i < s.length) result += s[i++]; // closing '
    } else if (ch === '"') {
      result += ch;
      i++;
      while (i < s.length && s[i] !== '"') {
        if (s[i] === "\\") result += s[i++]; // escape char
        result += s[i++];
      }
      if (i < s.length) result += s[i++]; // closing "
    } else if (/\s/.test(ch)) {
      result += " ";
      while (i < s.length && /\s/.test(s[i])) i++;
    } else {
      result += s[i++];
    }
  }
  return result;
}

export function parseCurlCommand(curlCommand: string): ParsedCurl {
  // Remove line continuations first, then collapse whitespace outside quotes
  const normalized = collapseOuterWhitespace(
    curlCommand.replace(/\\\s*\n\s*/g, " ")
  ).trim();

  // Extract URL - find the http(s):// pattern, optionally surrounded by quotes
  let url = "";
  const urlMatch = normalized.match(/['"]?(https?:\/\/[^\s'"]+)['"]?/);
  if (urlMatch) {
    url = urlMatch[1];
  }

  if (!url) {
    throw new Error("Could not extract URL from cURL command");
  }

  // Extract method
  let explicitMethod = false;
  let method = "GET";
  const methodMatch = normalized.match(/(?:-X|--request)\s+['"]?(\w+)['"]?/i);
  if (methodMatch) {
    method = methodMatch[1].toUpperCase();
    explicitMethod = true;
  }

  // Extract headers - handle single and double quoted values separately to
  // avoid truncating at an inner quote of the opposite type
  const headers: Record<string, string> = {};
  const headerRegex =
    /(?:-H|--header)\s+(?:'((?:[^'\\]|\\.)*)'|"((?:[^"\\]|\\.)*)")/g;
  let headerMatch;
  while ((headerMatch = headerRegex.exec(normalized)) !== null) {
    const headerLine = headerMatch[1] ?? headerMatch[2];
    const colonIndex = headerLine.indexOf(":");
    if (colonIndex > 0) {
      const name = headerLine.substring(0, colonIndex).trim();
      const value = headerLine.substring(colonIndex + 1).trim();
      headers[name] = value;
    }
  }

  // Extract body/data - match single and double quoted bodies separately to
  // avoid stopping early at an inner quote of the opposite type.
  // Also handles --data-binary in addition to -d / --data / --data-raw.
  let body: string | undefined = undefined;
  const dataMatchSingle = normalized.match(
    /(?:-d|--data(?:-raw|-binary)?)\s+'((?:[^'\\]|\\.)*)'/
  );
  const dataMatchDouble = normalized.match(
    /(?:-d|--data(?:-raw|-binary)?)\s+"((?:[^"\\]|\\.)*)"/
  );
  const dataMatch = dataMatchSingle || dataMatchDouble;
  if (dataMatch) {
    body = dataMatch[1];
  }

  // Infer POST when a body is present and no explicit method flag was given,
  // matching curl's own behaviour
  if (body !== undefined && !explicitMethod) {
    method = "POST";
  }

  return { method, url, headers, body };
}

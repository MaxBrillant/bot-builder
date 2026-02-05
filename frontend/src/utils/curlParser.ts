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

export function parseCurlCommand(curlCommand: string): ParsedCurl {
  // Remove line continuations and normalize whitespace
  const normalized = curlCommand
    .replace(/\\\s*\n\s*/g, " ")
    .replace(/\s+/g, " ")
    .trim();

  // Extract URL (first argument after 'curl' that's not a flag)
  let url = "";
  const urlMatch = normalized.match(/curl\s+(?:-[^\s]+\s+)*['"]?([^\s'"]+)['"]?/);
  if (urlMatch) {
    url = urlMatch[1];
  } else {
    // Try to find URL anywhere in the command
    const urlPattern = /(https?:\/\/[^\s'"]+)/;
    const match = normalized.match(urlPattern);
    if (match) {
      url = match[1];
    }
  }

  if (!url) {
    throw new Error("Could not extract URL from cURL command");
  }

  // Extract method
  let method = "GET";
  const methodMatch = normalized.match(/(?:-X|--request)\s+['"]?(\w+)['"]?/i);
  if (methodMatch) {
    method = methodMatch[1].toUpperCase();
  }

  // Extract headers
  const headers: Record<string, string> = {};
  const headerRegex = /(?:-H|--header)\s+['"]([^'"]+)['"]/g;
  let headerMatch;
  while ((headerMatch = headerRegex.exec(normalized)) !== null) {
    const headerLine = headerMatch[1];
    const colonIndex = headerLine.indexOf(":");
    if (colonIndex > 0) {
      const name = headerLine.substring(0, colonIndex).trim();
      const value = headerLine.substring(colonIndex + 1).trim();
      headers[name] = value;
    }
  }

  // Extract body/data
  let body: string | undefined = undefined;
  const dataMatch = normalized.match(/(?:-d|--data|--data-raw)\s+['"](.+?)['"]/);
  if (dataMatch) {
    body = dataMatch[1];
  }

  return { method, url, headers, body };
}

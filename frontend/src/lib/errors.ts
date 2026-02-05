import { AxiosError } from 'axios';
import type { APIError } from './types';

/**
 * Type guard to check if an error is an Axios API error
 */
export function isAPIError(error: unknown): error is AxiosError<APIError> {
  return (
    error instanceof AxiosError &&
    error.response?.data !== undefined
  );
}

/**
 * Extract a user-friendly error message from any error type
 * Handles Axios errors, validation errors, and generic errors
 */
export function getErrorMessage(error: unknown): string {
  if (isAPIError(error)) {
    const data = error.response?.data;

    // Handle custom error format with errors array (from flow validation)
    if (data?.errors && Array.isArray(data.errors)) {
      return data.errors
        .map((err: any) => {
          // Use the message field if available
          if (err.message) {
            return err.location ? `${err.location}: ${err.message}` : err.message;
          }
          // Fallback to combining type and location
          return err.type || 'Validation error';
        })
        .join('; ');
    }

    // Handle custom error format with error field
    if (data?.error && typeof data.error === 'string') {
      return data.error;
    }

    const detail = data?.detail;

    // Handle array of validation errors (Pydantic)
    if (Array.isArray(detail)) {
      return detail
        .map((err) => {
          const location = err.loc?.join('.') || 'field';
          return `${location}: ${err.msg}`;
        })
        .join(', ');
    }

    // Handle string error message
    if (typeof detail === 'string') {
      return detail;
    }

    // Fallback to status text
    return error.response?.statusText || 'An error occurred';
  }

  // Handle standard Error objects
  if (error instanceof Error) {
    return error.message;
  }

  // Handle string errors
  if (typeof error === 'string') {
    return error;
  }

  // Fallback for unknown error types
  return 'An unexpected error occurred';
}

/**
 * Check if error is a network error (no response from server)
 */
export function isNetworkError(error: unknown): boolean {
  return (
    error instanceof AxiosError &&
    !error.response &&
    error.request !== undefined
  );
}

/**
 * Check if error is an authentication error (401)
 */
export function isAuthError(error: unknown): boolean {
  return isAPIError(error) && error.response?.status === 401;
}

/**
 * Check if error is a forbidden error (403)
 */
export function isForbiddenError(error: unknown): boolean {
  return isAPIError(error) && error.response?.status === 403;
}

/**
 * Check if error is a not found error (404)
 */
export function isNotFoundError(error: unknown): boolean {
  return isAPIError(error) && error.response?.status === 404;
}

/**
 * Check if error is a validation error (422)
 */
export function isValidationError(error: unknown): boolean {
  return isAPIError(error) && error.response?.status === 422;
}

/**
 * Check if error is a server error (5xx)
 */
export function isServerError(error: unknown): boolean {
  return (
    isAPIError(error) &&
    error.response?.status !== undefined &&
    error.response.status >= 500
  );
}

import { toast } from 'sonner';
import { getErrorMessage, isNetworkError, isAuthError, isServerError, isValidationError } from './errors';

/**
 * Handle error with toast notification
 * Provides user-friendly error messages based on error type
 */
export function handleError(error: unknown, fallbackMessage: string): void {
  // Network error (no response)
  if (isNetworkError(error)) {
    toast.error('Network Error', {
      description: 'Unable to connect to the server. Please check your internet connection.',
    });
    console.error('Network error:', error);
    return;
  }

  // Authentication error
  if (isAuthError(error)) {
    toast.error('Authentication Required', {
      description: 'Your session has expired. Please log in again.',
    });
    console.error('Auth error:', error);
    return;
  }

  // Server error
  if (isServerError(error)) {
    toast.error('Server Error', {
      description: 'The server encountered an error. Please try again later.',
    });
    console.error('Server error:', error);
    return;
  }

  // Validation error (422)
  if (isValidationError(error)) {
    const message = getErrorMessage(error);
    toast.error('Validation Error', {
      description: message || 'Please check your input and try again.',
    });
    console.error('Validation error:', error);
    return;
  }

  // Extract and display error message
  const message = getErrorMessage(error);
  toast.error(message || fallbackMessage);
  console.error(error);
}

/**
 * Handle error with rollback function
 * Useful for optimistic updates that need to be reverted on error
 */
export function handleErrorWithRollback(
  error: unknown,
  fallbackMessage: string,
  rollbackFn: () => void
): void {
  handleError(error, fallbackMessage);
  rollbackFn();
}

/**
 * Handle error with custom action
 * Allows providing a custom action button in the toast
 */
export function handleErrorWithAction(
  error: unknown,
  fallbackMessage: string,
  actionLabel: string,
  actionFn: () => void
): void {
  const message = getErrorMessage(error);

  toast.error(message || fallbackMessage, {
    action: {
      label: actionLabel,
      onClick: actionFn,
    },
  });

  console.error(error);
}

/**
 * Handle success with toast notification
 */
export function handleSuccess(message: string, description?: string): void {
  toast.success(message, description ? { description } : undefined);
}

/**
 * Handle info with toast notification
 */
export function handleInfo(message: string, description?: string): void {
  toast.info(message, description ? { description } : undefined);
}

/**
 * Handle warning with toast notification
 */
export function handleWarning(message: string, description?: string): void {
  toast.warning(message, description ? { description } : undefined);
}

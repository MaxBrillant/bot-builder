"""
Response utilities for API endpoints.

Provides standardized error response helpers for consistent API behavior.
"""

from fastapi import HTTPException, status


def error_response(
    status_code: int,
    detail: str
) -> HTTPException:
    """
    Create a standardized HTTPException for API error responses.

    Args:
        status_code: HTTP status code (e.g., status.HTTP_404_NOT_FOUND)
        detail: Human-readable error message

    Returns:
        HTTPException configured with the specified status and detail

    Example:
        raise error_response(status.HTTP_404_NOT_FOUND, "Bot not found")
        raise error_response(status.HTTP_403_FORBIDDEN, "Not authorized")
        raise error_response(status.HTTP_400_BAD_REQUEST, "Invalid input")
    """
    return HTTPException(status_code=status_code, detail=detail)


# Convenience helpers for common error types
def not_found(detail: str) -> HTTPException:
    """Return 404 Not Found error."""
    return error_response(status.HTTP_404_NOT_FOUND, detail)


def forbidden(detail: str) -> HTTPException:
    """Return 403 Forbidden error."""
    return error_response(status.HTTP_403_FORBIDDEN, detail)


def bad_request(detail: str) -> HTTPException:
    """Return 400 Bad Request error."""
    return error_response(status.HTTP_400_BAD_REQUEST, detail)


def unauthorized(detail: str) -> HTTPException:
    """Return 401 Unauthorized error."""
    return error_response(status.HTTP_401_UNAUTHORIZED, detail)


def too_many_requests(detail: str) -> HTTPException:
    """Return 429 Too Many Requests error."""
    return error_response(status.HTTP_429_TOO_MANY_REQUESTS, detail)


def service_unavailable(detail: str) -> HTTPException:
    """Return 503 Service Unavailable error."""
    return error_response(status.HTTP_503_SERVICE_UNAVAILABLE, detail)


def internal_server_error(detail: str) -> HTTPException:
    """Return 500 Internal Server Error."""
    return error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, detail)


def bad_gateway(detail: str) -> HTTPException:
    """Return 502 Bad Gateway error."""
    return error_response(status.HTTP_502_BAD_GATEWAY, detail)

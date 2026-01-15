"""
Structured Logging System
Provides logging with PII masking capabilities
"""

import logging
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from functools import wraps


class StructuredLogger:
    """Structured logger with PII masking"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    def _setup_logger(self):
        """Configure logger with formatter"""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def _create_log_entry(self, level: str, message: str, **kwargs) -> Dict[str, Any]:
        """Create structured log entry"""
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
        }
        
        # Add additional context
        if kwargs:
            log_data.update(kwargs)
        
        return log_data
    
    def mask_pii(self, value: str, mask_type: str = "user_id") -> str:
        """
        Mask personally identifiable information
        
        Args:
            value: The value to mask
            mask_type: Type of masking (user_id, email, generic)
        
        Returns:
            Masked string
        """
        if not value:
            return "XXXXX"
        
        if mask_type == "user_id":
            # Mask user ID (works for phone, Slack ID, etc): +254XXXXXX456 (show first 4 and last 3)
            if len(value) > 7:
                return value[:4] + "X" * (len(value) - 7) + value[-3:]
            return "XXXXX"
        
        elif mask_type == "email":
            # Mask email: j***@example.com
            if "@" in value:
                parts = value.split("@")
                local = parts[0]
                domain = parts[1]
                masked_local = local[0] + "***" if len(local) > 0 else "***"
                return f"{masked_local}@{domain}"
            return "X***X"
        
        else:  # generic
            # Show first and last character only
            if len(value) > 2:
                return value[0] + "X" * (len(value) - 2) + value[-1]
            return "XXX"
    
    def log(self, level: int, message: str, **kwargs):
        """Generic log method"""
        log_entry = self._create_log_entry(
            logging.getLevelName(level),
            message,
            **kwargs
        )
        self.logger.log(level, json.dumps(log_entry))
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self.log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        self.log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self.log(logging.CRITICAL, message, **kwargs)
    
    def log_user_action(self, user_id: str, action: str, **kwargs):
        """Log user action with masked user identifier"""
        self.info(
            f"User action: {action}",
            user_id=self.mask_pii(user_id, "user_id"),
            action=action,
            **kwargs
        )
    
    def log_flow_execution(self, flow_id: str, node_id: str, **kwargs):
        """Log flow execution step"""
        self.info(
            f"Flow execution: {flow_id}",
            flow_id=flow_id,
            node_id=node_id,
            **kwargs
        )
    
    def log_api_call(self, method: str, url: str, status_code: Optional[int] = None, **kwargs):
        """Log API call (without sensitive data)"""
        # Remove sensitive headers and body data
        safe_kwargs = {k: v for k, v in kwargs.items() 
                      if k not in ['authorization', 'api_key', 'password', 'token']}
        
        self.info(
            f"API call: {method} {url}",
            method=method,
            url=url,
            status_code=status_code,
            **safe_kwargs
        )
    
    def log_validation_failure(self, node_id: str, attempt: int, **kwargs):
        """Log validation failure"""
        self.warning(
            f"Validation failed: {node_id}",
            node_id=node_id,
            attempt=attempt,
            **kwargs
        )
    
    def log_session_event(self, session_id: str, event: str, **kwargs):
        """Log session lifecycle event"""
        self.info(
            f"Session {event}",
            session_id=session_id,
            event=event,
            **kwargs
        )

    def log_security_event(self, event: str, user_id: Optional[str] = None, **kwargs):
        """
        Log security-related event

        Args:
            event: Security event description
            user_id: Optional user identifier (will be masked)
            **kwargs: Additional context
        """
        log_data = {
            "event": event,
            "security_event": True,
            **kwargs
        }

        if user_id:
            log_data["user_id"] = self.mask_pii(user_id, "user_id")

        self.warning(f"Security event: {event}", **log_data)

    def log_authentication_event(self, action: str, user_id: Optional[str] = None, result: str = "success", **kwargs):
        """
        Log authentication event

        Args:
            action: Auth action (login, logout, token_refresh, etc.)
            user_id: Optional user identifier (will be masked)
            result: Result of action (success, failed, blocked)
            **kwargs: Additional context
        """
        log_data = {
            "action": action,
            "result": result,
            "auth_event": True,
            **kwargs
        }

        if user_id:
            log_data["user_id"] = self.mask_pii(user_id, "user_id")

        if result == "success":
            self.info(f"Authentication: {action}", **log_data)
        else:
            self.warning(f"Authentication failed: {action}", **log_data)


def get_logger(name: str) -> StructuredLogger:
    """Get or create a logger instance"""
    return StructuredLogger(name)


# Create default logger
logger = get_logger("bot_builder")


def log_execution_time(logger_instance: Optional[StructuredLogger] = None):
    """Decorator to log function execution time"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = datetime.now(timezone.utc)
            try:
                result = await func(*args, **kwargs)
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                (logger_instance or logger).debug(
                    f"{func.__name__} completed",
                    function=func.__name__,
                    duration_seconds=duration
                )
                return result
            except Exception as e:
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                (logger_instance or logger).error(
                    f"{func.__name__} failed",
                    function=func.__name__,
                    duration_seconds=duration,
                    error=str(e)
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = datetime.now(timezone.utc)
            try:
                result = func(*args, **kwargs)
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                (logger_instance or logger).debug(
                    f"{func.__name__} completed",
                    function=func.__name__,
                    duration_seconds=duration
                )
                return result
            except Exception as e:
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                (logger_instance or logger).error(
                    f"{func.__name__} failed",
                    function=func.__name__,
                    duration_seconds=duration,
                    error=str(e)
                )
                raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator
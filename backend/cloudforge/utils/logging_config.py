"""
Structured logging configuration for CloudForge Bug Intelligence.

Provides JSON-formatted logging with CloudWatch integration, context fields,
and sensitive data sanitization.
"""

import logging
import json
import re
from datetime import datetime
from typing import Any, Dict, Optional
from logging import LogRecord


class SensitiveDataFilter(logging.Filter):
    """
    Filter to sanitize sensitive data from log records.
    
    Removes API keys, passwords, tokens, and other credentials from log messages
    and extra fields to comply with security requirements.
    """
    
    # Patterns for sensitive data
    SENSITIVE_PATTERNS = [
        (r'api[_-]?key["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-]+)', '[API_KEY_REDACTED]'),
        (r'password["\']?\s*[:=]\s*["\']?([^\s"\']+)', '[PASSWORD_REDACTED]'),
        (r'token["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-\.]+)', '[TOKEN_REDACTED]'),
        (r'secret["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-]+)', '[SECRET_REDACTED]'),
        (r'authorization:\s*bearer\s+([a-zA-Z0-9_\-\.]+)', 'Authorization: Bearer [TOKEN_REDACTED]'),
        (r'aws_access_key_id["\']?\s*[:=]\s*["\']?([A-Z0-9]+)', '[AWS_KEY_REDACTED]'),
        (r'aws_secret_access_key["\']?\s*[:=]\s*["\']?([a-zA-Z0-9/+]+)', '[AWS_SECRET_REDACTED]'),
    ]
    
    def filter(self, record: LogRecord) -> bool:
        """
        Sanitize sensitive data from log record.
        
        Args:
            record: Log record to filter
            
        Returns:
            True (always allow record, just sanitize it)
        """
        # Sanitize message
        if isinstance(record.msg, str):
            record.msg = self._sanitize_string(record.msg)
        
        # Sanitize args
        if record.args:
            record.args = tuple(
                self._sanitize_string(arg) if isinstance(arg, str) else arg
                for arg in record.args
            )
        
        # Sanitize extra fields - need to create a list of keys first to avoid dict size change during iteration
        if hasattr(record, '__dict__'):
            keys_to_sanitize = [
                key for key in record.__dict__.keys()
                if not key.startswith('_') and key not in [
                    'name', 'msg', 'args', 'created', 'filename', 'funcName',
                    'levelname', 'levelno', 'lineno', 'module', 'msecs',
                    'message', 'pathname', 'process', 'processName', 'relativeCreated',
                    'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info'
                ]
            ]
            
            for key in keys_to_sanitize:
                value = getattr(record, key, None)
                if isinstance(value, str):
                    setattr(record, key, self._sanitize_string(value))
                elif isinstance(value, dict):
                    setattr(record, key, self._sanitize_dict(value))
        
        return True
    
    def _sanitize_string(self, text: str) -> str:
        """Sanitize sensitive data from a string."""
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text
    
    def _sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize sensitive data from a dictionary."""
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = self._sanitize_string(value)
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_dict(value)
            else:
                sanitized[key] = value
        return sanitized


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    
    Formats log records as JSON with standard fields plus custom context fields
    for workflow tracking and debugging.
    """
    
    def format(self, record: LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON-formatted log string
        """
        # Build base log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add stack trace if present
        if record.stack_info:
            log_entry["stack_trace"] = self.formatStack(record.stack_info)
        
        # Add custom context fields
        context_fields = [
            "workflow_id",
            "agent_name",
            "action",
            "status",
            "bug_id",
            "test_id",
            "execution_time_ms",
            "error_type",
            "retry_count"
        ]
        
        for field in context_fields:
            if hasattr(record, field):
                log_entry[field] = getattr(record, field)
        
        # Add any other extra fields
        for key, value in record.__dict__.items():
            if key not in log_entry and not key.startswith('_') and key not in [
                'name', 'msg', 'args', 'created', 'filename', 'funcName',
                'levelname', 'levelno', 'lineno', 'module', 'msecs',
                'message', 'pathname', 'process', 'processName', 'relativeCreated',
                'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info'
            ]:
                log_entry[key] = value
        
        return json.dumps(log_entry)


def configure_logging(
    log_level: str = "INFO",
    enable_cloudwatch: bool = False,
    cloudwatch_log_group: Optional[str] = None,
    cloudwatch_stream_name: Optional[str] = None
) -> None:
    """
    Configure structured logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_cloudwatch: Whether to enable CloudWatch logging
        cloudwatch_log_group: CloudWatch log group name
        cloudwatch_stream_name: CloudWatch log stream name
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Create console handler with JSON formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JSONFormatter())
    console_handler.addFilter(SensitiveDataFilter())
    root_logger.addHandler(console_handler)
    
    # Add CloudWatch handler if enabled
    if enable_cloudwatch and cloudwatch_log_group and cloudwatch_stream_name:
        try:
            import watchtower
            
            cloudwatch_handler = watchtower.CloudWatchLogHandler(
                log_group=cloudwatch_log_group,
                stream_name=cloudwatch_stream_name,
                use_queues=True,
                send_interval=5,
                max_batch_count=100
            )
            cloudwatch_handler.setFormatter(JSONFormatter())
            cloudwatch_handler.addFilter(SensitiveDataFilter())
            root_logger.addHandler(cloudwatch_handler)
            
            root_logger.info(
                "CloudWatch logging enabled",
                extra={
                    "log_group": cloudwatch_log_group,
                    "stream_name": cloudwatch_stream_name
                }
            )
        except ImportError:
            root_logger.warning(
                "CloudWatch logging requested but watchtower not installed. "
                "Install with: pip install watchtower"
            )
        except Exception as e:
            root_logger.error(
                f"Failed to configure CloudWatch logging: {e}",
                exc_info=True
            )
    
    # Log configuration complete
    root_logger.info(
        "Logging configured",
        extra={
            "log_level": log_level,
            "cloudwatch_enabled": enable_cloudwatch
        }
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)

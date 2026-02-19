"""
Unit tests for structured logging configuration.

Tests JSON formatting, sensitive data sanitization, and CloudWatch integration.
"""

import pytest
import logging
import json
from io import StringIO

from cloudforge.utils.logging_config import (
    SensitiveDataFilter,
    JSONFormatter,
    configure_logging,
    get_logger
)


@pytest.fixture
def log_record():
    """Create a sample log record for testing."""
    logger = logging.getLogger("test")
    return logger.makeRecord(
        name="test",
        level=logging.INFO,
        fn="test.py",
        lno=10,
        msg="Test message",
        args=(),
        exc_info=None
    )


def test_sensitive_data_filter_sanitizes_api_keys(log_record):
    """Test that API keys are sanitized from log messages."""
    log_record.msg = "Using api_key=abc123def456 for authentication"
    
    filter_obj = SensitiveDataFilter()
    filter_obj.filter(log_record)
    
    assert "abc123def456" not in log_record.msg
    assert "[API_KEY_REDACTED]" in log_record.msg


def test_sensitive_data_filter_sanitizes_passwords(log_record):
    """Test that passwords are sanitized from log messages."""
    log_record.msg = "Login with password=secret123"
    
    filter_obj = SensitiveDataFilter()
    filter_obj.filter(log_record)
    
    assert "secret123" not in log_record.msg
    assert "[PASSWORD_REDACTED]" in log_record.msg


def test_sensitive_data_filter_sanitizes_tokens(log_record):
    """Test that tokens are sanitized from log messages."""
    log_record.msg = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    
    filter_obj = SensitiveDataFilter()
    filter_obj.filter(log_record)
    
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in log_record.msg
    assert "[TOKEN_REDACTED]" in log_record.msg


def test_sensitive_data_filter_sanitizes_aws_credentials(log_record):
    """Test that AWS credentials are sanitized from log messages."""
    log_record.msg = "Using aws_access_key_id=AKIAIOSFODNN7EXAMPLE"
    
    filter_obj = SensitiveDataFilter()
    filter_obj.filter(log_record)
    
    assert "AKIAIOSFODNN7EXAMPLE" not in log_record.msg
    assert "[AWS_KEY_REDACTED]" in log_record.msg


def test_sensitive_data_filter_sanitizes_extra_fields(log_record):
    """Test that sensitive data is sanitized from extra fields."""
    log_record.credentials = "api_key=secret_key_123"
    
    filter_obj = SensitiveDataFilter()
    filter_obj.filter(log_record)
    
    assert "secret_key_123" not in log_record.credentials
    assert "[API_KEY_REDACTED]" in log_record.credentials


def test_sensitive_data_filter_sanitizes_dict_values(log_record):
    """Test that sensitive data is sanitized from dictionary values."""
    log_record.config = {"credentials": "api_key=secret123", "endpoint": "https://api.example.com"}
    
    filter_obj = SensitiveDataFilter()
    filter_obj.filter(log_record)
    
    assert "secret123" not in log_record.config["credentials"]
    assert "[API_KEY_REDACTED]" in log_record.config["credentials"]
    assert log_record.config["endpoint"] == "https://api.example.com"


def test_json_formatter_creates_valid_json(log_record):
    """Test that JSONFormatter produces valid JSON output."""
    formatter = JSONFormatter()
    output = formatter.format(log_record)
    
    # Should be valid JSON
    parsed = json.loads(output)
    
    assert isinstance(parsed, dict)
    assert "timestamp" in parsed
    assert "level" in parsed
    assert "message" in parsed


def test_json_formatter_includes_standard_fields(log_record):
    """Test that JSONFormatter includes all standard fields."""
    formatter = JSONFormatter()
    output = formatter.format(log_record)
    parsed = json.loads(output)
    
    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "test"
    assert parsed["message"] == "Test message"
    assert parsed["module"] == "test"
    assert parsed["line"] == 10


def test_json_formatter_includes_context_fields(log_record):
    """Test that JSONFormatter includes custom context fields."""
    log_record.workflow_id = "wf-123"
    log_record.agent_name = "bug_detective"
    log_record.action = "scan_file"
    log_record.status = "success"
    
    formatter = JSONFormatter()
    output = formatter.format(log_record)
    parsed = json.loads(output)
    
    assert parsed["workflow_id"] == "wf-123"
    assert parsed["agent_name"] == "bug_detective"
    assert parsed["action"] == "scan_file"
    assert parsed["status"] == "success"


def test_json_formatter_includes_exception_info():
    """Test that JSONFormatter includes exception information."""
    logger = logging.getLogger("test")
    
    try:
        raise ValueError("Test error")
    except ValueError:
        import sys
        record = logger.makeRecord(
            name="test",
            level=logging.ERROR,
            fn="test.py",
            lno=10,
            msg="Error occurred",
            args=(),
            exc_info=sys.exc_info()
        )
    
    formatter = JSONFormatter()
    output = formatter.format(record)
    parsed = json.loads(output)
    
    assert "exception" in parsed
    assert "ValueError" in parsed["exception"]
    assert "Test error" in parsed["exception"]


def test_configure_logging_sets_log_level():
    """Test that configure_logging sets the correct log level."""
    configure_logging(log_level="DEBUG")
    
    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG


def test_configure_logging_adds_console_handler():
    """Test that configure_logging adds a console handler."""
    configure_logging(log_level="INFO")
    
    root_logger = logging.getLogger()
    assert len(root_logger.handlers) > 0
    
    # Check that at least one handler is a StreamHandler
    has_stream_handler = any(
        isinstance(h, logging.StreamHandler) for h in root_logger.handlers
    )
    assert has_stream_handler


def test_configure_logging_adds_json_formatter():
    """Test that configure_logging adds JSON formatter to handlers."""
    configure_logging(log_level="INFO")
    
    root_logger = logging.getLogger()
    
    # Check that at least one handler has JSONFormatter
    has_json_formatter = any(
        isinstance(h.formatter, JSONFormatter) for h in root_logger.handlers
    )
    assert has_json_formatter


def test_configure_logging_adds_sensitive_data_filter():
    """Test that configure_logging adds sensitive data filter to handlers."""
    configure_logging(log_level="INFO")
    
    root_logger = logging.getLogger()
    
    # Check that at least one handler has SensitiveDataFilter
    has_sensitive_filter = any(
        any(isinstance(f, SensitiveDataFilter) for f in h.filters)
        for h in root_logger.handlers
    )
    assert has_sensitive_filter


def test_get_logger_returns_logger():
    """Test that get_logger returns a logger instance."""
    logger = get_logger("test_module")
    
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_module"


def test_logging_produces_valid_json_output():
    """Test that actual logging produces valid JSON output."""
    # Capture log output
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JSONFormatter())
    handler.addFilter(SensitiveDataFilter())
    
    logger = logging.getLogger("test_json_output")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
    # Log a message
    logger.info("Test message", extra={"workflow_id": "wf-123"})
    
    # Get output and parse as JSON
    output = stream.getvalue()
    parsed = json.loads(output.strip())
    
    assert parsed["message"] == "Test message"
    assert parsed["workflow_id"] == "wf-123"


def test_logging_sanitizes_sensitive_data_in_output():
    """Test that actual logging sanitizes sensitive data."""
    # Capture log output
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JSONFormatter())
    handler.addFilter(SensitiveDataFilter())
    
    logger = logging.getLogger("test_sanitize")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
    # Log a message with sensitive data
    logger.info("Using api_key=secret123 for authentication")
    
    # Get output
    output = stream.getvalue()
    
    assert "secret123" not in output
    assert "[API_KEY_REDACTED]" in output


def test_sensitive_data_filter_handles_multiple_patterns():
    """Test that filter handles multiple sensitive patterns in one message."""
    log_record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Config: api_key=abc123 password=secret token=xyz789",
        args=(),
        exc_info=None
    )
    
    filter_obj = SensitiveDataFilter()
    filter_obj.filter(log_record)
    
    assert "abc123" not in log_record.msg
    assert "secret" not in log_record.msg
    assert "xyz789" not in log_record.msg
    assert "[API_KEY_REDACTED]" in log_record.msg
    assert "[PASSWORD_REDACTED]" in log_record.msg
    assert "[TOKEN_REDACTED]" in log_record.msg


def test_json_formatter_handles_non_string_extra_fields():
    """Test that JSONFormatter handles non-string extra fields correctly."""
    log_record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test message",
        args=(),
        exc_info=None
    )
    log_record.count = 42
    log_record.is_valid = True
    log_record.items = ["a", "b", "c"]
    
    formatter = JSONFormatter()
    output = formatter.format(log_record)
    parsed = json.loads(output)
    
    assert parsed["count"] == 42
    assert parsed["is_valid"] is True
    assert parsed["items"] == ["a", "b", "c"]

"""
Unit tests for SNS notification service.

Tests notifications for workflow failures, agent crashes, cost alerts,
and infrastructure failures.
"""

import pytest
import json
from unittest.mock import MagicMock

from cloudforge.utils.notifications import NotificationService


@pytest.fixture
def mock_sns():
    """Create mock SNS client."""
    sns = MagicMock()
    sns.publish.return_value = {"MessageId": "test-message-id-123"}
    return sns


@pytest.fixture
def notification_service(mock_sns):
    """Create notification service with mock SNS client."""
    return NotificationService(
        sns_client=mock_sns,
        topic_arn="arn:aws:sns:us-east-1:123456789012:cloudforge-alerts"
    )


@pytest.fixture
def notification_service_mock_mode():
    """Create notification service in mock mode (no SNS client)."""
    return NotificationService(
        sns_client=None,
        topic_arn=None
    )


def test_notification_service_initialization_with_sns(mock_sns):
    """Test notification service initializes with SNS client."""
    topic_arn = "arn:aws:sns:us-east-1:123456789012:test-topic"
    service = NotificationService(
        sns_client=mock_sns,
        topic_arn=topic_arn
    )
    
    assert service.sns == mock_sns
    assert service.topic_arn == topic_arn
    assert service.sns_enabled is True


def test_notification_service_initialization_without_sns():
    """Test notification service initializes in mock mode without SNS."""
    service = NotificationService(
        sns_client=None,
        topic_arn=None
    )
    
    assert service.sns is None
    assert service.topic_arn is None
    assert service.sns_enabled is False


def test_notify_workflow_failure(notification_service, mock_sns):
    """Test sending workflow failure notification."""
    result = notification_service.notify_workflow_failure(
        workflow_id="wf-123",
        repository_url="https://github.com/test/repo",
        error_message="Agent execution failed",
        current_agent="bug_detective",
        additional_context={"retry_count": 3}
    )
    
    assert result is True
    assert mock_sns.publish.call_count == 1
    
    # Verify SNS publish call
    call_args = mock_sns.publish.call_args
    assert call_args[1]["TopicArn"] == "arn:aws:sns:us-east-1:123456789012:cloudforge-alerts"
    assert "[CRITICAL]" in call_args[1]["Subject"]
    assert "wf-123" in call_args[1]["Subject"]
    
    # Verify message content
    message = json.loads(call_args[1]["Message"])
    assert message["alert_type"] == "workflow_failure"
    assert message["severity"] == "critical"
    assert message["workflow_id"] == "wf-123"
    assert message["repository_url"] == "https://github.com/test/repo"
    assert message["current_agent"] == "bug_detective"
    assert message["error_message"] == "Agent execution failed"
    assert message["additional_context"]["retry_count"] == 3
    
    # Verify message attributes
    attributes = call_args[1]["MessageAttributes"]
    assert attributes["alert_type"]["StringValue"] == "workflow_failure"
    assert attributes["severity"]["StringValue"] == "critical"


def test_notify_agent_crash(notification_service, mock_sns):
    """Test sending agent crash notification."""
    result = notification_service.notify_agent_crash(
        agent_name="test_architect",
        workflow_id="wf-456",
        error_type="RuntimeError",
        error_message="Unexpected error in test generation",
        stack_trace="Traceback (most recent call last)...",
        additional_context={"input_bugs": 5}
    )
    
    assert result is True
    assert mock_sns.publish.call_count == 1
    
    call_args = mock_sns.publish.call_args
    assert "[CRITICAL]" in call_args[1]["Subject"]
    assert "test_architect" in call_args[1]["Subject"]
    
    message = json.loads(call_args[1]["Message"])
    assert message["alert_type"] == "agent_crash"
    assert message["severity"] == "critical"
    assert message["agent_name"] == "test_architect"
    assert message["workflow_id"] == "wf-456"
    assert message["error_type"] == "RuntimeError"
    assert message["stack_trace"] == "Traceback (most recent call last)..."


def test_notify_cost_threshold_alert_warning(notification_service, mock_sns):
    """Test sending cost threshold warning notification."""
    result = notification_service.notify_cost_threshold_alert(
        current_cost=85.50,
        threshold=100.0,
        threshold_percentage=85.5,
        cost_breakdown={"Bedrock": 60.0, "Lambda": 15.5, "ECS": 10.0},
        additional_context={"period": "monthly"}
    )
    
    assert result is True
    assert mock_sns.publish.call_count == 1
    
    call_args = mock_sns.publish.call_args
    assert "[WARNING]" in call_args[1]["Subject"]
    assert "85.5%" in call_args[1]["Subject"]
    
    message = json.loads(call_args[1]["Message"])
    assert message["alert_type"] == "cost_threshold"
    assert message["severity"] == "warning"
    assert message["current_cost"] == 85.50
    assert message["threshold"] == 100.0
    assert message["threshold_percentage"] == 85.5
    assert message["cost_breakdown"]["Bedrock"] == 60.0


def test_notify_cost_threshold_alert_critical(notification_service, mock_sns):
    """Test sending cost threshold critical notification."""
    result = notification_service.notify_cost_threshold_alert(
        current_cost=105.0,
        threshold=100.0,
        threshold_percentage=105.0
    )
    
    assert result is True
    
    call_args = mock_sns.publish.call_args
    assert "[CRITICAL]" in call_args[1]["Subject"]
    
    message = json.loads(call_args[1]["Message"])
    assert message["severity"] == "critical"


def test_notify_infrastructure_failure(notification_service, mock_sns):
    """Test sending infrastructure failure notification."""
    result = notification_service.notify_infrastructure_failure(
        service_name="Lambda",
        failure_type="ThrottlingException",
        error_message="Rate exceeded",
        workflow_id="wf-789",
        additional_context={"region": "us-east-1"}
    )
    
    assert result is True
    assert mock_sns.publish.call_count == 1
    
    call_args = mock_sns.publish.call_args
    assert "[CRITICAL]" in call_args[1]["Subject"]
    assert "Lambda" in call_args[1]["Subject"]
    
    message = json.loads(call_args[1]["Message"])
    assert message["alert_type"] == "infrastructure_failure"
    assert message["severity"] == "critical"
    assert message["service_name"] == "Lambda"
    assert message["failure_type"] == "ThrottlingException"
    assert message["workflow_id"] == "wf-789"


def test_notify_circuit_breaker_open(notification_service, mock_sns):
    """Test sending circuit breaker open notification."""
    result = notification_service.notify_circuit_breaker_open(
        service_name="bedrock",
        failure_count=5,
        time_window_seconds=60,
        additional_context={"threshold": 5}
    )
    
    assert result is True
    assert mock_sns.publish.call_count == 1
    
    call_args = mock_sns.publish.call_args
    assert "[WARNING]" in call_args[1]["Subject"]
    assert "bedrock" in call_args[1]["Subject"]
    
    message = json.loads(call_args[1]["Message"])
    assert message["alert_type"] == "circuit_breaker_open"
    assert message["severity"] == "warning"
    assert message["service_name"] == "bedrock"
    assert message["failure_count"] == 5
    assert message["time_window_seconds"] == 60


def test_send_custom_notification(notification_service, mock_sns):
    """Test sending custom notification."""
    result = notification_service.send_custom_notification(
        subject="Test Notification",
        message="This is a test message",
        severity="info",
        additional_attributes={"custom_field": "custom_value"}
    )
    
    assert result is True
    assert mock_sns.publish.call_count == 1
    
    call_args = mock_sns.publish.call_args
    assert call_args[1]["Subject"] == "Test Notification"
    assert call_args[1]["Message"] == "This is a test message"
    
    attributes = call_args[1]["MessageAttributes"]
    assert attributes["severity"]["StringValue"] == "info"
    assert attributes["custom_field"]["StringValue"] == "custom_value"


def test_mock_mode_does_not_call_sns(notification_service_mock_mode):
    """Test that mock mode does not call SNS."""
    result = notification_service_mock_mode.notify_workflow_failure(
        workflow_id="wf-mock",
        repository_url="https://github.com/test/repo",
        error_message="Test error",
        current_agent="test_agent"
    )
    
    # Should return True even in mock mode
    assert result is True


def test_notification_handles_sns_error(notification_service, mock_sns):
    """Test that notification handles SNS errors gracefully."""
    # Make SNS raise an exception
    mock_sns.publish.side_effect = Exception("SNS error")
    
    result = notification_service.notify_workflow_failure(
        workflow_id="wf-error",
        repository_url="https://github.com/test/repo",
        error_message="Test error",
        current_agent="test_agent"
    )
    
    # Should return False on error
    assert result is False
    assert mock_sns.publish.call_count == 1


def test_notification_includes_timestamp(notification_service, mock_sns):
    """Test that notifications include timestamp."""
    notification_service.notify_agent_crash(
        agent_name="test_agent",
        workflow_id="wf-time",
        error_type="TestError",
        error_message="Test"
    )
    
    call_args = mock_sns.publish.call_args
    message = json.loads(call_args[1]["Message"])
    
    assert "timestamp" in message
    assert message["timestamp"].endswith("Z")


def test_notification_without_additional_context(notification_service, mock_sns):
    """Test notification without additional context."""
    result = notification_service.notify_workflow_failure(
        workflow_id="wf-no-context",
        repository_url="https://github.com/test/repo",
        error_message="Test error",
        current_agent="test_agent"
    )
    
    assert result is True
    
    call_args = mock_sns.publish.call_args
    message = json.loads(call_args[1]["Message"])
    
    assert message["additional_context"] == {}


def test_notification_without_optional_fields(notification_service, mock_sns):
    """Test notification without optional fields."""
    result = notification_service.notify_agent_crash(
        agent_name="test_agent",
        workflow_id="wf-minimal",
        error_type="TestError",
        error_message="Test"
    )
    
    assert result is True
    
    call_args = mock_sns.publish.call_args
    message = json.loads(call_args[1]["Message"])
    
    assert message["stack_trace"] is None
    assert message["additional_context"] == {}


def test_message_is_valid_json(notification_service, mock_sns):
    """Test that notification message is valid JSON."""
    notification_service.notify_workflow_failure(
        workflow_id="wf-json",
        repository_url="https://github.com/test/repo",
        error_message="Test error",
        current_agent="test_agent"
    )
    
    call_args = mock_sns.publish.call_args
    message_str = call_args[1]["Message"]
    
    # Should be valid JSON
    message = json.loads(message_str)
    assert isinstance(message, dict)


def test_topic_arn_is_used(notification_service, mock_sns):
    """Test that configured topic ARN is used."""
    notification_service.notify_workflow_failure(
        workflow_id="wf-arn",
        repository_url="https://github.com/test/repo",
        error_message="Test error",
        current_agent="test_agent"
    )
    
    call_args = mock_sns.publish.call_args
    assert call_args[1]["TopicArn"] == "arn:aws:sns:us-east-1:123456789012:cloudforge-alerts"


def test_custom_notification_without_additional_attributes(notification_service, mock_sns):
    """Test custom notification without additional attributes."""
    result = notification_service.send_custom_notification(
        subject="Test",
        message="Test message",
        severity="info"
    )
    
    assert result is True
    
    call_args = mock_sns.publish.call_args
    attributes = call_args[1]["MessageAttributes"]
    
    # Should only have severity attribute
    assert "severity" in attributes
    assert attributes["severity"]["StringValue"] == "info"

"""
Unit tests for CloudWatch metrics publisher.

Tests metrics publishing for agent execution times, success rates, API calls,
and circuit breaker states.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, call

from cloudforge.utils.metrics import MetricsPublisher


@pytest.fixture
def mock_cloudwatch():
    """Create mock CloudWatch client."""
    return MagicMock()


@pytest.fixture
def metrics_publisher(mock_cloudwatch):
    """Create metrics publisher with mock CloudWatch client."""
    return MetricsPublisher(
        cloudwatch_client=mock_cloudwatch,
        namespace="CloudForge/BugIntelligence"
    )


@pytest.fixture
def metrics_publisher_mock_mode():
    """Create metrics publisher in mock mode (no CloudWatch client)."""
    return MetricsPublisher(
        cloudwatch_client=None,
        namespace="CloudForge/BugIntelligence"
    )


def test_metrics_publisher_initialization_with_client(mock_cloudwatch):
    """Test metrics publisher initializes with CloudWatch client."""
    publisher = MetricsPublisher(
        cloudwatch_client=mock_cloudwatch,
        namespace="TestNamespace"
    )
    
    assert publisher.cloudwatch == mock_cloudwatch
    assert publisher.namespace == "TestNamespace"
    assert publisher.cloudwatch_enabled is True


def test_metrics_publisher_initialization_without_client():
    """Test metrics publisher initializes in mock mode without client."""
    publisher = MetricsPublisher(
        cloudwatch_client=None,
        namespace="TestNamespace"
    )
    
    assert publisher.cloudwatch is None
    assert publisher.namespace == "TestNamespace"
    assert publisher.cloudwatch_enabled is False


def test_publish_agent_execution_time(metrics_publisher, mock_cloudwatch):
    """Test publishing agent execution time metric."""
    metrics_publisher.publish_agent_execution_time(
        agent_name="bug_detective",
        execution_time_ms=1500,
        workflow_id="wf-123"
    )
    
    # Verify CloudWatch was called
    assert mock_cloudwatch.put_metric_data.call_count == 1
    
    # Verify metric data
    call_args = mock_cloudwatch.put_metric_data.call_args
    assert call_args[1]["Namespace"] == "CloudForge/BugIntelligence"
    
    metric_data = call_args[1]["MetricData"][0]
    assert metric_data["MetricName"] == "AgentExecutionTime"
    assert metric_data["Value"] == 1500
    assert metric_data["Unit"] == "Milliseconds"
    
    # Verify dimensions
    dimensions = {d["Name"]: d["Value"] for d in metric_data["Dimensions"]}
    assert dimensions["AgentName"] == "bug_detective"
    assert dimensions["WorkflowId"] == "wf-123"


def test_publish_agent_execution_time_with_custom_dimensions(metrics_publisher, mock_cloudwatch):
    """Test publishing agent execution time with custom dimensions."""
    metrics_publisher.publish_agent_execution_time(
        agent_name="test_architect",
        execution_time_ms=2000,
        workflow_id="wf-456",
        dimensions={"Environment": "production", "Region": "us-east-1"}
    )
    
    call_args = mock_cloudwatch.put_metric_data.call_args
    metric_data = call_args[1]["MetricData"][0]
    
    dimensions = {d["Name"]: d["Value"] for d in metric_data["Dimensions"]}
    assert dimensions["AgentName"] == "test_architect"
    assert dimensions["WorkflowId"] == "wf-456"
    assert dimensions["Environment"] == "production"
    assert dimensions["Region"] == "us-east-1"


def test_publish_agent_success(metrics_publisher, mock_cloudwatch):
    """Test publishing agent success metric."""
    metrics_publisher.publish_agent_success(
        agent_name="execution",
        workflow_id="wf-789"
    )
    
    call_args = mock_cloudwatch.put_metric_data.call_args
    metric_data = call_args[1]["MetricData"][0]
    
    assert metric_data["MetricName"] == "AgentSuccess"
    assert metric_data["Value"] == 1
    assert metric_data["Unit"] == "Count"
    
    dimensions = {d["Name"]: d["Value"] for d in metric_data["Dimensions"]}
    assert dimensions["AgentName"] == "execution"
    assert dimensions["WorkflowId"] == "wf-789"
    assert dimensions["Status"] == "Success"


def test_publish_agent_failure(metrics_publisher, mock_cloudwatch):
    """Test publishing agent failure metric."""
    metrics_publisher.publish_agent_failure(
        agent_name="analysis",
        workflow_id="wf-101",
        error_type="APIError"
    )
    
    call_args = mock_cloudwatch.put_metric_data.call_args
    metric_data = call_args[1]["MetricData"][0]
    
    assert metric_data["MetricName"] == "AgentFailure"
    assert metric_data["Value"] == 1
    assert metric_data["Unit"] == "Count"
    
    dimensions = {d["Name"]: d["Value"] for d in metric_data["Dimensions"]}
    assert dimensions["AgentName"] == "analysis"
    assert dimensions["WorkflowId"] == "wf-101"
    assert dimensions["Status"] == "Failure"
    assert dimensions["ErrorType"] == "APIError"


def test_publish_api_call_count(metrics_publisher, mock_cloudwatch):
    """Test publishing API call count metric."""
    metrics_publisher.publish_api_call_count(
        service_name="Bedrock",
        operation="InvokeModel",
        count=5
    )
    
    call_args = mock_cloudwatch.put_metric_data.call_args
    metric_data = call_args[1]["MetricData"][0]
    
    assert metric_data["MetricName"] == "APICallCount"
    assert metric_data["Value"] == 5
    assert metric_data["Unit"] == "Count"
    
    dimensions = {d["Name"]: d["Value"] for d in metric_data["Dimensions"]}
    assert dimensions["ServiceName"] == "Bedrock"
    assert dimensions["Operation"] == "InvokeModel"


def test_publish_execution_duration(metrics_publisher, mock_cloudwatch):
    """Test publishing execution duration metric."""
    metrics_publisher.publish_execution_duration(
        platform="lambda",
        duration_ms=3000,
        workflow_id="wf-202"
    )
    
    call_args = mock_cloudwatch.put_metric_data.call_args
    metric_data = call_args[1]["MetricData"][0]
    
    assert metric_data["MetricName"] == "ExecutionDuration"
    assert metric_data["Value"] == 3000
    assert metric_data["Unit"] == "Milliseconds"
    
    dimensions = {d["Name"]: d["Value"] for d in metric_data["Dimensions"]}
    assert dimensions["Platform"] == "lambda"
    assert dimensions["WorkflowId"] == "wf-202"


def test_publish_circuit_breaker_state_open(metrics_publisher, mock_cloudwatch):
    """Test publishing circuit breaker state when open."""
    metrics_publisher.publish_circuit_breaker_state(
        service_name="bedrock",
        state="open",
        failure_count=5
    )
    
    # Should publish 2 metrics: state and failure count
    assert mock_cloudwatch.put_metric_data.call_count == 2
    
    # Check first call (state metric)
    first_call = mock_cloudwatch.put_metric_data.call_args_list[0]
    state_metric = first_call[1]["MetricData"][0]
    
    assert state_metric["MetricName"] == "CircuitBreakerState"
    assert state_metric["Value"] == 1  # 1 for open
    
    # Check second call (failure count metric)
    second_call = mock_cloudwatch.put_metric_data.call_args_list[1]
    failure_metric = second_call[1]["MetricData"][0]
    
    assert failure_metric["MetricName"] == "CircuitBreakerFailures"
    assert failure_metric["Value"] == 5


def test_publish_circuit_breaker_state_closed(metrics_publisher, mock_cloudwatch):
    """Test publishing circuit breaker state when closed."""
    metrics_publisher.publish_circuit_breaker_state(
        service_name="bedrock",
        state="closed",
        failure_count=0
    )
    
    # Should publish only 1 metric (state, no failures)
    assert mock_cloudwatch.put_metric_data.call_count == 1
    
    call_args = mock_cloudwatch.put_metric_data.call_args
    metric_data = call_args[1]["MetricData"][0]
    
    assert metric_data["MetricName"] == "CircuitBreakerState"
    assert metric_data["Value"] == 0  # 0 for closed


def test_publish_workflow_metrics(metrics_publisher, mock_cloudwatch):
    """Test publishing comprehensive workflow metrics."""
    metrics_publisher.publish_workflow_metrics(
        workflow_id="wf-303",
        status="completed",
        bugs_found=10,
        tests_generated=8,
        tests_executed=8,
        root_causes_found=5,
        fixes_generated=5
    )
    
    # Should publish 5 metrics
    assert mock_cloudwatch.put_metric_data.call_count == 5
    
    # Collect all metric names and values
    metrics = {}
    for call_item in mock_cloudwatch.put_metric_data.call_args_list:
        metric_data = call_item[1]["MetricData"][0]
        metrics[metric_data["MetricName"]] = metric_data["Value"]
    
    assert metrics["BugsFound"] == 10
    assert metrics["TestsGenerated"] == 8
    assert metrics["TestsExecuted"] == 8
    assert metrics["RootCausesFound"] == 5
    assert metrics["FixesGenerated"] == 5


def test_publish_batch_metrics(metrics_publisher, mock_cloudwatch):
    """Test publishing multiple metrics in a batch."""
    metrics = [
        {
            "MetricName": "TestMetric1",
            "Value": 100,
            "Unit": "Count",
            "Timestamp": datetime.utcnow(),
            "Dimensions": [{"Name": "Test", "Value": "1"}]
        },
        {
            "MetricName": "TestMetric2",
            "Value": 200,
            "Unit": "Count",
            "Timestamp": datetime.utcnow(),
            "Dimensions": [{"Name": "Test", "Value": "2"}]
        }
    ]
    
    metrics_publisher.publish_batch_metrics(metrics)
    
    # Should publish once with both metrics
    assert mock_cloudwatch.put_metric_data.call_count == 1
    
    call_args = mock_cloudwatch.put_metric_data.call_args
    metric_data = call_args[1]["MetricData"]
    
    assert len(metric_data) == 2
    assert metric_data[0]["MetricName"] == "TestMetric1"
    assert metric_data[1]["MetricName"] == "TestMetric2"


def test_publish_batch_metrics_large_batch(metrics_publisher, mock_cloudwatch):
    """Test publishing large batch splits into multiple requests."""
    # Create 25 metrics (exceeds CloudWatch limit of 20)
    metrics = [
        {
            "MetricName": f"TestMetric{i}",
            "Value": i,
            "Unit": "Count",
            "Timestamp": datetime.utcnow(),
            "Dimensions": []
        }
        for i in range(25)
    ]
    
    metrics_publisher.publish_batch_metrics(metrics)
    
    # Should split into 2 calls (20 + 5)
    assert mock_cloudwatch.put_metric_data.call_count == 2
    
    # First batch should have 20 metrics
    first_call = mock_cloudwatch.put_metric_data.call_args_list[0]
    assert len(first_call[1]["MetricData"]) == 20
    
    # Second batch should have 5 metrics
    second_call = mock_cloudwatch.put_metric_data.call_args_list[1]
    assert len(second_call[1]["MetricData"]) == 5


def test_mock_mode_does_not_call_cloudwatch(metrics_publisher_mock_mode):
    """Test that mock mode does not call CloudWatch."""
    metrics_publisher_mock_mode.publish_agent_execution_time(
        agent_name="bug_detective",
        execution_time_ms=1000,
        workflow_id="wf-999"
    )
    
    # No CloudWatch client, so no calls should be made
    # Just verify no exception is raised


def test_publish_metric_handles_cloudwatch_error(metrics_publisher, mock_cloudwatch):
    """Test that metric publishing handles CloudWatch errors gracefully."""
    # Make CloudWatch raise an exception
    mock_cloudwatch.put_metric_data.side_effect = Exception("CloudWatch error")
    
    # Should not raise exception
    metrics_publisher.publish_agent_execution_time(
        agent_name="bug_detective",
        execution_time_ms=1000,
        workflow_id="wf-error"
    )
    
    # Verify CloudWatch was called despite error
    assert mock_cloudwatch.put_metric_data.call_count == 1


def test_publish_batch_metrics_handles_error(metrics_publisher, mock_cloudwatch):
    """Test that batch metric publishing handles errors gracefully."""
    mock_cloudwatch.put_metric_data.side_effect = Exception("Batch error")
    
    metrics = [
        {
            "MetricName": "TestMetric",
            "Value": 1,
            "Unit": "Count",
            "Timestamp": datetime.utcnow(),
            "Dimensions": []
        }
    ]
    
    # Should not raise exception
    metrics_publisher.publish_batch_metrics(metrics)


def test_metric_timestamp_is_datetime(metrics_publisher, mock_cloudwatch):
    """Test that published metrics include datetime timestamp."""
    metrics_publisher.publish_agent_success(
        agent_name="test_agent",
        workflow_id="wf-time"
    )
    
    call_args = mock_cloudwatch.put_metric_data.call_args
    metric_data = call_args[1]["MetricData"][0]
    
    assert "Timestamp" in metric_data
    assert isinstance(metric_data["Timestamp"], datetime)


def test_namespace_is_configurable():
    """Test that CloudWatch namespace is configurable."""
    custom_namespace = "MyApp/CustomMetrics"
    publisher = MetricsPublisher(
        cloudwatch_client=MagicMock(),
        namespace=custom_namespace
    )
    
    assert publisher.namespace == custom_namespace


def test_default_namespace():
    """Test that default namespace is used when not specified."""
    publisher = MetricsPublisher(cloudwatch_client=MagicMock())
    
    assert publisher.namespace == "CloudForge/BugIntelligence"

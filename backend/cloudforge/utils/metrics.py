"""
CloudWatch metrics publishing for CloudForge Bug Intelligence.

Publishes custom metrics for agent execution times, success rates, cost tracking,
and circuit breaker states.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime


logger = logging.getLogger(__name__)


class MetricsPublisher:
    """
    Publishes custom metrics to CloudWatch.
    
    Tracks agent execution times, success/failure rates, API call counts,
    and circuit breaker states for monitoring and cost management.
    """
    
    def __init__(self, cloudwatch_client=None, namespace: str = "CloudForge/BugIntelligence"):
        """
        Initialize metrics publisher.
        
        Args:
            cloudwatch_client: Boto3 CloudWatch client (optional, uses placeholder if None)
            namespace: CloudWatch namespace for metrics
        """
        self.cloudwatch = cloudwatch_client
        self.namespace = namespace
        self.logger = logging.getLogger(__name__)
        
        # Track if CloudWatch is available
        self.cloudwatch_enabled = cloudwatch_client is not None
        
        if not self.cloudwatch_enabled:
            self.logger.info(
                "CloudWatch metrics disabled - running in mock mode. "
                "Provide cloudwatch_client to enable metrics publishing."
            )
    
    def publish_agent_execution_time(
        self,
        agent_name: str,
        execution_time_ms: int,
        workflow_id: str,
        dimensions: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Publish agent execution time metric.
        
        Args:
            agent_name: Name of the agent (bug_detective, test_architect, etc.)
            execution_time_ms: Execution time in milliseconds
            workflow_id: Workflow identifier
            dimensions: Additional metric dimensions
        """
        metric_data = {
            "MetricName": "AgentExecutionTime",
            "Value": execution_time_ms,
            "Unit": "Milliseconds",
            "Timestamp": datetime.utcnow(),
            "Dimensions": [
                {"Name": "AgentName", "Value": agent_name},
                {"Name": "WorkflowId", "Value": workflow_id}
            ]
        }
        
        # Add custom dimensions
        if dimensions:
            for key, value in dimensions.items():
                metric_data["Dimensions"].append({"Name": key, "Value": value})
        
        self._publish_metric(metric_data)
        
        self.logger.debug(
            f"Published agent execution time metric",
            extra={
                "agent_name": agent_name,
                "execution_time_ms": execution_time_ms,
                "workflow_id": workflow_id
            }
        )
    
    def publish_agent_success(
        self,
        agent_name: str,
        workflow_id: str,
        dimensions: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Publish agent success metric.
        
        Args:
            agent_name: Name of the agent
            workflow_id: Workflow identifier
            dimensions: Additional metric dimensions
        """
        metric_data = {
            "MetricName": "AgentSuccess",
            "Value": 1,
            "Unit": "Count",
            "Timestamp": datetime.utcnow(),
            "Dimensions": [
                {"Name": "AgentName", "Value": agent_name},
                {"Name": "WorkflowId", "Value": workflow_id},
                {"Name": "Status", "Value": "Success"}
            ]
        }
        
        if dimensions:
            for key, value in dimensions.items():
                metric_data["Dimensions"].append({"Name": key, "Value": value})
        
        self._publish_metric(metric_data)
    
    def publish_agent_failure(
        self,
        agent_name: str,
        workflow_id: str,
        error_type: str,
        dimensions: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Publish agent failure metric.
        
        Args:
            agent_name: Name of the agent
            workflow_id: Workflow identifier
            error_type: Type of error that occurred
            dimensions: Additional metric dimensions
        """
        metric_data = {
            "MetricName": "AgentFailure",
            "Value": 1,
            "Unit": "Count",
            "Timestamp": datetime.utcnow(),
            "Dimensions": [
                {"Name": "AgentName", "Value": agent_name},
                {"Name": "WorkflowId", "Value": workflow_id},
                {"Name": "Status", "Value": "Failure"},
                {"Name": "ErrorType", "Value": error_type}
            ]
        }
        
        if dimensions:
            for key, value in dimensions.items():
                metric_data["Dimensions"].append({"Name": key, "Value": value})
        
        self._publish_metric(metric_data)
    
    def publish_api_call_count(
        self,
        service_name: str,
        operation: str,
        count: int = 1,
        dimensions: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Publish API call count metric for cost tracking.
        
        Args:
            service_name: AWS service name (Bedrock, Q Developer, etc.)
            operation: API operation name
            count: Number of API calls
            dimensions: Additional metric dimensions
        """
        metric_data = {
            "MetricName": "APICallCount",
            "Value": count,
            "Unit": "Count",
            "Timestamp": datetime.utcnow(),
            "Dimensions": [
                {"Name": "ServiceName", "Value": service_name},
                {"Name": "Operation", "Value": operation}
            ]
        }
        
        if dimensions:
            for key, value in dimensions.items():
                metric_data["Dimensions"].append({"Name": key, "Value": value})
        
        self._publish_metric(metric_data)
        
        self.logger.debug(
            f"Published API call count metric",
            extra={
                "service_name": service_name,
                "operation": operation,
                "count": count
            }
        )
    
    def publish_execution_duration(
        self,
        platform: str,
        duration_ms: int,
        workflow_id: str,
        dimensions: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Publish test execution duration metric for cost tracking.
        
        Args:
            platform: Execution platform (lambda or ecs)
            duration_ms: Execution duration in milliseconds
            workflow_id: Workflow identifier
            dimensions: Additional metric dimensions
        """
        metric_data = {
            "MetricName": "ExecutionDuration",
            "Value": duration_ms,
            "Unit": "Milliseconds",
            "Timestamp": datetime.utcnow(),
            "Dimensions": [
                {"Name": "Platform", "Value": platform},
                {"Name": "WorkflowId", "Value": workflow_id}
            ]
        }
        
        if dimensions:
            for key, value in dimensions.items():
                metric_data["Dimensions"].append({"Name": key, "Value": value})
        
        self._publish_metric(metric_data)
    
    def publish_circuit_breaker_state(
        self,
        service_name: str,
        state: str,
        failure_count: int = 0,
        dimensions: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Publish circuit breaker state metric.
        
        Args:
            service_name: Name of the service with circuit breaker
            state: Circuit breaker state (closed, open, half_open)
            failure_count: Current failure count
            dimensions: Additional metric dimensions
        """
        metric_data = {
            "MetricName": "CircuitBreakerState",
            "Value": 1 if state == "open" else 0,
            "Unit": "Count",
            "Timestamp": datetime.utcnow(),
            "Dimensions": [
                {"Name": "ServiceName", "Value": service_name},
                {"Name": "State", "Value": state}
            ]
        }
        
        if dimensions:
            for key, value in dimensions.items():
                metric_data["Dimensions"].append({"Name": key, "Value": value})
        
        self._publish_metric(metric_data)
        
        # Also publish failure count
        if failure_count > 0:
            failure_metric = {
                "MetricName": "CircuitBreakerFailures",
                "Value": failure_count,
                "Unit": "Count",
                "Timestamp": datetime.utcnow(),
                "Dimensions": [
                    {"Name": "ServiceName", "Value": service_name}
                ]
            }
            self._publish_metric(failure_metric)
    
    def publish_workflow_metrics(
        self,
        workflow_id: str,
        status: str,
        bugs_found: int,
        tests_generated: int,
        tests_executed: int,
        root_causes_found: int,
        fixes_generated: int,
        dimensions: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Publish comprehensive workflow metrics.
        
        Args:
            workflow_id: Workflow identifier
            status: Workflow status (completed, failed)
            bugs_found: Number of bugs detected
            tests_generated: Number of tests generated
            tests_executed: Number of tests executed
            root_causes_found: Number of root causes identified
            fixes_generated: Number of fixes generated
            dimensions: Additional metric dimensions
        """
        base_dimensions = [
            {"Name": "WorkflowId", "Value": workflow_id},
            {"Name": "Status", "Value": status}
        ]
        
        if dimensions:
            for key, value in dimensions.items():
                base_dimensions.append({"Name": key, "Value": value})
        
        metrics = [
            {"MetricName": "BugsFound", "Value": bugs_found},
            {"MetricName": "TestsGenerated", "Value": tests_generated},
            {"MetricName": "TestsExecuted", "Value": tests_executed},
            {"MetricName": "RootCausesFound", "Value": root_causes_found},
            {"MetricName": "FixesGenerated", "Value": fixes_generated}
        ]
        
        for metric in metrics:
            metric_data = {
                **metric,
                "Unit": "Count",
                "Timestamp": datetime.utcnow(),
                "Dimensions": base_dimensions.copy()
            }
            self._publish_metric(metric_data)
    
    def _publish_metric(self, metric_data: Dict[str, Any]) -> None:
        """
        Publish a single metric to CloudWatch.
        
        Args:
            metric_data: Metric data dictionary
        """
        if not self.cloudwatch_enabled:
            # Mock mode - just log the metric
            self.logger.debug(
                f"Mock metric: {metric_data['MetricName']}={metric_data['Value']}",
                extra={"metric_data": metric_data}
            )
            return
        
        try:
            # Publish to CloudWatch
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[metric_data]
            )
        except Exception as e:
            self.logger.error(
                f"Failed to publish metric {metric_data['MetricName']}: {e}",
                exc_info=True,
                extra={"metric_data": metric_data}
            )
    
    def publish_batch_metrics(self, metrics: List[Dict[str, Any]]) -> None:
        """
        Publish multiple metrics in a single batch.
        
        Args:
            metrics: List of metric data dictionaries
        """
        if not self.cloudwatch_enabled:
            for metric in metrics:
                self.logger.debug(
                    f"Mock metric: {metric['MetricName']}={metric['Value']}",
                    extra={"metric_data": metric}
                )
            return
        
        try:
            # CloudWatch supports up to 20 metrics per request
            batch_size = 20
            for i in range(0, len(metrics), batch_size):
                batch = metrics[i:i + batch_size]
                self.cloudwatch.put_metric_data(
                    Namespace=self.namespace,
                    MetricData=batch
                )
        except Exception as e:
            self.logger.error(
                f"Failed to publish batch metrics: {e}",
                exc_info=True
            )

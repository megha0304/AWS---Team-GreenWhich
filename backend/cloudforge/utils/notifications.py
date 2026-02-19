"""
SNS notification utility for CloudForge Bug Intelligence.

Sends notifications for critical errors including workflow failures,
agent crashes, and cost threshold alerts.
"""

import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime


logger = logging.getLogger(__name__)


class NotificationService:
    """
    Sends SNS notifications for critical system events.
    
    Handles workflow failures, agent crashes, and cost alerts to ensure
    operations team is notified of critical issues.
    """
    
    def __init__(self, sns_client=None, topic_arn: Optional[str] = None):
        """
        Initialize notification service.
        
        Args:
            sns_client: Boto3 SNS client (optional, uses placeholder if None)
            topic_arn: SNS topic ARN for notifications
        """
        self.sns = sns_client
        self.topic_arn = topic_arn
        self.logger = logging.getLogger(__name__)
        
        # Track if SNS is available
        self.sns_enabled = sns_client is not None and topic_arn is not None
        
        if not self.sns_enabled:
            self.logger.info(
                "SNS notifications disabled - running in mock mode. "
                "Provide sns_client and topic_arn to enable notifications."
            )
    
    def notify_workflow_failure(
        self,
        workflow_id: str,
        repository_url: str,
        error_message: str,
        current_agent: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send notification for workflow failure.
        
        Args:
            workflow_id: Workflow identifier
            repository_url: Repository being analyzed
            error_message: Error message describing the failure
            current_agent: Agent that was executing when failure occurred
            additional_context: Additional context information
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        subject = f"[CRITICAL] CloudForge Workflow Failed: {workflow_id}"
        
        message = {
            "alert_type": "workflow_failure",
            "severity": "critical",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "workflow_id": workflow_id,
            "repository_url": repository_url,
            "current_agent": current_agent,
            "error_message": error_message,
            "additional_context": additional_context or {}
        }
        
        return self._send_notification(subject, message)
    
    def notify_agent_crash(
        self,
        agent_name: str,
        workflow_id: str,
        error_type: str,
        error_message: str,
        stack_trace: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send notification for agent crash.
        
        Args:
            agent_name: Name of the crashed agent
            workflow_id: Workflow identifier
            error_type: Type of error that caused the crash
            error_message: Error message
            stack_trace: Stack trace if available
            additional_context: Additional context information
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        subject = f"[CRITICAL] CloudForge Agent Crashed: {agent_name}"
        
        message = {
            "alert_type": "agent_crash",
            "severity": "critical",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "agent_name": agent_name,
            "workflow_id": workflow_id,
            "error_type": error_type,
            "error_message": error_message,
            "stack_trace": stack_trace,
            "additional_context": additional_context or {}
        }
        
        return self._send_notification(subject, message)
    
    def notify_cost_threshold_alert(
        self,
        current_cost: float,
        threshold: float,
        threshold_percentage: float,
        cost_breakdown: Optional[Dict[str, float]] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send notification for cost threshold alert.
        
        Args:
            current_cost: Current monthly cost
            threshold: Cost threshold limit
            threshold_percentage: Percentage of threshold reached
            cost_breakdown: Breakdown of costs by service
            additional_context: Additional context information
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        severity = "critical" if threshold_percentage >= 100 else "warning"
        subject = f"[{severity.upper()}] CloudForge Cost Alert: {threshold_percentage:.1f}% of budget"
        
        message = {
            "alert_type": "cost_threshold",
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "current_cost": current_cost,
            "threshold": threshold,
            "threshold_percentage": threshold_percentage,
            "cost_breakdown": cost_breakdown or {},
            "additional_context": additional_context or {}
        }
        
        return self._send_notification(subject, message)
    
    def notify_infrastructure_failure(
        self,
        service_name: str,
        failure_type: str,
        error_message: str,
        workflow_id: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send notification for infrastructure failure.
        
        Args:
            service_name: Name of the failed service (Lambda, ECS, DynamoDB, etc.)
            failure_type: Type of failure
            error_message: Error message
            workflow_id: Workflow identifier if applicable
            additional_context: Additional context information
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        subject = f"[CRITICAL] CloudForge Infrastructure Failure: {service_name}"
        
        message = {
            "alert_type": "infrastructure_failure",
            "severity": "critical",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "service_name": service_name,
            "failure_type": failure_type,
            "error_message": error_message,
            "workflow_id": workflow_id,
            "additional_context": additional_context or {}
        }
        
        return self._send_notification(subject, message)
    
    def notify_circuit_breaker_open(
        self,
        service_name: str,
        failure_count: int,
        time_window_seconds: int,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send notification when circuit breaker opens.
        
        Args:
            service_name: Name of the service with open circuit breaker
            failure_count: Number of failures that triggered the circuit breaker
            time_window_seconds: Time window in which failures occurred
            additional_context: Additional context information
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        subject = f"[WARNING] CloudForge Circuit Breaker Opened: {service_name}"
        
        message = {
            "alert_type": "circuit_breaker_open",
            "severity": "warning",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "service_name": service_name,
            "failure_count": failure_count,
            "time_window_seconds": time_window_seconds,
            "additional_context": additional_context or {}
        }
        
        return self._send_notification(subject, message)
    
    def _send_notification(
        self,
        subject: str,
        message: Dict[str, Any]
    ) -> bool:
        """
        Send notification via SNS.
        
        Args:
            subject: Notification subject
            message: Notification message as dictionary
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        if not self.sns_enabled:
            # Mock mode - just log the notification
            self.logger.warning(
                f"Mock notification: {subject}",
                extra={
                    "subject": subject,
                    "notification_data": message
                }
            )
            return True
        
        try:
            # Format message as JSON
            message_json = json.dumps(message, indent=2)
            
            # Send to SNS
            response = self.sns.publish(
                TopicArn=self.topic_arn,
                Subject=subject,
                Message=message_json,
                MessageAttributes={
                    "alert_type": {
                        "DataType": "String",
                        "StringValue": message.get("alert_type", "unknown")
                    },
                    "severity": {
                        "DataType": "String",
                        "StringValue": message.get("severity", "info")
                    }
                }
            )
            
            self.logger.info(
                f"Notification sent successfully: {subject}",
                extra={
                    "message_id": response.get("MessageId"),
                    "subject": subject,
                    "alert_type": message.get("alert_type")
                }
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                f"Failed to send notification: {subject}",
                exc_info=True,
                extra={
                    "subject": subject,
                    "error": str(e)
                }
            )
            return False
    
    def send_custom_notification(
        self,
        subject: str,
        message: str,
        severity: str = "info",
        additional_attributes: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Send custom notification with arbitrary content.
        
        Args:
            subject: Notification subject
            message: Notification message (plain text or JSON string)
            severity: Severity level (info, warning, critical)
            additional_attributes: Additional SNS message attributes
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        if not self.sns_enabled:
            self.logger.info(
                f"Mock notification: {subject}",
                extra={
                    "subject": subject,
                    "notification_message": message,
                    "severity": severity
                }
            )
            return True
        
        try:
            # Build message attributes
            attributes = {
                "severity": {
                    "DataType": "String",
                    "StringValue": severity
                }
            }
            
            if additional_attributes:
                for key, value in additional_attributes.items():
                    attributes[key] = {
                        "DataType": "String",
                        "StringValue": value
                    }
            
            # Send to SNS
            response = self.sns.publish(
                TopicArn=self.topic_arn,
                Subject=subject,
                Message=message,
                MessageAttributes=attributes
            )
            
            self.logger.info(
                f"Custom notification sent: {subject}",
                extra={
                    "message_id": response.get("MessageId"),
                    "severity": severity
                }
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                f"Failed to send custom notification: {subject}",
                exc_info=True,
                extra={
                    "subject": subject,
                    "error": str(e)
                }
            )
            return False

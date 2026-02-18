"""
State persistence layer for CloudForge Bug Intelligence workflows.

This module provides the StateStore class for persisting and retrieving workflow
state from DynamoDB. It implements optimistic locking, query filtering, and
pagination support for managing workflow state across the multi-agent system.

Requirements: 6.3, 15.1, 15.3, 15.5
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

from cloudforge.models.state import AgentState


logger = logging.getLogger(__name__)


class StateStore:
    """
    Manages workflow state persistence in DynamoDB.
    
    This class provides methods for saving, loading, and querying workflow state
    with support for optimistic locking, filtering, and pagination. It handles
    serialization of AgentState objects to DynamoDB format and deserialization
    back to Python objects.
    
    Attributes:
        dynamodb: boto3 DynamoDB client
        table_name: Name of the DynamoDB table for workflow state
        logger: Logger instance for this class
    """
    
    def __init__(self, dynamodb_client, table_name: str):
        """
        Initialize StateStore with DynamoDB client and table name.
        
        Args:
            dynamodb_client: boto3 DynamoDB client instance
            table_name: Name of the DynamoDB table to use for state storage
        """
        self.dynamodb = dynamodb_client
        self.table_name = table_name
        self.logger = logger
    
    async def save_state(self, state: AgentState, version: Optional[int] = None) -> None:
        """
        Save workflow state to DynamoDB with optimistic locking.
        
        This method persists the complete AgentState to DynamoDB. It uses a version
        number for optimistic locking to prevent concurrent updates from overwriting
        each other. If a version is provided, the save will only succeed if the
        current version in DynamoDB matches.
        
        Args:
            state: AgentState object to persist
            version: Optional version number for optimistic locking. If provided,
                    the save will only succeed if the current version matches.
        
        Raises:
            ValueError: If optimistic locking fails (version mismatch)
            ClientError: If DynamoDB operation fails
        
        Requirements: 6.3
        """
        try:
            # Convert state to DynamoDB format
            item = self._serialize_state(state)
            
            # Add version for optimistic locking
            current_version = version if version is not None else 0
            item["version"] = current_version + 1
            item["updated_at"] = Decimal(str(datetime.utcnow().timestamp()))
            
            # Build condition expression for optimistic locking
            if version is not None:
                # Only update if version matches (optimistic locking)
                condition_expression = "version = :expected_version"
                expression_attribute_values = {":expected_version": version}
                
                self.dynamodb.put_item(
                    TableName=self.table_name,
                    Item=item,
                    ConditionExpression=condition_expression,
                    ExpressionAttributeValues=expression_attribute_values
                )
            else:
                # First save or no version check
                self.dynamodb.put_item(
                    TableName=self.table_name,
                    Item=item
                )
            
            self.logger.info(
                f"Saved state for workflow {state.workflow_id} "
                f"(version {item['version']})"
            )
        
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            
            if error_code == "ConditionalCheckFailedException":
                raise ValueError(
                    f"Optimistic locking failed for workflow {state.workflow_id}. "
                    f"Expected version {version}, but state was modified by another process."
                )
            else:
                self.logger.error(
                    f"Failed to save state for workflow {state.workflow_id}: {e}"
                )
                raise
    
    async def load_state(self, workflow_id: str) -> Optional[AgentState]:
        """
        Load workflow state from DynamoDB.
        
        This method retrieves the complete AgentState for a given workflow ID.
        It deserializes the DynamoDB item back into an AgentState object.
        
        Args:
            workflow_id: Unique identifier for the workflow
        
        Returns:
            AgentState object if found, None otherwise
        
        Raises:
            ClientError: If DynamoDB operation fails
        
        Requirements: 6.3
        """
        try:
            response = self.dynamodb.get_item(
                TableName=self.table_name,
                Key={"workflow_id": {"S": workflow_id}}
            )
            
            if "Item" not in response:
                self.logger.info(f"No state found for workflow {workflow_id}")
                return None
            
            # Deserialize DynamoDB item to AgentState
            state = self._deserialize_state(response["Item"])
            
            self.logger.info(f"Loaded state for workflow {workflow_id}")
            return state
        
        except ClientError as e:
            self.logger.error(
                f"Failed to load state for workflow {workflow_id}: {e}"
            )
            raise
    
    async def query_workflows(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Query workflows with filtering and pagination support.
        
        This method queries the DynamoDB table for workflows matching the specified
        filters. It supports filtering by status, date range, and severity, and
        provides pagination for large result sets.
        
        Args:
            filters: Optional dictionary of filter criteria:
                - status: Filter by workflow status (pending, in_progress, completed, failed)
                - date_from: Filter workflows created after this datetime
                - date_to: Filter workflows created before this datetime
                - severity: Filter by bug severity (critical, high, medium, low)
            limit: Maximum number of results to return (default: 50)
            offset: Number of results to skip for pagination (default: 0)
        
        Returns:
            Dictionary containing:
                - workflows: List of AgentState objects matching filters
                - total_count: Total number of matching workflows
                - limit: Limit used for this query
                - offset: Offset used for this query
                - has_more: Boolean indicating if more results are available
        
        Raises:
            ClientError: If DynamoDB operation fails
        
        Requirements: 15.3, 15.5
        """
        try:
            filters = filters or {}
            
            # Build scan parameters
            scan_params = {
                "TableName": self.table_name,
                "Limit": limit + offset  # Fetch extra to handle offset
            }
            
            # Build filter expression
            filter_expressions = []
            expression_attribute_values = {}
            expression_attribute_names = {}
            
            # Status filter
            if "status" in filters:
                filter_expressions.append("#status = :status")
                expression_attribute_names["#status"] = "status"
                expression_attribute_values[":status"] = {"S": filters["status"]}
            
            # Date range filters
            if "date_from" in filters:
                filter_expressions.append("created_at >= :date_from")
                date_from = filters["date_from"]
                if isinstance(date_from, datetime):
                    date_from = date_from.timestamp()
                expression_attribute_values[":date_from"] = {"N": str(date_from)}
            
            if "date_to" in filters:
                filter_expressions.append("created_at <= :date_to")
                date_to = filters["date_to"]
                if isinstance(date_to, datetime):
                    date_to = date_to.timestamp()
                expression_attribute_values[":date_to"] = {"N": str(date_to)}
            
            # Severity filter (checks if any bug has the specified severity)
            if "severity" in filters:
                filter_expressions.append("contains(severity_list, :severity)")
                expression_attribute_values[":severity"] = {"S": filters["severity"]}
            
            # Add filter expression if any filters were specified
            if filter_expressions:
                scan_params["FilterExpression"] = " AND ".join(filter_expressions)
                scan_params["ExpressionAttributeValues"] = expression_attribute_values
                if expression_attribute_names:
                    scan_params["ExpressionAttributeNames"] = expression_attribute_names
            
            # Execute scan
            response = self.dynamodb.scan(**scan_params)
            
            # Deserialize items
            all_items = [
                self._deserialize_state(item)
                for item in response.get("Items", [])
            ]
            
            # Handle pagination with offset
            total_count = len(all_items)
            paginated_items = all_items[offset:offset + limit]
            has_more = (offset + limit) < total_count
            
            self.logger.info(
                f"Queried workflows: found {total_count} total, "
                f"returning {len(paginated_items)} (offset={offset}, limit={limit})"
            )
            
            return {
                "workflows": paginated_items,
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": has_more
            }
        
        except ClientError as e:
            self.logger.error(f"Failed to query workflows: {e}")
            raise
    
    def _serialize_state(self, state: AgentState) -> Dict[str, Any]:
        """
        Serialize AgentState to DynamoDB item format.
        
        Converts a Pydantic AgentState object to DynamoDB's attribute format,
        handling type conversions for strings, numbers, lists, and nested objects.
        
        Args:
            state: AgentState object to serialize
        
        Returns:
            Dictionary in DynamoDB item format with type descriptors
        """
        # Convert state to dictionary
        state_dict = state.to_dict()
        
        # Build DynamoDB item with type descriptors
        item = {
            "workflow_id": {"S": state.workflow_id},
            "repository_url": {"S": state.repository_url},
            "repository_path": {"S": state.repository_path},
            "current_agent": {"S": state.current_agent},
            "status": {"S": state.status},
            "created_at": {"N": str(state.created_at.timestamp())},
            "updated_at": {"N": str(state.updated_at.timestamp())},
            "retry_count": {"N": str(state.retry_count)},
        }
        
        # Serialize lists as JSON strings for simplicity
        # In production, you might want to use DynamoDB's native list type
        import json
        
        item["bugs"] = {"S": json.dumps([bug.model_dump(mode="json") for bug in state.bugs])}
        item["test_cases"] = {"S": json.dumps([tc.model_dump(mode="json") for tc in state.test_cases])}
        item["test_results"] = {"S": json.dumps([tr.model_dump(mode="json") for tr in state.test_results])}
        item["root_causes"] = {"S": json.dumps([rc.model_dump(mode="json") for rc in state.root_causes])}
        item["fix_suggestions"] = {"S": json.dumps([fs.model_dump(mode="json") for fs in state.fix_suggestions])}
        item["errors"] = {"S": json.dumps(state.errors)}
        
        # Add severity list for filtering (extract unique severities from bugs)
        severities = list(set(bug.severity for bug in state.bugs))
        if severities:
            item["severity_list"] = {"SS": severities}
        
        return item
    
    def _deserialize_state(self, item: Dict[str, Any]) -> AgentState:
        """
        Deserialize DynamoDB item to AgentState object.
        
        Converts a DynamoDB item with type descriptors back to a Pydantic
        AgentState object, handling type conversions and nested objects.
        
        Args:
            item: DynamoDB item with type descriptors
        
        Returns:
            AgentState object
        """
        import json
        from cloudforge.models.state import (
            BugReport, TestCase, TestResult, RootCause, FixSuggestion
        )
        
        # Extract basic fields
        state_data = {
            "workflow_id": item["workflow_id"]["S"],
            "repository_url": item["repository_url"]["S"],
            "repository_path": item["repository_path"]["S"],
            "current_agent": item["current_agent"]["S"],
            "status": item["status"]["S"],
            "created_at": datetime.fromtimestamp(float(item["created_at"]["N"])),
            "updated_at": datetime.fromtimestamp(float(item["updated_at"]["N"])),
            "retry_count": int(item["retry_count"]["N"]),
        }
        
        # Deserialize lists from JSON
        state_data["bugs"] = [
            BugReport(**bug_data)
            for bug_data in json.loads(item.get("bugs", {"S": "[]"})["S"])
        ]
        state_data["test_cases"] = [
            TestCase(**tc_data)
            for tc_data in json.loads(item.get("test_cases", {"S": "[]"})["S"])
        ]
        state_data["test_results"] = [
            TestResult(**tr_data)
            for tr_data in json.loads(item.get("test_results", {"S": "[]"})["S"])
        ]
        state_data["root_causes"] = [
            RootCause(**rc_data)
            for rc_data in json.loads(item.get("root_causes", {"S": "[]"})["S"])
        ]
        state_data["fix_suggestions"] = [
            FixSuggestion(**fs_data)
            for fs_data in json.loads(item.get("fix_suggestions", {"S": "[]"})["S"])
        ]
        state_data["errors"] = json.loads(item.get("errors", {"S": "[]"})["S"])
        
        return AgentState(**state_data)


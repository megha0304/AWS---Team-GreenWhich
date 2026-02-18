"""
Unit tests for StateStore class.

Tests the state persistence layer including save_state, load_state, and
query_workflows methods with optimistic locking and pagination support.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock
from botocore.exceptions import ClientError

from cloudforge.orchestration.state_store import StateStore
from cloudforge.models.state import AgentState, BugReport


@pytest.fixture
def mock_dynamodb_client():
    """Create a mock DynamoDB client."""
    client = Mock()
    client.put_item = Mock()
    client.get_item = Mock()
    client.scan = Mock()
    return client


@pytest.fixture
def state_store(mock_dynamodb_client):
    """Create a StateStore instance with mock DynamoDB client."""
    return StateStore(mock_dynamodb_client, "test-workflows-table")


@pytest.fixture
def sample_state():
    """Create a sample AgentState for testing."""
    return AgentState(
        workflow_id="test-workflow-123",
        repository_url="https://github.com/test/repo",
        repository_path="/tmp/test-repo",
        current_agent="bug_detective",
        status="in_progress",
        bugs=[
            BugReport(
                bug_id="bug-1",
                file_path="src/main.py",
                line_number=42,
                severity="high",
                description="Potential null pointer dereference",
                code_snippet="x = obj.value",
                confidence_score=0.85
            )
        ]
    )


@pytest.mark.asyncio
async def test_save_state_first_time(state_store, mock_dynamodb_client, sample_state):
    """Test saving state for the first time (no version check)."""
    # Arrange
    mock_dynamodb_client.put_item.return_value = {}
    
    # Act
    await state_store.save_state(sample_state)
    
    # Assert
    mock_dynamodb_client.put_item.assert_called_once()
    call_args = mock_dynamodb_client.put_item.call_args
    assert call_args[1]["TableName"] == "test-workflows-table"
    assert call_args[1]["Item"]["workflow_id"]["S"] == "test-workflow-123"
    assert call_args[1]["Item"]["version"] == 1


@pytest.mark.asyncio
async def test_save_state_with_version(state_store, mock_dynamodb_client, sample_state):
    """Test saving state with optimistic locking (version check)."""
    # Arrange
    mock_dynamodb_client.put_item.return_value = {}
    
    # Act
    await state_store.save_state(sample_state, version=1)
    
    # Assert
    mock_dynamodb_client.put_item.assert_called_once()
    call_args = mock_dynamodb_client.put_item.call_args
    assert call_args[1]["ConditionExpression"] == "version = :expected_version"
    assert call_args[1]["ExpressionAttributeValues"][":expected_version"] == 1
    assert call_args[1]["Item"]["version"] == 2


@pytest.mark.asyncio
async def test_save_state_optimistic_locking_failure(state_store, mock_dynamodb_client, sample_state):
    """Test that optimistic locking failure raises ValueError."""
    # Arrange
    mock_dynamodb_client.put_item.side_effect = ClientError(
        {"Error": {"Code": "ConditionalCheckFailedException", "Message": "Condition failed"}},
        "PutItem"
    )
    
    # Act & Assert
    with pytest.raises(ValueError, match="Optimistic locking failed"):
        await state_store.save_state(sample_state, version=1)


@pytest.mark.asyncio
async def test_load_state_success(state_store, mock_dynamodb_client, sample_state):
    """Test loading state successfully."""
    # Arrange
    import json
    mock_dynamodb_client.get_item.return_value = {
        "Item": {
            "workflow_id": {"S": "test-workflow-123"},
            "repository_url": {"S": "https://github.com/test/repo"},
            "repository_path": {"S": "/tmp/test-repo"},
            "current_agent": {"S": "bug_detective"},
            "status": {"S": "in_progress"},
            "created_at": {"N": str(datetime.utcnow().timestamp())},
            "updated_at": {"N": str(datetime.utcnow().timestamp())},
            "retry_count": {"N": "0"},
            "bugs": {"S": json.dumps([{
                "bug_id": "bug-1",
                "file_path": "src/main.py",
                "line_number": 42,
                "severity": "high",
                "description": "Potential null pointer dereference",
                "code_snippet": "x = obj.value",
                "confidence_score": 0.85
            }])},
            "test_cases": {"S": "[]"},
            "test_results": {"S": "[]"},
            "root_causes": {"S": "[]"},
            "fix_suggestions": {"S": "[]"},
            "errors": {"S": "[]"}
        }
    }
    
    # Act
    result = await state_store.load_state("test-workflow-123")
    
    # Assert
    assert result is not None
    assert result.workflow_id == "test-workflow-123"
    assert result.status == "in_progress"
    assert len(result.bugs) == 1
    assert result.bugs[0].bug_id == "bug-1"


@pytest.mark.asyncio
async def test_load_state_not_found(state_store, mock_dynamodb_client):
    """Test loading state when workflow doesn't exist."""
    # Arrange
    mock_dynamodb_client.get_item.return_value = {}
    
    # Act
    result = await state_store.load_state("nonexistent-workflow")
    
    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_query_workflows_no_filters(state_store, mock_dynamodb_client):
    """Test querying workflows without filters."""
    # Arrange
    import json
    now = datetime.utcnow()
    mock_dynamodb_client.scan.return_value = {
        "Items": [
            {
                "workflow_id": {"S": "workflow-1"},
                "repository_url": {"S": "https://github.com/test/repo1"},
                "repository_path": {"S": "/tmp/repo1"},
                "current_agent": {"S": "bug_detective"},
                "status": {"S": "completed"},
                "created_at": {"N": str(now.timestamp())},
                "updated_at": {"N": str(now.timestamp())},
                "retry_count": {"N": "0"},
                "bugs": {"S": "[]"},
                "test_cases": {"S": "[]"},
                "test_results": {"S": "[]"},
                "root_causes": {"S": "[]"},
                "fix_suggestions": {"S": "[]"},
                "errors": {"S": "[]"}
            },
            {
                "workflow_id": {"S": "workflow-2"},
                "repository_url": {"S": "https://github.com/test/repo2"},
                "repository_path": {"S": "/tmp/repo2"},
                "current_agent": {"S": "test_architect"},
                "status": {"S": "in_progress"},
                "created_at": {"N": str(now.timestamp())},
                "updated_at": {"N": str(now.timestamp())},
                "retry_count": {"N": "0"},
                "bugs": {"S": "[]"},
                "test_cases": {"S": "[]"},
                "test_results": {"S": "[]"},
                "root_causes": {"S": "[]"},
                "fix_suggestions": {"S": "[]"},
                "errors": {"S": "[]"}
            }
        ]
    }
    
    # Act
    result = await state_store.query_workflows()
    
    # Assert
    assert result["total_count"] == 2
    assert len(result["workflows"]) == 2
    assert result["limit"] == 50
    assert result["offset"] == 0
    assert result["has_more"] is False


@pytest.mark.asyncio
async def test_query_workflows_with_status_filter(state_store, mock_dynamodb_client):
    """Test querying workflows with status filter."""
    # Arrange
    import json
    now = datetime.utcnow()
    mock_dynamodb_client.scan.return_value = {
        "Items": [
            {
                "workflow_id": {"S": "workflow-1"},
                "repository_url": {"S": "https://github.com/test/repo1"},
                "repository_path": {"S": "/tmp/repo1"},
                "current_agent": {"S": "bug_detective"},
                "status": {"S": "completed"},
                "created_at": {"N": str(now.timestamp())},
                "updated_at": {"N": str(now.timestamp())},
                "retry_count": {"N": "0"},
                "bugs": {"S": "[]"},
                "test_cases": {"S": "[]"},
                "test_results": {"S": "[]"},
                "root_causes": {"S": "[]"},
                "fix_suggestions": {"S": "[]"},
                "errors": {"S": "[]"}
            }
        ]
    }
    
    # Act
    result = await state_store.query_workflows(filters={"status": "completed"})
    
    # Assert
    call_args = mock_dynamodb_client.scan.call_args
    assert "#status = :status" in call_args[1]["FilterExpression"]
    assert call_args[1]["ExpressionAttributeValues"][":status"]["S"] == "completed"


@pytest.mark.asyncio
async def test_query_workflows_with_pagination(state_store, mock_dynamodb_client):
    """Test querying workflows with pagination."""
    # Arrange
    import json
    now = datetime.utcnow()
    items = []
    for i in range(10):
        items.append({
            "workflow_id": {"S": f"workflow-{i}"},
            "repository_url": {"S": f"https://github.com/test/repo{i}"},
            "repository_path": {"S": f"/tmp/repo{i}"},
            "current_agent": {"S": "bug_detective"},
            "status": {"S": "completed"},
            "created_at": {"N": str(now.timestamp())},
            "updated_at": {"N": str(now.timestamp())},
            "retry_count": {"N": "0"},
            "bugs": {"S": "[]"},
            "test_cases": {"S": "[]"},
            "test_results": {"S": "[]"},
            "root_causes": {"S": "[]"},
            "fix_suggestions": {"S": "[]"},
            "errors": {"S": "[]"}
        })
    
    mock_dynamodb_client.scan.return_value = {"Items": items}
    
    # Act
    result = await state_store.query_workflows(limit=5, offset=3)
    
    # Assert
    assert result["total_count"] == 10
    assert len(result["workflows"]) == 5
    assert result["limit"] == 5
    assert result["offset"] == 3
    assert result["has_more"] is True
    assert result["workflows"][0].workflow_id == "workflow-3"
    assert result["workflows"][4].workflow_id == "workflow-7"


@pytest.mark.asyncio
async def test_query_workflows_with_date_range(state_store, mock_dynamodb_client):
    """Test querying workflows with date range filters."""
    # Arrange
    mock_dynamodb_client.scan.return_value = {"Items": []}
    date_from = datetime.utcnow() - timedelta(days=7)
    date_to = datetime.utcnow()
    
    # Act
    result = await state_store.query_workflows(
        filters={"date_from": date_from, "date_to": date_to}
    )
    
    # Assert
    call_args = mock_dynamodb_client.scan.call_args
    assert "created_at >= :date_from" in call_args[1]["FilterExpression"]
    assert "created_at <= :date_to" in call_args[1]["FilterExpression"]


@pytest.mark.asyncio
async def test_serialize_deserialize_roundtrip(state_store, sample_state):
    """Test that serialization and deserialization are inverse operations."""
    # Act
    serialized = state_store._serialize_state(sample_state)
    deserialized = state_store._deserialize_state(serialized)
    
    # Assert
    assert deserialized.workflow_id == sample_state.workflow_id
    assert deserialized.repository_url == sample_state.repository_url
    assert deserialized.status == sample_state.status
    assert len(deserialized.bugs) == len(sample_state.bugs)
    assert deserialized.bugs[0].bug_id == sample_state.bugs[0].bug_id
    assert deserialized.bugs[0].severity == sample_state.bugs[0].severity


@pytest.mark.asyncio
async def test_save_state_includes_severity_list(state_store, mock_dynamodb_client, sample_state):
    """Test that save_state includes severity_list for filtering."""
    # Arrange
    sample_state.bugs.append(
        BugReport(
            bug_id="bug-2",
            file_path="src/utils.py",
            line_number=10,
            severity="critical",
            description="Security vulnerability detected",
            code_snippet="eval(user_input)",
            confidence_score=0.95
        )
    )
    mock_dynamodb_client.put_item.return_value = {}
    
    # Act
    await state_store.save_state(sample_state)
    
    # Assert
    call_args = mock_dynamodb_client.put_item.call_args
    severity_list = call_args[1]["Item"]["severity_list"]["SS"]
    assert "high" in severity_list
    assert "critical" in severity_list
    assert len(severity_list) == 2


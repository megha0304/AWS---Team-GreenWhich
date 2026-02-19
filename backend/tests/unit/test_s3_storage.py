"""
Unit tests for S3 storage utilities.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError
from cloudforge.utils.s3_storage import S3Storage


@pytest.fixture
def s3_storage():
    """Create S3Storage instance with mocked client."""
    with patch("cloudforge.utils.s3_storage.boto3.client") as mock_client:
        storage = S3Storage(bucket_name="test-bucket", region="us-east-1")
        storage.s3_client = Mock()
        return storage


def test_generate_path_basic(s3_storage):
    """Test basic path generation."""
    path = s3_storage._generate_path(
        artifact_type="test-results",
        workflow_id="wf-123",
        item_id="test-456"
    )
    assert path == "test-results/wf-123/test-456"


def test_generate_path_with_extension(s3_storage):
    """Test path generation with extension."""
    path = s3_storage._generate_path(
        artifact_type="test-results",
        workflow_id="wf-123",
        item_id="test-456",
        extension="json"
    )
    assert path == "test-results/wf-123/test-456.json"


def test_generate_path_with_dot_extension(s3_storage):
    """Test path generation with extension starting with dot."""
    path = s3_storage._generate_path(
        artifact_type="test-results",
        workflow_id="wf-123",
        item_id="test-456",
        extension=".json"
    )
    assert path == "test-results/wf-123/test-456.json"


def test_upload_artifact_success(s3_storage):
    """Test successful artifact upload."""
    content = b"test content"
    
    key = s3_storage.upload_artifact(
        artifact_type="test-results",
        workflow_id="wf-123",
        item_id="test-456",
        content=content,
        extension="json"
    )
    
    assert key == "test-results/wf-123/test-456.json"
    s3_storage.s3_client.put_object.assert_called_once()
    call_args = s3_storage.s3_client.put_object.call_args
    assert call_args[1]["Bucket"] == "test-bucket"
    assert call_args[1]["Key"] == "test-results/wf-123/test-456.json"
    assert call_args[1]["Body"] == content


def test_upload_artifact_with_content_type(s3_storage):
    """Test artifact upload with content type."""
    content = b"test content"
    
    s3_storage.upload_artifact(
        artifact_type="test-results",
        workflow_id="wf-123",
        item_id="test-456",
        content=content,
        extension="json",
        content_type="application/json"
    )
    
    call_args = s3_storage.s3_client.put_object.call_args
    assert call_args[1]["ContentType"] == "application/json"


def test_upload_artifact_failure(s3_storage):
    """Test artifact upload failure."""
    s3_storage.s3_client.put_object.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
        "PutObject"
    )
    
    with pytest.raises(ClientError):
        s3_storage.upload_artifact(
            artifact_type="test-results",
            workflow_id="wf-123",
            item_id="test-456",
            content=b"test"
        )


def test_download_artifact_success(s3_storage):
    """Test successful artifact download."""
    expected_content = b"test content"
    mock_response = {
        "Body": MagicMock()
    }
    mock_response["Body"].read.return_value = expected_content
    s3_storage.s3_client.get_object.return_value = mock_response
    
    content = s3_storage.download_artifact(
        artifact_type="test-results",
        workflow_id="wf-123",
        item_id="test-456",
        extension="json"
    )
    
    assert content == expected_content
    s3_storage.s3_client.get_object.assert_called_once()
    call_args = s3_storage.s3_client.get_object.call_args
    assert call_args[1]["Bucket"] == "test-bucket"
    assert call_args[1]["Key"] == "test-results/wf-123/test-456.json"


def test_download_artifact_failure(s3_storage):
    """Test artifact download failure."""
    s3_storage.s3_client.get_object.side_effect = ClientError(
        {"Error": {"Code": "NoSuchKey", "Message": "Key not found"}},
        "GetObject"
    )
    
    with pytest.raises(ClientError):
        s3_storage.download_artifact(
            artifact_type="test-results",
            workflow_id="wf-123",
            item_id="test-456"
        )


def test_list_artifacts_with_workflow_id(s3_storage):
    """Test listing artifacts filtered by workflow."""
    mock_response = {
        "Contents": [
            {"Key": "test-results/wf-123/test-1.json"},
            {"Key": "test-results/wf-123/test-2.json"},
        ]
    }
    s3_storage.s3_client.list_objects_v2.return_value = mock_response
    
    keys = s3_storage.list_artifacts(
        artifact_type="test-results",
        workflow_id="wf-123"
    )
    
    assert len(keys) == 2
    assert "test-results/wf-123/test-1.json" in keys
    assert "test-results/wf-123/test-2.json" in keys
    
    call_args = s3_storage.s3_client.list_objects_v2.call_args
    assert call_args[1]["Prefix"] == "test-results/wf-123/"


def test_list_artifacts_without_workflow_id(s3_storage):
    """Test listing all artifacts of a type."""
    mock_response = {
        "Contents": [
            {"Key": "test-results/wf-123/test-1.json"},
            {"Key": "test-results/wf-456/test-2.json"},
        ]
    }
    s3_storage.s3_client.list_objects_v2.return_value = mock_response
    
    keys = s3_storage.list_artifacts(artifact_type="test-results")
    
    assert len(keys) == 2
    call_args = s3_storage.s3_client.list_objects_v2.call_args
    assert call_args[1]["Prefix"] == "test-results/"


def test_list_artifacts_empty(s3_storage):
    """Test listing artifacts when none exist."""
    mock_response = {}
    s3_storage.s3_client.list_objects_v2.return_value = mock_response
    
    keys = s3_storage.list_artifacts(artifact_type="test-results")
    
    assert len(keys) == 0


def test_list_artifacts_failure(s3_storage):
    """Test listing artifacts failure."""
    s3_storage.s3_client.list_objects_v2.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
        "ListObjectsV2"
    )
    
    with pytest.raises(ClientError):
        s3_storage.list_artifacts(artifact_type="test-results")


def test_delete_artifact_success(s3_storage):
    """Test successful artifact deletion."""
    s3_storage.delete_artifact(
        artifact_type="test-results",
        workflow_id="wf-123",
        item_id="test-456",
        extension="json"
    )
    
    s3_storage.s3_client.delete_object.assert_called_once()
    call_args = s3_storage.s3_client.delete_object.call_args
    assert call_args[1]["Bucket"] == "test-bucket"
    assert call_args[1]["Key"] == "test-results/wf-123/test-456.json"


def test_delete_artifact_failure(s3_storage):
    """Test artifact deletion failure."""
    s3_storage.s3_client.delete_object.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
        "DeleteObject"
    )
    
    with pytest.raises(ClientError):
        s3_storage.delete_artifact(
            artifact_type="test-results",
            workflow_id="wf-123",
            item_id="test-456"
        )


def test_get_presigned_url_success(s3_storage):
    """Test presigned URL generation."""
    expected_url = "https://test-bucket.s3.amazonaws.com/test-results/wf-123/test-456.json?signature=..."
    s3_storage.s3_client.generate_presigned_url.return_value = expected_url
    
    url = s3_storage.get_presigned_url(
        artifact_type="test-results",
        workflow_id="wf-123",
        item_id="test-456",
        extension="json",
        expiration=7200
    )
    
    assert url == expected_url
    s3_storage.s3_client.generate_presigned_url.assert_called_once()
    call_args = s3_storage.s3_client.generate_presigned_url.call_args
    assert call_args[0][0] == "get_object"
    assert call_args[1]["Params"]["Bucket"] == "test-bucket"
    assert call_args[1]["Params"]["Key"] == "test-results/wf-123/test-456.json"
    assert call_args[1]["ExpiresIn"] == 7200


def test_get_presigned_url_failure(s3_storage):
    """Test presigned URL generation failure."""
    s3_storage.s3_client.generate_presigned_url.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
        "GeneratePresignedUrl"
    )
    
    with pytest.raises(ClientError):
        s3_storage.get_presigned_url(
            artifact_type="test-results",
            workflow_id="wf-123",
            item_id="test-456"
        )


def test_path_structure_validation(s3_storage):
    """Test that paths follow the required structure."""
    # Test various artifact types
    artifact_types = [
        "repositories",
        "test-results",
        "analysis-reports",
        "fix-patches"
    ]
    
    for artifact_type in artifact_types:
        path = s3_storage._generate_path(
            artifact_type=artifact_type,
            workflow_id="wf-123",
            item_id="item-456",
            extension="json"
        )
        
        # Verify structure: {artifact_type}/{workflow_id}/{item_id}.{extension}
        parts = path.split("/")
        assert len(parts) == 3
        assert parts[0] == artifact_type
        assert parts[1] == "wf-123"
        assert parts[2] == "item-456.json"

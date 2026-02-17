"""Shared pytest fixtures and configuration."""

import pytest
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock


@pytest.fixture
def mock_bedrock_client() -> Mock:
    """Mock AWS Bedrock client for testing."""
    client = Mock()
    client.invoke_model = AsyncMock()
    return client


@pytest.fixture
def mock_q_developer_client() -> Mock:
    """Mock Amazon Q Developer client for testing."""
    client = Mock()
    client.generate_code = AsyncMock()
    return client


@pytest.fixture
def mock_lambda_client() -> Mock:
    """Mock AWS Lambda client for testing."""
    client = Mock()
    client.invoke = AsyncMock()
    return client


@pytest.fixture
def mock_ecs_client() -> Mock:
    """Mock AWS ECS client for testing."""
    client = Mock()
    client.run_task = AsyncMock()
    return client


@pytest.fixture
def mock_dynamodb_client() -> Mock:
    """Mock AWS DynamoDB client for testing."""
    client = Mock()
    client.put_item = AsyncMock()
    client.get_item = AsyncMock()
    client.query = AsyncMock()
    return client


@pytest.fixture
def mock_s3_client() -> Mock:
    """Mock AWS S3 client for testing."""
    client = Mock()
    client.put_object = AsyncMock()
    client.get_object = AsyncMock()
    return client


@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """Sample configuration for testing."""
    return {
        "aws_region": "us-east-1",
        "bedrock_model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
        "max_retries": 3,
        "retry_backoff_base": 2.0,
        "max_files_per_batch": 100,
    }

"""
Unit tests for SystemConfig model.

Tests configuration loading from environment variables, validation,
and AWS Secrets Manager integration.
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError
from cloudforge.models.config import SystemConfig


class TestSystemConfigDefaults:
    """Test SystemConfig default values."""
    
    def test_default_values(self):
        """Test that SystemConfig initializes with correct default values."""
        config = SystemConfig()
        
        # AWS Configuration
        assert config.aws_region == "us-east-1"
        assert config.aws_profile is None
        
        # Bedrock Configuration
        assert config.bedrock_model_id == "anthropic.claude-3-sonnet-20240229-v1:0"
        assert config.bedrock_region == "us-east-1"
        
        # Cost Management
        assert config.max_monthly_cost == 100.0
        assert config.api_rate_limit_per_minute == 60
        
        # Agent Configuration
        assert config.max_retries == 3
        assert config.retry_backoff_base == 2.0
        
        # Execution Configuration
        assert config.lambda_timeout_seconds == 900
        assert config.lambda_memory_mb == 10240
        assert config.ecs_cpu == 2048
        assert config.ecs_memory_mb == 16384

    def test_field_constraints(self):
        """Test that field constraints are enforced."""
        # Test max_retries constraint
        with pytest.raises(ValueError):
            SystemConfig(max_retries=-1)
        
        with pytest.raises(ValueError):
            SystemConfig(max_retries=11)
        
        # Test cost_alert_threshold_percent constraint
        with pytest.raises(ValueError):
            SystemConfig(cost_alert_threshold_percent=-1.0)
        
        with pytest.raises(ValueError):
            SystemConfig(cost_alert_threshold_percent=101.0)


class TestSystemConfigValidation:
    """Test SystemConfig validation methods."""
    
    def test_validate_log_level(self):
        """Test log level validation."""
        # Valid log levels
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            config = SystemConfig(log_level=level)
            assert config.log_level == level
        
        # Case insensitive
        config = SystemConfig(log_level="info")
        assert config.log_level == "INFO"
        
        # Invalid log level
        with pytest.raises(ValueError, match="log_level must be one of"):
            SystemConfig(log_level="INVALID")
    
    def test_validate_log_format(self):
        """Test log format validation."""
        # Valid formats
        config = SystemConfig(log_format="json")
        assert config.log_format == "json"
        
        config = SystemConfig(log_format="text")
        assert config.log_format == "text"
        
        # Case insensitive
        config = SystemConfig(log_format="JSON")
        assert config.log_format == "json"
        
        # Invalid format
        with pytest.raises(ValueError, match="log_format must be one of"):
            SystemConfig(log_format="xml")

    def test_validate_environment(self):
        """Test environment validation."""
        # Valid environments
        for env in ["development", "staging", "production", "test"]:
            config = SystemConfig(environment=env)
            assert config.environment == env
        
        # Case insensitive
        config = SystemConfig(environment="PRODUCTION")
        assert config.environment == "production"
        
        # Invalid environment
        with pytest.raises(ValueError, match="environment must be one of"):
            SystemConfig(environment="invalid")
    
    def test_validate_api_configuration_success(self):
        """Test API configuration validation with valid config."""
        config = SystemConfig(
            q_developer_endpoint="https://valid-endpoint.amazonaws.com",
            q_developer_api_key="valid-api-key"
        )
        
        # Should not raise
        config.validate_api_configuration()
    
    def test_validate_api_configuration_missing_q_developer(self):
        """Test API configuration validation fails with placeholder values."""
        config = SystemConfig()
        
        with pytest.raises(ValueError, match="API configuration validation failed"):
            config.validate_api_configuration()


class TestSystemConfigSecretsManager:
    """Test AWS Secrets Manager integration."""
    
    @patch("cloudforge.models.config.boto3.session.Session")
    def test_load_from_secrets_manager_success(self, mock_session_class):
        """Test successful loading from Secrets Manager."""
        # Mock Secrets Manager client
        mock_client = Mock()
        mock_session = Mock()
        mock_session.client.return_value = mock_client
        mock_session_class.return_value = mock_session
        
        # Mock secret response
        secret_data = {
            "bedrock_model_id": "anthropic.claude-3-opus-20240229-v1:0",
            "q_developer_endpoint": "https://custom-endpoint.amazonaws.com",
            "q_developer_api_key": "secret-api-key"
        }
        mock_client.get_secret_value.return_value = {
            "SecretString": '{"bedrock_model_id": "anthropic.claude-3-opus-20240229-v1:0", "q_developer_endpoint": "https://custom-endpoint.amazonaws.com", "q_developer_api_key": "secret-api-key"}'
        }
        
        # Load config
        config = SystemConfig()
        config.load_from_secrets_manager("test-secret")
        
        # Verify values were updated
        assert config.bedrock_model_id == "anthropic.claude-3-opus-20240229-v1:0"
        assert config.q_developer_endpoint == "https://custom-endpoint.amazonaws.com"
        assert config.q_developer_api_key == "secret-api-key"

    @patch("cloudforge.models.config.boto3.session.Session")
    def test_load_from_secrets_manager_not_found(self, mock_session_class):
        """Test loading from Secrets Manager when secret doesn't exist."""
        # Mock Secrets Manager client
        mock_client = Mock()
        mock_session = Mock()
        mock_session.client.return_value = mock_client
        mock_session_class.return_value = mock_session
        
        # Mock ResourceNotFoundException
        error_response = {"Error": {"Code": "ResourceNotFoundException"}}
        mock_client.get_secret_value.side_effect = ClientError(error_response, "GetSecretValue")
        
        # Load config
        config = SystemConfig()
        
        with pytest.raises(ValueError, match="Secret 'test-secret' not found"):
            config.load_from_secrets_manager("test-secret")
    
    def test_load_from_secrets_manager_no_secret_name(self):
        """Test loading from Secrets Manager without secret name."""
        config = SystemConfig()
        
        with pytest.raises(ValueError, match="secret_name must be provided"):
            config.load_from_secrets_manager()


class TestSystemConfigLoadConfig:
    """Test SystemConfig.load_config class method."""
    
    def test_load_config_defaults(self):
        """Test loading config with defaults."""
        config = SystemConfig.load_config()
        
        assert config.aws_region == "us-east-1"
        assert config.max_retries == 3
    
    @patch("cloudforge.models.config.os.path.exists")
    def test_load_config_with_env_file(self, mock_exists):
        """Test loading config from custom env file."""
        mock_exists.return_value = True
        
        with patch.dict(os.environ, {"AWS_REGION": "us-west-2"}):
            config = SystemConfig.load_config(env_file=".env.test")
            # Note: actual env file loading would require a real file
            # This test verifies the method doesn't crash
            assert isinstance(config, SystemConfig)
    
    @patch("cloudforge.models.config.SystemConfig.load_from_secrets_manager")
    def test_load_config_with_secrets_manager(self, mock_load_secrets):
        """Test loading config with Secrets Manager."""
        config = SystemConfig.load_config(
            secrets_manager_secret_name="test-secret"
        )
        
        # Verify load_from_secrets_manager was called
        mock_load_secrets.assert_called_once_with("test-secret")
        assert isinstance(config, SystemConfig)


class TestSystemConfigBoto3Clients:
    """Test boto3 client creation methods."""
    
    @patch("cloudforge.models.config.boto3.Session")
    def test_get_boto3_session(self, mock_session_class):
        """Test creating boto3 session."""
        config = SystemConfig(aws_region="us-west-2")
        session = config.get_boto3_session()
        
        mock_session_class.assert_called_once_with(region_name="us-west-2")
    
    @patch("cloudforge.models.config.boto3.Session")
    def test_get_boto3_session_with_profile(self, mock_session_class):
        """Test creating boto3 session with profile."""
        config = SystemConfig(aws_region="us-west-2", aws_profile="dev")
        session = config.get_boto3_session()
        
        mock_session_class.assert_called_once_with(
            region_name="us-west-2",
            profile_name="dev"
        )

    @patch("cloudforge.models.config.boto3.Session")
    def test_get_bedrock_client(self, mock_session_class):
        """Test creating Bedrock client."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        config = SystemConfig(bedrock_region="us-east-1")
        client = config.get_bedrock_client()
        
        mock_session.client.assert_called_once_with(
            "bedrock-runtime",
            region_name="us-east-1"
        )
    
    @patch("cloudforge.models.config.boto3.Session")
    def test_get_bedrock_client_with_endpoint(self, mock_session_class):
        """Test creating Bedrock client with custom endpoint."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        config = SystemConfig(
            bedrock_region="us-east-1",
            bedrock_endpoint_url="http://localhost:4566"
        )
        client = config.get_bedrock_client()
        
        mock_session.client.assert_called_once_with(
            "bedrock-runtime",
            region_name="us-east-1",
            endpoint_url="http://localhost:4566"
        )
    
    @patch("cloudforge.models.config.boto3.Session")
    def test_get_dynamodb_client(self, mock_session_class):
        """Test creating DynamoDB client."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        config = SystemConfig()
        client = config.get_dynamodb_client()
        
        mock_session.client.assert_called_once_with("dynamodb")
    
    @patch("cloudforge.models.config.boto3.Session")
    def test_get_s3_client(self, mock_session_class):
        """Test creating S3 client."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        config = SystemConfig()
        client = config.get_s3_client()
        
        mock_session.client.assert_called_once_with("s3")


class TestSystemConfigEnvironmentVariables:
    """Test loading configuration from environment variables."""
    
    def test_load_from_environment(self):
        """Test loading config from environment variables."""
        with patch.dict(os.environ, {
            "AWS_REGION": "eu-west-1",
            "MAX_RETRIES": "5",
            "BEDROCK_MODEL_ID": "anthropic.claude-3-haiku-20240307-v1:0",
            "LOG_LEVEL": "DEBUG"
        }):
            config = SystemConfig()
            
            assert config.aws_region == "eu-west-1"
            assert config.max_retries == 5
            assert config.bedrock_model_id == "anthropic.claude-3-haiku-20240307-v1:0"
            assert config.log_level == "DEBUG"

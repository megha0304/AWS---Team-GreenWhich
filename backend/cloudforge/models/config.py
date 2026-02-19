"""
System configuration model for CloudForge Bug Intelligence.

This module defines the SystemConfig model with support for loading configuration
from environment variables and AWS Secrets Manager. It includes all AWS configuration,
cost management settings, agent retry/timeout settings, and execution parameters.

Requirements: 10.2, 10.3, 10.4, 8.2
"""

import json
import os
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import boto3
from botocore.exceptions import ClientError


class SystemConfig(BaseSettings):
    """
    System configuration with support for environment variables and AWS Secrets Manager.
    
    Configuration values are loaded in the following priority order:
    1. Environment variables
    2. AWS Secrets Manager (if secret_name is provided)
    3. Default values
    
    All API integrations include placeholder comments for users to add their own credentials.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # ============================================================================
    # AWS Configuration
    # ============================================================================
    aws_region: str = Field(
        default="us-east-1",
        description="AWS region for all services"
    )
    aws_profile: Optional[str] = Field(
        default=None,
        description="AWS profile name for local development"
    )
    
    # ============================================================================
    # AWS Bedrock Configuration
    # ============================================================================
    # TODO: Configure your AWS Bedrock credentials
    # 
    # To use AWS Bedrock:
    # 1. Enable Bedrock in your AWS account
    # 2. Request access to Claude models in the Bedrock console
    # 3. Set BEDROCK_MODEL_ID environment variable or update default below
    # 4. Ensure your AWS credentials have bedrock:InvokeModel permissions
    #
    # Available models: https://docs.aws.amazon.com/bedrock/latest/userguide/model-ids.html
    bedrock_model_id: str = Field(
        default="anthropic.claude-3-sonnet-20240229-v1:0",
        description="AWS Bedrock model ID for code analysis"
    )
    bedrock_region: str = Field(
        default="us-east-1",
        description="AWS region for Bedrock service"
    )
    bedrock_endpoint_url: Optional[str] = Field(
        default=None,
        description="Custom Bedrock endpoint URL (optional)"
    )
    
    # ============================================================================
    # Amazon Q Developer Configuration
    # ============================================================================
    # TODO: Configure your Amazon Q Developer API credentials
    #
    # To use Amazon Q Developer:
    # 1. Sign up for Amazon Q Developer access
    # 2. Obtain your API endpoint and credentials
    # 3. Set Q_DEVELOPER_ENDPOINT and Q_DEVELOPER_API_KEY environment variables
    # 4. See: https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/what-is.html
    #
    # NOTE: Amazon Q Developer API requires separate enrollment
    q_developer_endpoint: str = Field(
        default="https://your-q-developer-endpoint.amazonaws.com",
        description="Amazon Q Developer API endpoint"
    )
    q_developer_api_key: str = Field(
        default="your-api-key-here",
        description="Amazon Q Developer API key"
    )
    
    # ============================================================================
    # AWS Secrets Manager Configuration
    # ============================================================================
    secrets_manager_secret_name: Optional[str] = Field(
        default=None,
        description="AWS Secrets Manager secret name for loading credentials"
    )
    
    # ============================================================================
    # Cost Management Settings
    # ============================================================================
    max_monthly_cost: float = Field(
        default=100.0,
        ge=0.0,
        description="Maximum monthly operational cost target in USD"
    )
    api_rate_limit_per_minute: int = Field(
        default=60,
        ge=1,
        description="Maximum API calls per minute to control costs"
    )
    cost_alert_threshold_percent: float = Field(
        default=80.0,
        ge=0.0,
        le=100.0,
        description="Percentage of max_monthly_cost that triggers alerts"
    )
    
    # ============================================================================
    # Agent Retry and Timeout Settings
    # ============================================================================
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts for agent operations"
    )
    retry_backoff_base: float = Field(
        default=2.0,
        ge=1.0,
        description="Base multiplier for exponential backoff (delay = base^attempt)"
    )
    agent_timeout_seconds: int = Field(
        default=300,
        ge=1,
        description="Timeout for individual agent operations in seconds"
    )
    workflow_timeout_seconds: int = Field(
        default=3600,
        ge=1,
        description="Timeout for complete workflow execution in seconds"
    )
    
    # ============================================================================
    # Bug Detection Configuration
    # ============================================================================
    max_files_per_batch: int = Field(
        default=100,
        ge=1,
        description="Maximum files to process in a single batch"
    )
    large_repository_threshold: int = Field(
        default=10000,
        ge=1,
        description="File count threshold for enabling batch processing"
    )
    
    # ============================================================================
    # Execution Configuration
    # ============================================================================
    lambda_timeout_seconds: int = Field(
        default=900,
        ge=1,
        le=900,
        description="AWS Lambda timeout in seconds (max 15 minutes)"
    )
    lambda_memory_mb: int = Field(
        default=10240,
        ge=128,
        le=10240,
        description="AWS Lambda memory allocation in MB (max 10GB)"
    )
    ecs_cpu: int = Field(
        default=2048,
        ge=256,
        description="AWS ECS CPU units (1024 = 1 vCPU)"
    )
    ecs_memory_mb: int = Field(
        default=16384,
        ge=512,
        description="AWS ECS memory allocation in MB"
    )
    
    # Resource routing thresholds
    lambda_max_runtime_seconds: int = Field(
        default=900,
        ge=1,
        description="Maximum estimated runtime for Lambda routing"
    )
    lambda_max_memory_mb: int = Field(
        default=10240,
        ge=1,
        description="Maximum estimated memory for Lambda routing"
    )
    
    # ============================================================================
    # Storage Configuration
    # ============================================================================
    data_retention_days: int = Field(
        default=90,
        ge=1,
        description="Number of days to retain workflow data"
    )
    s3_lifecycle_archive_days: int = Field(
        default=30,
        ge=1,
        description="Number of days before archiving S3 objects to Glacier"
    )
    
    # ============================================================================
    # DynamoDB Configuration
    # ============================================================================
    dynamodb_workflows_table: str = Field(
        default="cloudforge-workflows",
        description="DynamoDB table name for workflow state"
    )
    dynamodb_bugs_table: str = Field(
        default="cloudforge-bugs",
        description="DynamoDB table name for bug reports"
    )
    dynamodb_endpoint_url: Optional[str] = Field(
        default=None,
        description="Custom DynamoDB endpoint URL (for LocalStack)"
    )
    
    # ============================================================================
    # S3 Configuration
    # ============================================================================
    s3_artifacts_bucket: str = Field(
        default="cloudforge-artifacts",
        description="S3 bucket name for storing artifacts"
    )
    s3_endpoint_url: Optional[str] = Field(
        default=None,
        description="Custom S3 endpoint URL (for LocalStack)"
    )
    
    # ============================================================================
    # CloudWatch Configuration
    # ============================================================================
    cloudwatch_log_group: str = Field(
        default="/aws/cloudforge/bug-intelligence",
        description="CloudWatch log group name"
    )
    cloudwatch_metrics_namespace: str = Field(
        default="CloudForge/BugIntelligence",
        description="CloudWatch metrics namespace"
    )
    
    # ============================================================================
    # SNS Configuration
    # ============================================================================
    sns_alert_topic_arn: Optional[str] = Field(
        default=None,
        description="SNS topic ARN for critical alerts"
    )
    
    # ============================================================================
    # API Configuration
    # ============================================================================
    api_host: str = Field(
        default="0.0.0.0",
        description="API server host"
    )
    api_port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="API server port"
    )
    api_rate_limit: int = Field(
        default=100,
        ge=1,
        description="API rate limit per minute per client"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="API authentication key"
    )
    
    # ============================================================================
    # Logging Configuration
    # ============================================================================
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    log_format: str = Field(
        default="json",
        description="Log format (json or text)"
    )
    
    # ============================================================================
    # Environment Configuration
    # ============================================================================
    environment: str = Field(
        default="development",
        description="Environment name (development, staging, production)"
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    
    # ============================================================================
    # Circuit Breaker Configuration
    # ============================================================================
    circuit_breaker_failure_threshold: int = Field(
        default=5,
        ge=1,
        description="Number of failures before opening circuit breaker"
    )
    circuit_breaker_timeout_seconds: int = Field(
        default=30,
        ge=1,
        description="Seconds to wait before attempting to close circuit breaker"
    )
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is a valid Python logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v_upper
    
    @field_validator("log_format")
    @classmethod
    def validate_log_format(cls, v: str) -> str:
        """Validate log format is either json or text."""
        valid_formats = ["json", "text"]
        v_lower = v.lower()
        if v_lower not in valid_formats:
            raise ValueError(f"log_format must be one of {valid_formats}")
        return v_lower
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment is a known environment name."""
        valid_environments = ["development", "staging", "production", "test"]
        v_lower = v.lower()
        if v_lower not in valid_environments:
            raise ValueError(f"environment must be one of {valid_environments}")
        return v_lower
    
    def load_from_secrets_manager(self, secret_name: Optional[str] = None) -> None:
        """
        Load configuration values from AWS Secrets Manager.
        
        This method fetches a secret from AWS Secrets Manager and updates
        configuration values. Values from Secrets Manager override environment
        variables and defaults.
        
        Args:
            secret_name: Name of the secret in AWS Secrets Manager.
                        If None, uses self.secrets_manager_secret_name.
        
        Raises:
            ValueError: If secret_name is not provided and not set in config
            ClientError: If secret cannot be retrieved from Secrets Manager
        
        Example secret JSON structure:
        {
            "bedrock_model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
            "q_developer_endpoint": "https://your-endpoint.amazonaws.com",
            "q_developer_api_key": "your-actual-api-key",
            "api_key": "your-api-authentication-key"
        }
        """
        secret_name = secret_name or self.secrets_manager_secret_name
        
        if not secret_name:
            raise ValueError(
                "secret_name must be provided or secrets_manager_secret_name must be set"
            )
        
        # Create Secrets Manager client
        session_kwargs = {"region_name": self.aws_region}
        if self.aws_profile:
            session_kwargs["profile_name"] = self.aws_profile
        
        session = boto3.session.Session(**session_kwargs)
        client = session.client("secretsmanager")
        
        try:
            # Retrieve secret value
            response = client.get_secret_value(SecretId=secret_name)
            
            # Parse secret JSON
            if "SecretString" in response:
                secret_data = json.loads(response["SecretString"])
            else:
                raise ValueError("Secret does not contain SecretString")
            
            # Update configuration with secret values
            for key, value in secret_data.items():
                if hasattr(self, key):
                    setattr(self, key, value)
        
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "ResourceNotFoundException":
                raise ValueError(f"Secret '{secret_name}' not found in Secrets Manager")
            elif error_code == "InvalidRequestException":
                raise ValueError(f"Invalid request for secret '{secret_name}'")
            elif error_code == "InvalidParameterException":
                raise ValueError(f"Invalid parameter for secret '{secret_name}'")
            else:
                raise
    
    @classmethod
    def load_config(
        cls,
        env_file: Optional[str] = None,
        secrets_manager_secret_name: Optional[str] = None
    ) -> "SystemConfig":
        """
        Load configuration from environment variables and optionally from Secrets Manager.
        
        This is the recommended way to instantiate SystemConfig. It loads configuration
        in the following order:
        1. Default values
        2. Environment variables (from .env file if provided)
        3. AWS Secrets Manager (if secret_name is provided)
        
        Args:
            env_file: Path to .env file (optional)
            secrets_manager_secret_name: Name of AWS Secrets Manager secret (optional)
        
        Returns:
            SystemConfig instance with loaded configuration
        
        Example:
            # Load from environment variables only
            config = SystemConfig.load_config()
            
            # Load from custom .env file
            config = SystemConfig.load_config(env_file=".env.production")
            
            # Load from environment variables and Secrets Manager
            config = SystemConfig.load_config(
                secrets_manager_secret_name="cloudforge/production/config"
            )
        """
        # Load from environment variables
        if env_file and os.path.exists(env_file):
            config = cls(_env_file=env_file)
        else:
            config = cls()
        
        # Load from Secrets Manager if specified
        if secrets_manager_secret_name:
            config.load_from_secrets_manager(secrets_manager_secret_name)
        
        return config
    
    def validate_api_configuration(self) -> None:
        """
        Validate that all required API configurations are set.
        
        This method checks that API endpoints and credentials are configured
        and not using placeholder values. It should be called at startup before
        processing any requests.
        
        Raises:
            ValueError: If any required API configuration is missing or invalid
        
        Requirements: 10.5, 10.6
        """
        errors = []
        
        # Validate Bedrock configuration
        if not self.bedrock_model_id:
            errors.append("bedrock_model_id is required")
        
        if not self.bedrock_region:
            errors.append("bedrock_region is required")
        
        # Validate Q Developer configuration
        if self.q_developer_endpoint == "https://your-q-developer-endpoint.amazonaws.com":
            errors.append(
                "q_developer_endpoint is not configured. "
                "Please set Q_DEVELOPER_ENDPOINT environment variable or update config."
            )
        
        if self.q_developer_api_key == "your-api-key-here":
            errors.append(
                "q_developer_api_key is not configured. "
                "Please set Q_DEVELOPER_API_KEY environment variable or update config."
            )
        
        # Validate AWS region
        if not self.aws_region:
            errors.append("aws_region is required")
        
        if errors:
            error_message = "API configuration validation failed:\n" + "\n".join(
                f"  - {error}" for error in errors
            )
            raise ValueError(error_message)
    
    def get_boto3_session(self) -> boto3.Session:
        """
        Create a boto3 session with configured AWS credentials.
        
        Returns:
            boto3.Session configured with region and profile (if set)
        """
        session_kwargs = {"region_name": self.aws_region}
        if self.aws_profile:
            session_kwargs["profile_name"] = self.aws_profile
        return boto3.Session(**session_kwargs)
    
    def get_bedrock_client(self):
        """
        Create an AWS Bedrock client with configured settings.
        
        Returns:
            boto3 Bedrock Runtime client
        """
        session = self.get_boto3_session()
        client_kwargs = {"region_name": self.bedrock_region}
        if self.bedrock_endpoint_url:
            client_kwargs["endpoint_url"] = self.bedrock_endpoint_url
        return session.client("bedrock-runtime", **client_kwargs)
    
    def get_dynamodb_client(self):
        """
        Create a DynamoDB client with configured settings.
        
        Returns:
            boto3 DynamoDB client
        """
        session = self.get_boto3_session()
        client_kwargs = {}
        if self.dynamodb_endpoint_url:
            client_kwargs["endpoint_url"] = self.dynamodb_endpoint_url
        return session.client("dynamodb", **client_kwargs)
    
    def get_s3_client(self):
        """
        Create an S3 client with configured settings.
        
        Returns:
            boto3 S3 client
        """
        session = self.get_boto3_session()
        client_kwargs = {}
        if self.s3_endpoint_url:
            client_kwargs["endpoint_url"] = self.s3_endpoint_url
        return session.client("s3", **client_kwargs)
    
    @property
    def workflows_table_name(self) -> str:
        """Get workflows table name."""
        return self.dynamodb_workflows_table
    
    @property
    def bugs_table_name(self) -> str:
        """Get bugs table name."""
        return self.dynamodb_bugs_table
    
    @property
    def artifacts_bucket_name(self) -> str:
        """Get artifacts bucket name."""
        return self.s3_artifacts_bucket
    
    @classmethod
    def from_env(cls) -> "SystemConfig":
        """
        Create SystemConfig from environment variables.
        
        Returns:
            SystemConfig instance
        """
        return cls.load_config()

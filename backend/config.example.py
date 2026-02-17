"""
Example configuration file for CloudForge Bug Intelligence.

This file demonstrates how to configure API integrations for external services.
Copy this file to config.py and fill in your actual credentials and endpoints.

IMPORTANT: Never commit config.py with real credentials to version control!
"""

from typing import Optional
from pydantic_settings import BaseSettings


class SystemConfig(BaseSettings):
    """System configuration with API integration placeholders."""

    # ============================================================================
    # AWS Configuration
    # ============================================================================
    aws_region: str = "us-east-1"
    aws_profile: Optional[str] = None

    # ============================================================================
    # AWS Bedrock Configuration
    # ============================================================================
    # TODO: Configure your AWS Bedrock model ID and region
    # 
    # To use AWS Bedrock:
    # 1. Enable Bedrock in your AWS account
    # 2. Request access to Claude models in the Bedrock console
    # 3. Set the model ID below (see available models at:
    #    https://docs.aws.amazon.com/bedrock/latest/userguide/model-ids.html)
    # 4. Ensure your AWS credentials have bedrock:InvokeModel permissions
    #
    # Example model IDs:
    # - anthropic.claude-3-sonnet-20240229-v1:0 (recommended)
    # - anthropic.claude-3-haiku-20240307-v1:0 (faster, cheaper)
    # - anthropic.claude-3-opus-20240229-v1:0 (most capable)
    bedrock_model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    bedrock_region: str = "us-east-1"

    # ============================================================================
    # Amazon Q Developer Configuration
    # ============================================================================
    # TODO: Configure your Amazon Q Developer API endpoint and credentials
    #
    # To use Amazon Q Developer:
    # 1. Sign up for Amazon Q Developer access
    # 2. Obtain your API endpoint and credentials
    # 3. Set the endpoint and API key below
    # 4. See: https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/what-is.html
    #
    # NOTE: Amazon Q Developer API is currently in preview and requires
    # separate enrollment. If you don't have access, you can:
    # - Use mock implementations for testing (see tests/conftest.py)
    # - Replace with alternative code generation APIs
    # - Implement manual test generation workflows
    q_developer_endpoint: str = "https://your-q-developer-endpoint.amazonaws.com"
    q_developer_api_key: str = "your-api-key-here"

    # ============================================================================
    # Cost Management
    # ============================================================================
    max_monthly_cost: float = 100.0
    api_rate_limit_per_minute: int = 60

    # ============================================================================
    # Agent Configuration
    # ============================================================================
    max_retries: int = 3
    retry_backoff_base: float = 2.0
    max_files_per_batch: int = 100

    # ============================================================================
    # Execution Configuration
    # ============================================================================
    lambda_timeout_seconds: int = 900  # 15 minutes
    lambda_memory_mb: int = 10240  # 10 GB
    ecs_cpu: int = 2048
    ecs_memory_mb: int = 16384

    # ============================================================================
    # Storage Configuration
    # ============================================================================
    data_retention_days: int = 90
    s3_lifecycle_archive_days: int = 30

    # ============================================================================
    # DynamoDB Tables
    # ============================================================================
    dynamodb_workflows_table: str = "cloudforge-workflows"
    dynamodb_bugs_table: str = "cloudforge-bugs"

    # ============================================================================
    # S3 Buckets
    # ============================================================================
    s3_artifacts_bucket: str = "cloudforge-artifacts"

    # ============================================================================
    # API Configuration
    # ============================================================================
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_rate_limit: int = 100

    # ============================================================================
    # Logging
    # ============================================================================
    log_level: str = "INFO"
    log_format: str = "json"

    # ============================================================================
    # Development
    # ============================================================================
    environment: str = "development"
    debug: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# ============================================================================
# Usage Example
# ============================================================================
# 
# from config import SystemConfig
# 
# config = SystemConfig()
# 
# # Access configuration values
# print(f"Using Bedrock model: {config.bedrock_model_id}")
# print(f"API rate limit: {config.api_rate_limit_per_minute} requests/minute")
# 
# ============================================================================

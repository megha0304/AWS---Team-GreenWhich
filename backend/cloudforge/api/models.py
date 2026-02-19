"""
Pydantic models for FastAPI request/response schemas.

These models define the API contract for the CloudForge Bug Intelligence REST API.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class WorkflowCreateRequest(BaseModel):
    """
    Request model for creating a new workflow.
    
    Attributes:
        repository_url: URL of the Git repository to analyze
        branch: Git branch to analyze (defaults to "main")
    """
    repository_url: str = Field(
        min_length=1,
        description="URL of the Git repository to analyze",
        examples=["https://github.com/user/repo.git"]
    )
    branch: Optional[str] = Field(
        default="main",
        description="Git branch to analyze"
    )
    
    @field_validator("repository_url")
    @classmethod
    def validate_repository_url(cls, v: str) -> str:
        """Ensure repository URL is not empty or whitespace only."""
        if not v.strip():
            raise ValueError("repository_url cannot be empty or whitespace")
        return v.strip()


class WorkflowResponse(BaseModel):
    """
    Response model for workflow information.
    
    Provides a summary of workflow status and results.
    
    Attributes:
        workflow_id: Unique identifier for the workflow
        status: Current workflow status
        created_at: Timestamp when workflow was created
        updated_at: Timestamp of last workflow update
        repository_url: URL of the analyzed repository
        bugs_found: Number of bugs detected
        tests_generated: Number of test cases generated
        tests_executed: Number of tests executed
        root_causes_found: Number of root causes identified
        fixes_generated: Number of fix suggestions generated
    """
    workflow_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    repository_url: str
    bugs_found: int = Field(ge=0)
    tests_generated: int = Field(ge=0)
    tests_executed: int = Field(ge=0, default=0)
    root_causes_found: int = Field(ge=0, default=0)
    fixes_generated: int = Field(ge=0, default=0)


class WorkflowListResponse(BaseModel):
    """
    Response model for listing workflows.
    
    Includes pagination metadata.
    
    Attributes:
        workflows: List of workflow summaries
        total: Total number of workflows matching filters
        limit: Maximum number of results per page
        offset: Number of results skipped
    """
    workflows: List[WorkflowResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


class ErrorResponse(BaseModel):
    """
    Response model for API errors.
    
    Attributes:
        error: Error type/category
        detail: Detailed error message
    """
    error: str
    detail: str

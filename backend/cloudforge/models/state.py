"""
Pydantic models for CloudForge Bug Intelligence agent state and sub-models.

This module defines the core data structures used throughout the multi-agent workflow,
including bug reports, test cases, test results, root causes, and fix suggestions.
All models include validation rules and support serialization/deserialization.
"""

from datetime import datetime
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
from uuid import uuid4


class BugReport(BaseModel):
    """
    Represents a detected bug in the codebase.
    
    Attributes:
        bug_id: Unique identifier for the bug
        file_path: Path to the file containing the bug
        line_number: Line number where the bug occurs (must be positive)
        severity: Bug severity level (critical, high, medium, low)
        description: Human-readable description of the bug
        code_snippet: Code excerpt showing the bug with context
        confidence_score: AI confidence in bug detection (0.0 to 1.0)
    """
    bug_id: str = Field(default_factory=lambda: str(uuid4()))
    file_path: str = Field(min_length=1)
    line_number: int = Field(gt=0)
    severity: Literal["critical", "high", "medium", "low"]
    description: str = Field(min_length=10)
    code_snippet: str = Field(min_length=1)
    confidence_score: float = Field(ge=0.0, le=1.0)
    
    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        """Ensure file path is not empty or whitespace only."""
        if not v.strip():
            raise ValueError("file_path cannot be empty or whitespace")
        return v.strip()
    
    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Ensure description is meaningful."""
        if not v.strip():
            raise ValueError("description cannot be empty or whitespace")
        return v.strip()


class TestCase(BaseModel):
    """
    Represents a generated test case for a detected bug.
    
    Attributes:
        test_id: Unique identifier for the test case
        bug_id: Reference to the bug this test validates
        test_code: Executable test code
        test_framework: Testing framework used (pytest, unittest, jest, etc.)
        expected_outcome: Description of expected test behavior
    """
    test_id: str = Field(default_factory=lambda: str(uuid4()))
    bug_id: str = Field(min_length=1)
    test_code: str = Field(min_length=1)
    test_framework: str = Field(min_length=1)
    expected_outcome: str = Field(min_length=1)
    
    @field_validator("test_code", "expected_outcome")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Ensure fields are not empty or whitespace only."""
        if not v.strip():
            raise ValueError("field cannot be empty or whitespace")
        return v.strip()


class TestResult(BaseModel):
    """
    Represents the result of executing a test case.
    
    Attributes:
        test_id: Reference to the executed test case
        status: Test execution status
        stdout: Standard output from test execution
        stderr: Standard error from test execution
        exit_code: Process exit code
        execution_time_ms: Test execution duration in milliseconds
        execution_platform: Platform where test was executed (lambda or ecs)
    """
    test_id: str = Field(min_length=1)
    status: Literal["passed", "failed", "error", "skipped"]
    stdout: str = Field(default="")
    stderr: str = Field(default="")
    exit_code: int
    execution_time_ms: int = Field(ge=0)
    execution_platform: Literal["lambda", "ecs"]
    
    @model_validator(mode="after")
    def validate_status_consistency(self) -> "TestResult":
        """Ensure status is consistent with exit code."""
        if self.status == "passed" and self.exit_code != 0:
            raise ValueError("passed status requires exit_code 0")
        if self.status in ["failed", "error"] and self.exit_code == 0:
            raise ValueError(f"{self.status} status requires non-zero exit_code")
        return self


class RootCause(BaseModel):
    """
    Represents an identified root cause for a bug.
    
    Attributes:
        bug_id: Reference to the primary bug
        cause_description: Detailed explanation of the root cause
        related_bugs: List of other bug IDs sharing this root cause
        confidence_score: AI confidence in root cause analysis (0.0 to 1.0)
    """
    bug_id: str = Field(min_length=1)
    cause_description: str = Field(min_length=10)
    related_bugs: List[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0)
    
    @field_validator("cause_description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Ensure description is meaningful."""
        if not v.strip():
            raise ValueError("cause_description cannot be empty or whitespace")
        return v.strip()
    
    @field_validator("related_bugs")
    @classmethod
    def validate_related_bugs(cls, v: List[str]) -> List[str]:
        """Ensure related bugs list contains no duplicates."""
        if len(v) != len(set(v)):
            raise ValueError("related_bugs cannot contain duplicates")
        return v


class FixSuggestion(BaseModel):
    """
    Represents a suggested fix for a bug.
    
    Attributes:
        bug_id: Reference to the bug being fixed
        fix_description: Human-readable explanation of the fix
        code_diff: Unified diff format showing the changes
        safety_score: Estimated safety of applying this fix (0.0 to 1.0)
        impact_assessment: Description of the fix's impact on the codebase
    """
    bug_id: str = Field(min_length=1)
    fix_description: str = Field(min_length=10)
    code_diff: str = Field(min_length=1)
    safety_score: float = Field(ge=0.0, le=1.0)
    impact_assessment: str = Field(min_length=1)
    
    @field_validator("fix_description", "impact_assessment")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Ensure fields are not empty or whitespace only."""
        if not v.strip():
            raise ValueError("field cannot be empty or whitespace")
        return v.strip()


class AgentState(BaseModel):
    """
    Shared state object passed between agents in the workflow.
    
    This is the central data structure that flows through the multi-agent system,
    accumulating results from each agent (Bug Detective, Test Architect, Execution,
    Analysis, and Resolution agents).
    
    Attributes:
        workflow_id: Unique identifier for this workflow execution
        repository_url: URL of the code repository being analyzed
        repository_path: Local filesystem path to the cloned repository
        current_agent: Name of the agent currently processing this state
        status: Current workflow status
        created_at: Timestamp when workflow was created
        updated_at: Timestamp of last state update
        bugs: List of detected bugs (populated by Bug Detective Agent)
        test_cases: List of generated test cases (populated by Test Architect Agent)
        test_results: List of test execution results (populated by Execution Agent)
        root_causes: List of identified root causes (populated by Analysis Agent)
        fix_suggestions: List of fix suggestions (populated by Resolution Agent)
        errors: List of errors encountered during workflow execution
        retry_count: Number of retry attempts for the current agent
    """
    workflow_id: str = Field(default_factory=lambda: str(uuid4()))
    repository_url: str = Field(min_length=1)
    repository_path: str = Field(min_length=1)
    current_agent: str = Field(min_length=1)
    status: Literal["pending", "in_progress", "completed", "failed"]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Agent outputs
    bugs: List[BugReport] = Field(default_factory=list)
    test_cases: List[TestCase] = Field(default_factory=list)
    test_results: List[TestResult] = Field(default_factory=list)
    root_causes: List[RootCause] = Field(default_factory=list)
    fix_suggestions: List[FixSuggestion] = Field(default_factory=list)
    
    # Error tracking
    errors: List[Dict[str, str]] = Field(default_factory=list)
    retry_count: int = Field(default=0, ge=0)
    
    @field_validator("repository_url", "repository_path", "current_agent")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Ensure fields are not empty or whitespace only."""
        if not v.strip():
            raise ValueError("field cannot be empty or whitespace")
        return v.strip()
    
    @model_validator(mode="after")
    def update_timestamp(self) -> "AgentState":
        """Automatically update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()
        return self
    
    def to_dict(self) -> dict:
        """
        Serialize the state to a dictionary.
        
        Returns:
            Dictionary representation with datetime objects as ISO strings
        """
        return self.model_dump(mode="json")
    
    @classmethod
    def from_dict(cls, data: dict) -> "AgentState":
        """
        Deserialize state from a dictionary.
        
        Args:
            data: Dictionary containing state data
            
        Returns:
            AgentState instance
        """
        return cls.model_validate(data)
    
    def add_error(self, error_type: str, error_message: str, agent_name: Optional[str] = None) -> None:
        """
        Add an error to the error tracking list.
        
        Args:
            error_type: Type/category of the error
            error_message: Detailed error message
            agent_name: Name of the agent where error occurred (defaults to current_agent)
        """
        self.errors.append({
            "timestamp": datetime.utcnow().isoformat(),
            "agent": agent_name or self.current_agent,
            "error_type": error_type,
            "message": error_message
        })
        self.updated_at = datetime.utcnow()

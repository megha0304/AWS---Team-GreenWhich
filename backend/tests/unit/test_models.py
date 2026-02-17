"""
Unit tests for Pydantic data models.

Tests validation rules, field constraints, and serialization/deserialization
for all model classes.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from cloudforge.models import (
    AgentState,
    BugReport,
    TestCase,
    TestResult,
    RootCause,
    FixSuggestion,
)


class TestBugReport:
    """Test BugReport model validation and behavior."""
    
    def test_valid_bug_report(self):
        """Test creating a valid bug report."""
        bug = BugReport(
            file_path="src/main.py",
            line_number=42,
            severity="high",
            description="Null pointer dereference in main function",
            code_snippet="def main():\n    obj.method()",
            confidence_score=0.85
        )
        assert bug.file_path == "src/main.py"
        assert bug.line_number == 42
        assert bug.severity == "high"
        assert bug.confidence_score == 0.85
        assert bug.bug_id  # Should have auto-generated ID
    
    def test_bug_report_with_custom_id(self):
        """Test creating bug report with custom ID."""
        bug = BugReport(
            bug_id="custom-bug-123",
            file_path="src/main.py",
            line_number=1,
            severity="low",
            description="Minor style issue",
            code_snippet="x=1",
            confidence_score=0.5
        )
        assert bug.bug_id == "custom-bug-123"
    
    def test_invalid_line_number(self):
        """Test that line_number must be positive."""
        with pytest.raises(ValidationError) as exc_info:
            BugReport(
                file_path="src/main.py",
                line_number=0,
                severity="high",
                description="Test bug description",
                code_snippet="code",
                confidence_score=0.5
            )
        assert "line_number" in str(exc_info.value)
    
    def test_invalid_severity(self):
        """Test that severity must be one of the allowed values."""
        with pytest.raises(ValidationError):
            BugReport(
                file_path="src/main.py",
                line_number=1,
                severity="super-critical",  # Invalid
                description="Test bug description",
                code_snippet="code",
                confidence_score=0.5
            )
    
    def test_invalid_confidence_score(self):
        """Test that confidence_score must be between 0 and 1."""
        with pytest.raises(ValidationError):
            BugReport(
                file_path="src/main.py",
                line_number=1,
                severity="high",
                description="Test bug description",
                code_snippet="code",
                confidence_score=1.5  # Invalid
            )
    
    def test_description_too_short(self):
        """Test that description must be at least 10 characters."""
        with pytest.raises(ValidationError):
            BugReport(
                file_path="src/main.py",
                line_number=1,
                severity="high",
                description="short",  # Too short
                code_snippet="code",
                confidence_score=0.5
            )
    
    def test_empty_file_path(self):
        """Test that file_path cannot be empty or whitespace."""
        with pytest.raises(ValidationError):
            BugReport(
                file_path="   ",  # Whitespace only
                line_number=1,
                severity="high",
                description="Test bug description",
                code_snippet="code",
                confidence_score=0.5
            )


class TestTestCase:
    """Test TestCase model validation and behavior."""
    
    def test_valid_test_case(self):
        """Test creating a valid test case."""
        test = TestCase(
            bug_id="bug-123",
            test_code="def test_bug():\n    assert True",
            test_framework="pytest",
            expected_outcome="Test should pass"
        )
        assert test.bug_id == "bug-123"
        assert test.test_framework == "pytest"
        assert test.test_id  # Should have auto-generated ID
    
    def test_empty_test_code(self):
        """Test that test_code cannot be empty."""
        with pytest.raises(ValidationError):
            TestCase(
                bug_id="bug-123",
                test_code="   ",  # Whitespace only
                test_framework="pytest",
                expected_outcome="Test should pass"
            )


class TestTestResult:
    """Test TestResult model validation and behavior."""
    
    def test_valid_passed_result(self):
        """Test creating a valid passed test result."""
        result = TestResult(
            test_id="test-123",
            status="passed",
            stdout="All tests passed",
            stderr="",
            exit_code=0,
            execution_time_ms=1500,
            execution_platform="lambda"
        )
        assert result.status == "passed"
        assert result.exit_code == 0
        assert result.execution_time_ms == 1500
    
    def test_valid_failed_result(self):
        """Test creating a valid failed test result."""
        result = TestResult(
            test_id="test-123",
            status="failed",
            stdout="Test output",
            stderr="AssertionError",
            exit_code=1,
            execution_time_ms=2000,
            execution_platform="ecs"
        )
        assert result.status == "failed"
        assert result.exit_code == 1
    
    def test_inconsistent_passed_status(self):
        """Test that passed status requires exit_code 0."""
        with pytest.raises(ValidationError) as exc_info:
            TestResult(
                test_id="test-123",
                status="passed",
                exit_code=1,  # Inconsistent with passed status
                execution_time_ms=1000,
                execution_platform="lambda"
            )
        assert "exit_code" in str(exc_info.value).lower()
    
    def test_inconsistent_failed_status(self):
        """Test that failed status requires non-zero exit_code."""
        with pytest.raises(ValidationError) as exc_info:
            TestResult(
                test_id="test-123",
                status="failed",
                exit_code=0,  # Inconsistent with failed status
                execution_time_ms=1000,
                execution_platform="lambda"
            )
        assert "exit_code" in str(exc_info.value).lower()
    
    def test_negative_execution_time(self):
        """Test that execution_time_ms cannot be negative."""
        with pytest.raises(ValidationError):
            TestResult(
                test_id="test-123",
                status="passed",
                exit_code=0,
                execution_time_ms=-100,  # Invalid
                execution_platform="lambda"
            )


class TestRootCause:
    """Test RootCause model validation and behavior."""
    
    def test_valid_root_cause(self):
        """Test creating a valid root cause."""
        cause = RootCause(
            bug_id="bug-123",
            cause_description="Uninitialized variable access in loop",
            related_bugs=["bug-124", "bug-125"],
            confidence_score=0.9
        )
        assert cause.bug_id == "bug-123"
        assert len(cause.related_bugs) == 2
        assert cause.confidence_score == 0.9
    
    def test_root_cause_without_related_bugs(self):
        """Test creating root cause with no related bugs."""
        cause = RootCause(
            bug_id="bug-123",
            cause_description="Unique issue with no related bugs",
            confidence_score=0.8
        )
        assert cause.related_bugs == []
    
    def test_duplicate_related_bugs(self):
        """Test that related_bugs cannot contain duplicates."""
        with pytest.raises(ValidationError) as exc_info:
            RootCause(
                bug_id="bug-123",
                cause_description="Test root cause",
                related_bugs=["bug-124", "bug-124"],  # Duplicate
                confidence_score=0.8
            )
        assert "duplicates" in str(exc_info.value).lower()
    
    def test_short_cause_description(self):
        """Test that cause_description must be at least 10 characters."""
        with pytest.raises(ValidationError):
            RootCause(
                bug_id="bug-123",
                cause_description="short",  # Too short
                confidence_score=0.8
            )


class TestFixSuggestion:
    """Test FixSuggestion model validation and behavior."""
    
    def test_valid_fix_suggestion(self):
        """Test creating a valid fix suggestion."""
        fix = FixSuggestion(
            bug_id="bug-123",
            fix_description="Initialize variable before use",
            code_diff="- x = None\n+ x = 0",
            safety_score=0.95,
            impact_assessment="Low impact, safe to apply"
        )
        assert fix.bug_id == "bug-123"
        assert fix.safety_score == 0.95
    
    def test_empty_impact_assessment(self):
        """Test that impact_assessment cannot be empty."""
        with pytest.raises(ValidationError):
            FixSuggestion(
                bug_id="bug-123",
                fix_description="Test fix description",
                code_diff="- old\n+ new",
                safety_score=0.8,
                impact_assessment="   "  # Whitespace only
            )


class TestAgentState:
    """Test AgentState model validation and behavior."""
    
    def test_valid_agent_state(self):
        """Test creating a valid agent state."""
        state = AgentState(
            repository_url="https://github.com/example/repo",
            repository_path="/tmp/repo",
            current_agent="bug_detective",
            status="in_progress"
        )
        assert state.repository_url == "https://github.com/example/repo"
        assert state.status == "in_progress"
        assert state.workflow_id  # Should have auto-generated ID
        assert state.created_at
        assert state.updated_at
        assert state.bugs == []
        assert state.test_cases == []
        assert state.retry_count == 0
    
    def test_agent_state_with_bugs(self):
        """Test agent state with bug reports."""
        bug = BugReport(
            file_path="src/main.py",
            line_number=1,
            severity="high",
            description="Test bug description",
            code_snippet="code",
            confidence_score=0.8
        )
        state = AgentState(
            repository_url="https://github.com/example/repo",
            repository_path="/tmp/repo",
            current_agent="test_architect",
            status="in_progress",
            bugs=[bug]
        )
        assert len(state.bugs) == 1
        assert state.bugs[0].severity == "high"
    
    def test_serialization_to_dict(self):
        """Test serializing state to dictionary."""
        state = AgentState(
            repository_url="https://github.com/example/repo",
            repository_path="/tmp/repo",
            current_agent="bug_detective",
            status="pending"
        )
        state_dict = state.to_dict()
        
        assert isinstance(state_dict, dict)
        assert state_dict["repository_url"] == "https://github.com/example/repo"
        assert state_dict["status"] == "pending"
        assert "created_at" in state_dict
    
    def test_deserialization_from_dict(self):
        """Test deserializing state from dictionary."""
        state_dict = {
            "workflow_id": "test-workflow-123",
            "repository_url": "https://github.com/example/repo",
            "repository_path": "/tmp/repo",
            "current_agent": "bug_detective",
            "status": "pending",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
            "bugs": [],
            "test_cases": [],
            "test_results": [],
            "root_causes": [],
            "fix_suggestions": [],
            "errors": [],
            "retry_count": 0
        }
        state = AgentState.from_dict(state_dict)
        
        assert state.workflow_id == "test-workflow-123"
        assert state.repository_url == "https://github.com/example/repo"
        assert state.status == "pending"
    
    def test_add_error(self):
        """Test adding errors to state."""
        state = AgentState(
            repository_url="https://github.com/example/repo",
            repository_path="/tmp/repo",
            current_agent="bug_detective",
            status="in_progress"
        )
        
        state.add_error("APIError", "Bedrock API call failed")
        
        assert len(state.errors) == 1
        assert state.errors[0]["error_type"] == "APIError"
        assert state.errors[0]["message"] == "Bedrock API call failed"
        assert state.errors[0]["agent"] == "bug_detective"
        assert "timestamp" in state.errors[0]
    
    def test_add_error_with_custom_agent(self):
        """Test adding error with custom agent name."""
        state = AgentState(
            repository_url="https://github.com/example/repo",
            repository_path="/tmp/repo",
            current_agent="bug_detective",
            status="in_progress"
        )
        
        state.add_error("NetworkError", "Connection timeout", agent_name="test_architect")
        
        assert state.errors[0]["agent"] == "test_architect"
    
    def test_negative_retry_count(self):
        """Test that retry_count cannot be negative."""
        with pytest.raises(ValidationError):
            AgentState(
                repository_url="https://github.com/example/repo",
                repository_path="/tmp/repo",
                current_agent="bug_detective",
                status="pending",
                retry_count=-1  # Invalid
            )
    
    def test_empty_repository_url(self):
        """Test that repository_url cannot be empty."""
        with pytest.raises(ValidationError):
            AgentState(
                repository_url="   ",  # Whitespace only
                repository_path="/tmp/repo",
                current_agent="bug_detective",
                status="pending"
            )
    
    def test_roundtrip_serialization(self):
        """Test that serialization and deserialization preserve data."""
        original = AgentState(
            workflow_id="test-123",
            repository_url="https://github.com/example/repo",
            repository_path="/tmp/repo",
            current_agent="bug_detective",
            status="in_progress",
            bugs=[
                BugReport(
                    file_path="src/main.py",
                    line_number=42,
                    severity="high",
                    description="Test bug description",
                    code_snippet="code",
                    confidence_score=0.85
                )
            ]
        )
        
        # Serialize and deserialize
        state_dict = original.to_dict()
        restored = AgentState.from_dict(state_dict)
        
        assert restored.workflow_id == original.workflow_id
        assert restored.repository_url == original.repository_url
        assert len(restored.bugs) == 1
        assert restored.bugs[0].severity == "high"
        assert restored.bugs[0].confidence_score == 0.85

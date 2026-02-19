"""
Unit tests for export utilities.

Tests JSON and CSV export functionality for bug reports, fix suggestions,
and complete workflow summaries.
"""

import json
import csv
from io import StringIO
from datetime import datetime

import pytest

from cloudforge.models.state import (
    BugReport,
    FixSuggestion,
    AgentState,
    TestCase,
    TestResult,
    RootCause
)
from cloudforge.utils.export import (
    export_bugs_to_json,
    export_bugs_to_csv,
    export_fixes_to_json,
    export_fixes_to_csv,
    export_workflow_summary_to_json
)


@pytest.fixture
def sample_bugs():
    """Create sample bug reports for testing."""
    return [
        BugReport(
            bug_id="bug-1",
            file_path="src/main.py",
            line_number=42,
            severity="high",
            description="Potential null pointer dereference",
            code_snippet="result = obj.method()\nreturn result",
            confidence_score=0.85
        ),
        BugReport(
            bug_id="bug-2",
            file_path="src/utils.py",
            line_number=15,
            severity="medium",
            description="Unused variable detected",
            code_snippet="x = calculate()\ny = process()",
            confidence_score=0.92
        )
    ]


@pytest.fixture
def sample_fixes():
    """Create sample fix suggestions for testing."""
    return [
        FixSuggestion(
            bug_id="bug-1",
            fix_description="Add null check before method call",
            code_diff="- result = obj.method()\n+ result = obj.method() if obj else None",
            safety_score=0.95,
            impact_assessment="Low risk - defensive programming"
        ),
        FixSuggestion(
            bug_id="bug-2",
            fix_description="Remove unused variable",
            code_diff="- x = calculate()\n  y = process()",
            safety_score=0.99,
            impact_assessment="No risk - cleanup only"
        )
    ]


@pytest.fixture
def sample_workflow_state(sample_bugs, sample_fixes):
    """Create sample workflow state for testing."""
    state = AgentState(
        workflow_id="wf-123",
        repository_url="https://github.com/test/repo",
        repository_path="/tmp/repos/wf-123",
        current_agent="completed",
        status="completed"
    )
    
    state.bugs = sample_bugs
    state.fix_suggestions = sample_fixes
    
    state.test_cases = [
        TestCase(
            test_id="test-1",
            bug_id="bug-1",
            test_code="def test_null_check(): assert obj.method() is not None",
            test_framework="pytest",
            expected_outcome="Should handle null objects"
        )
    ]
    
    state.test_results = [
        TestResult(
            test_id="test-1",
            status="failed",
            stdout="Test output",
            stderr="",
            exit_code=1,
            execution_time_ms=150,
            execution_platform="lambda"
        )
    ]
    
    state.root_causes = [
        RootCause(
            bug_id="bug-1",
            cause_description="Missing null validation in API response handler",
            related_bugs=[],
            confidence_score=0.88
        )
    ]
    
    return state


class TestBugExportJSON:
    """Tests for bug export to JSON format."""
    
    def test_export_bugs_to_json_pretty(self, sample_bugs):
        """Test exporting bugs to pretty-printed JSON."""
        result = export_bugs_to_json(sample_bugs, pretty=True)
        
        # Should be valid JSON
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) == 2
        
        # Check first bug
        assert data[0]["bug_id"] == "bug-1"
        assert data[0]["file_path"] == "src/main.py"
        assert data[0]["line_number"] == 42
        assert data[0]["severity"] == "high"
        assert data[0]["confidence_score"] == 0.85
        
        # Should be pretty-printed (contains newlines and indentation)
        assert "\n" in result
        assert "  " in result
    
    def test_export_bugs_to_json_compact(self, sample_bugs):
        """Test exporting bugs to compact JSON."""
        result = export_bugs_to_json(sample_bugs, pretty=False)
        
        # Should be valid JSON
        data = json.loads(result)
        assert len(data) == 2
        
        # Should be compact (minimal whitespace)
        assert result.count("\n") < 5
    
    def test_export_empty_bugs_to_json(self):
        """Test exporting empty bug list to JSON."""
        result = export_bugs_to_json([])
        
        data = json.loads(result)
        assert data == []
    
    def test_export_bugs_preserves_all_fields(self, sample_bugs):
        """Test that all bug fields are preserved in JSON export."""
        result = export_bugs_to_json(sample_bugs)
        data = json.loads(result)
        
        bug = data[0]
        assert "bug_id" in bug
        assert "file_path" in bug
        assert "line_number" in bug
        assert "severity" in bug
        assert "description" in bug
        assert "code_snippet" in bug
        assert "confidence_score" in bug


class TestBugExportCSV:
    """Tests for bug export to CSV format."""
    
    def test_export_bugs_to_csv(self, sample_bugs):
        """Test exporting bugs to CSV format."""
        result = export_bugs_to_csv(sample_bugs)
        
        # Parse CSV
        reader = csv.DictReader(StringIO(result))
        rows = list(reader)
        
        assert len(rows) == 2
        
        # Check first bug
        assert rows[0]["bug_id"] == "bug-1"
        assert rows[0]["file_path"] == "src/main.py"
        assert rows[0]["line_number"] == "42"
        assert rows[0]["severity"] == "high"
        assert rows[0]["confidence_score"] == "0.85"
    
    def test_export_bugs_csv_headers(self, sample_bugs):
        """Test that CSV export includes correct headers."""
        result = export_bugs_to_csv(sample_bugs)
        
        # Parse CSV properly to get headers
        reader = csv.DictReader(StringIO(result))
        headers = reader.fieldnames
        
        assert "bug_id" in headers
        assert "file_path" in headers
        assert "line_number" in headers
        assert "severity" in headers
        assert "description" in headers
        assert "code_snippet" in headers
        assert "confidence_score" in headers
    
    def test_export_empty_bugs_to_csv(self):
        """Test exporting empty bug list to CSV."""
        result = export_bugs_to_csv([])
        
        # Should have headers only
        lines = result.strip().split("\n")
        assert len(lines) == 1
        assert "bug_id" in lines[0]
    
    def test_export_bugs_csv_escapes_newlines(self):
        """Test that newlines in code snippets are escaped."""
        bug = BugReport(
            bug_id="bug-1",
            file_path="test.py",
            line_number=1,
            severity="low",
            description="Test bug with sufficient length for validation",
            code_snippet="line1\nline2\nline3",
            confidence_score=0.5
        )
        
        result = export_bugs_to_csv([bug])
        
        # Newlines should be escaped as \n
        assert "\\n" in result
        # Should not have actual newlines in data (only header/row separators)
        lines = result.split("\n")
        assert len(lines) == 3  # header + 1 data row + trailing newline


class TestFixExportJSON:
    """Tests for fix suggestion export to JSON format."""
    
    def test_export_fixes_to_json_pretty(self, sample_fixes):
        """Test exporting fixes to pretty-printed JSON."""
        result = export_fixes_to_json(sample_fixes, pretty=True)
        
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) == 2
        
        # Check first fix
        assert data[0]["bug_id"] == "bug-1"
        assert data[0]["fix_description"] == "Add null check before method call"
        assert data[0]["safety_score"] == 0.95
        
        # Should be pretty-printed
        assert "\n" in result
    
    def test_export_fixes_to_json_compact(self, sample_fixes):
        """Test exporting fixes to compact JSON."""
        result = export_fixes_to_json(sample_fixes, pretty=False)
        
        data = json.loads(result)
        assert len(data) == 2
        
        # Should be compact
        assert result.count("\n") < 5
    
    def test_export_empty_fixes_to_json(self):
        """Test exporting empty fix list to JSON."""
        result = export_fixes_to_json([])
        
        data = json.loads(result)
        assert data == []


class TestFixExportCSV:
    """Tests for fix suggestion export to CSV format."""
    
    def test_export_fixes_to_csv(self, sample_fixes):
        """Test exporting fixes to CSV format."""
        result = export_fixes_to_csv(sample_fixes)
        
        reader = csv.DictReader(StringIO(result))
        rows = list(reader)
        
        assert len(rows) == 2
        
        # Check first fix
        assert rows[0]["bug_id"] == "bug-1"
        assert rows[0]["safety_score"] == "0.95"
    
    def test_export_fixes_csv_headers(self, sample_fixes):
        """Test that CSV export includes correct headers."""
        result = export_fixes_to_csv(sample_fixes)
        
        lines = result.split("\n")
        header_line = lines[0].strip()
        
        assert "bug_id" in header_line
        assert "fix_description" in header_line
        assert "code_diff" in header_line
        assert "safety_score" in header_line
        assert "impact_assessment" in header_line
    
    def test_export_empty_fixes_to_csv(self):
        """Test exporting empty fix list to CSV."""
        result = export_fixes_to_csv([])
        
        lines = result.strip().split("\n")
        assert len(lines) == 1
        assert "bug_id" in lines[0]
    
    def test_export_fixes_csv_escapes_newlines(self):
        """Test that newlines in diffs are escaped."""
        fix = FixSuggestion(
            bug_id="bug-1",
            fix_description="Multi-line description",
            code_diff="- old line\n+ new line",
            safety_score=0.8,
            impact_assessment="Test impact"
        )
        
        result = export_fixes_to_csv([fix])
        
        # Newlines should be escaped
        assert "\\n" in result


class TestWorkflowExport:
    """Tests for complete workflow export."""
    
    def test_export_workflow_summary_to_json(self, sample_workflow_state):
        """Test exporting complete workflow summary to JSON."""
        result = export_workflow_summary_to_json(sample_workflow_state, pretty=True)
        
        data = json.loads(result)
        
        # Check metadata
        assert data["workflow_id"] == "wf-123"
        assert data["repository_url"] == "https://github.com/test/repo"
        assert data["status"] == "completed"
        
        # Check summary
        assert data["summary"]["bugs_found"] == 2
        assert data["summary"]["tests_generated"] == 1
        assert data["summary"]["tests_executed"] == 1
        assert data["summary"]["root_causes_identified"] == 1
        assert data["summary"]["fixes_suggested"] == 2
        
        # Check data arrays
        assert len(data["bugs"]) == 2
        assert len(data["test_cases"]) == 1
        assert len(data["test_results"]) == 1
        assert len(data["root_causes"]) == 1
        assert len(data["fix_suggestions"]) == 2
    
    def test_export_workflow_includes_timestamps(self, sample_workflow_state):
        """Test that workflow export includes timestamps."""
        result = export_workflow_summary_to_json(sample_workflow_state)
        
        data = json.loads(result)
        
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_export_workflow_compact(self, sample_workflow_state):
        """Test exporting workflow in compact format."""
        result = export_workflow_summary_to_json(sample_workflow_state, pretty=False)
        
        data = json.loads(result)
        assert data["workflow_id"] == "wf-123"
        
        # Should be compact
        assert result.count("\n") < 10
    
    def test_export_empty_workflow(self):
        """Test exporting workflow with no results."""
        state = AgentState(
            workflow_id="wf-empty",
            repository_url="https://github.com/test/empty",
            repository_path="/tmp/repos/wf-empty",
            current_agent="detect",
            status="pending"
        )
        
        result = export_workflow_summary_to_json(state)
        data = json.loads(result)
        
        # Summary should show zeros
        assert data["summary"]["bugs_found"] == 0
        assert data["summary"]["tests_generated"] == 0
        assert data["summary"]["tests_executed"] == 0
        assert data["summary"]["root_causes_identified"] == 0
        assert data["summary"]["fixes_suggested"] == 0
        
        # Arrays should be empty
        assert data["bugs"] == []
        assert data["test_cases"] == []
        assert data["test_results"] == []
        assert data["root_causes"] == []
        assert data["fix_suggestions"] == []

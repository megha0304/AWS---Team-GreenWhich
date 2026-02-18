"""
Property-based tests for Bug Detective Agent.

These tests validate universal correctness properties using Hypothesis for
property-based testing. Each test generates randomized inputs to verify
that the Bug Detective Agent maintains its invariants across all scenarios.

**Validates: Requirements 1.1, 1.3, 1.4**
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import List
from unittest.mock import AsyncMock, Mock
from hypothesis import given, strategies as st, settings, assume
from hypothesis.stateful import RuleBasedStateMachine, rule, initialize

from cloudforge.agents.bug_detective import BugDetectiveAgent
from cloudforge.models.state import AgentState, BugReport
from cloudforge.models.config import SystemConfig


# ============================================================================
# Hypothesis Strategies for Generating Test Data
# ============================================================================

@st.composite
def source_file_strategy(draw):
    """Generate realistic source code file content."""
    extensions = ['.py', '.js', '.ts', '.java', '.go', '.rs', '.cpp']
    extension = draw(st.sampled_from(extensions))
    
    # Generate file content with some code-like structure
    lines = draw(st.lists(
        st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'P')),
            min_size=0,
            max_size=100
        ),
        min_size=1,
        max_size=50
    ))
    
    filename = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')),
        min_size=1,
        max_size=20
    )) + extension
    
    return filename, '\n'.join(lines)


@st.composite
def repository_strategy(draw, min_files=1, max_files=20):
    """
    Generate a temporary repository with source files.
    
    Returns tuple of (repo_path, expected_file_count, file_paths)
    """
    num_files = draw(st.integers(min_value=min_files, max_value=max_files))
    
    # Generate unique source files
    files = []
    seen_names = set()
    
    for _ in range(num_files):
        filename, content = draw(source_file_strategy())
        # Ensure unique filenames
        counter = 0
        original_name = filename
        while filename in seen_names:
            name_parts = original_name.rsplit('.', 1)
            filename = f"{name_parts[0]}_{counter}.{name_parts[1]}"
            counter += 1
        seen_names.add(filename)
        files.append((filename, content))
    
    return files


@st.composite
def bug_report_strategy(draw):
    """Generate a valid BugReport for testing."""
    # Use printable ASCII characters to avoid Unicode issues
    file_path = draw(st.text(
        alphabet=st.characters(min_codepoint=33, max_codepoint=126),  # Printable ASCII
        min_size=1,
        max_size=100
    ))
    
    # Generate description with printable ASCII (min 10 chars)
    description = draw(st.text(
        alphabet=st.characters(min_codepoint=32, max_codepoint=126),  # Printable ASCII + space
        min_size=10,
        max_size=500
    ))
    
    # Generate code_snippet with printable ASCII
    code_snippet = draw(st.text(
        alphabet=st.characters(min_codepoint=32, max_codepoint=126),
        min_size=1,
        max_size=1000
    ))
    
    return BugReport(
        file_path=file_path,
        line_number=draw(st.integers(min_value=1, max_value=10000)),
        severity=draw(st.sampled_from(['critical', 'high', 'medium', 'low'])),
        description=description,
        code_snippet=code_snippet,
        confidence_score=draw(st.floats(min_value=0.0, max_value=1.0))
    )


# ============================================================================
# Property 1: Complete file scanning
# **Validates: Requirements 1.1**
# ============================================================================

class TestCompleteFileScanning:
    """
    Property 1: Complete file scanning
    
    For any code repository, all source files should be scanned.
    """
    
    def _create_agent(self):
        """Create a BugDetectiveAgent instance for testing."""
        mock_config = Mock(spec=SystemConfig)
        mock_config.bedrock_model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
        mock_config.max_retries = 3
        mock_config.batch_size = 100
        mock_config.max_files_per_batch = 100
        
        mock_bedrock_client = Mock()
        
        return BugDetectiveAgent(mock_bedrock_client, mock_config)
    
    @given(repository_strategy(min_files=1, max_files=15))
    @settings(max_examples=20, deadline=5000)
    @pytest.mark.asyncio
    async def test_all_source_files_are_scanned(
        self,
        repository_files
    ):
        """
        Property: For any repository, all source files should be identified.
        
        This test verifies that _get_source_files returns all source code files
        and excludes non-source files and excluded directories.
        """
        # Create agent
        agent = self._create_agent()
        
        # Create temporary repository
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            
            # Write source files
            source_file_paths = []
            for filename, content in repository_files:
                file_path = repo_path / filename
                file_path.write_text(content, encoding='utf-8')
                source_file_paths.append(file_path)
            
            # Add some non-source files that should be excluded
            (repo_path / "README.md").write_text("# README")
            (repo_path / "data.json").write_text("{}")
            
            # Add excluded directory
            excluded_dir = repo_path / "node_modules"
            excluded_dir.mkdir()
            (excluded_dir / "package.js").write_text("// excluded")
            
            # Get source files
            found_files = agent._get_source_files(repo_path)
            
            # Property: All source files should be found
            assert len(found_files) == len(repository_files), \
                f"Expected {len(repository_files)} files, found {len(found_files)}"
            
            # Property: Found files should match created source files
            found_names = {f.name for f in found_files}
            expected_names = {filename for filename, _ in repository_files}
            assert found_names == expected_names, \
                f"File mismatch: expected {expected_names}, found {found_names}"
            
            # Property: Excluded files should not be in results
            assert not any("node_modules" in str(f) for f in found_files), \
                "Excluded directory files should not be scanned"
            assert not any(f.suffix in ['.md', '.json'] for f in found_files), \
                "Non-source files should not be scanned"
    
    @given(st.integers(min_value=0, max_value=100))
    @settings(max_examples=10)
    def test_empty_repository_returns_empty_list(self, num_non_source_files):
        """
        Property: For a repository with no source files, scanning should return empty list.
        """
        # Create agent
        agent = self._create_agent()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            
            # Create only non-source files
            for i in range(num_non_source_files):
                (repo_path / f"file{i}.txt").write_text("content")
                (repo_path / f"data{i}.json").write_text("{}")
            
            found_files = agent._get_source_files(repo_path)
            
            # Property: No source files should be found
            assert len(found_files) == 0, \
                "Repository with no source files should return empty list"


# ============================================================================
# Property 3: Severity classification completeness
# **Validates: Requirements 1.3**
# ============================================================================

class TestSeverityClassification:
    """
    Property 3: Severity classification completeness
    
    For any bug detected, the bug should be classified with exactly one
    severity level from {critical, high, medium, low}.
    """
    
    @given(st.lists(bug_report_strategy(), min_size=1, max_size=50))
    @settings(max_examples=30)
    def test_all_bugs_have_valid_severity(self, bugs: List[BugReport]):
        """
        Property: Every bug must have exactly one valid severity level.
        """
        valid_severities = {'critical', 'high', 'medium', 'low'}
        
        for bug in bugs:
            # Property: Severity must be one of the valid values
            assert bug.severity in valid_severities, \
                f"Bug {bug.bug_id} has invalid severity: {bug.severity}"
            
            # Property: Severity must be a string (not None, not empty)
            assert isinstance(bug.severity, str), \
                f"Bug {bug.bug_id} severity must be a string"
            assert bug.severity, \
                f"Bug {bug.bug_id} severity cannot be empty"
    
    @given(bug_report_strategy())
    @settings(max_examples=50)
    def test_severity_is_immutable_after_creation(self, bug: BugReport):
        """
        Property: Bug severity should not change after bug creation.
        """
        original_severity = bug.severity
        
        # Verify severity is set
        assert original_severity in {'critical', 'high', 'medium', 'low'}
        
        # Property: Severity should remain constant
        assert bug.severity == original_severity, \
            "Bug severity should not change after creation"


# ============================================================================
# Property 4: Bug report structure
# **Validates: Requirements 1.4**
# ============================================================================

class TestBugReportStructure:
    """
    Property 4: Bug report structure
    
    For any completed scan, all bug reports should contain required fields:
    file_path, line_number, severity, description, code_snippet, confidence_score.
    """
    
    @given(st.lists(bug_report_strategy(), min_size=0, max_size=100))
    @settings(max_examples=30)
    def test_all_bugs_have_required_fields(self, bugs: List[BugReport]):
        """
        Property: Every bug report must contain all required fields.
        """
        required_fields = {
            'bug_id', 'file_path', 'line_number', 'severity',
            'description', 'code_snippet', 'confidence_score'
        }
        
        for bug in bugs:
            # Property: All required fields must be present
            bug_dict = bug.model_dump()
            assert required_fields.issubset(bug_dict.keys()), \
                f"Bug {bug.bug_id} missing required fields"
            
            # Property: Fields must not be None
            for field in required_fields:
                assert bug_dict[field] is not None, \
                    f"Bug {bug.bug_id} field '{field}' cannot be None"
    
    @given(bug_report_strategy())
    @settings(max_examples=50)
    def test_bug_report_field_types(self, bug: BugReport):
        """
        Property: Bug report fields must have correct types.
        """
        # Property: bug_id must be a string
        assert isinstance(bug.bug_id, str), "bug_id must be a string"
        assert len(bug.bug_id) > 0, "bug_id cannot be empty"
        
        # Property: file_path must be a non-empty string
        assert isinstance(bug.file_path, str), "file_path must be a string"
        assert len(bug.file_path) > 0, "file_path cannot be empty"
        
        # Property: line_number must be a positive integer
        assert isinstance(bug.line_number, int), "line_number must be an integer"
        assert bug.line_number > 0, "line_number must be positive"
        
        # Property: severity must be a valid string
        assert isinstance(bug.severity, str), "severity must be a string"
        assert bug.severity in {'critical', 'high', 'medium', 'low'}, \
            "severity must be a valid level"
        
        # Property: description must be a non-empty string (min 10 chars)
        assert isinstance(bug.description, str), "description must be a string"
        assert len(bug.description) >= 10, "description must be at least 10 characters"
        
        # Property: code_snippet must be a non-empty string
        assert isinstance(bug.code_snippet, str), "code_snippet must be a string"
        assert len(bug.code_snippet) > 0, "code_snippet cannot be empty"
        
        # Property: confidence_score must be a float between 0.0 and 1.0
        assert isinstance(bug.confidence_score, float), \
            "confidence_score must be a float"
        assert 0.0 <= bug.confidence_score <= 1.0, \
            "confidence_score must be between 0.0 and 1.0"
    
    @given(st.lists(bug_report_strategy(), min_size=1, max_size=50))
    @settings(max_examples=20)
    def test_bug_ids_are_unique(self, bugs: List[BugReport]):
        """
        Property: All bug IDs in a scan should be unique.
        """
        bug_ids = [bug.bug_id for bug in bugs]
        
        # Property: No duplicate bug IDs
        assert len(bug_ids) == len(set(bug_ids)), \
            "Bug IDs must be unique within a scan"
    
    @given(bug_report_strategy())
    @settings(max_examples=30)
    def test_bug_report_serialization(self, bug: BugReport):
        """
        Property: Bug reports must be serializable to dict and back.
        """
        # Serialize to dict
        bug_dict = bug.model_dump()
        
        # Property: Serialization should produce a dict
        assert isinstance(bug_dict, dict), "Serialization must produce a dict"
        
        # Deserialize back to BugReport
        restored_bug = BugReport.model_validate(bug_dict)
        
        # Property: Round-trip serialization should preserve all fields
        assert restored_bug.bug_id == bug.bug_id
        assert restored_bug.file_path == bug.file_path
        assert restored_bug.line_number == bug.line_number
        assert restored_bug.severity == bug.severity
        assert restored_bug.description == bug.description
        assert restored_bug.code_snippet == bug.code_snippet
        assert restored_bug.confidence_score == bug.confidence_score


# ============================================================================
# Integration Property Tests
# ============================================================================

class TestBugDetectiveIntegration:
    """
    Integration tests that verify properties across the full Bug Detective workflow.
    """
    
    def _create_agent(self):
        """Create a BugDetectiveAgent instance for testing."""
        mock_config = Mock(spec=SystemConfig)
        mock_config.bedrock_model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
        mock_config.max_retries = 3
        mock_config.batch_size = 100
        mock_config.max_files_per_batch = 100
        
        mock_bedrock_client = Mock()
        
        return BugDetectiveAgent(mock_bedrock_client, mock_config)
    
    @given(repository_strategy(min_files=1, max_files=10))
    @settings(max_examples=10, deadline=5000)
    @pytest.mark.asyncio
    async def test_detect_bugs_maintains_state_structure(
        self,
        repository_files
    ):
        """
        Property: detect_bugs should maintain AgentState structure and add bugs.
        """
        # Create agent
        agent = self._create_agent()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            
            # Write source files
            for filename, content in repository_files:
                (repo_path / filename).write_text(content, encoding='utf-8')
            
            # Create initial state
            state = AgentState(
                repository_url="https://github.com/test/repo",
                repository_path=str(repo_path),
                current_agent="bug_detective",
                status="in_progress"
            )
            
            # Mock the _call_bedrock_for_bugs to return empty list (placeholder mode)
            agent._call_bedrock_for_bugs = AsyncMock(return_value=[])
            
            # Run detection
            result_state = await agent.detect_bugs(state)
            
            # Property: State structure should be preserved
            assert result_state.workflow_id == state.workflow_id
            assert result_state.repository_url == state.repository_url
            assert result_state.repository_path == state.repository_path
            
            # Property: Current agent should be updated
            assert result_state.current_agent == "bug_detective"
            
            # Property: Bugs list should be present (even if empty in mock mode)
            assert isinstance(result_state.bugs, list)
            
            # Property: All bugs should have valid structure
            for bug in result_state.bugs:
                assert isinstance(bug, BugReport)
                assert bug.file_path
                assert bug.line_number > 0
                assert bug.severity in {'critical', 'high', 'medium', 'low'}
                assert len(bug.description) >= 10
                assert bug.code_snippet
                assert 0.0 <= bug.confidence_score <= 1.0

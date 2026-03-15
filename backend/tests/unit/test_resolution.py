"""
Unit tests for Resolution Agent.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from cloudforge.agents.resolution import ResolutionAgent
from cloudforge.models.state import (
    AgentState,
    BugReport,
    RootCause,
    FixSuggestion
)


@pytest.fixture
def mock_q_developer_client():
    """Create a mock Q Developer client."""
    client = Mock()
    client.generate_fix = AsyncMock()
    return client


@pytest.fixture
def resolution_config():
    """Create test configuration."""
    return {
        "q_developer_endpoint": "https://q-developer.example.com",
        "max_fixes_per_bug": 3,
        "timeout_seconds": 30,
        "bedrock_model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
        "max_retries": 3
    }


@pytest.fixture
def resolution_agent(mock_q_developer_client, resolution_config):
    """Create a Resolution Agent instance."""
    return ResolutionAgent(mock_q_developer_client, resolution_config)


@pytest.fixture
def sample_bug():
    """Create a sample bug report."""
    return BugReport(
        bug_id="bug-001",
        file_path="src/utils/helper.py",
        line_number=42,
        severity="high",
        description="Potential null pointer dereference",
        code_snippet="result = obj.value",
        confidence_score=0.85
    )


@pytest.fixture
def sample_root_cause(sample_bug):
    """Create a sample root cause."""
    return RootCause(
        bug_id=sample_bug.bug_id,
        cause_description="Missing null check before accessing object property",
        related_bugs=["bug-002", "bug-003"],
        confidence_score=0.90
    )


@pytest.fixture
def sample_state(sample_bug, sample_root_cause):
    """Create a sample agent state."""
    return AgentState(
        workflow_id="test-workflow-001",
        repository_url="https://github.com/example/repo",
        repository_path="/tmp/repo",
        current_agent="analysis",
        status="in_progress",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        bugs=[sample_bug],
        root_causes=[sample_root_cause]
    )


class TestResolutionAgentInitialization:
    """Test Resolution Agent initialization."""
    
    def test_initialization(self, mock_q_developer_client, resolution_config):
        """Test agent initializes correctly."""
        agent = ResolutionAgent(mock_q_developer_client, resolution_config)
        
        assert agent.q_developer_client == mock_q_developer_client
        assert agent.config == resolution_config
        assert agent.logger is not None


class TestGenerateFixes:
    """Test fix generation functionality."""
    
    @pytest.mark.asyncio
    async def test_generate_fixes_success(self, resolution_agent, sample_state):
        """Test successful fix generation."""
        result = await resolution_agent.generate_fixes(sample_state)
        
        assert result.current_agent == "resolution"
        assert result.status == "completed"
        assert len(result.fix_suggestions) == 1
        assert result.fix_suggestions[0].bug_id == "bug-001"
    
    @pytest.mark.asyncio
    async def test_generate_fixes_no_root_causes(self, resolution_agent):
        """Test handling of state with no root causes."""
        state = AgentState(
            workflow_id="test-workflow-002",
            repository_url="https://github.com/example/repo",
            repository_path="/tmp/repo",
            current_agent="analysis",
            status="in_progress",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            bugs=[],
            root_causes=[]
        )
        
        result = await resolution_agent.generate_fixes(state)
        
        assert result.status == "completed"
        assert len(result.fix_suggestions) == 0
    
    @pytest.mark.asyncio
    async def test_generate_fixes_multiple_root_causes(self, resolution_agent):
        """Test fix generation for multiple root causes."""
        bug1 = BugReport(
            bug_id="bug-001",
            file_path="src/a.py",
            line_number=10,
            severity="critical",
            description="Critical bug in module A",
            code_snippet="code1",
            confidence_score=0.9
        )
        bug2 = BugReport(
            bug_id="bug-002",
            file_path="src/b.py",
            line_number=20,
            severity="medium",
            description="Medium severity bug in module B",
            code_snippet="code2",
            confidence_score=0.7
        )
        
        root_cause1 = RootCause(
            bug_id="bug-001",
            cause_description="Root cause for bug 001",
            related_bugs=[],
            confidence_score=0.85
        )
        root_cause2 = RootCause(
            bug_id="bug-002",
            cause_description="Root cause for bug 002",
            related_bugs=[],
            confidence_score=0.75
        )
        
        state = AgentState(
            workflow_id="test-workflow-003",
            repository_url="https://github.com/example/repo",
            repository_path="/tmp/repo",
            current_agent="analysis",
            status="in_progress",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            bugs=[bug1, bug2],
            root_causes=[root_cause1, root_cause2]
        )
        
        result = await resolution_agent.generate_fixes(state)
        
        assert result.status == "completed"
        assert len(result.fix_suggestions) == 2
        
        # Verify fixes are ranked by safety score (descending)
        for i in range(len(result.fix_suggestions) - 1):
            assert result.fix_suggestions[i].safety_score >= result.fix_suggestions[i + 1].safety_score
    
    @pytest.mark.asyncio
    async def test_generate_fixes_missing_bug(self, resolution_agent):
        """Test handling when bug is not found for root cause."""
        root_cause = RootCause(
            bug_id="nonexistent-bug",
            cause_description="Some cause",
            related_bugs=[],
            confidence_score=0.8
        )
        
        state = AgentState(
            workflow_id="test-workflow-004",
            repository_url="https://github.com/example/repo",
            repository_path="/tmp/repo",
            current_agent="analysis",
            status="in_progress",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            bugs=[],
            root_causes=[root_cause]
        )
        
        result = await resolution_agent.generate_fixes(state)
        
        assert result.status == "completed"
        assert len(result.fix_suggestions) == 0


class TestFixGeneration:
    """Test individual fix generation."""
    
    @pytest.mark.asyncio
    async def test_generate_fix_structure(self, resolution_agent, sample_bug, sample_root_cause):
        """Test that generated fix has correct structure."""
        fix = await resolution_agent._generate_fix(
            sample_root_cause,
            sample_bug,
            "/tmp/repo"
        )
        
        assert isinstance(fix, FixSuggestion)
        assert fix.bug_id == sample_bug.bug_id
        assert fix.fix_description
        assert fix.code_diff
        assert 0.0 <= fix.safety_score <= 1.0
        assert fix.impact_assessment
    
    @pytest.mark.asyncio
    async def test_generate_fix_description(self, resolution_agent, sample_bug, sample_root_cause):
        """Test fallback diff generation."""
        diff = ResolutionAgent._generate_fallback_diff(sample_bug)
        
        assert "---" in diff
        assert "+++" in diff
        assert "@@" in diff
        assert sample_bug.file_path in diff
    
    @pytest.mark.asyncio
    async def test_generate_code_diff_format(self, resolution_agent, sample_bug):
        """Test that fallback code diff is in unified diff format."""
        diff = ResolutionAgent._generate_fallback_diff(sample_bug)
        
        # Check unified diff format markers
        assert "---" in diff
        assert "+++" in diff
        assert "@@" in diff
        assert sample_bug.file_path in diff


class TestSafetyScoreCalculation:
    """Test safety score calculation."""
    
    def test_safety_score_critical_severity(self, resolution_agent):
        """Test safety score for critical severity bug."""
        bug = BugReport(
            bug_id="bug-001",
            file_path="test.py",
            line_number=1,
            severity="critical",
            description="Test critical bug",
            code_snippet="code",
            confidence_score=0.9
        )
        root_cause = RootCause(
            bug_id="bug-001",
            cause_description="Test root cause",
            related_bugs=[],
            confidence_score=0.9
        )
        
        score = resolution_agent._calculate_safety_score(bug, root_cause)
        
        assert 0.0 <= score <= 1.0
        assert score > 0.8  # Critical bugs with high confidence should have high safety scores
    
    def test_safety_score_low_severity(self, resolution_agent):
        """Test safety score for low severity bug."""
        bug = BugReport(
            bug_id="bug-002",
            file_path="test.py",
            line_number=1,
            severity="low",
            description="Test low severity bug",
            code_snippet="code",
            confidence_score=0.5
        )
        root_cause = RootCause(
            bug_id="bug-002",
            cause_description="Test root cause",
            related_bugs=[],
            confidence_score=0.5
        )
        
        score = resolution_agent._calculate_safety_score(bug, root_cause)
        
        assert 0.0 <= score <= 1.0
        assert score < 0.6  # Low severity with low confidence should have lower safety scores
    
    def test_safety_score_range(self, resolution_agent):
        """Test that safety scores are always in valid range."""
        severities = ["critical", "high", "medium", "low"]
        
        for severity in severities:
            bug = BugReport(
                bug_id="bug-test",
                file_path="test.py",
                line_number=1,
                severity=severity,
                description="Test bug description",
                code_snippet="code",
                confidence_score=0.75
            )
            root_cause = RootCause(
                bug_id="bug-test",
                cause_description="Test root cause",
                related_bugs=[],
                confidence_score=0.75
            )
            
            score = resolution_agent._calculate_safety_score(bug, root_cause)
            assert 0.0 <= score <= 1.0


class TestImpactAssessment:
    """Test impact assessment generation."""
    
    def test_impact_assessment_critical(self, resolution_agent):
        """Test impact assessment for critical bug."""
        bug = BugReport(
            bug_id="bug-001",
            file_path="test.py",
            line_number=1,
            severity="critical",
            description="Test critical bug",
            code_snippet="code",
            confidence_score=0.9
        )
        root_cause = RootCause(
            bug_id="bug-001",
            cause_description="Test root cause",
            related_bugs=[],
            confidence_score=0.9
        )
        
        assessment = resolution_agent._generate_impact_assessment(bug, root_cause)
        
        assert "critical" in assessment.lower() or "high impact" in assessment.lower()
    
    def test_impact_assessment_with_related_bugs(self, resolution_agent):
        """Test impact assessment mentions related bugs."""
        bug = BugReport(
            bug_id="bug-001",
            file_path="test.py",
            line_number=1,
            severity="high",
            description="Test high severity bug",
            code_snippet="code",
            confidence_score=0.9
        )
        root_cause = RootCause(
            bug_id="bug-001",
            cause_description="Test root cause",
            related_bugs=["bug-002", "bug-003"],
            confidence_score=0.9
        )
        
        assessment = resolution_agent._generate_impact_assessment(bug, root_cause)
        
        assert "2" in assessment or "related" in assessment.lower()


class TestFixRanking:
    """Test fix ranking functionality."""
    
    def test_rank_fixes_by_safety_score(self, resolution_agent):
        """Test that fixes are ranked by safety score descending."""
        fixes = [
            FixSuggestion(
                bug_id="bug-001",
                fix_description="Fix for bug 001",
                code_diff="diff1",
                safety_score=0.5,
                impact_assessment="Low"
            ),
            FixSuggestion(
                bug_id="bug-002",
                fix_description="Fix for bug 002",
                code_diff="diff2",
                safety_score=0.9,
                impact_assessment="High"
            ),
            FixSuggestion(
                bug_id="bug-003",
                fix_description="Fix for bug 003",
                code_diff="diff3",
                safety_score=0.7,
                impact_assessment="Medium"
            )
        ]
        
        ranked = resolution_agent._rank_fixes(fixes)
        
        assert len(ranked) == 3
        assert ranked[0].safety_score == 0.9
        assert ranked[1].safety_score == 0.7
        assert ranked[2].safety_score == 0.5
    
    def test_rank_fixes_empty_list(self, resolution_agent):
        """Test ranking empty list of fixes."""
        ranked = resolution_agent._rank_fixes([])
        assert ranked == []


class TestUtilityMethods:
    """Test utility methods."""
    
    def test_find_bug_by_id_found(self, resolution_agent, sample_bug):
        """Test finding bug by ID when it exists."""
        bugs = [sample_bug]
        found = resolution_agent._find_bug_by_id(bugs, "bug-001")
        
        assert found == sample_bug
    
    def test_find_bug_by_id_not_found(self, resolution_agent, sample_bug):
        """Test finding bug by ID when it doesn't exist."""
        bugs = [sample_bug]
        found = resolution_agent._find_bug_by_id(bugs, "nonexistent")
        
        assert found is None
    
    def test_find_bug_by_id_empty_list(self, resolution_agent):
        """Test finding bug in empty list."""
        found = resolution_agent._find_bug_by_id([], "bug-001")
        assert found is None


class TestErrorHandling:
    """Test error handling in Resolution Agent."""
    
    @pytest.mark.asyncio
    async def test_error_handling_continues_processing(self, resolution_agent, monkeypatch):
        """Test that errors in one fix don't stop processing others."""
        bug1 = BugReport(
            bug_id="bug-001",
            file_path="src/a.py",
            line_number=10,
            severity="high",
            description="High severity bug in module A",
            code_snippet="code1",
            confidence_score=0.9
        )
        bug2 = BugReport(
            bug_id="bug-002",
            file_path="src/b.py",
            line_number=20,
            severity="medium",
            description="Medium severity bug in module B",
            code_snippet="code2",
            confidence_score=0.7
        )
        
        root_cause1 = RootCause(
            bug_id="bug-001",
            cause_description="Root cause for bug 001",
            related_bugs=[],
            confidence_score=0.85
        )
        root_cause2 = RootCause(
            bug_id="bug-002",
            cause_description="Root cause for bug 002",
            related_bugs=[],
            confidence_score=0.75
        )
        
        state = AgentState(
            workflow_id="test-workflow-error",
            repository_url="https://github.com/example/repo",
            repository_path="/tmp/repo",
            current_agent="analysis",
            status="in_progress",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            bugs=[bug1, bug2],
            root_causes=[root_cause1, root_cause2]
        )
        
        # Make _generate_fix fail for first bug but succeed for second
        original_generate_fix = resolution_agent._generate_fix
        call_count = [0]
        
        async def failing_generate_fix(root_cause, bug, repo_path):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Simulated failure")
            return await original_generate_fix(root_cause, bug, repo_path)
        
        monkeypatch.setattr(resolution_agent, "_generate_fix", failing_generate_fix)
        
        result = await resolution_agent.generate_fixes(state)
        
        # Should complete with one fix and one error
        assert result.status == "completed"
        assert len(result.fix_suggestions) == 1
        assert len(result.errors) == 1
        assert result.errors[0]["agent"] == "resolution"

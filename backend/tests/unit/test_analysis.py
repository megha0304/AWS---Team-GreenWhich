"""Unit tests for Analysis Agent."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import json

from cloudforge.agents.analysis import AnalysisAgent
from cloudforge.models.state import AgentState, TestResult, BugReport, RootCause, TestCase
from cloudforge.models.config import SystemConfig


@pytest.fixture
def mock_config():
    """Create a mock SystemConfig for testing."""
    config = Mock(spec=SystemConfig)
    config.bedrock_model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
    config.max_retries = 3
    return config


@pytest.fixture
def mock_bedrock_client():
    """Create a mock Bedrock client."""
    return Mock()


@pytest.fixture
def agent(mock_bedrock_client, mock_config):
    """Create an AnalysisAgent instance for testing."""
    return AnalysisAgent(mock_bedrock_client, mock_config)


@pytest.fixture
def sample_bug():
    """Create a sample bug report for testing."""
    return BugReport(
        bug_id="bug-123",
        file_path="src/utils.py",
        line_number=42,
        severity="high",
        description="Potential null pointer dereference",
        code_snippet="result = obj.value",
        confidence_score=0.85
    )


@pytest.fixture
def sample_test_case(sample_bug):
    """Create a sample test case for testing."""
    return TestCase(
        test_id="test-123",
        bug_id=sample_bug.bug_id,
        test_code="def test_null_check(): assert obj is not None",
        test_framework="pytest",
        expected_outcome="Test should pass"
    )


@pytest.fixture
def sample_test_result():
    """Create a sample failed test result for testing."""
    return TestResult(
        test_id="test-123",
        status="failed",
        stdout="",
        stderr="AttributeError: 'NoneType' object has no attribute 'value'",
        exit_code=1,
        execution_time_ms=150,
        execution_platform="lambda"
    )


@pytest.fixture
def sample_state_with_results(sample_bug, sample_test_case, sample_test_result):
    """Create a sample AgentState with test results."""
    return AgentState(
        workflow_id="workflow-123",
        repository_url="https://github.com/test/repo",
        repository_path="/tmp/test-repo",
        current_agent="execution",
        status="in_progress",
        bugs=[sample_bug],
        test_cases=[sample_test_case],
        test_results=[sample_test_result]
    )


class TestAnalysisAgentInitialization:
    """Test Analysis Agent initialization."""
    
    def test_agent_initialization(self, mock_bedrock_client, mock_config):
        """Test that agent initializes correctly with configuration."""
        agent = AnalysisAgent(mock_bedrock_client, mock_config)
        
        assert agent.bedrock_client == mock_bedrock_client
        assert agent.config == mock_config
        assert agent.model_id == "anthropic.claude-3-sonnet-20240229-v1:0"
        assert agent.max_retries == 3


class TestBugFinding:
    """Test bug finding logic."""
    
    def test_find_bug_for_test_success(self, agent, sample_bug, sample_test_case, sample_test_result):
        """Test finding bug for a test result."""
        bug = agent._find_bug_for_test(
            sample_test_result,
            [sample_bug],
            [sample_test_case]
        )
        
        assert bug is not None
        assert bug.bug_id == sample_bug.bug_id
    
    def test_find_bug_for_test_no_test_case(self, agent, sample_bug, sample_test_result):
        """Test finding bug when test case doesn't exist."""
        bug = agent._find_bug_for_test(
            sample_test_result,
            [sample_bug],
            []  # No test cases
        )
        
        assert bug is None
    
    def test_find_bug_for_test_no_bug(self, agent, sample_test_case, sample_test_result):
        """Test finding bug when bug doesn't exist."""
        bug = agent._find_bug_for_test(
            sample_test_result,
            [],  # No bugs
            [sample_test_case]
        )
        
        assert bug is None


class TestMockCauseGeneration:
    """Test mock cause generation logic."""
    
    def test_generate_mock_cause_null_pointer(self, agent, sample_test_result):
        """Test mock cause generation for null pointer bugs."""
        bug = BugReport(
            bug_id="bug-1",
            file_path="test.py",
            line_number=10,
            severity="high",
            description="Null pointer dereference detected",
            code_snippet="x = obj.value",
            confidence_score=0.9
        )
        
        cause = agent._generate_mock_cause(bug, sample_test_result)
        
        assert "Null pointer" in cause or "None value" in cause
        assert "test.py" in cause
        assert "10" in cause
    
    def test_generate_mock_cause_index_error(self, agent, sample_test_result):
        """Test mock cause generation for index errors."""
        bug = BugReport(
            bug_id="bug-2",
            file_path="test.py",
            line_number=20,
            severity="medium",
            description="Array index out of bounds",
            code_snippet="item = arr[10]",
            confidence_score=0.8
        )
        
        cause = agent._generate_mock_cause(bug, sample_test_result)
        
        assert "index" in cause.lower() or "array" in cause.lower()
        assert "test.py" in cause
    
    def test_generate_mock_cause_type_error(self, agent, sample_test_result):
        """Test mock cause generation for type errors."""
        bug = BugReport(
            bug_id="bug-3",
            file_path="test.py",
            line_number=30,
            severity="low",
            description="Type mismatch in function call",
            code_snippet="result = func('string')",
            confidence_score=0.7
        )
        
        cause = agent._generate_mock_cause(bug, sample_test_result)
        
        assert "type" in cause.lower()
        assert "test.py" in cause


class TestConfidenceEstimation:
    """Test confidence score estimation."""
    
    def test_estimate_confidence_base(self, agent, sample_bug, sample_test_result):
        """Test base confidence estimation."""
        confidence = agent._estimate_mock_confidence(sample_bug, sample_test_result)
        
        assert 0.0 <= confidence <= 1.0
        # Should be close to bug confidence
        assert abs(confidence - sample_bug.confidence_score) < 0.2
    
    def test_estimate_confidence_with_clear_error(self, agent, sample_bug):
        """Test confidence boost with clear error message."""
        test_result = TestResult(
            test_id="test-1",
            status="failed",
            stdout="",
            stderr="Very detailed error message explaining exactly what went wrong",
            exit_code=1,
            execution_time_ms=100,
            execution_platform="lambda"
        )
        
        confidence = agent._estimate_mock_confidence(sample_bug, test_result)
        
        # Should be higher than base bug confidence
        assert confidence >= sample_bug.confidence_score
    
    def test_estimate_confidence_critical_severity(self, agent, sample_test_result):
        """Test confidence boost for critical bugs."""
        bug = BugReport(
            bug_id="bug-1",
            file_path="test.py",
            line_number=10,
            severity="critical",
            description="Critical bug",
            code_snippet="code",
            confidence_score=0.5
        )
        
        confidence = agent._estimate_mock_confidence(bug, sample_test_result)
        
        # Should be higher than base confidence
        assert confidence > 0.5


class TestKeyTermExtraction:
    """Test key term extraction for grouping."""
    
    def test_extract_key_terms_basic(self, agent):
        """Test basic key term extraction."""
        text = "Null pointer dereference in authentication module"
        terms = agent._extract_key_terms(text)
        
        assert "pointer" in terms
        assert "dereference" in terms
        assert "authentication" in terms
        assert "module" in terms
        # Stopwords should be filtered
        assert "in" not in terms
    
    def test_extract_key_terms_filters_short_words(self, agent):
        """Test that short words are filtered."""
        text = "A bug in the code at line ten"
        terms = agent._extract_key_terms(text)
        
        # Short words should be filtered
        assert "a" not in terms
        assert "in" not in terms
        assert "at" not in terms
    
    def test_extract_key_terms_case_insensitive(self, agent):
        """Test that extraction is case insensitive."""
        text = "ERROR in Module"
        terms = agent._extract_key_terms(text)
        
        assert "error" in terms
        assert "module" in terms
        assert "ERROR" not in terms  # Should be lowercase


class TestBugGrouping:
    """Test bug grouping logic."""
    
    def test_group_single_bug(self, agent):
        """Test grouping with single bug."""
        root_causes = [
            RootCause(
                bug_id="bug-1",
                cause_description="Null pointer in auth",
                related_bugs=[],
                confidence_score=0.9
            )
        ]
        
        grouped = agent._group_related_bugs(root_causes)
        
        assert len(grouped) == 1
        assert grouped[0].related_bugs == []
    
    def test_group_similar_bugs(self, agent):
        """Test grouping of similar bugs."""
        root_causes = [
            RootCause(
                bug_id="bug-1",
                cause_description="Null pointer dereference in authentication module",
                related_bugs=[],
                confidence_score=0.9
            ),
            RootCause(
                bug_id="bug-2",
                cause_description="Null pointer dereference in authentication system",
                related_bugs=[],
                confidence_score=0.85
            )
        ]
        
        grouped = agent._group_related_bugs(root_causes)
        
        assert len(grouped) == 2
        # Both should have each other as related
        assert "bug-2" in grouped[0].related_bugs
        assert "bug-1" in grouped[1].related_bugs
    
    def test_group_different_bugs(self, agent):
        """Test that different bugs are not grouped."""
        root_causes = [
            RootCause(
                bug_id="bug-1",
                cause_description="Null pointer dereference",
                related_bugs=[],
                confidence_score=0.9
            ),
            RootCause(
                bug_id="bug-2",
                cause_description="Array index out of bounds",
                related_bugs=[],
                confidence_score=0.85
            )
        ]
        
        grouped = agent._group_related_bugs(root_causes)
        
        assert len(grouped) == 2
        # Should not be related
        assert grouped[0].related_bugs == []
        assert grouped[1].related_bugs == []


class TestResultAnalysis:
    """Test result analysis logic."""
    
    @pytest.mark.asyncio
    async def test_analyze_results_with_failures(self, agent, sample_state_with_results):
        """Test analyzing results with failed tests."""
        result_state = await agent.analyze_results(sample_state_with_results)
        
        # Should have root causes
        assert len(result_state.root_causes) > 0
        assert result_state.current_agent == "analysis"
        
        # Root cause should be for the failed test
        root_cause = result_state.root_causes[0]
        assert root_cause.bug_id == "bug-123"
        assert 0.0 <= root_cause.confidence_score <= 1.0
    
    @pytest.mark.asyncio
    async def test_analyze_results_with_no_results(self, agent):
        """Test analyzing when no test results exist."""
        state = AgentState(
            workflow_id="workflow-123",
            repository_url="https://github.com/test/repo",
            repository_path="/tmp/test-repo",
            current_agent="execution",
            status="in_progress",
            test_results=[]
        )
        
        result_state = await agent.analyze_results(state)
        
        # Should return state with empty root causes
        assert len(result_state.root_causes) == 0
        assert result_state.current_agent == "analysis"
    
    @pytest.mark.asyncio
    async def test_analyze_results_skips_passed_tests(self, agent, sample_state_with_results):
        """Test that passed tests are skipped."""
        # Add a passed test
        passed_test = TestResult(
            test_id="test-passed",
            status="passed",
            stdout="Test passed",
            stderr="",
            exit_code=0,
            execution_time_ms=100,
            execution_platform="lambda"
        )
        sample_state_with_results.test_results.append(passed_test)
        
        result_state = await agent.analyze_results(sample_state_with_results)
        
        # Should only analyze failed test
        assert len(result_state.root_causes) == 1
    
    @pytest.mark.asyncio
    async def test_analyze_results_continues_on_error(self, agent, sample_state_with_results):
        """Test that analysis continues when one test fails."""
        # Add another failed test with a bug
        bug2 = BugReport(
            bug_id="bug-456",
            file_path="src/other.py",
            line_number=10,
            severity="medium",
            description="Another bug",
            code_snippet="code",
            confidence_score=0.7
        )
        test_case2 = TestCase(
            test_id="test-456",
            bug_id="bug-456",
            test_code="def test_other(): pass",
            test_framework="pytest",
            expected_outcome="Pass"
        )
        test_result2 = TestResult(
            test_id="test-456",
            status="failed",
            stdout="",
            stderr="Error",
            exit_code=1,
            execution_time_ms=100,
            execution_platform="lambda"
        )
        
        sample_state_with_results.bugs.append(bug2)
        sample_state_with_results.test_cases.append(test_case2)
        sample_state_with_results.test_results.append(test_result2)
        
        result_state = await agent.analyze_results(sample_state_with_results)
        
        # Should have analyzed both tests
        assert len(result_state.root_causes) == 2


class TestPlaceholderAnalysis:
    """Test placeholder analysis mode."""
    
    @pytest.mark.asyncio
    async def test_placeholder_analysis(self, agent, sample_bug, sample_test_result):
        """Test placeholder analysis returns valid root cause."""
        root_cause = await agent._analyze_failure(
            sample_test_result,
            sample_bug,
            "workflow-123"
        )
        
        assert isinstance(root_cause, RootCause)
        assert root_cause.bug_id == sample_bug.bug_id
        assert len(root_cause.cause_description) > 0
        assert 0.0 <= root_cause.confidence_score <= 1.0


class TestIntegration:
    """Integration tests for Analysis Agent."""
    
    @pytest.mark.asyncio
    async def test_full_analysis_workflow(self, agent):
        """Test complete analysis workflow from state to root causes."""
        # Create state with multiple bugs and test results
        bugs = [
            BugReport(
                bug_id="bug-1",
                file_path="src/auth.py",
                line_number=10,
                severity="high",
                description="Null pointer in authentication",
                code_snippet="user = None",
                confidence_score=0.9
            ),
            BugReport(
                bug_id="bug-2",
                file_path="src/auth.py",
                line_number=20,
                severity="high",
                description="Null pointer in authorization",
                code_snippet="role = None",
                confidence_score=0.85
            )
        ]
        
        test_cases = [
            TestCase(
                test_id="test-1",
                bug_id="bug-1",
                test_code="def test_auth(): pass",
                test_framework="pytest",
                expected_outcome="Pass"
            ),
            TestCase(
                test_id="test-2",
                bug_id="bug-2",
                test_code="def test_authz(): pass",
                test_framework="pytest",
                expected_outcome="Pass"
            )
        ]
        
        test_results = [
            TestResult(
                test_id="test-1",
                status="failed",
                stdout="",
                stderr="AttributeError: NoneType",
                exit_code=1,
                execution_time_ms=100,
                execution_platform="lambda"
            ),
            TestResult(
                test_id="test-2",
                status="failed",
                stdout="",
                stderr="AttributeError: NoneType",
                exit_code=1,
                execution_time_ms=100,
                execution_platform="lambda"
            )
        ]
        
        state = AgentState(
            workflow_id="workflow-123",
            repository_url="https://github.com/test/repo",
            repository_path="/tmp/test-repo",
            current_agent="execution",
            status="in_progress",
            bugs=bugs,
            test_cases=test_cases,
            test_results=test_results
        )
        
        result_state = await agent.analyze_results(state)
        
        # Verify both bugs were analyzed
        assert len(result_state.root_causes) == 2
        
        # Verify bugs were grouped (similar descriptions)
        root_causes = result_state.root_causes
        assert any(len(rc.related_bugs) > 0 for rc in root_causes)

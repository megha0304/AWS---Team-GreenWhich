"""
Unit tests for WorkflowOrchestrator.

Tests the orchestration of all five agents in the bug lifecycle workflow.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from cloudforge.orchestration.workflow_orchestrator import WorkflowOrchestrator
from cloudforge.models.state import (
    AgentState,
    BugReport,
    TestCase,
    TestResult,
    RootCause,
    FixSuggestion
)


@pytest.fixture
def mock_agents():
    """Create mock agents for testing."""
    return {
        "bug_detective": MagicMock(),
        "test_architect": MagicMock(),
        "execution_agent": MagicMock(),
        "analysis_agent": MagicMock(),
        "resolution_agent": MagicMock()
    }


@pytest.fixture
def mock_state_store():
    """Create mock state store."""
    store = MagicMock()
    store.save_state = AsyncMock()
    store.load_state = AsyncMock()
    return store


@pytest.fixture
def orchestrator(mock_agents, mock_state_store):
    """Create orchestrator with mock dependencies."""
    config = {
        "max_retries": 3,
        "retry_backoff_base": 2.0
    }
    
    return WorkflowOrchestrator(
        bug_detective=mock_agents["bug_detective"],
        test_architect=mock_agents["test_architect"],
        execution_agent=mock_agents["execution_agent"],
        analysis_agent=mock_agents["analysis_agent"],
        resolution_agent=mock_agents["resolution_agent"],
        state_store=mock_state_store,
        config=config
    )


@pytest.fixture
def sample_state():
    """Create a sample workflow state."""
    return AgentState(
        workflow_id=str(uuid4()),
        repository_url="https://github.com/test/repo",
        repository_path="/tmp/repo",
        current_agent="initializing",
        status="pending"
    )


@pytest.mark.asyncio
async def test_execute_workflow_complete_success(orchestrator, mock_agents, mock_state_store, sample_state):
    """Test complete workflow execution with all agents succeeding."""
    # Setup mock agent responses
    async def mock_detect_bugs(state):
        state.bugs = [
            BugReport(
                file_path="test.py",
                line_number=10,
                severity="high",
                description="Test bug description",
                code_snippet="def test(): pass",
                confidence_score=0.9
            )
        ]
        return state
    
    async def mock_generate_tests(state):
        state.test_cases = [
            TestCase(
                bug_id=state.bugs[0].bug_id,
                test_code="def test_bug(): assert True",
                test_framework="pytest",
                expected_outcome="Test should pass"
            )
        ]
        return state
    
    async def mock_execute_tests(state):
        state.test_results = [
            TestResult(
                test_id=state.test_cases[0].test_id,
                status="failed",
                stdout="Test output",
                stderr="",
                exit_code=1,
                execution_time_ms=100,
                execution_platform="lambda"
            )
        ]
        return state
    
    async def mock_analyze_results(state):
        state.root_causes = [
            RootCause(
                bug_id=state.bugs[0].bug_id,
                cause_description="Root cause description",
                confidence_score=0.85
            )
        ]
        return state
    
    async def mock_generate_fixes(state):
        state.fix_suggestions = [
            FixSuggestion(
                bug_id=state.bugs[0].bug_id,
                fix_description="Fix description",
                code_diff="--- a/test.py\n+++ b/test.py\n@@ -1 +1 @@\n-old\n+new",
                safety_score=0.9,
                impact_assessment="Low impact"
            )
        ]
        return state
    
    mock_agents["bug_detective"].detect_bugs = mock_detect_bugs
    mock_agents["test_architect"].generate_tests = mock_generate_tests
    mock_agents["execution_agent"].execute_tests = mock_execute_tests
    mock_agents["analysis_agent"].analyze_results = mock_analyze_results
    mock_agents["resolution_agent"].generate_fixes = mock_generate_fixes
    
    # Execute workflow
    result = await orchestrator.execute_workflow(
        repository_url="https://github.com/test/repo",
        repository_path="/tmp/repo"
    )
    
    # Verify workflow completed
    assert result.status == "completed"
    assert len(result.bugs) == 1
    assert len(result.test_cases) == 1
    assert len(result.test_results) == 1
    assert len(result.root_causes) == 1
    assert len(result.fix_suggestions) == 1
    
    # Verify state was saved multiple times (initial + after each agent)
    assert mock_state_store.save_state.call_count >= 6


@pytest.mark.asyncio
async def test_execute_workflow_with_workflow_id(orchestrator, mock_agents, mock_state_store):
    """Test workflow execution with provided workflow ID."""
    workflow_id = str(uuid4())
    
    # Setup minimal mock responses
    async def mock_detect_bugs(state):
        state.bugs = []
        return state
    
    mock_agents["bug_detective"].detect_bugs = mock_detect_bugs
    
    # Execute workflow
    result = await orchestrator.execute_workflow(
        repository_url="https://github.com/test/repo",
        repository_path="/tmp/repo",
        workflow_id=workflow_id
    )
    
    # Verify workflow ID was used
    assert result.workflow_id == workflow_id


@pytest.mark.asyncio
async def test_execute_workflow_stops_when_no_bugs_found(orchestrator, mock_agents, mock_state_store):
    """Test workflow stops after bug detection if no bugs found."""
    # Setup mock to return no bugs
    async def mock_detect_bugs(state):
        state.bugs = []
        return state
    
    mock_agents["bug_detective"].detect_bugs = mock_detect_bugs
    
    # Execute workflow
    result = await orchestrator.execute_workflow(
        repository_url="https://github.com/test/repo",
        repository_path="/tmp/repo"
    )
    
    # Verify workflow stopped early
    assert result.status == "completed"
    assert len(result.bugs) == 0
    assert len(result.test_cases) == 0
    assert len(result.test_results) == 0


@pytest.mark.asyncio
async def test_execute_workflow_stops_when_no_tests_generated(orchestrator, mock_agents, mock_state_store):
    """Test workflow stops after test generation if no tests generated."""
    # Setup mocks
    async def mock_detect_bugs(state):
        state.bugs = [
            BugReport(
                file_path="test.py",
                line_number=10,
                severity="high",
                description="Test bug description",
                code_snippet="def test(): pass",
                confidence_score=0.9
            )
        ]
        return state
    
    async def mock_generate_tests(state):
        state.test_cases = []
        return state
    
    mock_agents["bug_detective"].detect_bugs = mock_detect_bugs
    mock_agents["test_architect"].generate_tests = mock_generate_tests
    
    # Execute workflow
    result = await orchestrator.execute_workflow(
        repository_url="https://github.com/test/repo",
        repository_path="/tmp/repo"
    )
    
    # Verify workflow stopped after test generation
    assert result.status == "completed"
    assert len(result.bugs) == 1
    assert len(result.test_cases) == 0
    assert len(result.test_results) == 0


@pytest.mark.asyncio
async def test_execute_workflow_stops_when_no_test_results(orchestrator, mock_agents, mock_state_store):
    """Test workflow stops after test execution if no results."""
    # Setup mocks
    async def mock_detect_bugs(state):
        state.bugs = [
            BugReport(
                file_path="test.py",
                line_number=10,
                severity="high",
                description="Test bug description",
                code_snippet="def test(): pass",
                confidence_score=0.9
            )
        ]
        return state
    
    async def mock_generate_tests(state):
        state.test_cases = [
            TestCase(
                bug_id=state.bugs[0].bug_id,
                test_code="def test_bug(): assert True",
                test_framework="pytest",
                expected_outcome="Test should pass"
            )
        ]
        return state
    
    async def mock_execute_tests(state):
        state.test_results = []
        return state
    
    mock_agents["bug_detective"].detect_bugs = mock_detect_bugs
    mock_agents["test_architect"].generate_tests = mock_generate_tests
    mock_agents["execution_agent"].execute_tests = mock_execute_tests
    
    # Execute workflow
    result = await orchestrator.execute_workflow(
        repository_url="https://github.com/test/repo",
        repository_path="/tmp/repo"
    )
    
    # Verify workflow stopped after test execution
    assert result.status == "completed"
    assert len(result.bugs) == 1
    assert len(result.test_cases) == 1
    assert len(result.test_results) == 0


@pytest.mark.asyncio
async def test_execute_workflow_stops_when_no_root_causes(orchestrator, mock_agents, mock_state_store):
    """Test workflow stops after analysis if no root causes found."""
    # Setup mocks
    async def mock_detect_bugs(state):
        state.bugs = [
            BugReport(
                file_path="test.py",
                line_number=10,
                severity="high",
                description="Test bug description",
                code_snippet="def test(): pass",
                confidence_score=0.9
            )
        ]
        return state
    
    async def mock_generate_tests(state):
        state.test_cases = [
            TestCase(
                bug_id=state.bugs[0].bug_id,
                test_code="def test_bug(): assert True",
                test_framework="pytest",
                expected_outcome="Test should pass"
            )
        ]
        return state
    
    async def mock_execute_tests(state):
        state.test_results = [
            TestResult(
                test_id=state.test_cases[0].test_id,
                status="failed",
                stdout="Test output",
                stderr="",
                exit_code=1,
                execution_time_ms=100,
                execution_platform="lambda"
            )
        ]
        return state
    
    async def mock_analyze_results(state):
        state.root_causes = []
        return state
    
    mock_agents["bug_detective"].detect_bugs = mock_detect_bugs
    mock_agents["test_architect"].generate_tests = mock_generate_tests
    mock_agents["execution_agent"].execute_tests = mock_execute_tests
    mock_agents["analysis_agent"].analyze_results = mock_analyze_results
    
    # Execute workflow
    result = await orchestrator.execute_workflow(
        repository_url="https://github.com/test/repo",
        repository_path="/tmp/repo"
    )
    
    # Verify workflow stopped after analysis
    assert result.status == "completed"
    assert len(result.bugs) == 1
    assert len(result.test_cases) == 1
    assert len(result.test_results) == 1
    assert len(result.root_causes) == 0


@pytest.mark.asyncio
async def test_execute_workflow_handles_agent_failure(orchestrator, mock_agents, mock_state_store):
    """Test workflow handles agent failures gracefully."""
    # Setup mock to raise exception
    async def mock_detect_bugs(state):
        raise Exception("Agent failed")
    
    mock_agents["bug_detective"].detect_bugs = mock_detect_bugs
    
    # Execute workflow and expect exception
    with pytest.raises(Exception, match="Agent failed"):
        await orchestrator.execute_workflow(
            repository_url="https://github.com/test/repo",
            repository_path="/tmp/repo"
        )
    
    # Verify state was saved with error
    assert mock_state_store.save_state.call_count >= 2
    saved_state = mock_state_store.save_state.call_args[0][0]
    assert saved_state.status == "failed"
    assert len(saved_state.errors) > 0


@pytest.mark.asyncio
async def test_generate_summary_with_complete_workflow(orchestrator):
    """Test summary generation with complete workflow data."""
    state = AgentState(
        workflow_id=str(uuid4()),
        repository_url="https://github.com/test/repo",
        repository_path="/tmp/repo",
        current_agent="resolution",
        status="completed"
    )
    
    # Add sample data
    state.bugs = [
        BugReport(
            file_path="test.py",
            line_number=10,
            severity="high",
            description="Test bug 1 description",
            code_snippet="def test(): pass",
            confidence_score=0.9
        ),
        BugReport(
            file_path="test2.py",
            line_number=20,
            severity="medium",
            description="Test bug 2 description",
            code_snippet="def test2(): pass",
            confidence_score=0.8
        )
    ]
    
    state.test_cases = [
        TestCase(
            bug_id=state.bugs[0].bug_id,
            test_code="def test_bug(): assert True",
            test_framework="pytest",
            expected_outcome="Test should pass"
        )
    ]
    
    state.test_results = [
        TestResult(
            test_id=state.test_cases[0].test_id,
            status="failed",
            stdout="Test output",
            stderr="",
            exit_code=1,
            execution_time_ms=100,
            execution_platform="lambda"
        )
    ]
    
    state.root_causes = [
        RootCause(
            bug_id=state.bugs[0].bug_id,
            cause_description="Root cause description",
            confidence_score=0.85
        )
    ]
    
    state.fix_suggestions = [
        FixSuggestion(
            bug_id=state.bugs[0].bug_id,
            fix_description="Fix description",
            code_diff="--- a/test.py\n+++ b/test.py\n@@ -1 +1 @@\n-old\n+new",
            safety_score=0.9,
            impact_assessment="Low impact"
        )
    ]
    
    # Generate summary
    summary = orchestrator._generate_summary(state)
    
    # Verify summary contents
    assert summary["workflow_id"] == state.workflow_id
    assert summary["status"] == "completed"
    assert summary["bugs_found"] == 2
    assert summary["bugs_by_severity"]["high"] == 1
    assert summary["bugs_by_severity"]["medium"] == 1
    assert summary["tests_generated"] == 1
    assert summary["tests_executed"] == 1
    assert summary["test_results_by_status"]["failed"] == 1
    assert summary["root_causes_identified"] == 1
    assert summary["fixes_suggested"] == 1
    assert summary["errors"] == 0


@pytest.mark.asyncio
async def test_should_continue_returns_false_for_failed_status(orchestrator):
    """Test _should_continue returns False for failed workflows."""
    state = AgentState(
        workflow_id=str(uuid4()),
        repository_url="https://github.com/test/repo",
        repository_path="/tmp/repo",
        current_agent="bug_detective",
        status="failed"
    )
    
    assert orchestrator._should_continue(state) is False


@pytest.mark.asyncio
async def test_state_persistence_after_each_agent(orchestrator, mock_agents, mock_state_store):
    """Test state is persisted after each agent execution."""
    # Setup mock responses
    async def mock_detect_bugs(state):
        state.bugs = [
            BugReport(
                file_path="test.py",
                line_number=10,
                severity="high",
                description="Test bug description",
                code_snippet="def test(): pass",
                confidence_score=0.9
            )
        ]
        return state
    
    async def mock_generate_tests(state):
        state.test_cases = [
            TestCase(
                bug_id=state.bugs[0].bug_id,
                test_code="def test_bug(): assert True",
                test_framework="pytest",
                expected_outcome="Test should pass"
            )
        ]
        return state
    
    async def mock_execute_tests(state):
        state.test_results = [
            TestResult(
                test_id=state.test_cases[0].test_id,
                status="failed",
                stdout="Test output",
                stderr="",
                exit_code=1,
                execution_time_ms=100,
                execution_platform="lambda"
            )
        ]
        return state
    
    async def mock_analyze_results(state):
        state.root_causes = [
            RootCause(
                bug_id=state.bugs[0].bug_id,
                cause_description="Root cause description",
                confidence_score=0.85
            )
        ]
        return state
    
    async def mock_generate_fixes(state):
        state.fix_suggestions = [
            FixSuggestion(
                bug_id=state.bugs[0].bug_id,
                fix_description="Fix description",
                code_diff="--- a/test.py\n+++ b/test.py\n@@ -1 +1 @@\n-old\n+new",
                safety_score=0.9,
                impact_assessment="Low impact"
            )
        ]
        return state
    
    mock_agents["bug_detective"].detect_bugs = mock_detect_bugs
    mock_agents["test_architect"].generate_tests = mock_generate_tests
    mock_agents["execution_agent"].execute_tests = mock_execute_tests
    mock_agents["analysis_agent"].analyze_results = mock_analyze_results
    mock_agents["resolution_agent"].generate_fixes = mock_generate_fixes
    
    # Execute workflow
    await orchestrator.execute_workflow(
        repository_url="https://github.com/test/repo",
        repository_path="/tmp/repo"
    )
    
    # Verify state was saved after each agent
    # Initial save + 5 agents (before) + 5 agents (after) + final save = 12 saves
    # But we save before and after in the same call, so it's:
    # Initial + bug_detective (before+after) + test_architect (before+after) + 
    # execution (before+after) + analysis (before+after) + resolution (before+after) + final
    assert mock_state_store.save_state.call_count >= 6


@pytest.mark.asyncio
async def test_workflow_updates_current_agent(orchestrator, mock_agents, mock_state_store):
    """Test workflow updates current_agent field correctly."""
    # Setup mock responses
    async def mock_detect_bugs(state):
        assert state.current_agent == "bug_detective"
        state.bugs = []
        return state
    
    mock_agents["bug_detective"].detect_bugs = mock_detect_bugs
    
    # Execute workflow
    result = await orchestrator.execute_workflow(
        repository_url="https://github.com/test/repo",
        repository_path="/tmp/repo"
    )
    
    # Verify current_agent was updated
    assert result.current_agent == "bug_detective"

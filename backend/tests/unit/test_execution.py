"""Unit tests for Execution Agent."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import time

from cloudforge.agents.execution import ExecutionAgent
from cloudforge.models.state import AgentState, TestCase, TestResult, BugReport
from cloudforge.models.config import SystemConfig


@pytest.fixture
def mock_config():
    """Create a mock SystemConfig for testing."""
    config = Mock(spec=SystemConfig)
    config.lambda_max_runtime_seconds = 900  # 15 minutes
    config.lambda_max_memory_mb = 10240  # 10 GB
    config.max_retries = 3
    config.dynamodb_workflows_table = "test-workflows"
    config.environment = "test"
    return config


@pytest.fixture
def mock_lambda_client():
    """Create a mock Lambda client."""
    return Mock()


@pytest.fixture
def mock_ecs_client():
    """Create a mock ECS client."""
    return Mock()


@pytest.fixture
def mock_dynamodb_client():
    """Create a mock DynamoDB client."""
    return Mock()


@pytest.fixture
def agent(mock_lambda_client, mock_ecs_client, mock_dynamodb_client, mock_config):
    """Create an ExecutionAgent instance for testing."""
    return ExecutionAgent(
        mock_lambda_client,
        mock_ecs_client,
        mock_dynamodb_client,
        mock_config
    )


@pytest.fixture
def sample_test_case():
    """Create a sample test case for testing."""
    return TestCase(
        test_id="test-123",
        bug_id="bug-123",
        test_code="def test_example():\n    assert True",
        test_framework="pytest",
        expected_outcome="Test should pass"
    )


@pytest.fixture
def sample_state_with_tests(sample_test_case):
    """Create a sample AgentState with test cases."""
    return AgentState(
        workflow_id="workflow-123",
        repository_url="https://github.com/test/repo",
        repository_path="/tmp/test-repo",
        current_agent="test_architect",
        status="in_progress",
        test_cases=[sample_test_case]
    )


class TestExecutionAgentInitialization:
    """Test Execution Agent initialization."""
    
    def test_agent_initialization(
        self,
        mock_lambda_client,
        mock_ecs_client,
        mock_dynamodb_client,
        mock_config
    ):
        """Test that agent initializes correctly with configuration."""
        agent = ExecutionAgent(
            mock_lambda_client,
            mock_ecs_client,
            mock_dynamodb_client,
            mock_config
        )
        
        assert agent.lambda_client == mock_lambda_client
        assert agent.ecs_client == mock_ecs_client
        assert agent.dynamodb_client == mock_dynamodb_client
        assert agent.config == mock_config
        assert agent.lambda_max_runtime == 900
        assert agent.lambda_max_memory == 10240
        assert agent.max_retries == 3


class TestResourceEstimation:
    """Test resource estimation logic."""
    
    def test_estimate_resources_small_test(self, agent):
        """Test resource estimation for small test."""
        test_case = TestCase(
            test_id="test-1",
            bug_id="bug-1",
            test_code="def test_small():\n    assert True",
            test_framework="pytest",
            expected_outcome="Pass"
        )
        
        estimate = agent._estimate_resources(test_case)
        
        assert "runtime_seconds" in estimate
        assert "memory_mb" in estimate
        assert estimate["runtime_seconds"] > 0
        assert estimate["memory_mb"] > 0
    
    def test_estimate_resources_large_test(self, agent):
        """Test resource estimation for large test."""
        # Create test with >100 lines
        large_code = "\n".join([f"    line_{i} = {i}" for i in range(150)])
        test_case = TestCase(
            test_id="test-2",
            bug_id="bug-2",
            test_code=f"def test_large():\n{large_code}\n    assert True",
            test_framework="pytest",
            expected_outcome="Pass"
        )
        
        estimate = agent._estimate_resources(test_case)
        
        # Large tests should have higher estimates
        assert estimate["runtime_seconds"] >= 60
        assert estimate["memory_mb"] >= 1024
    
    def test_estimate_resources_python_test(self, agent):
        """Test that Python tests get appropriate memory allocation."""
        test_case = TestCase(
            test_id="test-3",
            bug_id="bug-3",
            test_code="def test_python():\n    assert True",
            test_framework="pytest",
            expected_outcome="Pass"
        )
        
        estimate = agent._estimate_resources(test_case)
        
        # Python tests should have at least 1GB memory
        assert estimate["memory_mb"] >= 1024
    
    def test_estimate_resources_with_sleep_keyword(self, agent):
        """Test that tests with sleep/wait keywords get longer runtime."""
        test_case = TestCase(
            test_id="test-4",
            bug_id="bug-4",
            test_code="def test_slow():\n    time.sleep(10)\n    assert True",
            test_framework="pytest",
            expected_outcome="Pass"
        )
        
        estimate = agent._estimate_resources(test_case)
        
        # Tests with sleep should have longer runtime
        assert estimate["runtime_seconds"] >= 90


class TestPlatformRouting:
    """Test platform routing logic."""
    
    def test_should_use_lambda_for_small_test(self, agent):
        """Test that small tests are routed to Lambda."""
        estimate = {
            "runtime_seconds": 60,
            "memory_mb": 1024
        }
        
        assert agent._should_use_lambda(estimate) is True
    
    def test_should_use_ecs_for_long_runtime(self, agent):
        """Test that long-running tests are routed to ECS."""
        estimate = {
            "runtime_seconds": 1000,  # > 900 seconds
            "memory_mb": 1024
        }
        
        assert agent._should_use_lambda(estimate) is False
    
    def test_should_use_ecs_for_high_memory(self, agent):
        """Test that high-memory tests are routed to ECS."""
        estimate = {
            "runtime_seconds": 60,
            "memory_mb": 12000  # > 10240 MB
        }
        
        assert agent._should_use_lambda(estimate) is False
    
    def test_should_use_ecs_for_both_limits_exceeded(self, agent):
        """Test that tests exceeding both limits are routed to ECS."""
        estimate = {
            "runtime_seconds": 1000,
            "memory_mb": 12000
        }
        
        assert agent._should_use_lambda(estimate) is False


class TestTestExecution:
    """Test test execution logic."""
    
    @pytest.mark.asyncio
    async def test_execute_tests_with_test_cases(self, agent, sample_state_with_tests):
        """Test execution of test cases."""
        # Mock the execution methods
        agent._execute_on_lambda = AsyncMock(return_value=TestResult(
            test_id="test-123",
            status="passed",
            stdout="Test passed",
            stderr="",
            exit_code=0,
            execution_time_ms=100,
            execution_platform="lambda"
        ))
        agent._persist_result = AsyncMock()
        
        result_state = await agent.execute_tests(sample_state_with_tests)
        
        # Verify test results were generated
        assert len(result_state.test_results) == 1
        assert result_state.test_results[0].test_id == "test-123"
        assert result_state.test_results[0].status == "passed"
        assert result_state.current_agent == "execution"
        
        # Verify persistence was called
        agent._persist_result.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_tests_with_no_tests(self, agent):
        """Test execution when no test cases are present."""
        state = AgentState(
            workflow_id="workflow-123",
            repository_url="https://github.com/test/repo",
            repository_path="/tmp/test-repo",
            current_agent="test_architect",
            status="in_progress",
            test_cases=[]
        )
        
        result_state = await agent.execute_tests(state)
        
        # Should return state with empty test_results
        assert len(result_state.test_results) == 0
        assert result_state.current_agent == "execution"
    
    @pytest.mark.asyncio
    async def test_execute_tests_continues_on_error(self, agent):
        """Test that execution continues when one test fails."""
        test1 = TestCase(
            test_id="test-1",
            bug_id="bug-1",
            test_code="def test_1(): assert True",
            test_framework="pytest",
            expected_outcome="Pass"
        )
        test2 = TestCase(
            test_id="test-2",
            bug_id="bug-2",
            test_code="def test_2(): assert True",
            test_framework="pytest",
            expected_outcome="Pass"
        )
        
        state = AgentState(
            workflow_id="workflow-123",
            repository_url="https://github.com/test/repo",
            repository_path="/tmp/test-repo",
            current_agent="test_architect",
            status="in_progress",
            test_cases=[test1, test2]
        )
        
        # Mock execution to fail for first test, succeed for second
        call_count = 0
        async def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Execution error")
            return TestResult(
                test_id="test-2",
                status="passed",
                stdout="Test passed",
                stderr="",
                exit_code=0,
                execution_time_ms=100,
                execution_platform="lambda"
            )
        
        agent._execute_on_lambda = mock_execute
        agent._persist_result = AsyncMock()
        
        result_state = await agent.execute_tests(state)
        
        # Should have 1 test result (second test succeeded)
        assert len(result_state.test_results) == 1
        assert result_state.test_results[0].test_id == "test-2"
        
        # Should have error logged
        assert len(result_state.errors) >= 1


class TestLambdaExecution:
    """Test Lambda execution logic."""
    
    @pytest.mark.asyncio
    async def test_execute_on_lambda(self, agent, sample_test_case):
        """Test Lambda execution with mocked invoke."""
        import json as _json
        mock_payload = Mock()
        mock_payload.read.return_value = _json.dumps({
            "exit_code": 0,
            "stdout": "Test passed",
            "stderr": ""
        }).encode()
        agent.lambda_client.invoke.return_value = {
            "StatusCode": 200,
            "Payload": mock_payload,
        }

        result = await agent._execute_on_lambda(sample_test_case, "workflow-123")

        assert isinstance(result, TestResult)
        assert result.test_id == sample_test_case.test_id
        assert result.execution_platform == "lambda"
        assert result.status == "passed"
        assert result.execution_time_ms >= 0
        assert result.exit_code == 0


class TestECSExecution:
    """Test ECS execution logic."""
    
    @pytest.mark.asyncio
    async def test_execute_on_ecs(self, agent, sample_test_case):
        """Test ECS execution with mocked run_task."""
        agent.ecs_client.run_task.return_value = {
            "tasks": [{"taskArn": "arn:aws:ecs:us-east-1:123:task/abc"}],
            "failures": [],
        }
        mock_waiter = Mock()
        mock_waiter.wait.return_value = None
        agent.ecs_client.get_waiter.return_value = mock_waiter
        agent.ecs_client.describe_tasks.return_value = {
            "tasks": [{
                "taskArn": "arn:aws:ecs:us-east-1:123:task/abc",
                "containers": [{"exitCode": 0, "reason": "Test passed on ECS"}],
            }]
        }
        agent.config.__dict__["ecs_subnet"] = "subnet-test"

        result = await agent._execute_on_ecs(sample_test_case, "workflow-123")

        assert isinstance(result, TestResult)
        assert result.test_id == sample_test_case.test_id
        assert result.execution_platform == "ecs"
        assert result.status == "passed"
        assert result.execution_time_ms >= 0
        assert result.exit_code == 0


class TestResultPersistence:
    """Test result persistence logic."""
    
    @pytest.mark.asyncio
    async def test_persist_result_placeholder(self, agent):
        """Test placeholder result persistence."""
        test_result = TestResult(
            test_id="test-123",
            status="passed",
            stdout="Test output",
            stderr="",
            exit_code=0,
            execution_time_ms=100,
            execution_platform="lambda"
        )
        
        # Should not raise an exception
        await agent._persist_result(test_result, "workflow-123")


class TestTestResultModel:
    """Test TestResult model validation."""
    
    def test_test_result_creation(self):
        """Test that TestResult can be created with valid data."""
        result = TestResult(
            test_id="test-123",
            status="passed",
            stdout="Test output",
            stderr="",
            exit_code=0,
            execution_time_ms=100,
            execution_platform="lambda"
        )
        
        assert result.test_id == "test-123"
        assert result.status == "passed"
        assert result.execution_platform == "lambda"
    
    def test_test_result_status_validation(self):
        """Test that TestResult validates status consistency."""
        # This should raise validation error: passed status with non-zero exit code
        with pytest.raises(Exception):  # Pydantic ValidationError
            TestResult(
                test_id="test-123",
                status="passed",
                stdout="",
                stderr="",
                exit_code=1,  # Non-zero exit code
                execution_time_ms=100,
                execution_platform="lambda"
            )


class TestIntegration:
    """Integration tests for Execution Agent."""
    
    @pytest.mark.asyncio
    async def test_full_execution_workflow(self, agent):
        """Test complete execution workflow from state to results."""
        # Create state with multiple test cases
        test1 = TestCase(
            test_id="test-1",
            bug_id="bug-1",
            test_code="def test_small(): assert True",  # Small test -> Lambda
            test_framework="pytest",
            expected_outcome="Pass"
        )
        
        # Large test that should go to ECS
        large_code = "\n".join([f"    line_{i} = {i}" for i in range(150)])
        test2 = TestCase(
            test_id="test-2",
            bug_id="bug-2",
            test_code=f"def test_large():\n{large_code}\n    assert True",
            test_framework="pytest",
            expected_outcome="Pass"
        )
        
        state = AgentState(
            workflow_id="workflow-123",
            repository_url="https://github.com/test/repo",
            repository_path="/tmp/test-repo",
            current_agent="test_architect",
            status="in_progress",
            test_cases=[test1, test2]
        )
        
        # Mock Lambda and ECS execution
        agent._execute_on_lambda = AsyncMock(return_value=TestResult(
            test_id="test-1",
            status="passed",
            stdout="Test passed",
            stderr="",
            exit_code=0,
            execution_time_ms=100,
            execution_platform="lambda"
        ))
        agent._execute_on_ecs = AsyncMock(return_value=TestResult(
            test_id="test-2",
            status="passed",
            stdout="Test passed on ECS",
            stderr="",
            exit_code=0,
            execution_time_ms=200,
            execution_platform="ecs"
        ))
        agent._persist_result = AsyncMock()
        
        result_state = await agent.execute_tests(state)
        
        # Verify both tests were executed
        assert len(result_state.test_results) == 2
        
        # Verify first test used Lambda (small test)
        assert result_state.test_results[0].execution_platform == "lambda"
        
        # Verify second test used ECS (large test)
        assert result_state.test_results[1].execution_platform == "ecs"
        
        # Verify persistence was called for both
        assert agent._persist_result.call_count == 2

"""Unit tests for Test Architect Agent."""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from cloudforge.agents.test_architect import TestArchitectAgent
from cloudforge.models.state import AgentState, BugReport, TestCase
from cloudforge.models.config import SystemConfig


@pytest.fixture
def mock_config():
    """Create a mock SystemConfig for testing."""
    config = Mock(spec=SystemConfig)
    config.q_developer_endpoint = "https://test-endpoint.amazonaws.com"
    config.q_developer_api_key = "test-api-key"
    config.max_retries = 3
    config.bedrock_model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
    return config


@pytest.fixture
def mock_q_developer_client():
    """Create a mock Q Developer client."""
    return Mock()


@pytest.fixture
def agent(mock_q_developer_client, mock_config):
    """Create a TestArchitectAgent instance for testing."""
    return TestArchitectAgent(mock_q_developer_client, mock_config)


@pytest.fixture
def sample_bug():
    """Create a sample bug report for testing."""
    return BugReport(
        bug_id="bug-123",
        file_path="src/utils.py",
        line_number=42,
        severity="high",
        description="Null pointer dereference in utility function",
        code_snippet="def process(data):\n    return data.value  # data can be None",
        confidence_score=0.85
    )


@pytest.fixture
def sample_state_with_bugs(sample_bug):
    """Create a sample AgentState with bugs."""
    return AgentState(
        workflow_id="workflow-123",
        repository_url="https://github.com/test/repo",
        repository_path="/tmp/test-repo",
        current_agent="bug_detective",
        status="in_progress",
        bugs=[sample_bug]
    )


class TestTestArchitectAgentInitialization:
    """Test Test Architect Agent initialization."""
    
    def test_agent_initialization(self, mock_q_developer_client, mock_config):
        """Test that agent initializes correctly with configuration."""
        agent = TestArchitectAgent(mock_q_developer_client, mock_config)
        
        assert agent.q_developer_client == mock_q_developer_client
        assert agent.config == mock_config
        assert agent.q_developer_endpoint == "https://test-endpoint.amazonaws.com"
        assert agent.q_developer_api_key == "test-api-key"
        assert agent.max_retries == 3
        assert agent.model_id == "anthropic.claude-3-sonnet-20240229-v1:0"


class TestFrameworkDetection:
    """Test test framework detection logic."""
    
    def test_detect_pytest_from_pytest_ini(self, agent):
        """Test detection of pytest from pytest.ini file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            (repo_path / "pytest.ini").write_text("[pytest]\ntestpaths = tests")
            
            framework = agent._detect_test_framework(str(repo_path))
            assert framework == "pytest"
    
    def test_detect_pytest_from_pyproject_toml(self, agent):
        """Test detection of pytest from pyproject.toml."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            (repo_path / "pyproject.toml").write_text("[tool.pytest.ini_options]\ntestpaths = ['tests']")
            
            framework = agent._detect_test_framework(str(repo_path))
            assert framework == "pytest"
    
    def test_detect_unittest_from_test_files(self, agent):
        """Test detection of unittest from test file patterns."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            (repo_path / "test_utils.py").write_text("import unittest")
            
            framework = agent._detect_test_framework(str(repo_path))
            assert framework == "unittest"
    
    def test_detect_jest_from_package_json(self, agent):
        """Test detection of jest from package.json."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            (repo_path / "package.json").write_text('{"devDependencies": {"jest": "^29.0.0"}}')
            
            framework = agent._detect_test_framework(str(repo_path))
            assert framework == "jest"
    
    def test_detect_mocha_from_package_json(self, agent):
        """Test detection of mocha from package.json."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            (repo_path / "package.json").write_text('{"devDependencies": {"mocha": "^10.0.0"}}')
            
            framework = agent._detect_test_framework(str(repo_path))
            assert framework == "mocha"
    
    def test_detect_junit_from_pom_xml(self, agent):
        """Test detection of JUnit from pom.xml."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            (repo_path / "pom.xml").write_text('<dependency><artifactId>junit</artifactId></dependency>')
            
            framework = agent._detect_test_framework(str(repo_path))
            assert framework == "junit"
    
    def test_detect_go_test_from_test_files(self, agent):
        """Test detection of Go test framework from test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            (repo_path / "utils_test.go").write_text("package main")
            
            framework = agent._detect_test_framework(str(repo_path))
            assert framework == "go-test"
    
    def test_detect_rust_test_from_cargo_toml(self, agent):
        """Test detection of Rust test framework from Cargo.toml."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            (repo_path / "Cargo.toml").write_text('[package]\nname = "test"')
            
            framework = agent._detect_test_framework(str(repo_path))
            assert framework == "rust-test"
    
    def test_default_to_pytest_for_python_files(self, agent):
        """Test default to pytest when Python files exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            (repo_path / "utils.py").write_text("def hello(): pass")
            
            framework = agent._detect_test_framework(str(repo_path))
            assert framework == "pytest"
    
    def test_default_to_jest_for_js_files(self, agent):
        """Test default to jest when JavaScript files exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            (repo_path / "utils.js").write_text("function hello() {}")
            
            framework = agent._detect_test_framework(str(repo_path))
            assert framework == "jest"
    
    def test_unknown_framework_for_empty_repo(self, agent):
        """Test unknown framework for empty repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            framework = agent._detect_test_framework(temp_dir)
            assert framework == "unknown"


class TestRepositoryContext:
    """Test repository context extraction."""
    
    def test_get_repository_context_with_requirements(self, agent):
        """Test context extraction with requirements.txt."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            (repo_path / "requirements.txt").write_text("pytest==7.0.0\nrequests==2.28.0")
            (repo_path / "src").mkdir()
            (repo_path / "tests").mkdir()
            
            context = agent._get_repository_context(str(repo_path))
            
            assert "Repository Structure:" in context
            assert "Python Dependencies:" in context
            assert "pytest" in context or "requests" in context
    
    def test_get_repository_context_with_package_json(self, agent):
        """Test context extraction with package.json."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            (repo_path / "package.json").write_text('{"name": "test-project"}')
            (repo_path / "src").mkdir()
            
            context = agent._get_repository_context(str(repo_path))
            
            assert "Repository Structure:" in context
            assert "JavaScript/TypeScript Project" in context


class TestTestGeneration:
    """Test test case generation."""
    
    @pytest.mark.asyncio
    async def test_generate_tests_with_bugs(self, agent, sample_state_with_bugs):
        """Test test generation for state with bugs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Update state with valid repository path
            sample_state_with_bugs.repository_path = temp_dir
            (Path(temp_dir) / "test_file.py").write_text("# test")
            
            # Mock the Bedrock call
            agent._call_bedrock_for_test = AsyncMock(
                return_value=("test_code", "expected_outcome")
            )
            
            result_state = await agent.generate_tests(sample_state_with_bugs)
            
            # Verify test cases were generated
            assert len(result_state.test_cases) == 1
            assert result_state.test_cases[0].bug_id == "bug-123"
            assert result_state.test_cases[0].test_code == "test_code"
            assert result_state.test_cases[0].expected_outcome == "expected_outcome"
            assert result_state.current_agent == "test_architect"
    
    @pytest.mark.asyncio
    async def test_generate_tests_with_no_bugs(self, agent):
        """Test test generation when no bugs are present."""
        state = AgentState(
            workflow_id="workflow-123",
            repository_url="https://github.com/test/repo",
            repository_path="/tmp/test-repo",
            current_agent="bug_detective",
            status="in_progress",
            bugs=[]
        )
        
        result_state = await agent.generate_tests(state)
        
        # Should return state with empty test_cases
        assert len(result_state.test_cases) == 0
        assert result_state.current_agent == "test_architect"
    
    @pytest.mark.asyncio
    async def test_generate_tests_without_repository_path(self, agent, sample_bug):
        """Test that missing repository_path raises ValueError."""
        # Create state with a placeholder path first
        state = AgentState(
            workflow_id="workflow-123",
            repository_url="https://github.com/test/repo",
            repository_path="/nonexistent/path",
            current_agent="bug_detective",
            status="in_progress",
            bugs=[sample_bug]
        )
        
        # Then set it to empty to bypass Pydantic validation
        state.repository_path = ""
        
        with pytest.raises(ValueError, match="repository_path is required"):
            await agent.generate_tests(state)
    
    @pytest.mark.asyncio
    async def test_generate_tests_continues_on_error(self, agent, sample_bug):
        """Test that test generation continues when one bug fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            bug2 = BugReport(
                bug_id="bug-456",
                file_path="src/other.py",
                line_number=10,
                severity="medium",
                description="Another bug",
                code_snippet="code",
                confidence_score=0.7
            )
            
            state = AgentState(
                workflow_id="workflow-123",
                repository_url="https://github.com/test/repo",
                repository_path=temp_dir,
                current_agent="bug_detective",
                status="in_progress",
                bugs=[sample_bug, bug2]
            )
            
            (Path(temp_dir) / "test.py").write_text("# test")
            
            # Mock Q Developer to always fail for first bug (even with retries)
            call_count = 0
            async def mock_call(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                # Fail for first bug (all retry attempts)
                if args[0].bug_id == "bug-123":
                    raise Exception("API error")
                # Succeed for second bug
                return ("test_code", "expected_outcome")
            
            agent._call_bedrock_for_test = mock_call
            
            result_state = await agent.generate_tests(state)
            
            # Should have 1 test case (second bug succeeded, first failed)
            assert len(result_state.test_cases) == 1
            assert result_state.test_cases[0].bug_id == "bug-456"
            
            # Should have error logged for first bug
            assert len(result_state.errors) >= 1
            assert any("test_generation_failed" in err["error_type"] for err in result_state.errors)


class TestPlaceholderTestGeneration:
    """Test Bedrock-based test generation logic."""
    
    @pytest.mark.asyncio
    async def test_bedrock_pytest_generation(self, agent, sample_bug):
        """Test Bedrock generates pytest code."""
        mock_response_body = json.dumps({
            "content": [{"text": json.dumps({
                "test_code": "import pytest\n\ndef test_null_check():\n    assert obj is not None",
                "expected_outcome": sample_bug.description[:100]
            })}]
        }).encode()
        mock_stream = Mock()
        mock_stream.read.return_value = mock_response_body
        agent.q_developer_client.invoke_model.return_value = {"body": mock_stream}
        
        test_code, expected_outcome = await agent._call_bedrock_for_test(
            sample_bug,
            "pytest",
            "repo context"
        )
        
        assert "import pytest" in test_code
        assert "def test_" in test_code
        assert "assert" in test_code
    
    @pytest.mark.asyncio
    async def test_bedrock_unittest_generation(self, agent, sample_bug):
        """Test Bedrock generates unittest code."""
        mock_response_body = json.dumps({
            "content": [{"text": json.dumps({
                "test_code": "import unittest\n\nclass TestUtils(unittest.TestCase):\n    def test_null_check(self):\n        self.assertIsNotNone(obj)",
                "expected_outcome": sample_bug.description[:100]
            })}]
        }).encode()
        mock_stream = Mock()
        mock_stream.read.return_value = mock_response_body
        agent.q_developer_client.invoke_model.return_value = {"body": mock_stream}
        
        test_code, expected_outcome = await agent._call_bedrock_for_test(
            sample_bug,
            "unittest",
            "repo context"
        )
        
        assert "import unittest" in test_code
        assert "class Test" in test_code
        assert "def test_" in test_code
    
    @pytest.mark.asyncio
    async def test_bedrock_jest_generation(self, agent, sample_bug):
        """Test Bedrock generates jest code."""
        mock_response_body = json.dumps({
            "content": [{"text": json.dumps({
                "test_code": "describe('utils', () => {\n  test('null check', () => {\n    expect(obj).not.toBeNull();\n  });\n});",
                "expected_outcome": sample_bug.description[:100]
            })}]
        }).encode()
        mock_stream = Mock()
        mock_stream.read.return_value = mock_response_body
        agent.q_developer_client.invoke_model.return_value = {"body": mock_stream}
        
        test_code, expected_outcome = await agent._call_bedrock_for_test(
            sample_bug,
            "jest",
            "repo context"
        )
        
        assert "describe(" in test_code
        assert "test(" in test_code
        assert "expect(" in test_code


class TestTestCaseCreation:
    """Test TestCase model creation."""
    
    @pytest.mark.asyncio
    async def test_generate_test_for_bug_creates_valid_test_case(self, agent, sample_bug):
        """Test that _generate_test_for_bug creates a valid TestCase."""
        agent._call_bedrock_for_test = AsyncMock(
            return_value=("test_code_here", "validates the bug")
        )
        
        test_case = await agent._generate_test_for_bug(
            sample_bug,
            "pytest",
            "repo context"
        )
        
        assert isinstance(test_case, TestCase)
        assert test_case.bug_id == sample_bug.bug_id
        assert test_case.test_code == "test_code_here"
        assert test_case.test_framework == "pytest"
        assert test_case.expected_outcome == "validates the bug"
        assert test_case.test_id  # Should have a generated ID

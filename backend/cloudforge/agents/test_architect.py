"""
Test Architect Agent - Generates executable test cases for detected bugs using Amazon Q Developer.

This agent uses Amazon Q Developer to generate test code that validates the presence
of bugs and verifies fixes. It detects the testing framework used in the repository
and generates appropriate test code.

REQUIRED AMAZON Q DEVELOPER SETUP:
===================================
1. Amazon Q Developer Access:
   - Sign up for Amazon Q Developer: https://aws.amazon.com/q/developer/
   - Obtain API credentials and endpoint
   - Note: Q Developer API requires separate enrollment from AWS Bedrock

2. Configuration (set in environment or SystemConfig):
   - Q_DEVELOPER_ENDPOINT: API endpoint URL
   - Q_DEVELOPER_API_KEY: Your API key
   - See: backend/REQUIRED_INPUTS.md for setup instructions

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6
"""

import logging
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from uuid import uuid4

from cloudforge.models.state import AgentState, BugReport, TestCase
from cloudforge.models.config import SystemConfig
from cloudforge.utils.retry import retry_with_backoff

logger = logging.getLogger(__name__)


class TestArchitectAgent:
    """
    Agent responsible for generating executable test cases for detected bugs.
    
    Uses Amazon Q Developer to generate test code that validates bugs and verifies fixes.
    Detects the testing framework used in the repository and generates appropriate tests.
    
    Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6
    """
    
    def __init__(self, q_developer_client: Any, config: SystemConfig):
        """
        Initialize Test Architect Agent.
        
        Args:
            q_developer_client: Amazon Q Developer API client
                               (Mock or real client depending on configuration)
            config: System configuration with Q Developer and agent settings
        
        Example:
            >>> config = SystemConfig.load_config()
            >>> q_client = Mock()  # Replace with real Q Developer client
            >>> agent = TestArchitectAgent(q_client, config)
        """
        self.q_developer_client = q_developer_client
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.q_developer_endpoint = config.q_developer_endpoint
        self.q_developer_api_key = config.q_developer_api_key
        self.max_retries = config.max_retries
        
        self.logger.info(
            "Initialized TestArchitectAgent",
            extra={
                "endpoint": self.q_developer_endpoint,
                "max_retries": self.max_retries
            }
        )
    
    async def generate_tests(self, state: AgentState) -> AgentState:
        """
        Generate test cases for all detected bugs.
        
        This is the main entry point for the Test Architect Agent. It generates
        executable test cases for each bug detected by the Bug Detective Agent.
        
        Args:
            state: Current workflow state with bugs list populated
        
        Returns:
            Updated state with test_cases list populated
        
        Raises:
            ValueError: If bugs list is empty or repository_path is not set
            Exception: If test generation fails after retries
        
        Requirements: 2.1, 2.2, 2.3, 2.4
        """
        self.logger.info(
            f"Starting test generation for workflow {state.workflow_id}",
            extra={
                "workflow_id": state.workflow_id,
                "bugs_count": len(state.bugs)
            }
        )
        
        # Validate state
        if not state.bugs:
            self.logger.warning(
                f"No bugs found for workflow {state.workflow_id}, skipping test generation",
                extra={"workflow_id": state.workflow_id}
            )
            state.current_agent = "test_architect"
            return state
        
        if not state.repository_path:
            error_msg = "repository_path is required for test generation"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Detect test framework
        test_framework = self._detect_test_framework(state.repository_path)
        self.logger.info(
            f"Detected test framework: {test_framework}",
            extra={
                "workflow_id": state.workflow_id,
                "framework": test_framework
            }
        )
        
        # Get repository context for test generation
        repo_context = self._get_repository_context(state.repository_path)
        
        # Generate test cases for each bug
        test_cases = []
        for bug in state.bugs:
            try:
                test_case = await self._generate_test_for_bug(
                    bug,
                    test_framework,
                    repo_context
                )
                test_cases.append(test_case)
                
                self.logger.info(
                    f"Generated test case for bug {bug.bug_id}",
                    extra={
                        "workflow_id": state.workflow_id,
                        "bug_id": bug.bug_id,
                        "test_id": test_case.test_id
                    }
                )
            except Exception as e:
                # Requirement 2.6: Log error and continue processing
                self.logger.error(
                    f"Failed to generate test for bug {bug.bug_id}: {e}",
                    extra={
                        "workflow_id": state.workflow_id,
                        "bug_id": bug.bug_id,
                        "error": str(e)
                    }
                )
                # Add error to state but continue with other bugs
                state.add_error(
                    error_type="test_generation_failed",
                    error_message=f"Failed to generate test for bug {bug.bug_id}: {e}",
                    agent_name="test_architect"
                )
                continue
        
        # Update state with generated test cases
        state.test_cases = test_cases
        state.current_agent = "test_architect"
        
        self.logger.info(
            f"Test generation complete: generated {len(test_cases)} test cases",
            extra={
                "workflow_id": state.workflow_id,
                "tests_generated": len(test_cases),
                "bugs_processed": len(state.bugs)
            }
        )
        
        return state
    
    def _detect_test_framework(self, repository_path: str) -> str:
        """
        Detect the testing framework used in the repository.
        
        Examines the repository structure and configuration files to determine
        which testing framework is being used.
        
        Args:
            repository_path: Path to repository root
        
        Returns:
            Name of detected test framework (pytest, unittest, jest, etc.)
        
        Requirements: 2.4
        """
        repo_path = Path(repository_path)
        
        # Check for Python test frameworks
        if (repo_path / "pytest.ini").exists():
            return "pytest"
        
        if (repo_path / "pyproject.toml").exists():
            pyproject = repo_path / "pyproject.toml"
            content = pyproject.read_text(encoding='utf-8')
            if '[tool.pytest' in content or 'pytest' in content:
                return "pytest"
        
        # Check for unittest (Python standard library)
        if any(repo_path.rglob('test_*.py')) or any(repo_path.rglob('*_test.py')):
            # If pytest not detected but test files exist, assume unittest
            return "unittest"
        
        # Check for JavaScript/TypeScript test frameworks
        package_json = repo_path / "package.json"
        if package_json.exists():
            content = package_json.read_text(encoding='utf-8')
            if 'jest' in content:
                return "jest"
            elif 'mocha' in content:
                return "mocha"
            elif 'vitest' in content:
                return "vitest"
        
        # Check for Java test frameworks
        pom_xml = repo_path / "pom.xml"
        if pom_xml.exists():
            content = pom_xml.read_text(encoding='utf-8')
            if 'junit' in content.lower():
                return "junit"
        
        build_gradle = repo_path / "build.gradle"
        if build_gradle.exists():
            content = build_gradle.read_text(encoding='utf-8')
            if 'junit' in content.lower():
                return "junit"
        
        # Check for Go test framework
        if any(repo_path.rglob('*_test.go')):
            return "go-test"
        
        # Check for Rust test framework
        if (repo_path / "Cargo.toml").exists():
            return "rust-test"
        
        # Default to pytest for Python projects, jest for JS projects
        if any(repo_path.rglob('*.py')):
            return "pytest"
        elif any(repo_path.rglob('*.js')) or any(repo_path.rglob('*.ts')):
            return "jest"
        
        # Fallback
        return "unknown"
    
    def _get_repository_context(self, repository_path: str) -> str:
        """
        Get relevant context from the repository for test generation.
        
        Extracts information about the repository structure, dependencies,
        and existing test patterns to help generate appropriate tests.
        
        Args:
            repository_path: Path to repository root
        
        Returns:
            String containing repository context information
        """
        repo_path = Path(repository_path)
        context_parts = []
        
        # Add repository structure overview
        context_parts.append("Repository Structure:")
        source_dirs = []
        for item in repo_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                source_dirs.append(item.name)
        context_parts.append(f"Directories: {', '.join(source_dirs[:10])}")
        
        # Add dependency information
        if (repo_path / "requirements.txt").exists():
            context_parts.append("\nPython Dependencies:")
            deps = (repo_path / "requirements.txt").read_text(encoding='utf-8')
            context_parts.append(deps[:500])  # Limit size
        
        if (repo_path / "package.json").exists():
            context_parts.append("\nJavaScript/TypeScript Project")
        
        return '\n'.join(context_parts)
    
    async def _generate_test_for_bug(
        self,
        bug: BugReport,
        test_framework: str,
        repo_context: str
    ) -> TestCase:
        """
        Generate a single test case for a bug using Q Developer.
        
        This method calls Amazon Q Developer API to generate test code that
        validates the bug and can verify fixes.
        
        Args:
            bug: Bug report to generate test for
            test_framework: Testing framework to use
            repo_context: Repository context information
        
        Returns:
            Generated test case
        
        Requirements: 2.2, 2.3, 2.4
        """
        # Call Q Developer with retry logic
        test_code, expected_outcome = await retry_with_backoff(
            self._call_q_developer_for_test,
            bug,
            test_framework,
            repo_context,
            max_retries=self.max_retries,
            base_delay=2.0
        )
        
        # Create test case
        test_case = TestCase(
            test_id=str(uuid4()),
            bug_id=bug.bug_id,
            test_code=test_code,
            test_framework=test_framework,
            expected_outcome=expected_outcome
        )
        
        return test_case
    
    async def _call_q_developer_for_test(
        self,
        bug: BugReport,
        test_framework: str,
        repo_context: str
    ) -> tuple[str, str]:
        """
        Call Amazon Q Developer API to generate test code.
        
        ⚠️  USER ACTION REQUIRED ⚠️
        ================================
        This method contains placeholder logic. To use real Amazon Q Developer:
        
        1. Sign up for Amazon Q Developer access
        2. Obtain API credentials and endpoint
        3. Set Q_DEVELOPER_ENDPOINT and Q_DEVELOPER_API_KEY environment variables
        4. Uncomment the Q Developer API call code below
        5. Remove or modify the placeholder return statement
        
        The placeholder currently returns mock test code for testing.
        
        Args:
            bug: Bug report to generate test for
            test_framework: Testing framework to use
            repo_context: Repository context information
        
        Returns:
            Tuple of (test_code, expected_outcome)
        
        Requirements: 2.2, 2.3
        """
        # Construct prompt for Q Developer
        prompt = f"""Generate a test case for the following bug using {test_framework}.

Bug Details:
- File: {bug.file_path}
- Line: {bug.line_number}
- Severity: {bug.severity}
- Description: {bug.description}
- Code Snippet:
{bug.code_snippet}

Repository Context:
{repo_context[:500]}

Requirements:
1. Generate test code using {test_framework} framework
2. Include both positive test (expected behavior) and negative test (error handling)
3. Include necessary imports and setup/teardown code
4. Test should validate the bug exists and can verify when it's fixed
5. Use descriptive test names and comments

Format your response as:
TEST_CODE:
<test code here>

EXPECTED_OUTCOME:
<description of what the test validates>
"""

        # ============================================================================
        # PLACEHOLDER: Replace this section with actual Q Developer API call
        # ============================================================================
        # TODO: Uncomment and configure the following code when ready to use Q Developer
        
        """
        import json
        import requests
        
        # Prepare request for Q Developer API
        headers = {
            "Authorization": f"Bearer {self.q_developer_api_key}",
            "Content-Type": "application/json"
        }
        
        request_body = {
            "prompt": prompt,
            "max_tokens": 2048,
            "temperature": 0.2,  # Low temperature for consistent code generation
            "language": test_framework
        }
        
        # Call Q Developer API
        response = requests.post(
            f"{self.q_developer_endpoint}/generate",
            headers=headers,
            json=request_body,
            timeout=30
        )
        
        response.raise_for_status()
        result = response.json()
        
        # Parse response
        generated_text = result.get('generated_code', '')
        
        # Extract test code and expected outcome
        if 'TEST_CODE:' in generated_text and 'EXPECTED_OUTCOME:' in generated_text:
            parts = generated_text.split('EXPECTED_OUTCOME:')
            test_code = parts[0].replace('TEST_CODE:', '').strip()
            expected_outcome = parts[1].strip()
        else:
            test_code = generated_text
            expected_outcome = f"Validates bug in {bug.file_path} at line {bug.line_number}"
        """
        
        # PLACEHOLDER: Mock response for testing
        # Remove this when implementing real Q Developer integration
        self.logger.warning(
            f"Using placeholder test generation for bug {bug.bug_id}. "
            "Configure Amazon Q Developer credentials to use real generation."
        )
        
        # Generate placeholder test code based on framework
        if test_framework == "pytest":
            test_code = f"""import pytest

def test_{bug.file_path.replace('/', '_').replace('.', '_')}_line_{bug.line_number}():
    \"\"\"
    Test for bug: {bug.description[:100]}
    
    This test validates the bug exists and can verify when it's fixed.
    \"\"\"
    # TODO: Implement actual test logic
    # Positive test: Verify expected behavior
    assert True, "Placeholder test - implement actual validation"
    
    # Negative test: Verify error handling
    with pytest.raises(Exception):
        pass  # TODO: Test error condition
"""
        elif test_framework == "unittest":
            test_code = f"""import unittest

class Test{bug.file_path.replace('/', '_').replace('.', '_')}(unittest.TestCase):
    def test_line_{bug.line_number}(self):
        \"\"\"
        Test for bug: {bug.description[:100]}
        \"\"\"
        # TODO: Implement actual test logic
        self.assertTrue(True, "Placeholder test")
"""
        elif test_framework == "jest":
            test_code = f"""describe('{bug.file_path}', () => {{
    test('bug at line {bug.line_number}', () => {{
        // Test for: {bug.description[:100]}
        // TODO: Implement actual test logic
        expect(true).toBe(true);
    }});
}});
"""
        else:
            test_code = f"""# Test for bug in {bug.file_path} at line {bug.line_number}
# Framework: {test_framework}
# Description: {bug.description[:100]}
# TODO: Implement test using {test_framework}
"""
        
        expected_outcome = f"Validates bug: {bug.description[:200]}"
        
        return test_code, expected_outcome

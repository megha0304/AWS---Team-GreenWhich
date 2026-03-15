"""
Test Architect Agent - Generates executable test cases for detected bugs.

Uses AWS Bedrock (Claude) to generate test code that validates the presence
of bugs and verifies fixes. Detects the testing framework used in the repository.

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6
"""

import json
import logging
import re
from pathlib import Path
from typing import List, Any
from uuid import uuid4

from cloudforge.models.state import AgentState, BugReport, TestCase
from cloudforge.models.config import SystemConfig
from cloudforge.utils.retry import retry_with_backoff

logger = logging.getLogger(__name__)


class TestArchitectAgent:
    """
    Generates executable test cases for detected bugs via AWS Bedrock (Claude).

    Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6
    """

    def __init__(self, q_developer_client: Any, config: SystemConfig):
        """
        Initialize Test Architect Agent.

        Args:
            q_developer_client: Bedrock Runtime client (used for Claude-based test generation).
                               Named q_developer_client for backward compatibility.
            config: System configuration
        """
        self.q_developer_client = q_developer_client  # Actually a bedrock-runtime client
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.q_developer_endpoint = config.q_developer_endpoint
        self.q_developer_api_key = config.q_developer_api_key
        self.model_id = config.bedrock_model_id
        self.max_retries = config.max_retries

    async def generate_tests(self, state: AgentState) -> AgentState:
        """Generate test cases for all detected bugs. Main entry point."""
        self.logger.info(
            f"Starting test generation for workflow {state.workflow_id}",
            extra={"bugs_count": len(state.bugs)},
        )

        if not state.bugs:
            self.logger.warning("No bugs found, skipping test generation")
            state.current_agent = "test_architect"
            return state

        if not state.repository_path:
            raise ValueError("repository_path is required for test generation")

        test_framework = self._detect_test_framework(state.repository_path)
        repo_context = self._get_repository_context(state.repository_path)

        test_cases = []
        for bug in state.bugs:
            try:
                test_case = await self._generate_test_for_bug(bug, test_framework, repo_context)
                test_cases.append(test_case)
            except Exception as e:
                self.logger.error(f"Failed to generate test for bug {bug.bug_id}: {e}")
                state.add_error("test_generation_failed", str(e), "test_architect")
                continue

        state.test_cases = test_cases
        state.current_agent = "test_architect"
        self.logger.info(f"Generated {len(test_cases)} test cases for {len(state.bugs)} bugs")
        return state

    # ------------------------------------------------------------------
    # Framework detection
    # ------------------------------------------------------------------

    def _detect_test_framework(self, repository_path: str) -> str:
        repo = Path(repository_path)

        if (repo / "pytest.ini").exists():
            return "pytest"
        if (repo / "pyproject.toml").exists():
            content = (repo / "pyproject.toml").read_text(encoding='utf-8')
            if '[tool.pytest' in content or 'pytest' in content:
                return "pytest"
        if any(repo.rglob('test_*.py')) or any(repo.rglob('*_test.py')):
            return "unittest"

        pkg = repo / "package.json"
        if pkg.exists():
            content = pkg.read_text(encoding='utf-8')
            if 'jest' in content:
                return "jest"
            if 'mocha' in content:
                return "mocha"
            if 'vitest' in content:
                return "vitest"

        if any(repo.rglob('*.py')):
            return "pytest"
        if any(repo.rglob('*.js')) or any(repo.rglob('*.ts')):
            return "jest"
        return "unknown"

    def _get_repository_context(self, repository_path: str) -> str:
        repo = Path(repository_path)
        parts = ["Repository Structure:"]
        dirs = [d.name for d in repo.iterdir() if d.is_dir() and not d.name.startswith('.')]
        parts.append(f"Directories: {', '.join(dirs[:10])}")
        req = repo / "requirements.txt"
        if req.exists():
            parts.append(f"\nPython Dependencies:\n{req.read_text(encoding='utf-8')[:500]}")
        return '\n'.join(parts)

    # ------------------------------------------------------------------
    # Test generation via Bedrock (Claude)
    # ------------------------------------------------------------------

    async def _generate_test_for_bug(
        self, bug: BugReport, test_framework: str, repo_context: str
    ) -> TestCase:
        test_code, expected_outcome = await retry_with_backoff(
            self._call_bedrock_for_test,
            bug,
            test_framework,
            repo_context,
            max_retries=self.max_retries,
            base_delay=2.0,
        )
        return TestCase(
            test_id=str(uuid4()),
            bug_id=bug.bug_id,
            test_code=test_code,
            test_framework=test_framework,
            expected_outcome=expected_outcome,
        )

    async def _call_bedrock_for_test(
        self, bug: BugReport, test_framework: str, repo_context: str
    ) -> tuple:
        """Call AWS Bedrock (Claude) to generate test code."""
        prompt = (
            f"Generate a test case for the following bug using {test_framework}.\n\n"
            f"Bug Details:\n"
            f"- File: {bug.file_path}\n"
            f"- Line: {bug.line_number}\n"
            f"- Severity: {bug.severity}\n"
            f"- Description: {bug.description}\n"
            f"- Code Snippet:\n{bug.code_snippet}\n\n"
            f"Repository Context:\n{repo_context[:500]}\n\n"
            "Requirements:\n"
            f"1. Use {test_framework} framework\n"
            "2. Include both positive and negative test scenarios\n"
            "3. Include necessary imports and setup\n"
            "4. Use descriptive test names\n\n"
            "Respond ONLY with a JSON object:\n"
            '{"test_code": "...", "expected_outcome": "..."}\n'
            "Respond ONLY with the JSON object."
        )

        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 3072,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }

        response = self.q_developer_client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json",
        )

        response_body = json.loads(response["body"].read())
        claude_text = response_body["content"][0]["text"]

        parsed = self._parse_json(claude_text)
        test_code = parsed.get("test_code", "")
        expected_outcome = parsed.get("expected_outcome", "")

        # Fallback if parsing failed
        if not test_code:
            test_code = claude_text
        if not expected_outcome:
            expected_outcome = f"Validates bug: {bug.description[:200]}"

        return test_code, expected_outcome

    @staticmethod
    def _parse_json(text: str) -> dict:
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass
        for i, ch in enumerate(text):
            if ch == "{":
                try:
                    return json.loads(text[i:])
                except json.JSONDecodeError:
                    continue
        return {}

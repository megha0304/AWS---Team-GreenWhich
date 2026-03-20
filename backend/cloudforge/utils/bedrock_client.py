"""
AWS Bedrock Client Utility for CloudForge Bug Intelligence.

This module provides a high-level interface for interacting with AWS Bedrock
to perform code analysis, bug detection, and root cause analysis using Claude.

Requirements: AWS Bedrock access with Claude 3 Sonnet model
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional

import boto3
from botocore.exceptions import ClientError

from cloudforge.models.config import SystemConfig
from cloudforge.utils.retry import retry_with_backoff

logger = logging.getLogger(__name__)

# Language detection map
EXTENSION_LANGUAGE_MAP = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
    ".jsx": "React JSX", ".tsx": "React TSX", ".java": "Java",
    ".kt": "Kotlin", ".scala": "Scala", ".go": "Go", ".rs": "Rust",
    ".c": "C", ".cpp": "C++", ".h": "C/C++ Header", ".hpp": "C++ Header",
    ".rb": "Ruby", ".php": "PHP", ".swift": "Swift", ".m": "Objective-C",
    ".cs": "C#", ".fs": "F#", ".vb": "Visual Basic",
}


class BedrockClient:
    """
    High-level client for AWS Bedrock interactions.

    Provides methods for:
    - Code analysis and bug detection
    - Root cause analysis
    - Fix suggestion generation
    - Test case generation

    Handles API calls, retries, and response parsing.
    """

    def __init__(self, config: SystemConfig):
        self.config = config
        self.model_id = config.bedrock_model_id
        self.max_retries = config.max_retries
        self.logger = logging.getLogger(__name__)

        try:
            self.client = config.get_bedrock_client()
            self.logger.info(
                f"Initialized Bedrock client with model {self.model_id}",
                extra={"model_id": self.model_id, "region": config.bedrock_region},
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize Bedrock client: {e}")
            raise

    # ------------------------------------------------------------------
    # Core invoke helper
    # ------------------------------------------------------------------

    def _invoke_claude(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.1,
        system: Optional[str] = None,
    ) -> str:
        """
        Invoke Claude model via Bedrock Runtime ``invoke_model`` API.

        This is a *synchronous* call; the async retry wrapper handles
        awaiting it properly.

        Returns:
            The text content from Claude's response.
        """
        messages = [{"role": "user", "content": prompt}]

        request_body: Dict[str, Any] = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": messages,
            "temperature": temperature,
        }
        if system:
            request_body["system"] = system

        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json",
        )

        response_body = json.loads(response["body"].read())
        return response_body["content"][0]["text"]

    # ------------------------------------------------------------------
    # Language detection
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_language(file_path: str) -> str:
        ext = "." + file_path.rsplit(".", 1)[-1] if "." in file_path else ""
        return EXTENSION_LANGUAGE_MAP.get(ext.lower(), "Unknown")

    # ------------------------------------------------------------------
    # Prompt builders
    # ------------------------------------------------------------------

    def _build_bug_detection_prompt(
        self, file_path: str, code_content: str, language: str
    ) -> str:
        # Truncate very large files to stay within token budget
        code = code_content[:8000]
        return f"""Analyze the following {language} code file for potential bugs, security issues, and code quality problems.

File: {file_path}

```{language.lower()}
{code}
```

For each bug found, respond with a JSON array. Each element must have exactly these keys:
- "line_number" (int): approximate line number
- "severity" (string): one of "critical", "high", "medium", "low"
- "description" (string): clear explanation of the bug (at least 10 characters)
- "code_snippet" (string): the relevant code fragment
- "confidence" (float): your confidence between 0.0 and 1.0

If no bugs are found, return an empty JSON array: []

Respond ONLY with the JSON array, no other text."""

    def _build_root_cause_prompt(
        self,
        bug_description: str,
        code_snippet: str,
        test_output: str,
        file_path: str,
    ) -> str:
        return f"""Analyze this test failure and identify the root cause.

Bug Information:
- File: {file_path}
- Description: {bug_description}
- Code Snippet:
{code_snippet}

Test Output:
{test_output[:3000]}

Respond ONLY with a JSON object with these keys:
- "cause_description" (string): detailed root cause explanation (at least 10 characters)
- "confidence_score" (float): between 0.0 and 1.0
- "causal_chain" (string): how the bug leads to the failure
- "suggested_investigation" (array of strings): next steps to investigate

Respond ONLY with the JSON object, no other text."""

    def _build_fix_generation_prompt(
        self,
        bug_description: str,
        code_snippet: str,
        root_cause: str,
        file_path: str,
        language: str,
    ) -> str:
        return f"""Generate a fix for the following bug in {language}.

File: {file_path}
Bug: {bug_description}
Root Cause: {root_cause}

Original Code:
```{language.lower()}
{code_snippet}
```

Respond ONLY with a JSON object with these keys:
- "description" (string): what the fix does (at least 10 characters)
- "code_diff" (string): unified diff format patch
- "safety_score" (float): 0.0-1.0 how safe this fix is
- "impact_score" (float): 0.0-1.0 how impactful
- "explanation" (string): why this fix works

Respond ONLY with the JSON object, no other text."""

    def _build_test_generation_prompt(
        self,
        bug_description: str,
        code_snippet: str,
        file_path: str,
        test_framework: str,
        repo_context: str,
    ) -> str:
        return f"""Generate a test case for the following bug using {test_framework}.

Bug Details:
- File: {file_path}
- Description: {bug_description}
- Code Snippet:
{code_snippet}

Repository Context:
{repo_context[:500]}

Requirements:
1. Use {test_framework} framework
2. Include both a positive test (expected behavior) and a negative test (error handling)
3. Include necessary imports and setup
4. Use descriptive test names

Respond ONLY with a JSON object with these keys:
- "test_code" (string): complete executable test code
- "expected_outcome" (string): what the test validates

Respond ONLY with the JSON object, no other text."""

    # ------------------------------------------------------------------
    # Response parsers
    # ------------------------------------------------------------------

    def _extract_json(self, text: str) -> Any:
        """Extract JSON from a response that may contain markdown fences."""
        # Try direct parse first
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code fences
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Last resort: find first [ or { and parse from there
        for i, ch in enumerate(text):
            if ch in ("[", "{"):
                try:
                    return json.loads(text[i:])
                except json.JSONDecodeError:
                    continue

        self.logger.warning("Could not parse JSON from Bedrock response")
        return None

    def _parse_bug_detection_response(self, response_text: str) -> List[Dict[str, Any]]:
        parsed = self._extract_json(response_text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and "bugs" in parsed:
            return parsed["bugs"]
        return []

    def _parse_root_cause_response(self, response_text: str) -> Dict[str, Any]:
        parsed = self._extract_json(response_text)
        if isinstance(parsed, dict):
            return parsed
        return {
            "cause_description": response_text[:500],
            "confidence_score": 0.5,
            "causal_chain": "Unable to parse structured response",
            "suggested_investigation": [],
        }

    def _parse_fix_suggestion_response(self, response_text: str) -> Dict[str, Any]:
        parsed = self._extract_json(response_text)
        if isinstance(parsed, dict):
            return parsed
        return {
            "description": response_text[:500],
            "code_diff": "",
            "safety_score": 0.5,
            "impact_score": 0.5,
            "explanation": "Unable to parse structured response",
        }

    def _parse_test_generation_response(self, response_text: str) -> Dict[str, Any]:
        parsed = self._extract_json(response_text)
        if isinstance(parsed, dict):
            return parsed
        return {
            "test_code": response_text,
            "expected_outcome": "Unable to parse structured response",
        }

    # ------------------------------------------------------------------
    # Public high-level methods
    # ------------------------------------------------------------------

    async def analyze_code_for_bugs(
        self, file_path: str, code_content: str, language: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Analyze code for potential bugs using Claude."""
        if not language:
            language = self._detect_language(file_path)

        prompt = self._build_bug_detection_prompt(file_path, code_content, language)

        try:
            response_text = await retry_with_backoff(
                self._invoke_claude_async,
                prompt,
                max_tokens=4096,
                temperature=0.1,
                max_retries=self.max_retries,
                base_delay=2.0,
            )
            bugs = self._parse_bug_detection_response(response_text)
            self.logger.info(
                f"Analyzed {file_path}: found {len(bugs)} potential bugs",
                extra={"file_path": file_path, "bugs_found": len(bugs)},
            )
            return bugs
        except Exception as e:
            self.logger.error(f"Failed to analyze code for bugs: {e}", extra={"file_path": file_path})
            raise

    async def analyze_root_cause(
        self, bug_description: str, code_snippet: str, test_output: str, file_path: str
    ) -> Dict[str, Any]:
        """Analyze test failure to identify root cause."""
        prompt = self._build_root_cause_prompt(bug_description, code_snippet, test_output, file_path)
        try:
            response_text = await retry_with_backoff(
                self._invoke_claude_async, prompt, max_tokens=2048, temperature=0.3,
                max_retries=self.max_retries, base_delay=2.0,
            )
            return self._parse_root_cause_response(response_text)
        except Exception as e:
            self.logger.error(f"Failed to analyze root cause: {e}", extra={"file_path": file_path})
            raise

    async def generate_fix_suggestion(
        self, bug_description: str, code_snippet: str, root_cause: str,
        file_path: str, language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate fix suggestion for a bug."""
        if not language:
            language = self._detect_language(file_path)
        prompt = self._build_fix_generation_prompt(
            bug_description, code_snippet, root_cause, file_path, language
        )
        try:
            response_text = await retry_with_backoff(
                self._invoke_claude_async, prompt, max_tokens=3072, temperature=0.2,
                max_retries=self.max_retries, base_delay=2.0,
            )
            return self._parse_fix_suggestion_response(response_text)
        except Exception as e:
            self.logger.error(f"Failed to generate fix suggestion: {e}", extra={"file_path": file_path})
            raise

    async def generate_test_code(
        self, bug_description: str, code_snippet: str, file_path: str,
        test_framework: str, repo_context: str,
    ) -> Dict[str, Any]:
        """Generate test code for a bug using Claude."""
        prompt = self._build_test_generation_prompt(
            bug_description, code_snippet, file_path, test_framework, repo_context
        )
        try:
            response_text = await retry_with_backoff(
                self._invoke_claude_async, prompt, max_tokens=3072, temperature=0.2,
                max_retries=self.max_retries, base_delay=2.0,
            )
            return self._parse_test_generation_response(response_text)
        except Exception as e:
            self.logger.error(f"Failed to generate test code: {e}", extra={"file_path": file_path})
            raise

    # Thin async wrapper around the synchronous invoke so retry_with_backoff can await it
    async def _invoke_claude_async(
        self, prompt: str, max_tokens: int = 4096, temperature: float = 0.1,
        system: Optional[str] = None,
    ) -> str:
        return self._invoke_claude(prompt, max_tokens=max_tokens, temperature=temperature, system=system)

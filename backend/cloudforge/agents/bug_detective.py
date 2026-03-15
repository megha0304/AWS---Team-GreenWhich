"""
Bug Detective Agent - Scans code repositories for potential bugs using AWS Bedrock.

Uses AWS Bedrock with Claude to analyze code semantics and identify bugs.

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6
"""

import json
import logging
from pathlib import Path
from typing import List, Any
from uuid import uuid4

from cloudforge.models.state import AgentState, BugReport
from cloudforge.models.config import SystemConfig
from cloudforge.utils.retry import retry_with_backoff

logger = logging.getLogger(__name__)


class BugDetectiveAgent:
    """
    Scans code repositories and detects bugs via AWS Bedrock (Claude).

    Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6
    """

    # File extensions to scan
    SOURCE_EXTENSIONS = {
        '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.kt', '.scala',
        '.go', '.rs', '.c', '.cpp', '.h', '.hpp', '.rb', '.php',
        '.swift', '.m', '.cs', '.fs', '.vb',
    }

    # Directories to skip
    EXCLUDE_DIRS = {
        'node_modules', '.git', '__pycache__', '.pytest_cache',
        'venv', 'env', '.venv', 'dist', 'build', 'target',
        '.next', '.nuxt', 'coverage', '.coverage',
    }

    def __init__(self, bedrock_client: Any, config: SystemConfig):
        self.bedrock_client = bedrock_client
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.model_id = config.bedrock_model_id
        self.max_retries = config.max_retries
        self.batch_size = config.max_files_per_batch

    async def detect_bugs(self, state: AgentState) -> AgentState:
        """Scan repository and detect bugs. Main entry point."""
        self.logger.info(
            f"Starting bug detection for workflow {state.workflow_id}",
            extra={"workflow_id": state.workflow_id, "repository_path": state.repository_path},
        )

        repo_path = Path(state.repository_path)
        if not repo_path.exists():
            raise ValueError(f"Repository path does not exist: {state.repository_path}")

        source_files = self._get_source_files(repo_path)
        total_files = len(source_files)
        self.logger.info(f"Found {total_files} source files to scan")

        if total_files > 10000:
            bugs = await self._batch_scan(source_files, state.workflow_id)
        else:
            bugs = []
            for file_path in source_files:
                try:
                    file_bugs = await self._scan_file(file_path, repo_path)
                    bugs.extend(file_bugs)
                except Exception as e:
                    self.logger.warning(f"Failed to scan file {file_path}: {e}")
                    continue

        state.bugs = bugs
        state.current_agent = "bug_detective"
        self.logger.info(f"Bug detection complete: found {len(bugs)} bugs in {total_files} files")
        return state

    # ------------------------------------------------------------------
    # File discovery
    # ------------------------------------------------------------------

    def _get_source_files(self, repo_path: Path) -> List[Path]:
        source_files = []
        for file_path in repo_path.rglob('*'):
            if not file_path.is_file():
                continue
            if any(excluded in file_path.parts for excluded in self.EXCLUDE_DIRS):
                continue
            if file_path.suffix.lower() in self.SOURCE_EXTENSIONS:
                source_files.append(file_path)
        return source_files

    # ------------------------------------------------------------------
    # Single-file scan (real Bedrock call)
    # ------------------------------------------------------------------

    async def _scan_file(self, file_path: Path, repo_root: Path) -> List[BugReport]:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                code_content = f.read()
        except Exception as e:
            self.logger.error(f"Error reading file {file_path}: {e}")
            raise

        relative_path = str(file_path.relative_to(repo_root))

        bugs_data = await retry_with_backoff(
            self._call_bedrock_for_bugs,
            relative_path,
            code_content,
            max_retries=self.max_retries,
            base_delay=2.0,
        )
        return bugs_data

    async def _call_bedrock_for_bugs(
        self, file_path: str, code_content: str
    ) -> List[BugReport]:
        """Call AWS Bedrock to analyze code and detect bugs."""
        # Build the prompt
        language = self._detect_language(file_path)
        code = code_content[:8000]  # Token budget management

        prompt = (
            f"Analyze the following {language} code file for potential bugs, "
            f"security issues, and code quality problems.\n\n"
            f"File: {file_path}\n\n"
            f"```{language.lower()}\n{code}\n```\n\n"
            "For each bug found, respond with a JSON array. Each element must have:\n"
            '- "line_number" (int)\n'
            '- "severity" (string): "critical", "high", "medium", or "low"\n'
            '- "description" (string): at least 10 characters\n'
            '- "code_snippet" (string)\n'
            '- "confidence" (float): 0.0 to 1.0\n\n'
            "If no bugs are found, return: []\n"
            "Respond ONLY with the JSON array."
        )

        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        }

        response = self.bedrock_client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json",
        )

        response_body = json.loads(response["body"].read())
        claude_text = response_body["content"][0]["text"]

        # Parse response
        bugs_raw = self._parse_bugs_json(claude_text)
        bugs = []
        for bug_data in bugs_raw:
            try:
                line_num = int(bug_data.get("line_number", 1))
                severity = bug_data.get("severity", "medium").lower()
                if severity not in ("critical", "high", "medium", "low"):
                    severity = "medium"
                description = bug_data.get("description", "")
                if len(description) < 10:
                    description = f"Bug detected in {file_path} at line {line_num}: {description}"
                snippet = bug_data.get("code_snippet", "")
                if not snippet:
                    snippet = self._extract_code_snippet(code_content, line_num)
                confidence = float(bug_data.get("confidence", 0.8))
                confidence = max(0.0, min(1.0, confidence))

                bugs.append(BugReport(
                    bug_id=str(uuid4()),
                    file_path=file_path,
                    line_number=max(1, line_num),
                    severity=severity,
                    description=description,
                    code_snippet=snippet if snippet else f"Line {line_num}",
                    confidence_score=confidence,
                ))
            except Exception as e:
                self.logger.warning(f"Skipping malformed bug entry: {e}")
                continue

        return bugs

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_language(file_path: str) -> str:
        ext_map = {
            ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
            ".java": "Java", ".go": "Go", ".rs": "Rust", ".rb": "Ruby",
            ".php": "PHP", ".c": "C", ".cpp": "C++", ".cs": "C#",
        }
        ext = "." + file_path.rsplit(".", 1)[-1] if "." in file_path else ""
        return ext_map.get(ext.lower(), "Unknown")

    @staticmethod
    def _parse_bugs_json(text: str) -> list:
        import re
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
            if ch == "[":
                try:
                    return json.loads(text[i:])
                except json.JSONDecodeError:
                    continue
        return []

    def _extract_code_snippet(self, code_content: str, line_number: int, context: int = 5) -> str:
        lines = code_content.split('\n')
        start = max(0, line_number - context - 1)
        end = min(len(lines), line_number + context)
        numbered = []
        for i, line in enumerate(lines[start:end], start=start + 1):
            marker = ">>>" if i == line_number else "   "
            numbered.append(f"{marker} {i:4d} | {line}")
        return '\n'.join(numbered)

    async def _batch_scan(self, file_paths: List[Path], workflow_id: str) -> List[BugReport]:
        all_bugs = []
        total = len(file_paths)
        for i in range(0, total, self.batch_size):
            batch = file_paths[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            self.logger.info(f"Processing batch {batch_num}, {len(batch)} files")
            for fp in batch:
                try:
                    repo_root = fp.parents[len(fp.parents) - 2]
                    file_bugs = await self._scan_file(fp, repo_root)
                    all_bugs.extend(file_bugs)
                except Exception as e:
                    self.logger.warning(f"Failed to scan {fp} in batch: {e}")
                    continue
        return all_bugs

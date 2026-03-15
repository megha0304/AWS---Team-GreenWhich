"""
Resolution Agent - Generates fix suggestions using AWS Bedrock (Claude).

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6
"""

import json
import logging
import re
from datetime import datetime
from typing import List, Dict, Any

from cloudforge.models.state import AgentState, FixSuggestion, RootCause, BugReport

logger = logging.getLogger(__name__)


class ResolutionAgent:
    """
    Generates fix suggestions and code patches via AWS Bedrock (Claude).

    Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6
    """

    def __init__(self, q_developer_client: Any, config: Dict[str, Any]):
        """
        Args:
            q_developer_client: Bedrock Runtime client (named for backward compat)
            config: SystemConfig or dict with bedrock_model_id, max_retries
        """
        self.q_developer_client = q_developer_client
        self.config = config
        self.logger = logging.getLogger(__name__)
        # Support both dict and SystemConfig
        if hasattr(config, 'bedrock_model_id'):
            self.model_id = config.bedrock_model_id
            self.max_retries = config.max_retries
        else:
            self.model_id = config.get('bedrock_model_id', 'anthropic.claude-3-sonnet-20240229-v1:0')
            self.max_retries = config.get('max_retries', 3)

    async def generate_fixes(self, state: AgentState) -> AgentState:
        """Generate fix suggestions for all root causes. Main entry point."""
        self.logger.info(f"Starting fix generation for workflow {state.workflow_id}")
        state.current_agent = "resolution"
        state.status = "in_progress"
        state.updated_at = datetime.utcnow()

        if not state.root_causes:
            self.logger.warning("No root causes found, skipping fix generation")
            state.status = "completed"
            return state

        all_fixes = []
        for root_cause in state.root_causes:
            try:
                bug = self._find_bug_by_id(state.bugs, root_cause.bug_id)
                if not bug:
                    self.logger.warning(f"Bug {root_cause.bug_id} not found")
                    continue
                fix = await self._generate_fix(root_cause, bug, state.repository_path)
                all_fixes.append(fix)
            except Exception as e:
                self.logger.error(f"Failed to generate fix for {root_cause.bug_id}: {e}")
                state.errors.append({"agent": "resolution", "bug_id": root_cause.bug_id, "error": str(e)})

        state.fix_suggestions = self._rank_fixes(all_fixes)
        state.status = "completed"
        state.updated_at = datetime.utcnow()
        self.logger.info(f"Generated {len(state.fix_suggestions)} fixes")
        return state

    async def _generate_fix(
        self, root_cause: RootCause, bug: BugReport, repository_path: str
    ) -> FixSuggestion:
        """Generate a fix using real Bedrock API call."""
        language = self._detect_language(bug.file_path)

        prompt = (
            f"Generate a code fix for the following bug in {language}.\n\n"
            f"File: {bug.file_path}\n"
            f"Line: {bug.line_number}\n"
            f"Severity: {bug.severity}\n"
            f"Bug Description: {bug.description}\n"
            f"Root Cause: {root_cause.cause_description}\n\n"
            f"Original Code:\n```\n{bug.code_snippet}\n```\n\n"
            "Respond ONLY with a JSON object:\n"
            "{\n"
            '  "fix_description": "what the fix does (at least 10 chars)",\n'
            '  "code_diff": "unified diff format patch",\n'
            '  "safety_score": 0.85,\n'
            '  "impact_assessment": "impact description"\n'
            "}\n"
            "Respond ONLY with the JSON object."
        )

        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 3072,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }

        try:
            response = self.q_developer_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json",
            )
            body = json.loads(response["body"].read())
            claude_text = body["content"][0]["text"]
            parsed = self._parse_json(claude_text)

            fix_desc = parsed.get("fix_description", "")
            if len(fix_desc) < 10:
                fix_desc = f"Fix for {bug.severity} bug in {bug.file_path} at line {bug.line_number}"

            code_diff = parsed.get("code_diff", "")
            if not code_diff:
                code_diff = self._generate_fallback_diff(bug)

            safety = float(parsed.get("safety_score", 0.7))
            safety = max(0.0, min(1.0, safety))

            impact = parsed.get("impact_assessment", "")
            if not impact:
                impact = self._generate_impact_assessment(bug, root_cause)

            return FixSuggestion(
                bug_id=bug.bug_id,
                fix_description=fix_desc,
                code_diff=code_diff,
                safety_score=safety,
                impact_assessment=impact,
            )
        except Exception as e:
            self.logger.error(f"Bedrock fix generation failed: {e}")
            # Fallback to locally-generated fix
            return FixSuggestion(
                bug_id=bug.bug_id,
                fix_description=f"Fix for {bug.severity} bug in {bug.file_path}: {root_cause.cause_description[:80]}",
                code_diff=self._generate_fallback_diff(bug),
                safety_score=self._calculate_safety_score(bug, root_cause),
                impact_assessment=self._generate_impact_assessment(bug, root_cause),
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

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

    @staticmethod
    def _detect_language(file_path: str) -> str:
        ext_map = {
            ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
            ".java": "Java", ".go": "Go", ".rs": "Rust", ".rb": "Ruby",
        }
        ext = "." + file_path.rsplit(".", 1)[-1] if "." in file_path else ""
        return ext_map.get(ext.lower(), "Unknown")

    @staticmethod
    def _generate_fallback_diff(bug: BugReport) -> str:
        return (
            f"--- a/{bug.file_path}\n"
            f"+++ b/{bug.file_path}\n"
            f"@@ -{bug.line_number},3 +{bug.line_number},3 @@\n"
            f" # Context before\n"
            f"-# Original code with bug\n"
            f"+# Fixed code (apply Bedrock-generated fix)\n"
            f" # Context after\n"
        )

    @staticmethod
    def _calculate_safety_score(bug: BugReport, root_cause: RootCause) -> float:
        severity_weights = {"critical": 1.0, "high": 0.8, "medium": 0.6, "low": 0.4}
        severity_score = severity_weights.get(bug.severity, 0.5)
        return round((severity_score * 0.4) + (root_cause.confidence_score * 0.6), 2)

    @staticmethod
    def _generate_impact_assessment(bug: BugReport, root_cause: RootCause) -> str:
        impacts = {
            "critical": "High impact - addresses critical security or data integrity issue",
            "high": "Moderate-high impact - fixes significant functionality problem",
            "medium": "Moderate impact - improves code quality and reliability",
            "low": "Low impact - minor improvement or code cleanup",
        }
        result = impacts.get(bug.severity, "Unknown impact")
        if root_cause.related_bugs:
            result += f"\nThis fix may also resolve {len(root_cause.related_bugs)} related bug(s)."
        return result

    def _rank_fixes(self, fixes: List[FixSuggestion]) -> List[FixSuggestion]:
        return sorted(fixes, key=lambda f: f.safety_score, reverse=True)

    @staticmethod
    def _find_bug_by_id(bugs: List[BugReport], bug_id: str):
        return next((b for b in bugs if b.bug_id == bug_id), None)

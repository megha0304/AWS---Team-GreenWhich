"""
Analysis Agent - Analyzes test results and identifies root causes using AWS Bedrock.

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional

from cloudforge.models.state import AgentState, TestResult, BugReport, RootCause
from cloudforge.models.config import SystemConfig
from cloudforge.utils.retry import retry_with_backoff

logger = logging.getLogger(__name__)


class AnalysisAgent:
    """
    Analyzes test results and identifies root causes via AWS Bedrock (Claude).

    Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
    """

    def __init__(self, bedrock_client: Any, config: SystemConfig):
        self.bedrock_client = bedrock_client
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.model_id = config.bedrock_model_id
        self.max_retries = config.max_retries

    async def analyze_results(self, state: AgentState) -> AgentState:
        """Analyze test results and identify root causes. Main entry point."""
        self.logger.info(
            f"Starting analysis for workflow {state.workflow_id}",
            extra={"test_results": len(state.test_results), "bugs": len(state.bugs)},
        )

        if not state.test_results:
            self.logger.warning("No test results to analyze")
            state.current_agent = "analysis"
            return state

        root_causes = []
        for test_result in state.test_results:
            if test_result.status != "failed":
                continue
            try:
                bug = self._find_bug_for_test(test_result, state.bugs, state.test_cases)
                if not bug:
                    self.logger.warning(f"No bug found for test {test_result.test_id}")
                    continue
                root_cause = await self._analyze_failure(test_result, bug, state.workflow_id)
                root_causes.append(root_cause)
            except Exception as e:
                self.logger.error(f"Failed to analyze test {test_result.test_id}: {e}")
                state.add_error("analysis_failed", str(e), "analysis")
                continue

        if root_causes:
            root_causes = self._group_related_bugs(root_causes)

        state.root_causes = root_causes
        state.current_agent = "analysis"
        self.logger.info(f"Analysis complete: {len(root_causes)} root causes identified")
        return state

    def _find_bug_for_test(
        self, test_result: TestResult, bugs: List[BugReport], test_cases: List[Any]
    ) -> Optional[BugReport]:
        test_case = next((tc for tc in test_cases if tc.test_id == test_result.test_id), None)
        if not test_case:
            return None
        return next((b for b in bugs if b.bug_id == test_case.bug_id), None)

    async def _analyze_failure(
        self, test_result: TestResult, bug: BugReport, workflow_id: str
    ) -> RootCause:
        """Analyze a test failure using real Bedrock API call."""
        prompt = (
            "Analyze this test failure and identify the root cause.\n\n"
            f"Bug Information:\n"
            f"- File: {bug.file_path}\n"
            f"- Line: {bug.line_number}\n"
            f"- Severity: {bug.severity}\n"
            f"- Description: {bug.description}\n"
            f"- Code Snippet:\n{bug.code_snippet}\n\n"
            f"Test Failure:\n"
            f"- Exit Code: {test_result.exit_code}\n"
            f"- Stdout:\n{test_result.stdout[:2000]}\n"
            f"- Stderr:\n{test_result.stderr[:2000]}\n\n"
            "Respond ONLY with a JSON object:\n"
            '{"cause_description": "...", "confidence_score": 0.85, "causal_chain": "..."}\n'
            "Respond ONLY with the JSON object."
        )

        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2048,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
        }

        try:
            async def _invoke():
                resp = self.bedrock_client.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps(request_body),
                    contentType="application/json",
                    accept="application/json",
                )
                body = json.loads(resp["body"].read())
                return body["content"][0]["text"]

            response_text = await retry_with_backoff(
                _invoke, max_retries=self.max_retries, base_delay=2.0
            )
            analysis = self._parse_json(response_text)

            cause_desc = analysis.get("cause_description", f"Root cause for bug in {bug.file_path}")
            if len(cause_desc) < 10:
                cause_desc = f"Root cause analysis for bug in {bug.file_path} at line {bug.line_number}"
            confidence = float(analysis.get("confidence_score", 0.7))
            confidence = max(0.0, min(1.0, confidence))

            return RootCause(
                bug_id=bug.bug_id,
                cause_description=cause_desc,
                related_bugs=[],
                confidence_score=confidence,
            )
        except Exception as e:
            self.logger.error(f"Bedrock analysis failed for bug {bug.bug_id}: {e}")
            return RootCause(
                bug_id=bug.bug_id,
                cause_description=f"Analysis failed for bug in {bug.file_path}: {str(e)[:80]}",
                related_bugs=[],
                confidence_score=0.1,
            )

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

    def _group_related_bugs(self, root_causes: List[RootCause]) -> List[RootCause]:
        """Group bugs with similar root causes together."""
        if len(root_causes) <= 1:
            return root_causes

        groups: List[List[RootCause]] = []
        for rc in root_causes:
            rc_terms = self._extract_key_terms(rc.cause_description)
            found = False
            for group in groups:
                group_terms = self._extract_key_terms(group[0].cause_description)
                if rc_terms and group_terms:
                    intersection = len(rc_terms & group_terms)
                    union = len(rc_terms | group_terms)
                    if union > 0 and (intersection / union) > 0.3:
                        group.append(rc)
                        found = True
                        break
            if not found:
                groups.append([rc])

        result = []
        for group_bugs in groups:
            if len(group_bugs) == 1:
                result.append(group_bugs[0])
            else:
                bug_ids = [rc.bug_id for rc in group_bugs]
                for rc in group_bugs:
                    rc.related_bugs = [bid for bid in bug_ids if bid != rc.bug_id]
                    result.append(rc)
        return result

    @staticmethod
    def _extract_key_terms(text: str) -> set:
        stopwords = {
            'a', 'an', 'the', 'in', 'at', 'on', 'for', 'to', 'of', 'and', 'or',
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
            'this', 'that', 'these', 'those', 'it', 'its',
        }
        return {
            w.strip('.,;:!?()[]{}')
            for w in text.lower().split()
            if len(w) > 4 and w not in stopwords
        }

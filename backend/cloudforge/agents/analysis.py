"""
Analysis Agent - Analyzes test results and identifies root causes.

This agent processes test execution results, correlates failures with code patterns,
and uses AWS Bedrock to identify root causes. It groups related bugs and provides
confidence scores for each hypothesis.

REQUIRED AWS SETUP:
===================
1. AWS Bedrock:
   - Model access for Claude 3 Sonnet
   - IAM permissions: bedrock:InvokeModel

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
"""

import logging
import json
from typing import List, Dict, Any, Optional
from collections import defaultdict

from cloudforge.models.state import AgentState, TestResult, BugReport, RootCause
from cloudforge.models.config import SystemConfig
from cloudforge.utils.retry import retry_with_backoff

logger = logging.getLogger(__name__)


class AnalysisAgent:
    """
    Agent responsible for analyzing test results and identifying root causes.
    
    Processes test execution results, correlates failures with code patterns,
    and uses Bedrock to identify root causes. Groups related bugs and provides
    confidence scores for each hypothesis.
    
    Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
    """
    
    def __init__(
        self,
        bedrock_client: Any,
        config: SystemConfig
    ):
        """
        Initialize Analysis Agent.
        
        Args:
            bedrock_client: Boto3 Bedrock Runtime client
            config: System configuration with analysis settings
        
        Example:
            >>> config = SystemConfig.load_config()
            >>> bedrock_client = boto3.client('bedrock-runtime')
            >>> agent = AnalysisAgent(bedrock_client, config)
        """
        self.bedrock_client = bedrock_client
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.model_id = config.bedrock_model_id
        self.max_retries = config.max_retries
        
        self.logger.info(
            "Initialized AnalysisAgent",
            extra={
                "model_id": self.model_id,
                "max_retries": self.max_retries
            }
        )
    
    async def analyze_results(self, state: AgentState) -> AgentState:
        """
        Analyze test results and identify root causes.
        
        This is the main entry point for the Analysis Agent. It processes all test
        results, identifies root causes using Bedrock, and groups related bugs.
        
        Args:
            state: Current workflow state with test_results and bugs lists populated
        
        Returns:
            Updated state with root_causes list populated
        
        Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
        """
        self.logger.info(
            f"Starting result analysis for workflow {state.workflow_id}",
            extra={
                "workflow_id": state.workflow_id,
                "test_result_count": len(state.test_results),
                "bug_count": len(state.bugs)
            }
        )
        
        # Validate state
        if not state.test_results:
            self.logger.warning(
                f"No test results found for workflow {state.workflow_id}, skipping analysis",
                extra={"workflow_id": state.workflow_id}
            )
            state.current_agent = "analysis"
            return state
        
        # Analyze each test result
        root_causes = []
        for test_result in state.test_results:
            # Only analyze failed tests
            if test_result.status != "failed":
                continue
            
            try:
                # Find the corresponding bug
                bug = self._find_bug_for_test(test_result, state.bugs, state.test_cases)
                
                if not bug:
                    self.logger.warning(
                        f"Could not find bug for test {test_result.test_id}",
                        extra={
                            "workflow_id": state.workflow_id,
                            "test_id": test_result.test_id
                        }
                    )
                    continue
                
                # Analyze the failure
                self.logger.info(
                    f"Analyzing failure for test {test_result.test_id}",
                    extra={
                        "workflow_id": state.workflow_id,
                        "test_id": test_result.test_id,
                        "bug_id": bug.bug_id
                    }
                )
                
                root_cause = await self._analyze_failure(test_result, bug, state.workflow_id)
                root_causes.append(root_cause)
                
                self.logger.info(
                    f"Root cause identified for bug {bug.bug_id}",
                    extra={
                        "workflow_id": state.workflow_id,
                        "bug_id": bug.bug_id,
                        "confidence": root_cause.confidence_score
                    }
                )
                
            except Exception as e:
                self.logger.error(
                    f"Failed to analyze test result {test_result.test_id}: {e}",
                    extra={
                        "workflow_id": state.workflow_id,
                        "test_id": test_result.test_id,
                        "error": str(e)
                    }
                )
                # Add error to state but continue with other results
                state.add_error(
                    error_type="analysis_failed",
                    error_message=f"Failed to analyze test {test_result.test_id}: {e}",
                    agent_name="analysis"
                )
                continue
        
        # Group related bugs (Requirement 4.5)
        if root_causes:
            root_causes = self._group_related_bugs(root_causes)
        
        # Update state with root causes
        state.root_causes = root_causes
        state.current_agent = "analysis"
        
        self.logger.info(
            f"Analysis complete: identified {len(root_causes)} root causes",
            extra={
                "workflow_id": state.workflow_id,
                "root_cause_count": len(root_causes),
                "grouped_bugs": sum(len(rc.related_bugs) for rc in root_causes)
            }
        )
        
        return state

    def _find_bug_for_test(
        self,
        test_result: TestResult,
        bugs: List[BugReport],
        test_cases: List[Any]
    ) -> Optional[BugReport]:
        """
        Find the bug associated with a test result.
        
        Args:
            test_result: Test result to find bug for
            bugs: List of all bugs
            test_cases: List of all test cases
        
        Returns:
            BugReport if found, None otherwise
        """
        # Find the test case for this result
        test_case = next((tc for tc in test_cases if tc.test_id == test_result.test_id), None)
        
        if not test_case:
            return None
        
        # Find the bug for this test case
        bug = next((b for b in bugs if b.bug_id == test_case.bug_id), None)
        
        return bug
    
    async def _analyze_failure(
        self,
        test_result: TestResult,
        bug: BugReport,
        workflow_id: str
    ) -> RootCause:
        """
        Analyze a test failure and identify root cause using Bedrock.
        
        ⚠️  USER ACTION REQUIRED ⚠️
        ================================
        This method contains placeholder logic. To use real AWS Bedrock:
        
        1. Configure AWS credentials and Bedrock model access
        2. Uncomment the Bedrock API call code below
        3. Remove or modify the placeholder return statement
        
        The placeholder currently returns mock root causes.
        
        Args:
            test_result: Failed test result
            bug: Bug report associated with the test
            workflow_id: Workflow ID for logging
        
        Returns:
            RootCause with analysis results
        
        Requirements: 4.2, 4.3, 4.6
        """
        # ============================================================================
        # PLACEHOLDER: Replace this section with actual Bedrock API call
        # ============================================================================
        # TODO: Uncomment and configure the following code when ready to use Bedrock
        
        """
        # Prepare prompt for Bedrock
        prompt = f'''Analyze this test failure and identify the root cause:

Bug Information:
- File: {bug.file_path}
- Line: {bug.line_number}
- Severity: {bug.severity}
- Description: {bug.description}
- Code Snippet:
{bug.code_snippet}

Test Failure:
- Exit Code: {test_result.exit_code}
- Stdout:
{test_result.stdout}
- Stderr:
{test_result.stderr}

Please provide:
1. Root cause description (what is the underlying issue?)
2. Confidence score (0.0-1.0)
3. Causal chain (how does the bug lead to the failure?)

Format your response as JSON:
{{
    "cause_description": "...",
    "confidence_score": 0.85,
    "causal_chain": "..."
}}'''

        # Call Bedrock
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2000,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3  # Lower temperature for more consistent analysis
        }
        
        try:
            response = await retry_with_backoff(
                lambda: self.bedrock_client.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps(request_body)
                ),
                max_retries=self.max_retries
            )
            
            response_body = json.loads(response['body'].read())
            content = response_body['content'][0]['text']
            
            # Parse JSON response
            analysis = json.loads(content)
            
            # Create root cause
            root_cause = RootCause(
                bug_id=bug.bug_id,
                cause_description=analysis['cause_description'],
                related_bugs=[],  # Will be populated by grouping
                confidence_score=analysis['confidence_score']
            )
            
            return root_cause
            
        except Exception as e:
            self.logger.error(
                f"Bedrock analysis failed for bug {bug.bug_id}: {e}",
                extra={
                    "workflow_id": workflow_id,
                    "bug_id": bug.bug_id,
                    "error": str(e)
                }
            )
            # Return low-confidence placeholder
            return RootCause(
                bug_id=bug.bug_id,
                cause_description=f"Analysis failed: {str(e)}",
                related_bugs=[],
                confidence_score=0.0
            )
        """
        
        # PLACEHOLDER: Mock root cause analysis
        self.logger.warning(
            f"Using placeholder analysis for bug {bug.bug_id}. "
            "Configure AWS Bedrock to use real analysis."
        )
        
        # Generate mock root cause based on bug severity and test output
        cause_description = self._generate_mock_cause(bug, test_result)
        confidence = self._estimate_mock_confidence(bug, test_result)
        
        root_cause = RootCause(
            bug_id=bug.bug_id,
            cause_description=cause_description,
            related_bugs=[],  # Will be populated by grouping
            confidence_score=confidence
        )
        
        return root_cause
    
    def _generate_mock_cause(self, bug: BugReport, test_result: TestResult) -> str:
        """Generate mock root cause description for placeholder mode."""
        # Simple heuristic based on bug description and test output
        if "null" in bug.description.lower() or "none" in bug.description.lower():
            return f"Null pointer or None value access in {bug.file_path} at line {bug.line_number}"
        elif "index" in bug.description.lower() or "array" in bug.description.lower():
            return f"Array index out of bounds in {bug.file_path} at line {bug.line_number}"
        elif "type" in bug.description.lower():
            return f"Type mismatch or incorrect type usage in {bug.file_path} at line {bug.line_number}"
        else:
            return f"Logic error in {bug.file_path} at line {bug.line_number}: {bug.description}"
    
    def _estimate_mock_confidence(self, bug: BugReport, test_result: TestResult) -> float:
        """Estimate mock confidence score for placeholder mode."""
        # Base confidence on bug confidence and test result clarity
        base_confidence = bug.confidence_score
        
        # Adjust based on test output clarity
        if test_result.stderr and len(test_result.stderr) > 50:
            # Clear error message increases confidence
            base_confidence = min(1.0, base_confidence + 0.1)
        
        # Adjust based on bug severity
        severity_boost = {
            "critical": 0.1,
            "high": 0.05,
            "medium": 0.0,
            "low": -0.05
        }
        base_confidence += severity_boost.get(bug.severity, 0.0)
        
        return max(0.0, min(1.0, base_confidence))

    def _group_related_bugs(self, root_causes: List[RootCause]) -> List[RootCause]:
        """
        Group bugs with similar root causes together.
        
        Uses simple text similarity to identify related bugs. In production,
        this could use more sophisticated NLP techniques or embeddings.
        
        Args:
            root_causes: List of root causes to group
        
        Returns:
            List of root causes with related_bugs populated
        
        Requirements: 4.5
        """
        if len(root_causes) <= 1:
            return root_causes
        
        self.logger.info(
            f"Grouping {len(root_causes)} root causes",
            extra={"root_cause_count": len(root_causes)}
        )
        
        # Use similarity-based grouping instead of exact matching
        # Group bugs if they share significant overlap in key terms
        groups = []
        
        for rc in root_causes:
            # Extract key terms for this root cause
            rc_terms = self._extract_key_terms(rc.cause_description)
            
            # Try to find an existing group with similar terms
            found_group = False
            for group in groups:
                # Get terms from first bug in group (representative)
                group_terms = self._extract_key_terms(group[0].cause_description)
                
                # Calculate similarity (Jaccard similarity)
                if rc_terms and group_terms:
                    intersection = len(rc_terms & group_terms)
                    union = len(rc_terms | group_terms)
                    similarity = intersection / union if union > 0 else 0.0
                    
                    # Group if similarity > 0.3 (30% overlap)
                    if similarity > 0.3:
                        group.append(rc)
                        found_group = True
                        break
            
            # Create new group if no similar group found
            if not found_group:
                groups.append([rc])
        
        # Update related_bugs for each group
        grouped_root_causes = []
        for group_bugs in groups:
            if len(group_bugs) == 1:
                # Single bug, no related bugs
                grouped_root_causes.append(group_bugs[0])
            else:
                # Multiple bugs in group
                bug_ids = [rc.bug_id for rc in group_bugs]
                
                for rc in group_bugs:
                    # Add all other bugs in group as related
                    rc.related_bugs = [bid for bid in bug_ids if bid != rc.bug_id]
                    grouped_root_causes.append(rc)
                
                self.logger.info(
                    f"Grouped {len(group_bugs)} related bugs",
                    extra={
                        "bug_ids": bug_ids,
                        "group_size": len(group_bugs)
                    }
                )
        
        return grouped_root_causes
    
    def _extract_key_terms(self, text: str) -> set:
        """
        Extract key terms from text for grouping.
        
        Simple implementation that extracts important words. In production,
        use NLP libraries or embeddings for better accuracy.
        
        Args:
            text: Text to extract terms from
        
        Returns:
            Set of key terms
        """
        # Convert to lowercase and split
        words = text.lower().split()
        
        # Filter out common words (simple stopword list)
        stopwords = {
            'a', 'an', 'the', 'in', 'at', 'on', 'for', 'to', 'of', 'and', 'or',
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
            'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might',
            'can', 'this', 'that', 'these', 'those', 'it', 'its'
        }
        
        # Extract important terms (longer words, not stopwords)
        key_terms = {
            word.strip('.,;:!?()[]{}')
            for word in words
            if len(word) > 4 and word not in stopwords
        }
        
        return key_terms

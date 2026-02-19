"""
Resolution Agent for CloudForge Bug Intelligence.

This agent generates fix suggestions and code patches for identified root causes.
Uses Amazon Q Developer API for intelligent fix generation.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime

from cloudforge.models.state import AgentState, FixSuggestion, RootCause, BugReport


logger = logging.getLogger(__name__)


class ResolutionAgent:
    """
    Agent responsible for generating fix suggestions and code patches.
    
    Uses Amazon Q Developer to create intelligent code fixes that:
    - Maintain code style consistency
    - Provide before/after diffs
    - Include safety and impact assessments
    - Rank multiple fix strategies
    """
    
    def __init__(self, q_developer_client: Any, config: Dict[str, Any]):
        """
        Initialize the Resolution Agent.
        
        Args:
            q_developer_client: Amazon Q Developer API client
            config: Configuration dictionary with Q Developer settings
        """
        self.q_developer_client = q_developer_client
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    async def generate_fixes(self, state: AgentState) -> AgentState:
        """
        Generate fix suggestions for all identified root causes.
        
        Args:
            state: Current workflow state with root_causes populated
            
        Returns:
            Updated state with fix_suggestions populated
        """
        self.logger.info(
            f"Starting fix generation for workflow {state.workflow_id}",
            extra={"workflow_id": state.workflow_id, "root_causes_count": len(state.root_causes)}
        )
        
        state.current_agent = "resolution"
        state.status = "in_progress"
        state.updated_at = datetime.utcnow()
        
        if not state.root_causes:
            self.logger.warning(
                f"No root causes found for workflow {state.workflow_id}",
                extra={"workflow_id": state.workflow_id}
            )
            state.status = "completed"
            return state
        
        # Generate fixes for each root cause
        all_fixes = []
        for root_cause in state.root_causes:
            try:
                # Find the primary bug for this root cause
                bug = self._find_bug_by_id(state.bugs, root_cause.bug_id)
                if not bug:
                    self.logger.warning(
                        f"Bug {root_cause.bug_id} not found for root cause",
                        extra={"workflow_id": state.workflow_id, "bug_id": root_cause.bug_id}
                    )
                    continue
                
                # Generate fix for this root cause
                fix = await self._generate_fix(root_cause, bug, state.repository_path)
                all_fixes.append(fix)
                
                self.logger.info(
                    f"Generated fix for bug {bug.bug_id}",
                    extra={
                        "workflow_id": state.workflow_id,
                        "bug_id": bug.bug_id,
                        "safety_score": fix.safety_score
                    }
                )
                
            except Exception as e:
                # Log error but continue with other root causes
                self.logger.error(
                    f"Failed to generate fix for root cause {root_cause.bug_id}: {e}",
                    extra={
                        "workflow_id": state.workflow_id,
                        "bug_id": root_cause.bug_id,
                        "error": str(e)
                    },
                    exc_info=True
                )
                state.errors.append({
                    "agent": "resolution",
                    "bug_id": root_cause.bug_id,
                    "error": str(e)
                })
        
        # Rank all fixes by safety score
        ranked_fixes = self._rank_fixes(all_fixes)
        state.fix_suggestions = ranked_fixes
        
        state.status = "completed"
        state.updated_at = datetime.utcnow()
        
        self.logger.info(
            f"Fix generation completed for workflow {state.workflow_id}",
            extra={
                "workflow_id": state.workflow_id,
                "fixes_generated": len(ranked_fixes)
            }
        )
        
        return state
    
    async def _generate_fix(
        self,
        root_cause: RootCause,
        bug: BugReport,
        repository_path: str
    ) -> FixSuggestion:
        """
        Generate a fix suggestion for a specific root cause.
        
        Args:
            root_cause: The root cause to fix
            bug: The bug report associated with this root cause
            repository_path: Path to the repository
            
        Returns:
            FixSuggestion with code patch and metadata
        """
        # PLACEHOLDER: In production, this would call Amazon Q Developer API
        # For now, generate a mock fix suggestion
        
        # Simulate Q Developer API call
        fix_description = self._generate_fix_description(root_cause, bug)
        code_diff = self._generate_code_diff(bug)
        safety_score = self._calculate_safety_score(bug, root_cause)
        impact_assessment = self._generate_impact_assessment(bug, root_cause)
        
        return FixSuggestion(
            bug_id=bug.bug_id,
            fix_description=fix_description,
            code_diff=code_diff,
            safety_score=safety_score,
            impact_assessment=impact_assessment
        )
    
    def _generate_fix_description(self, root_cause: RootCause, bug: BugReport) -> str:
        """Generate a human-readable fix description."""
        return (
            f"Fix for {bug.severity} severity bug in {bug.file_path}:\n"
            f"Root cause: {root_cause.cause_description}\n"
            f"Recommended action: Apply the code patch to address the issue."
        )
    
    def _generate_code_diff(self, bug: BugReport) -> str:
        """
        Generate a unified diff format patch.
        
        In production, this would use Q Developer to generate actual code fixes.
        For now, generates a placeholder diff.
        """
        # Extract file name from path
        file_name = bug.file_path.split('/')[-1]
        
        # Generate unified diff format
        diff = f"""--- a/{bug.file_path}
+++ b/{bug.file_path}
@@ -{bug.line_number},3 +{bug.line_number},3 @@
 # Context before
-{bug.code_snippet.split('\\n')[0] if bug.code_snippet else 'old code'}
+# Fixed code (placeholder - Q Developer would generate actual fix)
 # Context after
"""
        return diff
    
    def _calculate_safety_score(self, bug: BugReport, root_cause: RootCause) -> float:
        """
        Calculate safety score for a fix.
        
        Safety score considers:
        - Bug severity (higher severity = more important to fix safely)
        - Root cause confidence (higher confidence = safer fix)
        - Code complexity (simpler fixes are safer)
        
        Returns:
            Float between 0.0 and 1.0
        """
        # Weight by severity
        severity_weights = {
            "critical": 1.0,
            "high": 0.8,
            "medium": 0.6,
            "low": 0.4
        }
        severity_score = severity_weights.get(bug.severity, 0.5)
        
        # Weight by root cause confidence
        confidence_score = root_cause.confidence_score
        
        # Combine scores (weighted average)
        safety_score = (severity_score * 0.4) + (confidence_score * 0.6)
        
        return round(safety_score, 2)
    
    def _generate_impact_assessment(self, bug: BugReport, root_cause: RootCause) -> str:
        """Generate an impact assessment for the fix."""
        severity_impacts = {
            "critical": "High impact - addresses critical security or data integrity issue",
            "high": "Moderate-high impact - fixes significant functionality problem",
            "medium": "Moderate impact - improves code quality and reliability",
            "low": "Low impact - minor improvement or code cleanup"
        }
        
        base_impact = severity_impacts.get(bug.severity, "Unknown impact")
        
        # Add information about related bugs
        if root_cause.related_bugs:
            related_count = len(root_cause.related_bugs)
            base_impact += f"\nThis fix may also resolve {related_count} related bug(s)."
        
        return base_impact
    
    def _rank_fixes(self, fixes: List[FixSuggestion]) -> List[FixSuggestion]:
        """
        Rank fixes by safety score (descending).
        
        Args:
            fixes: List of fix suggestions
            
        Returns:
            Sorted list with highest safety scores first
        """
        return sorted(fixes, key=lambda f: f.safety_score, reverse=True)
    
    def _find_bug_by_id(self, bugs: List[BugReport], bug_id: str) -> BugReport:
        """Find a bug by its ID."""
        for bug in bugs:
            if bug.bug_id == bug_id:
                return bug
        return None

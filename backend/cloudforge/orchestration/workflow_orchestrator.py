"""
Workflow Orchestrator for CloudForge Bug Intelligence.

This orchestrator coordinates the execution of all five agents in the bug lifecycle:
1. Bug Detective Agent - Detects bugs in code
2. Test Architect Agent - Generates tests for bugs
3. Execution Agent - Runs tests on AWS infrastructure
4. Analysis Agent - Analyzes test results and identifies root causes
5. Resolution Agent - Generates fix suggestions

Uses LangGraph for state machine orchestration with state persistence.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from cloudforge.models.state import AgentState
from cloudforge.orchestration.state_store import StateStore
from cloudforge.agents import (
    BugDetectiveAgent,
    TestArchitectAgent,
    ExecutionAgent,
    AnalysisAgent,
    ResolutionAgent
)
from cloudforge.utils.retry import retry_with_backoff


logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """
    Orchestrates the complete bug lifecycle workflow using all five agents.
    
    The workflow follows this sequence:
    1. Detect bugs in the repository
    2. Generate tests for detected bugs
    3. Execute tests on AWS infrastructure
    4. Analyze test results to identify root causes
    5. Generate fix suggestions for root causes
    
    State is persisted to DynamoDB after each agent execution.
    """
    
    def __init__(
        self,
        bug_detective: BugDetectiveAgent,
        test_architect: TestArchitectAgent,
        execution_agent: ExecutionAgent,
        analysis_agent: AnalysisAgent,
        resolution_agent: ResolutionAgent,
        state_store: StateStore,
        config: Dict[str, Any]
    ):
        """
        Initialize the workflow orchestrator.
        
        Args:
            bug_detective: Agent for detecting bugs
            test_architect: Agent for generating tests
            execution_agent: Agent for executing tests
            analysis_agent: Agent for analyzing results
            resolution_agent: Agent for generating fixes
            state_store: Store for persisting workflow state
            config: Configuration dictionary
        """
        self.bug_detective = bug_detective
        self.test_architect = test_architect
        self.execution_agent = execution_agent
        self.analysis_agent = analysis_agent
        self.resolution_agent = resolution_agent
        self.state_store = state_store
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    async def execute_workflow(
        self,
        repository_url: str,
        repository_path: str,
        workflow_id: Optional[str] = None
    ) -> AgentState:
        """
        Execute the complete bug lifecycle workflow.
        
        Args:
            repository_url: URL of the repository to analyze
            repository_path: Local path to the repository
            workflow_id: Optional workflow ID (generated if not provided)
            
        Returns:
            Final workflow state with all agent outputs
        """
        # Generate workflow ID if not provided
        if not workflow_id:
            workflow_id = str(uuid.uuid4())
        
        self.logger.info(
            f"Starting workflow {workflow_id}",
            extra={
                "workflow_id": workflow_id,
                "repository_url": repository_url
            }
        )
        
        # Initialize workflow state
        state = AgentState(
            workflow_id=workflow_id,
            repository_url=repository_url,
            repository_path=repository_path,
            current_agent="initializing",
            status="pending",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Save initial state
        await self.state_store.save_state(state)
        
        try:
            # Execute workflow steps sequentially
            state = await self._execute_bug_detection(state)
            
            # Check if we should continue
            if not self._should_continue(state):
                return state
            
            state = await self._execute_test_generation(state)
            
            if not self._should_continue(state):
                return state
            
            state = await self._execute_test_execution(state)
            
            if not self._should_continue(state):
                return state
            
            state = await self._execute_analysis(state)
            
            if not self._should_continue(state):
                return state
            
            state = await self._execute_resolution(state)
            
            # Mark workflow as completed
            state.status = "completed"
            state.updated_at = datetime.utcnow()
            await self.state_store.save_state(state)
            
            # Generate summary report
            summary = self._generate_summary(state)
            
            self.logger.info(
                f"Workflow {workflow_id} completed successfully",
                extra={
                    "workflow_id": workflow_id,
                    "summary": summary
                }
            )
            
            return state
            
        except Exception as e:
            # Mark workflow as failed
            state.status = "failed"
            state.updated_at = datetime.utcnow()
            state.errors.append({
                "agent": state.current_agent,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
            
            await self.state_store.save_state(state)
            
            self.logger.error(
                f"Workflow {workflow_id} failed",
                extra={
                    "workflow_id": workflow_id,
                    "error": str(e),
                    "current_agent": state.current_agent
                },
                exc_info=True
            )
            
            raise
    
    async def _execute_bug_detection(self, state: AgentState) -> AgentState:
        """Execute bug detection agent with retry logic."""
        self.logger.info(
            f"Executing bug detection for workflow {state.workflow_id}",
            extra={"workflow_id": state.workflow_id}
        )
        
        state.current_agent = "bug_detective"
        state.status = "in_progress"
        await self.state_store.save_state(state)
        
        # Execute with retry
        state = await retry_with_backoff(
            self.bug_detective.detect_bugs,
            state,
            max_retries=self.config.get("max_retries", 3),
            base_delay=self.config.get("retry_backoff_base", 2.0)
        )
        
        await self.state_store.save_state(state)
        
        self.logger.info(
            f"Bug detection completed for workflow {state.workflow_id}",
            extra={
                "workflow_id": state.workflow_id,
                "bugs_found": len(state.bugs)
            }
        )
        
        return state
    
    async def _execute_test_generation(self, state: AgentState) -> AgentState:
        """Execute test generation agent with retry logic."""
        self.logger.info(
            f"Executing test generation for workflow {state.workflow_id}",
            extra={"workflow_id": state.workflow_id}
        )
        
        state.current_agent = "test_architect"
        await self.state_store.save_state(state)
        
        # Execute with retry
        state = await retry_with_backoff(
            self.test_architect.generate_tests,
            state,
            max_retries=self.config.get("max_retries", 3),
            base_delay=self.config.get("retry_backoff_base", 2.0)
        )
        
        await self.state_store.save_state(state)
        
        self.logger.info(
            f"Test generation completed for workflow {state.workflow_id}",
            extra={
                "workflow_id": state.workflow_id,
                "tests_generated": len(state.test_cases)
            }
        )
        
        return state
    
    async def _execute_test_execution(self, state: AgentState) -> AgentState:
        """Execute test execution agent with retry logic."""
        self.logger.info(
            f"Executing tests for workflow {state.workflow_id}",
            extra={"workflow_id": state.workflow_id}
        )
        
        state.current_agent = "execution"
        await self.state_store.save_state(state)
        
        # Execute with retry
        state = await retry_with_backoff(
            self.execution_agent.execute_tests,
            state,
            max_retries=self.config.get("max_retries", 3),
            base_delay=self.config.get("retry_backoff_base", 2.0)
        )
        
        await self.state_store.save_state(state)
        
        self.logger.info(
            f"Test execution completed for workflow {state.workflow_id}",
            extra={
                "workflow_id": state.workflow_id,
                "tests_executed": len(state.test_results)
            }
        )
        
        return state
    
    async def _execute_analysis(self, state: AgentState) -> AgentState:
        """Execute analysis agent with retry logic."""
        self.logger.info(
            f"Executing analysis for workflow {state.workflow_id}",
            extra={"workflow_id": state.workflow_id}
        )
        
        state.current_agent = "analysis"
        await self.state_store.save_state(state)
        
        # Execute with retry
        state = await retry_with_backoff(
            self.analysis_agent.analyze_results,
            state,
            max_retries=self.config.get("max_retries", 3),
            base_delay=self.config.get("retry_backoff_base", 2.0)
        )
        
        await self.state_store.save_state(state)
        
        self.logger.info(
            f"Analysis completed for workflow {state.workflow_id}",
            extra={
                "workflow_id": state.workflow_id,
                "root_causes_found": len(state.root_causes)
            }
        )
        
        return state
    
    async def _execute_resolution(self, state: AgentState) -> AgentState:
        """Execute resolution agent with retry logic."""
        self.logger.info(
            f"Executing resolution for workflow {state.workflow_id}",
            extra={"workflow_id": state.workflow_id}
        )
        
        state.current_agent = "resolution"
        await self.state_store.save_state(state)
        
        # Execute with retry
        state = await retry_with_backoff(
            self.resolution_agent.generate_fixes,
            state,
            max_retries=self.config.get("max_retries", 3),
            base_delay=self.config.get("retry_backoff_base", 2.0)
        )
        
        await self.state_store.save_state(state)
        
        self.logger.info(
            f"Resolution completed for workflow {state.workflow_id}",
            extra={
                "workflow_id": state.workflow_id,
                "fixes_generated": len(state.fix_suggestions)
            }
        )
        
        return state
    
    def _should_continue(self, state: AgentState) -> bool:
        """
        Determine if workflow should continue to next agent.
        
        Args:
            state: Current workflow state
            
        Returns:
            True if workflow should continue, False otherwise
        """
        # Don't continue if workflow failed
        if state.status == "failed":
            return False
        
        # Don't continue if no bugs found
        if state.current_agent == "bug_detective" and len(state.bugs) == 0:
            self.logger.info(
                f"No bugs found for workflow {state.workflow_id}, stopping workflow",
                extra={"workflow_id": state.workflow_id}
            )
            state.status = "completed"
            return False
        
        # Don't continue if no tests generated
        if state.current_agent == "test_architect" and len(state.test_cases) == 0:
            self.logger.warning(
                f"No tests generated for workflow {state.workflow_id}, stopping workflow",
                extra={"workflow_id": state.workflow_id}
            )
            state.status = "completed"
            return False
        
        # Don't continue if no test results
        if state.current_agent == "execution" and len(state.test_results) == 0:
            self.logger.warning(
                f"No test results for workflow {state.workflow_id}, stopping workflow",
                extra={"workflow_id": state.workflow_id}
            )
            state.status = "completed"
            return False
        
        # Don't continue if no root causes found
        if state.current_agent == "analysis" and len(state.root_causes) == 0:
            self.logger.warning(
                f"No root causes found for workflow {state.workflow_id}, stopping workflow",
                extra={"workflow_id": state.workflow_id}
            )
            state.status = "completed"
            return False
        
        return True
    
    def _generate_summary(self, state: AgentState) -> Dict[str, Any]:
        """
        Generate a summary report of the workflow execution.
        
        Args:
            state: Final workflow state
            
        Returns:
            Dictionary containing workflow summary
        """
        # Count test results by status
        test_results_by_status = {}
        for result in state.test_results:
            status = result.status
            test_results_by_status[status] = test_results_by_status.get(status, 0) + 1
        
        # Count bugs by severity
        bugs_by_severity = {}
        for bug in state.bugs:
            severity = bug.severity
            bugs_by_severity[severity] = bugs_by_severity.get(severity, 0) + 1
        
        summary = {
            "workflow_id": state.workflow_id,
            "status": state.status,
            "repository_url": state.repository_url,
            "created_at": state.created_at.isoformat(),
            "completed_at": state.updated_at.isoformat(),
            "bugs_found": len(state.bugs),
            "bugs_by_severity": bugs_by_severity,
            "tests_generated": len(state.test_cases),
            "tests_executed": len(state.test_results),
            "test_results_by_status": test_results_by_status,
            "root_causes_identified": len(state.root_causes),
            "fixes_suggested": len(state.fix_suggestions),
            "errors": len(state.errors)
        }
        
        return summary

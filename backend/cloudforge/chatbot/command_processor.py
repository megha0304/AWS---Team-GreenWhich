"""
Command Processor - Handles chatbot commands for bug analysis and workflow management.

Processes commands like: analyze, suggest, rollback, status, list, export, etc.
Integrates with CloudForge agents and orchestrator.
"""

import logging
from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class CommandType(str, Enum):
    """Available chatbot commands."""
    ANALYZE = "analyze"
    SUGGEST = "suggest"
    ROLLBACK = "rollback"
    STATUS = "status"
    LIST = "list"
    EXPORT = "export"
    HELP = "help"
    FILTER = "filter"
    COMPARE = "compare"
    APPLY = "apply"


class CommandProcessor:
    """
    Processes chatbot commands for bug analysis and workflow management.
    
    Supported commands:
    - analyze: Analyze a specific bug
    - suggest: Get fix suggestions
    - rollback: Rollback changes
    - status: Check workflow status
    - list: List bugs/workflows
    - export: Export results
    - filter: Filter bugs by criteria
    - compare: Compare bugs or fixes
    - apply: Apply a fix
    """
    
    def __init__(
        self,
        orchestrator: Any,
        state_store: Any,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize command processor.
        
        Args:
            orchestrator: WorkflowOrchestrator instance
            state_store: StateStore instance
            config: Configuration dictionary
        """
        self.orchestrator = orchestrator
        self.state_store = state_store
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
    
    async def process_command(
        self,
        command: str,
        workflow_id: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a chatbot command.
        
        Args:
            command: Command type (analyze, suggest, etc.)
            workflow_id: Target workflow ID
            parameters: Command parameters
            
        Returns:
            Command result dictionary
        """
        parameters = parameters or {}
        self.logger.info(f"Processing command: {command} for workflow {workflow_id}")
        
        try:
            if command == CommandType.ANALYZE.value:
                return await self._handle_analyze(workflow_id, parameters)
            elif command == CommandType.SUGGEST.value:
                return await self._handle_suggest(workflow_id, parameters)
            elif command == CommandType.ROLLBACK.value:
                return await self._handle_rollback(workflow_id, parameters)
            elif command == CommandType.STATUS.value:
                return await self._handle_status(workflow_id, parameters)
            elif command == CommandType.LIST.value:
                return await self._handle_list(workflow_id, parameters)
            elif command == CommandType.EXPORT.value:
                return await self._handle_export(workflow_id, parameters)
            elif command == CommandType.FILTER.value:
                return await self._handle_filter(workflow_id, parameters)
            elif command == CommandType.COMPARE.value:
                return await self._handle_compare(workflow_id, parameters)
            elif command == CommandType.APPLY.value:
                return await self._handle_apply(workflow_id, parameters)
            elif command == CommandType.HELP.value:
                return self._handle_help()
            else:
                return {"error": f"Unknown command: {command}"}
        
        except Exception as e:
            self.logger.error(f"Error processing command {command}: {e}")
            return {"error": str(e), "command": command}
    
    async def _handle_analyze(
        self,
        workflow_id: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze a specific bug."""
        bug_id = parameters.get('bug_id')
        
        if not bug_id:
            return {
                "command": "analyze",
                "status": "help_needed",
                "message": "Please specify a bug ID to analyze",
                "example": "analyze bug_id=abc123",
                "help": "Use the 'list' command first to see available bugs"
            }
        
        try:
            # Get workflow state
            state = await self.state_store.load_state(workflow_id) if self.state_store else None
            
            if not state:
                return {
                    "command": "analyze",
                    "bug_id": bug_id,
                    "status": "demo_mode",
                    "message": f"Demo mode: Would analyze bug {bug_id}",
                    "note": "Connect to a real workflow for actual analysis"
                }
            
            # Find bug
            bug = next((b for b in state.bugs if b.bug_id == bug_id), None)
            if not bug:
                return {"error": f"Bug {bug_id} not found"}
            
            return {
                "command": "analyze",
                "bug_id": bug_id,
                "file_path": bug.file_path,
                "line_number": bug.line_number,
                "severity": bug.severity,
                "description": bug.description,
                "code_snippet": bug.code_snippet,
                "confidence_score": bug.confidence_score,
                "status": "success"
            }
        
        except Exception as e:
            return {"error": str(e), "command": "analyze"}
    
    async def _handle_suggest(
        self,
        workflow_id: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get fix suggestions."""
        bug_id = parameters.get('bug_id')
        limit = parameters.get('limit', 5)
        
        if not bug_id:
            return {
                "command": "suggest",
                "status": "help_needed",
                "message": "Please specify a bug ID to get suggestions for",
                "example": "suggest bug_id=abc123",
                "help": "Use the 'list' command first to see available bugs"
            }
        
        try:
            state = await self.state_store.load_state(workflow_id) if self.state_store else None
            
            if not state:
                return {
                    "command": "suggest",
                    "bug_id": bug_id,
                    "status": "demo_mode",
                    "message": f"Demo mode: Would suggest fixes for bug {bug_id}",
                    "note": "Connect to a real workflow for actual suggestions"
                }
            
            # Get fixes for bug
            fixes = [f for f in state.fix_suggestions if f.bug_id == bug_id][:limit]
            
            if not fixes:
                return {
                    "command": "suggest",
                    "bug_id": bug_id,
                    "fixes": [],
                    "message": "No fixes available for this bug"
                }
            
            return {
                "command": "suggest",
                "bug_id": bug_id,
                "fixes": [
                    {
                        "fix_id": f.fix_id,
                        "description": f.fix_description,
                        "safety_score": f.safety_score,
                        "impact": f.impact_assessment,
                        "code_diff": f.code_diff[:500] + "..." if len(f.code_diff) > 500 else f.code_diff
                    }
                    for f in fixes
                ],
                "status": "success"
            }
        
        except Exception as e:
            return {"error": str(e), "command": "suggest"}
    
    async def _handle_rollback(
        self,
        workflow_id: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Rollback changes."""
        fix_id = parameters.get('fix_id')
        
        if not fix_id:
            return {"error": "fix_id parameter required"}
        
        return {
            "command": "rollback",
            "fix_id": fix_id,
            "status": "pending",
            "message": f"Rollback initiated for fix {fix_id}",
            "note": "Rollback requires manual confirmation and git access"
        }
    
    async def _handle_status(
        self,
        workflow_id: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check workflow status."""
        try:
            state = await self.state_store.load_state(workflow_id)
            
            return {
                "command": "status",
                "workflow_id": workflow_id,
                "status": state.status,
                "current_agent": state.current_agent,
                "bugs_found": len(state.bugs),
                "tests_generated": len(state.test_cases),
                "tests_executed": len(state.test_results),
                "root_causes_found": len(state.root_causes),
                "fixes_suggested": len(state.fix_suggestions),
                "created_at": state.created_at.isoformat(),
                "updated_at": state.updated_at.isoformat()
            }
        
        except Exception as e:
            return {"error": str(e), "command": "status"}
    
    async def _handle_list(
        self,
        workflow_id: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """List bugs or workflows."""
        list_type = parameters.get('type', 'bugs')  # bugs, fixes, workflows
        limit = parameters.get('limit', 10)
        
        try:
            state = await self.state_store.load_state(workflow_id)
            
            if list_type == 'bugs':
                items = [
                    {
                        "bug_id": b.bug_id,
                        "file": b.file_path,
                        "line": b.line_number,
                        "severity": b.severity,
                        "description": b.description[:100]
                    }
                    for b in state.bugs[:limit]
                ]
            elif list_type == 'fixes':
                items = [
                    {
                        "fix_id": f.fix_id,
                        "bug_id": f.bug_id,
                        "safety_score": f.safety_score,
                        "description": f.fix_description[:100]
                    }
                    for f in state.fix_suggestions[:limit]
                ]
            else:
                items = []
            
            return {
                "command": "list",
                "type": list_type,
                "items": items,
                "total": len(items),
                "status": "success"
            }
        
        except Exception as e:
            return {"error": str(e), "command": "list"}
    
    async def _handle_export(
        self,
        workflow_id: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Export results."""
        export_format = parameters.get('format', 'json')  # json, csv, pdf
        
        return {
            "command": "export",
            "workflow_id": workflow_id,
            "format": export_format,
            "status": "pending",
            "message": f"Export to {export_format} initiated",
            "note": "Use /api/workflows/{workflow_id}/export endpoint"
        }
    
    async def _handle_filter(
        self,
        workflow_id: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Filter bugs by criteria."""
        severity = parameters.get('severity')
        min_confidence = parameters.get('min_confidence', 0.0)
        
        try:
            state = await self.state_store.load_state(workflow_id)
            
            filtered_bugs = [
                b for b in state.bugs
                if (not severity or b.severity == severity) and
                   b.confidence_score >= min_confidence
            ]
            
            return {
                "command": "filter",
                "criteria": {
                    "severity": severity,
                    "min_confidence": min_confidence
                },
                "results": len(filtered_bugs),
                "bugs": [
                    {
                        "bug_id": b.bug_id,
                        "severity": b.severity,
                        "confidence": b.confidence_score,
                        "description": b.description[:100]
                    }
                    for b in filtered_bugs[:10]
                ],
                "status": "success"
            }
        
        except Exception as e:
            return {"error": str(e), "command": "filter"}
    
    async def _handle_compare(
        self,
        workflow_id: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare bugs or fixes."""
        item_ids = parameters.get('item_ids', [])
        
        return {
            "command": "compare",
            "item_ids": item_ids,
            "status": "pending",
            "message": "Comparison initiated",
            "note": "Provide 2 or more item IDs to compare"
        }
    
    async def _handle_apply(
        self,
        workflow_id: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply a fix."""
        fix_id = parameters.get('fix_id')
        
        if not fix_id:
            return {"error": "fix_id parameter required"}
        
        return {
            "command": "apply",
            "fix_id": fix_id,
            "status": "pending",
            "message": f"Fix application initiated for {fix_id}",
            "note": "Requires git repository access and user confirmation"
        }
    
    def _handle_help(self) -> Dict[str, Any]:
        """Show help information."""
        return {
            "command": "help",
            "available_commands": {
                "analyze": "Analyze a specific bug - analyze bug_id=<id>",
                "suggest": "Get fix suggestions - suggest bug_id=<id>",
                "rollback": "Rollback changes - rollback fix_id=<id>",
                "status": "Check workflow status - status",
                "list": "List bugs/fixes - list type=bugs|fixes",
                "export": "Export results - export format=json|csv",
                "filter": "Filter bugs - filter severity=critical|high|medium|low",
                "compare": "Compare items - compare item_ids=<id1>,<id2>",
                "apply": "Apply fix - apply fix_id=<id>",
                "help": "Show this help message"
            },
            "voice_commands": {
                "analyze": "Say 'analyze' or 'explain'",
                "suggest": "Say 'suggest' or 'fix'",
                "rollback": "Say 'rollback' or 'undo'",
                "status": "Say 'status' or 'progress'",
                "list": "Say 'list' or 'show all'",
                "help": "Say 'help' or 'what can you do'"
            }
        }
    
    def get_available_commands(self) -> List[str]:
        """Get list of available commands."""
        return [cmd.value for cmd in CommandType]

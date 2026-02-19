"""
Export utilities for CloudForge Bug Intelligence.

Provides functions to export bug reports and workflow data in various formats
(JSON, CSV) for external analysis and reporting.
"""

import json
import csv
from io import StringIO
from typing import List, Dict, Any
from datetime import datetime

from cloudforge.models.state import BugReport, FixSuggestion, AgentState


def export_bugs_to_json(bugs: List[BugReport], pretty: bool = True) -> str:
    """
    Export bug reports to JSON format.
    
    Args:
        bugs: List of BugReport objects to export
        pretty: If True, format JSON with indentation for readability
        
    Returns:
        JSON string containing all bug reports
    """
    bugs_data = [bug.model_dump(mode="json") for bug in bugs]
    
    if pretty:
        return json.dumps(bugs_data, indent=2, default=str)
    return json.dumps(bugs_data, default=str)


def export_bugs_to_csv(bugs: List[BugReport]) -> str:
    """
    Export bug reports to CSV format.
    
    Args:
        bugs: List of BugReport objects to export
        
    Returns:
        CSV string containing all bug reports
    """
    if not bugs:
        return "bug_id,file_path,line_number,severity,description,confidence_score\n"
    
    output = StringIO()
    fieldnames = [
        "bug_id",
        "file_path",
        "line_number",
        "severity",
        "description",
        "code_snippet",
        "confidence_score"
    ]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for bug in bugs:
        bug_dict = bug.model_dump()
        # Escape newlines in code_snippet and description for CSV
        bug_dict["code_snippet"] = bug_dict["code_snippet"].replace("\n", "\\n")
        bug_dict["description"] = bug_dict["description"].replace("\n", " ")
        writer.writerow(bug_dict)
    
    return output.getvalue()


def export_fixes_to_json(fixes: List[FixSuggestion], pretty: bool = True) -> str:
    """
    Export fix suggestions to JSON format.
    
    Args:
        fixes: List of FixSuggestion objects to export
        pretty: If True, format JSON with indentation for readability
        
    Returns:
        JSON string containing all fix suggestions
    """
    fixes_data = [fix.model_dump(mode="json") for fix in fixes]
    
    if pretty:
        return json.dumps(fixes_data, indent=2, default=str)
    return json.dumps(fixes_data, default=str)


def export_fixes_to_csv(fixes: List[FixSuggestion]) -> str:
    """
    Export fix suggestions to CSV format.
    
    Args:
        fixes: List of FixSuggestion objects to export
        
    Returns:
        CSV string containing all fix suggestions
    """
    if not fixes:
        return "bug_id,fix_description,safety_score,impact_assessment\n"
    
    output = StringIO()
    fieldnames = [
        "bug_id",
        "fix_description",
        "code_diff",
        "safety_score",
        "impact_assessment"
    ]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for fix in fixes:
        fix_dict = fix.model_dump()
        # Escape newlines for CSV
        fix_dict["fix_description"] = fix_dict["fix_description"].replace("\n", " ")
        fix_dict["code_diff"] = fix_dict["code_diff"].replace("\n", "\\n")
        fix_dict["impact_assessment"] = fix_dict["impact_assessment"].replace("\n", " ")
        writer.writerow(fix_dict)
    
    return output.getvalue()


def export_workflow_summary_to_json(state: AgentState, pretty: bool = True) -> str:
    """
    Export complete workflow summary to JSON format.
    
    Args:
        state: AgentState object containing complete workflow data
        pretty: If True, format JSON with indentation for readability
        
    Returns:
        JSON string containing workflow summary
    """
    summary = {
        "workflow_id": state.workflow_id,
        "repository_url": state.repository_url,
        "status": state.status,
        "created_at": state.created_at.isoformat() if isinstance(state.created_at, datetime) else state.created_at,
        "updated_at": state.updated_at.isoformat() if isinstance(state.updated_at, datetime) else state.updated_at,
        "summary": {
            "bugs_found": len(state.bugs),
            "tests_generated": len(state.test_cases),
            "tests_executed": len(state.test_results),
            "root_causes_identified": len(state.root_causes),
            "fixes_suggested": len(state.fix_suggestions),
            "errors_encountered": len(state.errors)
        },
        "bugs": [bug.model_dump(mode="json") for bug in state.bugs],
        "test_cases": [tc.model_dump(mode="json") for tc in state.test_cases],
        "test_results": [tr.model_dump(mode="json") for tr in state.test_results],
        "root_causes": [rc.model_dump(mode="json") for rc in state.root_causes],
        "fix_suggestions": [fs.model_dump(mode="json") for fs in state.fix_suggestions],
        "errors": state.errors
    }
    
    if pretty:
        return json.dumps(summary, indent=2, default=str)
    return json.dumps(summary, default=str)

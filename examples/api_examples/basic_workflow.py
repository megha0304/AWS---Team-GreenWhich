#!/usr/bin/env python3
"""
Basic CloudForge Bug Intelligence workflow example.

This script demonstrates:
1. Creating a new workflow
2. Polling for completion
3. Retrieving bugs and fixes
4. Exporting results

Usage:
    python basic_workflow.py
"""

import requests
import time
import json
import sys
from typing import Dict, Any

# Configuration
API_BASE = "http://localhost:8000"
API_KEY = "your-api-key-here"  # Replace with your actual API key

# Request headers
HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}


def create_workflow(repository_url: str, branch: str = "main") -> Dict[str, Any]:
    """Create a new bug detection workflow."""
    print(f"Creating workflow for {repository_url}...")
    
    response = requests.post(
        f"{API_BASE}/workflows",
        headers=HEADERS,
        json={
            "repository_url": repository_url,
            "branch": branch,
            "scan_options": {
                "severity_filter": ["critical", "high", "medium"],
                "file_patterns": ["*.py", "*.js", "*.java", "*.go"]
            }
        }
    )
    
    if response.status_code == 201:
        workflow = response.json()
        print(f"✓ Workflow created: {workflow['workflow_id']}")
        return workflow
    else:
        print(f"✗ Failed to create workflow: {response.status_code}")
        print(response.json())
        sys.exit(1)


def wait_for_completion(workflow_id: str, max_wait: int = 3600) -> str:
    """
    Wait for workflow to complete with exponential backoff.
    
    Args:
        workflow_id: The workflow ID to monitor
        max_wait: Maximum time to wait in seconds (default: 1 hour)
    
    Returns:
        Final workflow status ('completed' or 'failed')
    """
    print(f"Waiting for workflow {workflow_id} to complete...")
    
    delay = 5  # Start with 5 seconds
    max_delay = 60  # Cap at 60 seconds
    elapsed = 0
    
    while elapsed < max_wait:
        response = requests.get(
            f"{API_BASE}/workflows/{workflow_id}",
            headers=HEADERS
        )
        
        if response.status_code != 200:
            print(f"✗ Failed to get workflow status: {response.status_code}")
            sys.exit(1)
        
        workflow = response.json()
        status = workflow["status"]
        current_agent = workflow.get("current_agent", "unknown")
        
        print(f"  Status: {status} | Agent: {current_agent} | Elapsed: {elapsed}s")
        
        if status == "completed":
            print(f"✓ Workflow completed successfully!")
            return status
        elif status == "failed":
            print(f"✗ Workflow failed!")
            errors = workflow.get("errors", [])
            for error in errors:
                print(f"  Error: {error}")
            return status
        
        # Exponential backoff
        time.sleep(delay)
        elapsed += delay
        delay = min(delay * 1.5, max_delay)
    
    print(f"✗ Workflow did not complete within {max_wait}s")
    sys.exit(1)


def get_bugs(workflow_id: str) -> list:
    """Retrieve all bugs detected for a workflow."""
    print(f"Retrieving bugs for workflow {workflow_id}...")
    
    response = requests.get(
        f"{API_BASE}/workflows/{workflow_id}/bugs",
        headers=HEADERS
    )
    
    if response.status_code == 200:
        bugs = response.json()
        print(f"✓ Found {len(bugs)} bugs")
        return bugs
    else:
        print(f"✗ Failed to retrieve bugs: {response.status_code}")
        return []


def get_fixes(workflow_id: str) -> list:
    """Retrieve all fix suggestions for a workflow."""
    print(f"Retrieving fixes for workflow {workflow_id}...")
    
    response = requests.get(
        f"{API_BASE}/workflows/{workflow_id}/fixes",
        headers=HEADERS
    )
    
    if response.status_code == 200:
        fixes = response.json()
        print(f"✓ Found {len(fixes)} fix suggestions")
        return fixes
    else:
        print(f"✗ Failed to retrieve fixes: {response.status_code}")
        return []


def export_results(workflow_id: str, output_file: str = "workflow_results.json"):
    """Export complete workflow results to a file."""
    print(f"Exporting workflow results to {output_file}...")
    
    response = requests.get(
        f"{API_BASE}/workflows/{workflow_id}/export",
        headers=HEADERS
    )
    
    if response.status_code == 200:
        with open(output_file, "w") as f:
            f.write(response.text)
        print(f"✓ Results exported to {output_file}")
    else:
        print(f"✗ Failed to export results: {response.status_code}")


def print_bug_summary(bugs: list):
    """Print a summary of detected bugs."""
    if not bugs:
        print("\nNo bugs detected!")
        return
    
    print("\n" + "="*80)
    print("BUG SUMMARY")
    print("="*80)
    
    # Group by severity
    by_severity = {}
    for bug in bugs:
        severity = bug.get("severity", "unknown")
        by_severity.setdefault(severity, []).append(bug)
    
    # Print summary by severity
    for severity in ["critical", "high", "medium", "low"]:
        if severity in by_severity:
            count = len(by_severity[severity])
            print(f"\n{severity.upper()}: {count} bugs")
            
            for bug in by_severity[severity][:3]:  # Show first 3
                print(f"  • {bug['file_path']}:{bug['line_number']}")
                print(f"    {bug['description']}")
            
            if count > 3:
                print(f"  ... and {count - 3} more")


def print_fix_summary(fixes: list):
    """Print a summary of fix suggestions."""
    if not fixes:
        print("\nNo fix suggestions generated!")
        return
    
    print("\n" + "="*80)
    print("FIX SUGGESTIONS")
    print("="*80)
    
    for i, fix in enumerate(fixes[:5], 1):  # Show first 5
        print(f"\n{i}. {fix['description']}")
        print(f"   File: {fix['file_path']}")
        print(f"   Safety Score: {fix['safety_score']:.2f}")
        print(f"   Impact Score: {fix['impact_score']:.2f}")
    
    if len(fixes) > 5:
        print(f"\n... and {len(fixes) - 5} more fix suggestions")


def main():
    """Main workflow execution."""
    print("="*80)
    print("CloudForge Bug Intelligence - Basic Workflow Example")
    print("="*80)
    
    # Example repository (replace with your own)
    repository_url = "https://github.com/example/sample-repo.git"
    
    # Step 1: Create workflow
    workflow = create_workflow(repository_url)
    workflow_id = workflow["workflow_id"]
    
    # Step 2: Wait for completion
    status = wait_for_completion(workflow_id)
    
    if status != "completed":
        print("\nWorkflow did not complete successfully. Exiting.")
        sys.exit(1)
    
    # Step 3: Get bugs
    bugs = get_bugs(workflow_id)
    print_bug_summary(bugs)
    
    # Step 4: Get fixes
    fixes = get_fixes(workflow_id)
    print_fix_summary(fixes)
    
    # Step 5: Export results
    export_results(workflow_id, f"results_{workflow_id}.json")
    
    print("\n" + "="*80)
    print("Workflow completed successfully!")
    print(f"Results saved to: results_{workflow_id}.json")
    print("="*80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nWorkflow interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

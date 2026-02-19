#!/usr/bin/env python3
"""
Security-focused bug detection workflow.

This example demonstrates how to configure CloudForge to focus on
security vulnerabilities like SQL injection, XSS, command injection, etc.
"""

import requests
import sys

API_BASE = "http://localhost:8000"
API_KEY = "your-api-key-here"

HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}


def run_security_scan(repository_url: str):
    """Run a security-focused scan on a repository."""
    print("Starting security vulnerability scan...")
    
    # Create workflow with security focus
    response = requests.post(
        f"{API_BASE}/workflows",
        headers=HEADERS,
        json={
            "repository_url": repository_url,
            "branch": "main",
            "scan_options": {
                # Focus on critical security issues only
                "severity_filter": ["critical"],
                "file_patterns": ["*.py", "*.js", "*.java", "*.php"],
                "exclude_patterns": ["tests/*", "*.test.*"]
            }
        }
    )
    
    if response.status_code == 201:
        workflow = response.json()
        workflow_id = workflow["workflow_id"]
        print(f"Security scan started: {workflow_id}")
        return workflow_id
    else:
        print(f"Failed to start scan: {response.status_code}")
        sys.exit(1)


if __name__ == "__main__":
    repo = "https://github.com/example/repo.git"
    run_security_scan(repo)

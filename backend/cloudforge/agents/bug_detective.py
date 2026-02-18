"""
Bug Detective Agent - Scans code repositories for potential bugs using AWS Bedrock.

This agent uses AWS Bedrock with Claude to analyze code semantics and identify bugs.

REQUIRED AWS BEDROCK SETUP:
===========================
1. AWS Credentials (one of the following):
   - Environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN (optional)
   - AWS CLI profile: Configure via `aws configure` or set AWS_PROFILE environment variable
   - IAM role (if running on EC2/ECS/Lambda)

2. Bedrock Model Access:
   - Go to AWS Console > Bedrock > Model access
   - Request access to: anthropic.claude-3-sonnet-20240229-v1:0
   - Wait for approval (usually instant for Claude models)

3. IAM Permissions Required:
   - bedrock:InvokeModel
   - bedrock:InvokeModelWithResponseStream (optional, for streaming)

4. Configuration (set in environment or SystemConfig):
   - AWS_REGION: AWS region (default: us-east-1)
   - BEDROCK_MODEL_ID: Model to use (default: anthropic.claude-3-sonnet-20240229-v1:0)
   - BEDROCK_ENDPOINT_URL: Custom endpoint (optional, for VPC endpoints)

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6
"""

import logging
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from uuid import uuid4

from cloudforge.models.state import AgentState, BugReport
from cloudforge.models.config import SystemConfig
from cloudforge.utils.retry import retry_with_backoff

logger = logging.getLogger(__name__)


class BugDetectiveAgent:
    """
    Agent responsible for scanning code repositories and detecting bugs.
    
    Uses AWS Bedrock with Claude to analyze code semantics and identify potential bugs.
    Implements batching for large repositories and exponential backoff for API calls.
    
    Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6
    """
    
    def __init__(self, bedrock_client: Any, config: SystemConfig):
        """
        Initialize Bug Detective Agent.
        
        Args:
            bedrock_client: Boto3 Bedrock Runtime client
                           Get via: config.get_bedrock_client()
            config: System configuration with AWS and agent settings
        
        Example:
            >>> config = SystemConfig.load_config()
            >>> bedrock_client = config.get_bedrock_client()
            >>> agent = BugDetectiveAgent(bedrock_client, config)
        """
        self.bedrock_client = bedrock_client
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.model_id = config.bedrock_model_id
        self.max_retries = config.max_retries
        self.batch_size = config.max_files_per_batch
        
        self.logger.info(
            f"Initialized BugDetectiveAgent with model {self.model_id}",
            extra={
                "model_id": self.model_id,
                "batch_size": self.batch_size,
                "max_retries": self.max_retries
            }
        )
    
    async def detect_bugs(self, state: AgentState) -> AgentState:
        """
        Scan repository and detect bugs.
        
        This is the main entry point for the Bug Detective Agent. It scans all
        source files in the repository and populates the state with detected bugs.
        
        Args:
            state: Current workflow state with repository_path set
        
        Returns:
            Updated state with bugs list populated
        
        Raises:
            ValueError: If repository_path is not set or doesn't exist
            Exception: If bug detection fails after retries
        
        Requirements: 1.1, 1.2, 1.3, 1.4
        """
        self.logger.info(
            f"Starting bug detection for workflow {state.workflow_id}",
            extra={
                "workflow_id": state.workflow_id,
                "repository_path": state.repository_path
            }
        )
        
        # Validate repository path
        repo_path = Path(state.repository_path)
        if not repo_path.exists():
            error_msg = f"Repository path does not exist: {state.repository_path}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Get all source files
        source_files = self._get_source_files(repo_path)
        total_files = len(source_files)
        
        self.logger.info(
            f"Found {total_files} source files to scan",
            extra={
                "workflow_id": state.workflow_id,
                "total_files": total_files
            }
        )
        
        # Check if we need batching (>10,000 files)
        if total_files > 10000:
            self.logger.info(
                f"Large repository detected ({total_files} files), using batch processing",
                extra={"workflow_id": state.workflow_id, "total_files": total_files}
            )
            bugs = await self._batch_scan(source_files, state.workflow_id)
        else:
            # Scan all files
            bugs = []
            for file_path in source_files:
                try:
                    file_bugs = await self._scan_file(file_path, repo_path)
                    bugs.extend(file_bugs)
                except Exception as e:
                    self.logger.warning(
                        f"Failed to scan file {file_path}: {e}",
                        extra={
                            "workflow_id": state.workflow_id,
                            "file_path": str(file_path),
                            "error": str(e)
                        }
                    )
                    # Continue with other files
                    continue
        
        # Update state with detected bugs
        state.bugs = bugs
        state.current_agent = "bug_detective"
        
        self.logger.info(
            f"Bug detection complete: found {len(bugs)} bugs",
            extra={
                "workflow_id": state.workflow_id,
                "bugs_found": len(bugs),
                "files_scanned": total_files
            }
        )
        
        return state
    
    def _get_source_files(self, repo_path: Path) -> List[Path]:
        """
        Get all source code files from repository.
        
        Filters for common source code extensions and excludes common
        non-source directories.
        
        Args:
            repo_path: Path to repository root
        
        Returns:
            List of source file paths
        
        Requirements: 1.1
        """
        # Common source code extensions
        source_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx',  # Python, JavaScript, TypeScript
            '.java', '.kt', '.scala',  # JVM languages
            '.go', '.rs', '.c', '.cpp', '.h', '.hpp',  # Systems languages
            '.rb', '.php', '.swift', '.m',  # Other languages
            '.cs', '.fs', '.vb',  # .NET languages
        }
        
        # Directories to exclude
        exclude_dirs = {
            'node_modules', '.git', '__pycache__', '.pytest_cache',
            'venv', 'env', '.venv', 'dist', 'build', 'target',
            '.next', '.nuxt', 'coverage', '.coverage'
        }
        
        source_files = []
        
        for file_path in repo_path.rglob('*'):
            # Skip if not a file
            if not file_path.is_file():
                continue
            
            # Skip if in excluded directory
            if any(excluded in file_path.parts for excluded in exclude_dirs):
                continue
            
            # Check if source file
            if file_path.suffix.lower() in source_extensions:
                source_files.append(file_path)
        
        return source_files
    
    async def _scan_file(self, file_path: Path, repo_root: Path) -> List[BugReport]:
        """
        Scan a single file for bugs using Bedrock.
        
        This method calls AWS Bedrock to analyze the file content and identify bugs.
        Implements exponential backoff retry logic for transient failures.
        
        Args:
            file_path: Path to file to scan
            repo_root: Repository root path (for relative paths)
        
        Returns:
            List of bug reports found in the file
        
        Requirements: 1.2, 1.3, 1.4, 1.6
        """
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                code_content = f.read()
            
            # Get relative path for reporting
            relative_path = file_path.relative_to(repo_root)
            
            # Call Bedrock with retry logic
            bugs = await retry_with_backoff(
                self._call_bedrock_for_bugs,
                str(relative_path),
                code_content,
                max_retries=self.max_retries,
                base_delay=2.0
            )
            
            return bugs
            
        except Exception as e:
            self.logger.error(
                f"Error scanning file {file_path}: {e}",
                extra={
                    "file_path": str(file_path),
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            )
            raise
    
    async def _call_bedrock_for_bugs(
        self,
        file_path: str,
        code_content: str
    ) -> List[BugReport]:
        """
        Call AWS Bedrock API to analyze code and detect bugs.
        
        ⚠️  USER ACTION REQUIRED ⚠️
        ================================
        This method contains placeholder logic. To use real AWS Bedrock:
        
        1. Ensure you have AWS credentials configured (see module docstring)
        2. Request access to Claude model in AWS Bedrock console
        3. Uncomment the Bedrock API call code below
        4. Remove or modify the placeholder return statement
        
        The placeholder currently returns mock bugs for testing.
        
        Args:
            file_path: Relative path to file being analyzed
            code_content: Content of the code file
        
        Returns:
            List of detected bugs
        
        Requirements: 1.2, 1.3, 1.4
        """
        # Construct prompt for Claude
        prompt = f"""Analyze the following code file for potential bugs, security issues, and code quality problems.

File: {file_path}

Code:
```
{code_content[:5000]}  # Limit to first 5000 chars to manage token usage
```

For each bug found, provide:
1. Line number (approximate)
2. Severity (critical, high, medium, low)
3. Description of the bug
4. Code snippet showing the issue

Format your response as JSON array of bugs."""

        # ============================================================================
        # PLACEHOLDER: Replace this section with actual Bedrock API call
        # ============================================================================
        # TODO: Uncomment and configure the following code when ready to use Bedrock
        
        """
        import json
        
        # Prepare request for Claude via Bedrock
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,  # Low temperature for consistent analysis
        }
        
        # Call Bedrock
        response = self.bedrock_client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json"
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        claude_response = response_body['content'][0]['text']
        
        # Parse bugs from Claude's response
        # (You'll need to implement parsing logic based on Claude's output format)
        bugs_data = json.loads(claude_response)
        """
        
        # PLACEHOLDER: Mock response for testing
        # Remove this when implementing real Bedrock integration
        self.logger.warning(
            f"Using placeholder bug detection for {file_path}. "
            "Configure AWS Bedrock credentials to use real detection."
        )
        
        # Return empty list for now (no bugs detected in placeholder mode)
        # In real implementation, this would return parsed bugs from Claude
        bugs = []
        
        # Example of how bugs would be created from Bedrock response:
        # for bug_data in bugs_data:
        #     bug = BugReport(
        #         bug_id=str(uuid4()),
        #         file_path=file_path,
        #         line_number=bug_data['line_number'],
        #         severity=bug_data['severity'],
        #         description=bug_data['description'],
        #         code_snippet=self._extract_code_snippet(
        #             code_content,
        #             bug_data['line_number']
        #         ),
        #         confidence_score=bug_data.get('confidence', 0.8)
        #     )
        #     bugs.append(bug)
        
        return bugs
    
    async def _batch_scan(
        self,
        file_paths: List[Path],
        workflow_id: str
    ) -> List[BugReport]:
        """
        Scan multiple files in batches to manage API costs.
        
        For repositories with >10,000 files, this method processes files in
        batches to avoid excessive API calls and costs.
        
        Args:
            file_paths: List of file paths to scan
            workflow_id: Workflow ID for logging
        
        Returns:
            List of all detected bugs across all files
        
        Requirements: 1.5
        """
        all_bugs = []
        total_files = len(file_paths)
        
        # Process in batches
        for i in range(0, total_files, self.batch_size):
            batch = file_paths[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (total_files + self.batch_size - 1) // self.batch_size
            
            self.logger.info(
                f"Processing batch {batch_num}/{total_batches}",
                extra={
                    "workflow_id": workflow_id,
                    "batch_num": batch_num,
                    "total_batches": total_batches,
                    "batch_size": len(batch)
                }
            )
            
            # Scan files in batch
            for file_path in batch:
                try:
                    # Get repo root from first file
                    repo_root = file_path.parents[len(file_path.parents) - 2]
                    file_bugs = await self._scan_file(file_path, repo_root)
                    all_bugs.extend(file_bugs)
                except Exception as e:
                    self.logger.warning(
                        f"Failed to scan file in batch: {file_path}",
                        extra={
                            "workflow_id": workflow_id,
                            "file_path": str(file_path),
                            "error": str(e)
                        }
                    )
                    continue
        
        return all_bugs
    
    def _extract_code_snippet(
        self,
        code_content: str,
        line_number: int,
        context_lines: int = 5
    ) -> str:
        """
        Extract code snippet with context around the bug line.
        
        Extracts ±5 lines of context around the specified line number.
        
        Args:
            code_content: Full file content
            line_number: Line number where bug is located
            context_lines: Number of lines to include before/after (default: 5)
        
        Returns:
            Code snippet with context
        
        Requirements: 1.4
        """
        lines = code_content.split('\n')
        
        # Calculate range (1-indexed to 0-indexed)
        start = max(0, line_number - context_lines - 1)
        end = min(len(lines), line_number + context_lines)
        
        # Extract snippet
        snippet_lines = lines[start:end]
        
        # Add line numbers
        numbered_lines = []
        for i, line in enumerate(snippet_lines, start=start + 1):
            marker = ">>>" if i == line_number else "   "
            numbered_lines.append(f"{marker} {i:4d} | {line}")
        
        return '\n'.join(numbered_lines)

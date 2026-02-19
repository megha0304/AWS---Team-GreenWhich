"""
AWS Bedrock Client Utility for CloudForge Bug Intelligence.

This module provides a high-level interface for interacting with AWS Bedrock
to perform code analysis, bug detection, and root cause analysis using Claude.

Requirements: AWS Bedrock access with Claude 3 Sonnet model
"""

import json
import logging
from typing import Dict, Any, List, Optional
import boto3
from botocore.exceptions import ClientError

from cloudforge.models.config import SystemConfig
from cloudforge.utils.retry import retry_with_backoff

logger = logging.getLogger(__name__)


class BedrockClient:
    """
    High-level client for AWS Bedrock interactions.
    
    Provides methods for:
    - Code analysis and bug detection
    - Root cause analysis
    - Fix suggestion generation
    
    Handles API calls, retries, and response parsing.
    """
    
    def __init__(self, config: SystemConfig):
        """
        Initialize Bedrock client.
        
        Args:
            config: System configuration with Bedrock settings
        """
        self.config = config
        self.model_id = config.bedrock_model_id
        self.max_retries = config.max_retries
        self.logger = logging.getLogger(__name__)
        
        # Initialize Bedrock Runtime client
        try:
            self.client = config.get_bedrock_client()
            self.logger.info(
                f"Initialized Bedrock client with model {self.model_id}",
                extra={
                    "model_id": self.model_id,
                    "region": config.bedrock_region
                }
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize Bedrock client: {e}")
            raise
    
    async def analyze_code_for_bugs(
        self,
        file_path: str,
        code_content: str,
        language: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Analyze code for potential bugs using Claude.
        
        Args:
            file_path: Path to the file being analyzed
            code_content: Content of the code file
            language: Programming language (auto-detected if None)
        
        Returns:
            List of detected bugs with structure:
            [
                {
                    "line_number": int,
                    "severity": str,  # critical, high, medium, low
                    "description": str,
                    "code_snippet": str,
                    "confidence": float  # 0.0-1.0
                }
            ]
        
        Raises:
            ClientError: If Bedrock API call fails
        """
        # Detect language from file extension if not provided
        if not language:
            language = self._detect_language(file_path)
        
        # Construct prompt for bug detection
        prompt = self._build_bug_detection_prompt(file_path, code_content, language)
        
        # Call Bedrock with retry logic
        try:
            response_text = await retry_with_backoff(
                lambda: self._invoke_claude(prompt, max_tokens=4096, temperature=0.1),
                max_retries=self.max_retries,
                base_delay=2.0
            )
            
            # Parse bugs from response
            bugs = self._parse_bug_detection_response(response_text)
            
            self.logger.info(
                f"Analyzed {file_path}: found {len(bugs)} potential bugs",
                extra={
                    "file_path": file_path,
                    "bugs_found": len(bugs),
                    "language": language
                }
            )
            
            return bugs
            
        except Exception as e:
            self.logger.error(
                f"Failed to analyze code for bugs: {e}",
                extra={
                    "file_path": file_path,
                    "error": str(e)
                }
            )
            raise
    
    async def analyze_root_cause(
        self,
        bug_description: str,
        code_snippet: str,
        test_output: str,
        file_path: str
    ) -> Dict[str, Any]:
        """
        Analyze test failure to identify root cause.
        
        Args:
            bug_description: Description of the bug
            code_snippet: Code snippet where bug occurs
            test_output: Test execution output (stdout/stderr)
            file_path: Path to file with bug
        
        Returns:
            Root cause analysis with structure:
            {
                "cause_description": str,
                "confidence_score": float,  # 0.0-1.0
                "causal_chain": str,
                "suggested_investigation": List[str]
            }
        
        Raises:
            ClientError: If Bedrock API call fails
        """
        # Construct prompt for root cause analysis
        prompt = self._build_root_cause_prompt(
            bug_description,
            code_snippet,
            test_output,
            file_path
        )
        
        # Call Bedrock with retry logic
        try:
            response_text = await retry_with_backoff(
                lambda: self._invoke_claude(prompt, max_tokens=2048, temperature=0.3),
                max_retries=self.max_retries,
                base_delay=2.0
            )
            
            # Parse root cause from response
            root_cause = self._parse_root_cause_response(response_text)
            
            self.logger.info(
                f"Root cause analysis complete for {file_path}",
                extra={
                    "file_path": file_path,
                    "confidence": root_cause.get("confidence_score", 0.0)
                }
            )
            
            return root_cause
            
        except Exception as e:
            self.logger.error(
                f"Failed to analyze root cause: {e}",
                extra={
                    "file_path": file_path,
                    "error": str(e)
                }
            )
            raise
    
    async def generate_fix_suggestion(
        self,
        bug_description: str,
        code_snippet: str,
        root_cause: str,
        file_path: str,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate fix suggestion for a bug.
        
        Args:
            bug_description: Description of the bug
            code_snippet: Code snippet where bug occurs
            root_cause: Root cause description
            file_path: Path to file with bug
            language: Programming language (auto-detected if None)
        
        Returns:
            Fix suggestion with structure:
            {
                "description": str,
                "code_diff": str,  # Unified diff format
                "safety_score": float,  # 0.0-1.0
                "impact_score": float,  # 0.0-1.0
                "explanation": str
            }
        
        Raises:
            ClientError: If Bedrock API call fails
        """
        # Detect language if not provided
        if not language:
            language = self._detect_language(file_path)
        
        # Construct prompt for fix generation
        prompt = self._build_fix_generation_prompt(
            bug_description,
            code_snippet,
            root_cause,
            file_path,
            language
        )
        
        # Call Bedrock with retry logic
        try:
            response_text = await retry_with_backoff(
                lambda: self._invoke_claude(prompt, max_tokens=3072, temperature=0.2),
                max_retries=self.max_retries,
                base_delay=2.0
            )
            
            # Parse fix suggestion from response
            fix_suggestion = self._parse_fix_suggestion_response(response_text)
            
            self.logger.info(
                f"Generated fix suggestion for {file_path}",
                extra={
                    "file_path": file_path,
                    "safety_score": fix_suggestion.get("safety_score", 0.0)
                }
            )
            
            return fix_suggestion
            
        except Exception as e:
            self.logger.error(
                f"Failed to generate fix suggestion: {e}",
                
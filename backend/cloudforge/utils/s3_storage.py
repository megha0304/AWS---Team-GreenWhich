"""
S3 Storage Utilities

Provides utilities for storing and retrieving artifacts from S3 with structured paths.
"""

import logging
from typing import List, Optional
import boto3
from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)


class S3Storage:
    """
    S3 storage manager for CloudForge artifacts.
    
    Implements structured path generation following the pattern:
    {artifact_type}/{workflow_id}/{item_id}.{extension}
    """
    
    def __init__(self, bucket_name: str, region: str = "us-east-1"):
        """
        Initialize S3 storage manager.
        
        Args:
            bucket_name: Name of the S3 bucket
            region: AWS region
        """
        self.bucket_name = bucket_name
        self.region = region
        self.s3_client = boto3.client("s3", region_name=region)
        logger.info(f"Initialized S3Storage with bucket: {bucket_name}")
    
    def _generate_path(
        self,
        artifact_type: str,
        workflow_id: str,
        item_id: str,
        extension: str = ""
    ) -> str:
        """
        Generate structured S3 path.
        
        Args:
            artifact_type: Type of artifact (repositories, test-results, analysis-reports, fix-patches)
            workflow_id: Workflow identifier
            item_id: Item identifier
            extension: File extension (optional)
        
        Returns:
            Structured S3 path
        """
        if extension and not extension.startswith("."):
            extension = f".{extension}"
        
        return f"{artifact_type}/{workflow_id}/{item_id}{extension}"
    
    def upload_artifact(
        self,
        artifact_type: str,
        workflow_id: str,
        item_id: str,
        content: bytes,
        extension: str = "",
        content_type: Optional[str] = None
    ) -> str:
        """
        Upload artifact to S3.
        
        Args:
            artifact_type: Type of artifact
            workflow_id: Workflow identifier
            item_id: Item identifier
            content: File content as bytes
            extension: File extension
            content_type: MIME type (optional)
        
        Returns:
            S3 key of uploaded artifact
        
        Raises:
            ClientError: If upload fails
        """
        key = self._generate_path(artifact_type, workflow_id, item_id, extension)
        
        try:
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=content,
                **extra_args
            )
            
            logger.info(f"Uploaded artifact to s3://{self.bucket_name}/{key}")
            return key
        
        except ClientError as e:
            logger.error(f"Failed to upload artifact to S3: {e}")
            raise
    
    def download_artifact(
        self,
        artifact_type: str,
        workflow_id: str,
        item_id: str,
        extension: str = ""
    ) -> bytes:
        """
        Download artifact from S3.
        
        Args:
            artifact_type: Type of artifact
            workflow_id: Workflow identifier
            item_id: Item identifier
            extension: File extension
        
        Returns:
            File content as bytes
        
        Raises:
            ClientError: If download fails
        """
        key = self._generate_path(artifact_type, workflow_id, item_id, extension)
        
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            content = response["Body"].read()
            logger.info(f"Downloaded artifact from s3://{self.bucket_name}/{key}")
            return content
        
        except ClientError as e:
            logger.error(f"Failed to download artifact from S3: {e}")
            raise
    
    def list_artifacts(
        self,
        artifact_type: str,
        workflow_id: Optional[str] = None,
        max_keys: int = 1000
    ) -> List[str]:
        """
        List artifacts with prefix filtering.
        
        Args:
            artifact_type: Type of artifact
            workflow_id: Workflow identifier (optional, filters by workflow)
            max_keys: Maximum number of keys to return
        
        Returns:
            List of S3 keys
        
        Raises:
            ClientError: If listing fails
        """
        if workflow_id:
            prefix = f"{artifact_type}/{workflow_id}/"
        else:
            prefix = f"{artifact_type}/"
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            keys = []
            if "Contents" in response:
                keys = [obj["Key"] for obj in response["Contents"]]
            
            logger.info(f"Listed {len(keys)} artifacts with prefix: {prefix}")
            return keys
        
        except ClientError as e:
            logger.error(f"Failed to list artifacts from S3: {e}")
            raise
    
    def delete_artifact(
        self,
        artifact_type: str,
        workflow_id: str,
        item_id: str,
        extension: str = ""
    ) -> None:
        """
        Delete artifact from S3.
        
        Args:
            artifact_type: Type of artifact
            workflow_id: Workflow identifier
            item_id: Item identifier
            extension: File extension
        
        Raises:
            ClientError: If deletion fails
        """
        key = self._generate_path(artifact_type, workflow_id, item_id, extension)
        
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            logger.info(f"Deleted artifact from s3://{self.bucket_name}/{key}")
        
        except ClientError as e:
            logger.error(f"Failed to delete artifact from S3: {e}")
            raise
    
    def get_presigned_url(
        self,
        artifact_type: str,
        workflow_id: str,
        item_id: str,
        extension: str = "",
        expiration: int = 3600
    ) -> str:
        """
        Generate presigned URL for artifact download.
        
        Args:
            artifact_type: Type of artifact
            workflow_id: Workflow identifier
            item_id: Item identifier
            extension: File extension
            expiration: URL expiration time in seconds (default: 1 hour)
        
        Returns:
            Presigned URL
        
        Raises:
            ClientError: If URL generation fails
        """
        key = self._generate_path(artifact_type, workflow_id, item_id, extension)
        
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": key
                },
                ExpiresIn=expiration
            )
            
            logger.info(f"Generated presigned URL for s3://{self.bucket_name}/{key}")
            return url
        
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise

"""
API authentication middleware for CloudForge Bug Intelligence.

Provides API key authentication for all endpoints.
"""

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from typing import Optional
import os


# API key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_api_key_from_env() -> Optional[str]:
    """
    Get API key from environment variable.
    
    Returns:
        API key if set, None otherwise
    """
    return os.getenv("API_KEY") or os.getenv("CLOUDFORGE_API_KEY")


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Verify API key from request header.
    
    Args:
        api_key: API key from X-API-Key header
        
    Returns:
        Validated API key
        
    Raises:
        HTTPException: If API key is missing or invalid
    """
    # Get expected API key from environment
    expected_api_key = get_api_key_from_env()
    
    # If no API key is configured, allow all requests (development mode)
    if not expected_api_key:
        return "development-mode"
    
    # Check if API key was provided
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Verify API key matches
    if api_key != expected_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    
    return api_key

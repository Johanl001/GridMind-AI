"""
Security utilities for GridMind AI API.
"""
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from app.core.config import settings

# Define API key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key(api_key_header: str = Security(api_key_header)):
    """
    Validate API key from request header.

    Args:
        api_key_header: The API key from X-API-Key header

    Returns:
        str: The validated API key

    Raises:
        HTTPException: If API key is invalid or missing
    """
    if not api_key_header:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key is missing"
        )

    if api_key_header != settings.GRIDMIND_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )

    return api_key_header


# Optional dependency for endpoints that don't require auth
async def get_api_key_optional(api_key_header: str = Security(api_key_header)):
    """
    Optionally validate API key from request header.

    Args:
        api_key_header: The API key from X-API-Key header

    Returns:
        str or None: The API key if provided and valid, None otherwise
    """
    if not api_key_header:
        return None

    if api_key_header != settings.GRIDMIND_API_KEY:
        return None

    return api_key_header
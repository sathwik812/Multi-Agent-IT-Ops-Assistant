import os
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from loguru import logger

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(api_key: str = Security(api_key_header)):
    """
    Validates the API key provided in the X-API-Key header.
    Fails loudly if the server is missing the API_SECRET_KEY configuration.
    """
    expected_key = os.getenv("API_SECRET_KEY")
    if not expected_key:
        logger.critical("API_SECRET_KEY environment variable is not set. Rejecting requests to prevent unauthorized access.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error"
        )
        
    if not api_key or api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key"
        )
    return api_key
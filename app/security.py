import os

from fastapi import Header, HTTPException


def require_api_key(x_api_key: str | None = Header(default=None)):
    """Protects staff-only endpoints when API_KEY is set. Open in local dev if it isn't."""
    expected = os.getenv("API_KEY")
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")

"""
Simple authentication for dashboard and internal API.
"""

from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets

from .config import get_settings

settings = get_settings()
security = HTTPBasic()


def verify_dashboard_password(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """Verify dashboard password using HTTP Basic Auth."""
    correct_password = secrets.compare_digest(
        credentials.password.encode("utf8"),
        settings.dashboard_password.encode("utf8")
    )
    if not correct_password:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def verify_internal_key(request: Request) -> None:
    """Verify internal API key from header."""
    api_key = request.headers.get("X-Internal-Key")
    if not api_key or not secrets.compare_digest(
        api_key.encode("utf8"),
        settings.internal_api_key.encode("utf8")
    ):
        raise HTTPException(status_code=401, detail="Invalid internal API key")


async def require_auth(request: Request) -> str:
    """
    Flexible auth: accepts either HTTP Basic or session cookie.
    For dashboard pages.
    """
    # Check for session cookie first
    session_token = request.cookies.get("session_token")
    if session_token and secrets.compare_digest(
        session_token.encode("utf8"),
        settings.dashboard_password.encode("utf8")
    ):
        return "authenticated"

    # Fall back to basic auth
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Basic "):
        import base64
        try:
            credentials = base64.b64decode(auth_header[6:]).decode("utf8")
            username, password = credentials.split(":", 1)
            if secrets.compare_digest(password.encode("utf8"), settings.dashboard_password.encode("utf8")):
                return username
        except Exception:
            pass

    raise HTTPException(
        status_code=401,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Basic"},
    )

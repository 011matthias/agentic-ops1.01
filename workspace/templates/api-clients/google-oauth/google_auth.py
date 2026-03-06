#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "google-auth-oauthlib>=1.2.0",
#     "google-auth>=2.29.0",
# ]
# ///
"""
Shared Google OAuth Authentication Module

Provides OAuth 2.0 authentication for all Google APIs (Sheets, Drive, Docs, Calendar, etc.).
Designed for Railway deployments - outputs refresh_token for env vars.

Usage:
    from google_oauth import get_credentials, resolve_scopes, SCOPE_ALIASES
"""

import json
import os
from pathlib import Path
from typing import Optional

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    raise ImportError(
        "Missing dependencies. Install with:\n"
        "  pip install google-auth-oauthlib google-auth"
    )


# Paths - relative to this module
MODULE_DIR = Path(__file__).parent
CLIENT_SECRETS_FILE = MODULE_DIR / "client_secrets.json"
TOKEN_FILE = MODULE_DIR / "token.json"


# Scope aliases for convenience - covers all major Google products
SCOPE_ALIASES = {
    # Google Sheets
    "spreadsheets": "https://www.googleapis.com/auth/spreadsheets",
    "spreadsheets.readonly": "https://www.googleapis.com/auth/spreadsheets.readonly",
    # Google Drive
    "drive": "https://www.googleapis.com/auth/drive",
    "drive.readonly": "https://www.googleapis.com/auth/drive.readonly",
    "drive.file": "https://www.googleapis.com/auth/drive.file",
    # Google Docs
    "docs": "https://www.googleapis.com/auth/documents",
    "docs.readonly": "https://www.googleapis.com/auth/documents.readonly",
    # Google Calendar
    "calendar": "https://www.googleapis.com/auth/calendar",
    "calendar.readonly": "https://www.googleapis.com/auth/calendar.readonly",
    "calendar.events": "https://www.googleapis.com/auth/calendar.events",
    "calendar.events.readonly": "https://www.googleapis.com/auth/calendar.events.readonly",
    # Gmail
    "gmail.readonly": "https://www.googleapis.com/auth/gmail.readonly",
    "gmail.modify": "https://www.googleapis.com/auth/gmail.modify",
    "gmail.send": "https://www.googleapis.com/auth/gmail.send",
    # YouTube (for analytics/channel management)
    "youtube.readonly": "https://www.googleapis.com/auth/youtube.readonly",
    "youtube": "https://www.googleapis.com/auth/youtube",
    "yt-analytics.readonly": "https://www.googleapis.com/auth/yt-analytics.readonly",
}


def resolve_scopes(scopes: list[str]) -> list[str]:
    """
    Convert scope aliases to full URLs.

    Args:
        scopes: List of scope aliases (e.g., ['spreadsheets', 'drive.readonly'])

    Returns:
        List of full scope URLs
    """
    resolved = []
    for scope in scopes:
        if scope in SCOPE_ALIASES:
            resolved.append(SCOPE_ALIASES[scope])
        elif scope.startswith("https://"):
            resolved.append(scope)
        else:
            # Assume it's a partial scope name
            resolved.append(f"https://www.googleapis.com/auth/{scope}")
    return resolved


def get_scope_alias(full_url: str) -> str:
    """Get the alias for a full scope URL, or return the URL if no alias exists."""
    for alias, url in SCOPE_ALIASES.items():
        if url == full_url:
            return alias
    return full_url


def load_token() -> Optional[dict]:
    """Load token data from file."""
    if not TOKEN_FILE.exists():
        return None
    with open(TOKEN_FILE, "r") as f:
        return json.load(f)


def save_token(credentials: Credentials, scopes: list[str]) -> None:
    """Save credentials to token file."""
    MODULE_DIR.mkdir(parents=True, exist_ok=True)
    token_data = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": scopes,
    }
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)


def get_credentials(
    required_scopes: list[str],
    interactive: bool = True,
    client_secrets_file: Path | None = None,
) -> Credentials:
    """
    Get Google OAuth credentials with required scopes.

    Args:
        required_scopes: List of scope aliases or full URLs
        interactive: If True, run OAuth flow when needed
        client_secrets_file: Optional path to client_secrets.json

    Returns:
        Google OAuth Credentials object

    Raises:
        RuntimeError: If credentials cannot be obtained
    """
    required_scopes = resolve_scopes(required_scopes)
    secrets_file = client_secrets_file or CLIENT_SECRETS_FILE

    if not secrets_file.exists():
        raise RuntimeError(
            f"Client secrets not found at {secrets_file}\n\n"
            "To set up:\n"
            "1. Go to https://console.cloud.google.com\n"
            "2. Create a project and enable needed APIs\n"
            "3. Create OAuth 2.0 credentials (Desktop app)\n"
            "4. Download JSON and save as client_secrets.json"
        )

    token_data = load_token()
    credentials = None

    if token_data:
        existing_scopes = set(token_data.get("scopes", []))

        if set(required_scopes).issubset(existing_scopes):
            # We have all needed scopes
            credentials = Credentials(
                token=token_data["token"],
                refresh_token=token_data["refresh_token"],
                token_uri=token_data["token_uri"],
                client_id=token_data["client_id"],
                client_secret=token_data["client_secret"],
                scopes=list(existing_scopes),
            )

            # Refresh if expired
            if credentials.expired and credentials.refresh_token:
                try:
                    credentials.refresh(Request())
                    save_token(credentials, list(existing_scopes))
                except Exception as e:
                    print(f"Token refresh failed: {e}")
                    credentials = None
        else:
            # Need additional scopes
            missing = set(required_scopes) - existing_scopes
            if not interactive:
                missing_aliases = [get_scope_alias(s) for s in missing]
                raise RuntimeError(
                    f"Missing scopes: {missing_aliases}\n"
                    f"Run: uv run cli_setup.py --scopes {','.join(missing_aliases)}"
                )

            # Re-authorize with all scopes
            all_scopes = list(existing_scopes | set(required_scopes))
            print(f"Requesting additional scopes: {[get_scope_alias(s) for s in missing]}")
            credentials = run_oauth_flow(all_scopes, secrets_file)
            save_token(credentials, all_scopes)

    if credentials is None:
        if not interactive:
            raise RuntimeError(
                "No credentials found.\n"
                "Run: uv run cli_setup.py --scopes spreadsheets"
            )
        credentials = run_oauth_flow(required_scopes, secrets_file)
        save_token(credentials, required_scopes)

    return credentials


def run_oauth_flow(scopes: list[str], secrets_file: Path, port: int = 8080) -> Credentials:
    """
    Run interactive OAuth authorization flow.

    Opens browser for user consent, returns credentials with refresh_token.
    Uses access_type=offline and prompt=consent to ensure refresh_token is returned.
    """
    print("Starting OAuth authorization flow...")
    print("A browser window will open for you to authorize access.")

    flow = InstalledAppFlow.from_client_secrets_file(str(secrets_file), scopes=scopes)

    # Try multiple ports in case one is in use
    for try_port in [port, 8081, 8082, 8090, 9000]:
        try:
            credentials = flow.run_local_server(
                port=try_port,
                prompt="consent",  # Force consent to get refresh_token
                access_type="offline",  # Get refresh_token
                success_message="Authorization complete! You can close this window.",
            )
            return credentials
        except OSError as e:
            if e.errno == 48:  # Port in use
                print(f"Port {try_port} in use, trying next...")
                continue
            raise

    raise RuntimeError("All ports in use. Please close other applications and try again.")


def get_authorized_scopes() -> list[str]:
    """Get list of currently authorized scopes as aliases."""
    token_data = load_token()
    if not token_data:
        return []
    return [get_scope_alias(s) for s in token_data.get("scopes", [])]


def get_refresh_token() -> Optional[str]:
    """Get the current refresh token (for copying to Railway env vars)."""
    token_data = load_token()
    return token_data.get("refresh_token") if token_data else None


def credentials_from_refresh_token(
    client_id: str,
    client_secret: str,
    refresh_token: str,
    scopes: list[str] | None = None,
) -> Credentials:
    """
    Create credentials from a refresh token (for runtime use in automations).

    This is the primary way automations should get credentials - using env vars.

    Args:
        client_id: Google OAuth client ID
        client_secret: Google OAuth client secret
        refresh_token: The refresh token from OAuth setup
        scopes: Optional list of scopes (not strictly required for refresh)

    Returns:
        Credentials object ready for use with Google APIs
    """
    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=resolve_scopes(scopes) if scopes else None,
    )

    # Refresh to get a valid access token
    credentials.refresh(Request())
    return credentials


# Convenience functions for common use cases
def get_sheets_credentials(readonly: bool = False) -> Credentials:
    """Get credentials for Google Sheets."""
    scope = "spreadsheets.readonly" if readonly else "spreadsheets"
    return get_credentials([scope])


def get_drive_credentials(readonly: bool = True) -> Credentials:
    """Get credentials for Google Drive."""
    scope = "drive.readonly" if readonly else "drive"
    return get_credentials([scope])


def get_docs_credentials(readonly: bool = False) -> Credentials:
    """Get credentials for Google Docs (includes Drive for file operations)."""
    scope = "docs.readonly" if readonly else "docs"
    return get_credentials([scope, "drive.readonly"])


def get_calendar_credentials(readonly: bool = False) -> Credentials:
    """Get credentials for Google Calendar."""
    scope = "calendar.events.readonly" if readonly else "calendar.events"
    return get_credentials([scope])


if __name__ == "__main__":
    print("Google OAuth Module")
    print("=" * 50)
    print(f"Client secrets: {'Found' if CLIENT_SECRETS_FILE.exists() else 'NOT FOUND'}")
    print(f"Token file: {'Found' if TOKEN_FILE.exists() else 'NOT FOUND'}")

    scopes = get_authorized_scopes()
    if scopes:
        print(f"\nAuthorized scopes:")
        for scope in scopes:
            print(f"  - {scope}")

        refresh_token = get_refresh_token()
        if refresh_token:
            print(f"\nRefresh token (first 20 chars): {refresh_token[:20]}...")

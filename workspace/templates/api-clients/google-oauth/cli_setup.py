#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "google-auth-oauthlib>=1.2.0",
#     "google-auth>=2.29.0",
# ]
# ///
"""
Google OAuth CLI Setup

One-time setup for Google OAuth authentication. Outputs refresh_token for Railway env vars.

Usage:
    # Authorize for Sheets only
    uv run cli_setup.py --scopes spreadsheets

    # Authorize for Sheets + Drive (read-only)
    uv run cli_setup.py --scopes spreadsheets,drive.readonly

    # Authorize for multiple services
    uv run cli_setup.py --scopes spreadsheets,drive,docs,calendar

    # Check current status
    uv run cli_setup.py --status

    # Add more scopes to existing auth
    uv run cli_setup.py --add-scope drive

    # Force re-authentication
    uv run cli_setup.py --refresh --scopes spreadsheets

Available scope aliases:
    spreadsheets, spreadsheets.readonly
    drive, drive.readonly, drive.file
    docs, docs.readonly
    calendar, calendar.readonly, calendar.events
    gmail.readonly, gmail.modify, gmail.send
"""

import argparse
import sys
from pathlib import Path

from google_auth import (
    get_credentials,
    get_authorized_scopes,
    get_refresh_token,
    resolve_scopes,
    load_token,
    CLIENT_SECRETS_FILE,
    TOKEN_FILE,
    SCOPE_ALIASES,
)


def show_status():
    """Display current authentication status."""
    print("Google OAuth Status")
    print("=" * 50)

    if CLIENT_SECRETS_FILE.exists():
        print("Client secrets: Found")
    else:
        print("Client secrets: NOT FOUND")
        print(f"  Expected at: {CLIENT_SECRETS_FILE}")
        print()
        print("To set up:")
        print("  1. Go to https://console.cloud.google.com")
        print("  2. Create a project and enable needed APIs")
        print("  3. Create OAuth 2.0 credentials (Desktop app)")
        print("  4. Download JSON and save as client_secrets.json")
        return

    print()

    if TOKEN_FILE.exists():
        print("Token file: Found")
        scopes = get_authorized_scopes()
        if scopes:
            print(f"Authorized scopes ({len(scopes)}):")
            for scope in sorted(scopes):
                print(f"  - {scope}")

            refresh_token = get_refresh_token()
            if refresh_token:
                print()
                print("=" * 50)
                print("REFRESH TOKEN FOR RAILWAY:")
                print("=" * 50)
                print()
                print(f"GOOGLE_REFRESH_TOKEN={refresh_token}")
                print()
        else:
            print("  No scopes in token (may be corrupted)")
    else:
        print("Token file: NOT FOUND")
        print("  Run with --scopes to authorize")

    print()


def show_available_scopes():
    """Display available scope aliases organized by category."""
    print("\nAvailable scope aliases:")
    print("-" * 40)

    categories = {
        "Sheets": ["spreadsheets", "spreadsheets.readonly"],
        "Drive": ["drive", "drive.readonly", "drive.file"],
        "Docs": ["docs", "docs.readonly"],
        "Calendar": ["calendar", "calendar.readonly", "calendar.events", "calendar.events.readonly"],
        "Gmail": ["gmail.readonly", "gmail.modify", "gmail.send"],
        "YouTube": ["youtube", "youtube.readonly", "yt-analytics.readonly"],
    }

    for category, scopes in categories.items():
        print(f"\n{category}:")
        for scope in scopes:
            print(f"  {scope}")

    print()


def initial_setup(scopes: list[str]):
    """Run initial OAuth setup with specified scopes."""
    if not CLIENT_SECRETS_FILE.exists():
        print(f"Error: Client secrets not found at {CLIENT_SECRETS_FILE}")
        print()
        print("To set up:")
        print("  1. Go to https://console.cloud.google.com")
        print("  2. Create a project and enable the required APIs:")
        print("     - Google Sheets API")
        print("     - Google Drive API")
        print("     - (and others as needed)")
        print("  3. Create OAuth 2.0 credentials (Desktop app)")
        print("  4. Download JSON and save as:")
        print(f"     {CLIENT_SECRETS_FILE}")
        sys.exit(1)

    print(f"Requesting authorization for scopes: {scopes}")
    print()
    print("A browser window will open. Sign in with the Google account")
    print("that has access to the spreadsheets/resources you need.")
    print()

    try:
        credentials = get_credentials(scopes, interactive=True)
        print()
        print("=" * 50)
        print("AUTHORIZATION COMPLETE!")
        print("=" * 50)
        print()
        print(f"Authorized scopes: {', '.join(scopes)}")
        print()

        refresh_token = get_refresh_token()
        if refresh_token:
            print("Add this to your Railway environment variables:")
            print()
            print(f"GOOGLE_REFRESH_TOKEN={refresh_token}")
            print()
            print("You'll also need these (from your OAuth credentials):")
            print("  GOOGLE_CLIENT_ID=<your-client-id>")
            print("  GOOGLE_CLIENT_SECRET=<your-client-secret>")
            print()

    except Exception as e:
        print(f"Setup failed: {e}")
        sys.exit(1)


def add_scopes(new_scopes: list[str]):
    """Add additional scopes to existing authorization."""
    existing = get_authorized_scopes()

    if not existing:
        print("No existing authorization. Running initial setup...")
        initial_setup(new_scopes)
        return

    # Check what's already authorized
    resolved_new = resolve_scopes(new_scopes)
    token_data = load_token()
    existing_urls = set(token_data.get("scopes", []))

    already_authorized = set(resolved_new) & existing_urls
    if already_authorized:
        print(f"Already authorized: {[s for s in new_scopes if resolve_scopes([s])[0] in already_authorized]}")

    need_auth = set(resolved_new) - existing_urls
    if not need_auth:
        print("All requested scopes are already authorized!")
        show_status()
        return

    print(f"Adding scopes: {new_scopes}")
    print()

    # Get credentials with combined scopes (triggers re-auth)
    all_scope_aliases = list(set(existing) | set(new_scopes))

    try:
        get_credentials(all_scope_aliases, interactive=True)
        print()
        print("Scopes added successfully!")
        show_status()
    except Exception as e:
        print(f"Failed to add scopes: {e}")
        sys.exit(1)


def refresh_auth(scopes: list[str] | None):
    """Force re-authentication."""
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
        print("Removed existing token.")
        print()

    if scopes:
        initial_setup(scopes)
    else:
        existing = get_authorized_scopes()
        if existing:
            initial_setup(existing)
        else:
            print("No previous scopes found. Please specify --scopes")
            sys.exit(1)


def revoke_credentials():
    """Remove stored credentials."""
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
        print("Removed stored credentials.")
        print()
        print("Note: To fully revoke access, visit:")
        print("  https://myaccount.google.com/permissions")
    else:
        print("No stored credentials found.")


def main():
    parser = argparse.ArgumentParser(
        description="Google OAuth setup for Railway deployments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run cli_setup.py --scopes spreadsheets
  uv run cli_setup.py --scopes spreadsheets,drive.readonly
  uv run cli_setup.py --status
  uv run cli_setup.py --add-scope drive
  uv run cli_setup.py --refresh --scopes spreadsheets
  uv run cli_setup.py --list-scopes
""",
    )

    parser.add_argument(
        "--scopes",
        type=str,
        help="Comma-separated scope aliases (e.g., spreadsheets,drive.readonly)",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current authentication status and refresh token",
    )
    parser.add_argument(
        "--add-scope",
        nargs="+",
        metavar="SCOPE",
        help="Add additional scope(s) to existing authorization",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Force re-authentication",
    )
    parser.add_argument(
        "--revoke",
        action="store_true",
        help="Remove stored credentials",
    )
    parser.add_argument(
        "--list-scopes",
        action="store_true",
        help="List available scope aliases",
    )

    args = parser.parse_args()

    # Parse scopes if provided
    scopes = None
    if args.scopes:
        scopes = [s.strip() for s in args.scopes.split(",")]

    # Handle commands
    if args.status:
        show_status()
    elif args.list_scopes:
        show_available_scopes()
    elif args.add_scope:
        add_scopes(args.add_scope)
    elif args.refresh:
        refresh_auth(scopes)
    elif args.revoke:
        revoke_credentials()
    elif scopes:
        # Initial setup with specified scopes
        if TOKEN_FILE.exists():
            print("Already authorized. Use --refresh to re-authenticate.")
            print()
            show_status()
        else:
            initial_setup(scopes)
    else:
        # No arguments - show status or prompt for scopes
        if TOKEN_FILE.exists():
            show_status()
        else:
            print("No authorization found.")
            print()
            print("To authorize, run with --scopes:")
            print("  uv run cli_setup.py --scopes spreadsheets")
            print("  uv run cli_setup.py --scopes spreadsheets,drive.readonly")
            print()
            print("For all available scopes, run:")
            print("  uv run cli_setup.py --list-scopes")


if __name__ == "__main__":
    main()

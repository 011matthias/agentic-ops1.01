#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "fastapi>=0.109.0",
#     "uvicorn>=0.27.0",
#     "google-auth-oauthlib>=1.2.0",
#     "google-auth>=2.29.0",
#     "httpx>=0.27.0",
# ]
# ///
"""
Google OAuth Web Server for Client Self-Service

Standalone FastAPI server that allows clients to authorize their Google account
without needing Python installed. Outputs refresh_token for Railway env vars.

Usage:
    # Start the server (requires OAuth credentials as env vars)
    GOOGLE_CLIENT_ID=xxx GOOGLE_CLIENT_SECRET=xxx uv run web_server.py

    # Then send the URL to your client:
    # http://localhost:8000

    # Client flow:
    # 1. Visit the URL
    # 2. Select scopes (Sheets, Drive, etc.)
    # 3. Click "Connect Google"
    # 4. Authorize with Google
    # 5. Copy the refresh_token and send it back to you

Environment Variables:
    GOOGLE_CLIENT_ID: Your OAuth client ID
    GOOGLE_CLIENT_SECRET: Your OAuth client secret
    PORT: Server port (default: 8000)
"""

import os
import urllib.parse
from typing import Optional

import httpx
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

# OAuth configuration from environment
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
PORT = int(os.environ.get("PORT", "8000"))

# Google OAuth endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

# Available scopes
SCOPE_OPTIONS = {
    "spreadsheets": {
        "name": "Google Sheets",
        "description": "Read and write spreadsheets",
        "url": "https://www.googleapis.com/auth/spreadsheets",
    },
    "drive.readonly": {
        "name": "Google Drive (Read)",
        "description": "View files in Drive",
        "url": "https://www.googleapis.com/auth/drive.readonly",
    },
    "drive": {
        "name": "Google Drive (Full)",
        "description": "Create, edit, delete files in Drive",
        "url": "https://www.googleapis.com/auth/drive",
    },
    "docs": {
        "name": "Google Docs",
        "description": "Read and write documents",
        "url": "https://www.googleapis.com/auth/documents",
    },
    "calendar.events": {
        "name": "Google Calendar",
        "description": "View and manage calendar events",
        "url": "https://www.googleapis.com/auth/calendar.events",
    },
}

app = FastAPI(title="Google OAuth Setup")


def get_redirect_uri(request: Request) -> str:
    """Get the callback URL based on the request."""
    return str(request.url_for("callback"))


# HTML Templates
LANDING_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Google Authorization</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 16px;
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25);
            max-width: 480px;
            width: 100%;
            padding: 40px;
        }
        h1 { color: #1a1a1a; margin-bottom: 8px; font-size: 24px; }
        .subtitle { color: #666; margin-bottom: 32px; font-size: 14px; }
        .scope-list { margin-bottom: 24px; }
        .scope-item {
            display: flex;
            align-items: flex-start;
            padding: 12px;
            border: 1px solid #e5e5e5;
            border-radius: 8px;
            margin-bottom: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .scope-item:hover { border-color: #667eea; background: #f8f9ff; }
        .scope-item.selected { border-color: #667eea; background: #f0f3ff; }
        .scope-item input { margin-right: 12px; margin-top: 3px; }
        .scope-name { font-weight: 500; color: #1a1a1a; }
        .scope-desc { font-size: 13px; color: #666; margin-top: 2px; }
        .btn {
            display: block;
            width: 100%;
            padding: 14px 24px;
            background: #4285f4;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 500;
            cursor: pointer;
            transition: background 0.2s;
        }
        .btn:hover { background: #3367d6; }
        .btn:disabled { background: #ccc; cursor: not-allowed; }
        .error { background: #fee; color: #c00; padding: 12px; border-radius: 8px; margin-bottom: 16px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Connect Google Account</h1>
        <p class="subtitle">Select the permissions needed for your automation</p>

        {error}

        <form action="/authorize" method="get">
            <div class="scope-list">
                {scope_options}
            </div>
            <button type="submit" class="btn">Connect with Google</button>
        </form>
    </div>

    <script>
        document.querySelectorAll('.scope-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (e.target.type !== 'checkbox') {
                    const checkbox = item.querySelector('input');
                    checkbox.checked = !checkbox.checked;
                }
                item.classList.toggle('selected', item.querySelector('input').checked);
            });
        });
    </script>
</body>
</html>
"""

SUCCESS_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Authorization Complete</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 16px;
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25);
            max-width: 600px;
            width: 100%;
            padding: 40px;
        }
        .success-icon {
            width: 64px;
            height: 64px;
            background: #4caf50;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 24px;
        }
        .success-icon::after {
            content: '✓';
            color: white;
            font-size: 32px;
        }
        h1 { color: #1a1a1a; margin-bottom: 8px; font-size: 24px; text-align: center; }
        .subtitle { color: #666; margin-bottom: 24px; font-size: 14px; text-align: center; }
        .token-box {
            background: #f5f5f5;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 16px;
        }
        .token-label {
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 8px;
        }
        .token-value {
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 13px;
            word-break: break-all;
            color: #1a1a1a;
            background: white;
            padding: 12px;
            border-radius: 4px;
            border: 1px solid #ddd;
        }
        .copy-btn {
            display: block;
            width: 100%;
            padding: 12px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            cursor: pointer;
            margin-top: 12px;
        }
        .copy-btn:hover { background: #5a6fd6; }
        .instructions {
            margin-top: 24px;
            padding-top: 24px;
            border-top: 1px solid #e5e5e5;
        }
        .instructions h3 { font-size: 16px; margin-bottom: 12px; }
        .instructions ol { padding-left: 20px; color: #666; font-size: 14px; line-height: 1.8; }
        .scopes { font-size: 13px; color: #888; margin-top: 12px; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <div class="success-icon"></div>
        <h1>Authorization Complete!</h1>
        <p class="subtitle">Copy the refresh token below and send it back</p>

        <div class="token-box">
            <div class="token-label">Refresh Token</div>
            <div class="token-value" id="token">{refresh_token}</div>
            <button class="copy-btn" onclick="copyToken()">Copy to Clipboard</button>
        </div>

        <p class="scopes">Authorized scopes: {scopes}</p>

        <div class="instructions">
            <h3>Next Steps</h3>
            <ol>
                <li>Copy the refresh token above</li>
                <li>Send it back to your automation provider</li>
                <li>You can close this window</li>
            </ol>
        </div>
    </div>

    <script>
        function copyToken() {
            const token = document.getElementById('token').textContent;
            navigator.clipboard.writeText(token).then(() => {
                const btn = document.querySelector('.copy-btn');
                btn.textContent = 'Copied!';
                setTimeout(() => btn.textContent = 'Copy to Clipboard', 2000);
            });
        }
    </script>
</body>
</html>
"""

ERROR_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Authorization Error</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 16px;
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25);
            max-width: 480px;
            width: 100%;
            padding: 40px;
            text-align: center;
        }
        .error-icon {
            width: 64px;
            height: 64px;
            background: #f44336;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 24px;
        }
        .error-icon::after {
            content: '✕';
            color: white;
            font-size: 32px;
        }
        h1 { color: #1a1a1a; margin-bottom: 8px; font-size: 24px; }
        .error-msg { color: #666; margin-bottom: 24px; }
        .btn {
            display: inline-block;
            padding: 12px 24px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="error-icon"></div>
        <h1>Authorization Failed</h1>
        <p class="error-msg">{error}</p>
        <a href="/" class="btn">Try Again</a>
    </div>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def landing(error: Optional[str] = None):
    """Landing page with scope selection."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return HTMLResponse(
            ERROR_PAGE.format(
                error="Server configuration error: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set"
            )
        )

    # Build scope checkboxes
    scope_html = ""
    for scope_id, scope_info in SCOPE_OPTIONS.items():
        checked = "checked" if scope_id == "spreadsheets" else ""
        selected = "selected" if scope_id == "spreadsheets" else ""
        scope_html += f"""
        <label class="scope-item {selected}">
            <input type="checkbox" name="scopes" value="{scope_id}" {checked}>
            <div>
                <div class="scope-name">{scope_info['name']}</div>
                <div class="scope-desc">{scope_info['description']}</div>
            </div>
        </label>
        """

    error_html = f'<div class="error">{error}</div>' if error else ""

    return HTMLResponse(
        LANDING_PAGE.format(scope_options=scope_html, error=error_html)
    )


@app.get("/authorize")
async def authorize(request: Request, scopes: list[str] = Query(default=["spreadsheets"])):
    """Redirect to Google OAuth consent screen."""
    if not scopes:
        return RedirectResponse("/?error=Please+select+at+least+one+scope")

    # Convert scope aliases to full URLs
    scope_urls = []
    for scope in scopes:
        if scope in SCOPE_OPTIONS:
            scope_urls.append(SCOPE_OPTIONS[scope]["url"])

    if not scope_urls:
        return RedirectResponse("/?error=Invalid+scopes+selected")

    # Build OAuth URL
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": get_redirect_uri(request),
        "response_type": "code",
        "scope": " ".join(scope_urls),
        "access_type": "offline",
        "prompt": "consent",  # Force consent to get refresh_token
        "state": ",".join(scopes),  # Pass selected scopes through state
    }

    auth_url = f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"
    return RedirectResponse(auth_url)


@app.get("/callback", response_class=HTMLResponse)
async def callback(
    request: Request,
    code: Optional[str] = None,
    error: Optional[str] = None,
    state: Optional[str] = None,
):
    """Handle OAuth callback from Google."""
    if error:
        return HTMLResponse(ERROR_PAGE.format(error=error))

    if not code:
        return HTMLResponse(ERROR_PAGE.format(error="No authorization code received"))

    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": get_redirect_uri(request),
            },
        )

    if response.status_code != 200:
        error_data = response.json()
        return HTMLResponse(
            ERROR_PAGE.format(
                error=f"Token exchange failed: {error_data.get('error_description', error_data.get('error', 'Unknown error'))}"
            )
        )

    token_data = response.json()
    refresh_token = token_data.get("refresh_token")

    if not refresh_token:
        return HTMLResponse(
            ERROR_PAGE.format(
                error="No refresh token received. This may happen if you've already authorized this app. "
                "Go to https://myaccount.google.com/permissions, remove access, and try again."
            )
        )

    # Get scopes from state
    scopes = state.split(",") if state else ["unknown"]

    return HTMLResponse(
        SUCCESS_PAGE.format(
            refresh_token=refresh_token,
            scopes=", ".join(scopes),
        )
    )


def main():
    """Run the web server."""
    import uvicorn

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        print("Error: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set")
        print()
        print("Usage:")
        print("  GOOGLE_CLIENT_ID=xxx GOOGLE_CLIENT_SECRET=xxx uv run web_server.py")
        return

    print(f"Starting Google OAuth server on http://localhost:{PORT}")
    print()
    print("Send this URL to your client to authorize their Google account.")
    print("They will receive a refresh_token to send back to you.")
    print()

    uvicorn.run(app, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()

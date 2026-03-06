"""
ClickUp authentication and user endpoints.
"""

import httpx
from typing import TYPE_CHECKING

from ..models import AccessTokenResponse, AuthorizedTeams, AuthorizedUser

if TYPE_CHECKING:
    from .base import BaseClient


class AuthMixin:
    """Authentication and user-related API methods."""

    @staticmethod
    def get_authorization_url(client_id: str, redirect_uri: str, state: str | None = None) -> str:
        """
        Get the OAuth authorization URL.

        Args:
            client_id: OAuth app client ID
            redirect_uri: Redirect URI after authorization
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL to redirect users to
        """
        url = f"https://app.clickup.com/api?client_id={client_id}&redirect_uri={redirect_uri}"
        if state:
            url += f"&state={state}"
        return url

    async def get_access_token(
        self: "BaseClient",
        client_id: str,
        client_secret: str,
        code: str,
    ) -> AccessTokenResponse:
        """
        Exchange authorization code for access token.

        Args:
            client_id: OAuth app client ID
            client_secret: OAuth app client secret
            code: Authorization code from redirect

        Returns:
            Access token response
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/oauth/token",
                params={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                },
            )
            response.raise_for_status()
            return AccessTokenResponse.model_validate(response.json())

    async def get_authorized_user(self: "BaseClient") -> AuthorizedUser:
        """Get the currently authorized user."""
        data = await self._request("GET", "/user")
        return AuthorizedUser.model_validate(data)

    async def get_teams(self: "BaseClient") -> AuthorizedTeams:
        """
        Get all accessible workspaces (teams in v2 terminology).

        Note: "Teams" in API v2 = "Workspaces" in the UI and API v3.
        """
        data = await self._request("GET", "/team")
        return AuthorizedTeams.model_validate(data)

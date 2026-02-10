"""Microsoft Graph API client using app-only authentication."""

from __future__ import annotations

from dataclasses import dataclass

import httpx
import structlog
from msal import ConfidentialClientApplication

logger = structlog.get_logger()


@dataclass
class UserInfo:
    """User information retrieved from Azure AD."""

    aad_object_id: str
    display_name: str
    email: str | None
    groups: list[dict[str, str]]  # [{"id": "object-id", "display_name": "Name"}]


class GraphClient:
    """Microsoft Graph API client using app-only (client credentials) auth.

    Requires admin-consented application permissions:
    - User.Read.All
    - GroupMember.Read.All
    """

    GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"

    def __init__(self, client_id: str, client_secret: str, tenant_id: str):
        self._msal_app = ConfidentialClientApplication(
            client_id=client_id,
            client_credential=client_secret,
            authority=f"https://login.microsoftonline.com/{tenant_id}",
        )
        self._http_client: httpx.AsyncClient | None = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    def _get_app_token(self) -> str:
        result = self._msal_app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )
        if "access_token" not in result:
            error = result.get("error_description", "Unknown error")
            raise Exception(f"Failed to get Graph API token: {error}")
        return result["access_token"]

    async def get_user_with_groups(self, aad_object_id: str) -> UserInfo:
        token = self._get_app_token()
        client = await self._get_http_client()
        headers = {"Authorization": f"Bearer {token}"}

        user_response = await client.get(
            f"{self.GRAPH_API_BASE}/users/{aad_object_id}",
            headers=headers,
        )
        user_response.raise_for_status()
        user_data = user_response.json()

        groups = await self._get_all_groups_paginated(aad_object_id, headers, client)

        return UserInfo(
            aad_object_id=aad_object_id,
            display_name=user_data.get("displayName", "Unknown"),
            email=user_data.get("mail") or user_data.get("userPrincipalName"),
            groups=groups,
        )

    async def _get_all_groups_paginated(
        self,
        aad_object_id: str,
        headers: dict,
        client: httpx.AsyncClient,
    ) -> list[dict[str, str]]:
        groups: list[dict[str, str]] = []
        url: str | None = (
            f"{self.GRAPH_API_BASE}/users/{aad_object_id}/transitiveMemberOf"
            "?$select=id,displayName&$top=999"
        )

        while url:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            for item in data.get("value", []):
                if item.get("@odata.type") == "#microsoft.graph.group":
                    groups.append({
                        "id": item["id"],
                        "display_name": item.get("displayName", "Unknown"),
                    })

            url = data.get("@odata.nextLink")

        return groups

    async def close(self) -> None:
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

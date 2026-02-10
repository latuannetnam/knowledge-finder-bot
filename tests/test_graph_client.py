"""Tests for Microsoft Graph API client."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from knowledge_finder_bot.auth.graph_client import GraphClient, UserInfo


@pytest.fixture
def mock_msal_app():
    """Mock MSAL ConfidentialClientApplication."""
    with patch(
        "knowledge_finder_bot.auth.graph_client.ConfidentialClientApplication"
    ) as mock_cls:
        mock_app = MagicMock()
        mock_app.acquire_token_for_client.return_value = {
            "access_token": "fake-token-123"
        }
        mock_cls.return_value = mock_app
        yield mock_app


@pytest.fixture
def graph_client(mock_msal_app):
    """Create GraphClient with mocked MSAL."""
    return GraphClient(
        client_id="test-client-id",
        client_secret="test-secret",
        tenant_id="test-tenant-id",
    )


class TestGetAppToken:
    def test_returns_access_token(self, graph_client, mock_msal_app):
        token = graph_client._get_app_token()
        assert token == "fake-token-123"
        mock_msal_app.acquire_token_for_client.assert_called_once_with(
            scopes=["https://graph.microsoft.com/.default"]
        )

    def test_raises_on_token_error(self, graph_client, mock_msal_app):
        mock_msal_app.acquire_token_for_client.return_value = {
            "error": "invalid_client",
            "error_description": "Bad credentials",
        }
        with pytest.raises(Exception, match="Failed to get Graph API token"):
            graph_client._get_app_token()


class TestGetUserWithGroups:
    @pytest.mark.asyncio
    async def test_returns_user_info_with_groups(self, graph_client):
        user_response = httpx.Response(
            200,
            json={
                "displayName": "John Doe",
                "mail": "john@company.com",
                "userPrincipalName": "john@company.com",
            },
            request=httpx.Request("GET", "http://test"),
        )
        groups_response = httpx.Response(
            200,
            json={
                "value": [
                    {
                        "@odata.type": "#microsoft.graph.group",
                        "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                        "displayName": "Engineering",
                    },
                    {
                        "@odata.type": "#microsoft.graph.group",
                        "id": "11111111-2222-3333-4444-555555555555",
                        "displayName": "All Employees",
                    },
                ]
            },
            request=httpx.Request("GET", "http://test"),
        )

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=[user_response, groups_response])
        mock_client.is_closed = False
        graph_client._http_client = mock_client

        result = await graph_client.get_user_with_groups("user-object-id-123")

        assert isinstance(result, UserInfo)
        assert result.aad_object_id == "user-object-id-123"
        assert result.display_name == "John Doe"
        assert result.email == "john@company.com"
        assert len(result.groups) == 2
        assert result.groups[0]["id"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

    @pytest.mark.asyncio
    async def test_filters_non_group_types(self, graph_client):
        user_response = httpx.Response(
            200,
            json={"displayName": "Jane", "mail": "jane@co.com"},
            request=httpx.Request("GET", "http://test"),
        )
        groups_response = httpx.Response(
            200,
            json={
                "value": [
                    {
                        "@odata.type": "#microsoft.graph.group",
                        "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                        "displayName": "Real Group",
                    },
                    {
                        "@odata.type": "#microsoft.graph.directoryRole",
                        "id": "bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
                        "displayName": "Global Admin",
                    },
                ]
            },
            request=httpx.Request("GET", "http://test"),
        )

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=[user_response, groups_response])
        mock_client.is_closed = False
        graph_client._http_client = mock_client

        result = await graph_client.get_user_with_groups("user-id")
        assert len(result.groups) == 1
        assert result.groups[0]["display_name"] == "Real Group"

    @pytest.mark.asyncio
    async def test_handles_pagination(self, graph_client):
        user_response = httpx.Response(
            200,
            json={"displayName": "Paged User", "mail": None, "userPrincipalName": "p@co.com"},
            request=httpx.Request("GET", "http://test"),
        )
        page1_response = httpx.Response(
            200,
            json={
                "value": [
                    {
                        "@odata.type": "#microsoft.graph.group",
                        "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                        "displayName": "Group A",
                    },
                ],
                "@odata.nextLink": "https://graph.microsoft.com/v1.0/next-page",
            },
            request=httpx.Request("GET", "http://test"),
        )
        page2_response = httpx.Response(
            200,
            json={
                "value": [
                    {
                        "@odata.type": "#microsoft.graph.group",
                        "id": "11111111-2222-3333-4444-555555555555",
                        "displayName": "Group B",
                    },
                ],
            },
            request=httpx.Request("GET", "http://test"),
        )

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(
            side_effect=[user_response, page1_response, page2_response]
        )
        mock_client.is_closed = False
        graph_client._http_client = mock_client

        result = await graph_client.get_user_with_groups("user-id")
        assert len(result.groups) == 2
        assert result.email == "p@co.com"  # falls back to UPN

    @pytest.mark.asyncio
    async def test_uses_upn_when_mail_is_none(self, graph_client):
        user_response = httpx.Response(
            200,
            json={
                "displayName": "No Mail",
                "mail": None,
                "userPrincipalName": "nomail@company.com",
            },
            request=httpx.Request("GET", "http://test"),
        )
        groups_response = httpx.Response(200, json={"value": []}, request=httpx.Request("GET", "http://test"))

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=[user_response, groups_response])
        mock_client.is_closed = False
        graph_client._http_client = mock_client

        result = await graph_client.get_user_with_groups("user-id")
        assert result.email == "nomail@company.com"


class TestClose:
    @pytest.mark.asyncio
    async def test_closes_http_client(self, graph_client):
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.is_closed = False
        graph_client._http_client = mock_client

        await graph_client.close()
        mock_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_noop_when_no_client(self, graph_client):
        await graph_client.close()  # Should not raise

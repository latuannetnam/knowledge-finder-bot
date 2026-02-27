"""Tests for MockGraphClient."""

import pytest
from knowledge_finder_bot.auth.mock_graph_client import MockGraphClient
from knowledge_finder_bot.auth.graph_client import UserInfo


@pytest.mark.asyncio
async def test_returns_user_info_with_groups():
    """get_user_with_groups returns UserInfo with configured test groups."""
    client = MockGraphClient(["group-1", "group-2"])
    result = await client.get_user_with_groups("fake-aad-id")

    assert isinstance(result, UserInfo)
    assert result.aad_object_id == "fake-aad-id"
    assert len(result.groups) == 2


@pytest.mark.asyncio
async def test_display_name_is_test_user():
    """display_name is 'Test User (Agent Playground)'."""
    client = MockGraphClient(["group-1"])
    result = await client.get_user_with_groups("any-id")

    assert result.display_name == "Test User (Agent Playground)"
    assert result.email == "test@playground.local"


@pytest.mark.asyncio
async def test_groups_match_configured_ids():
    """Returned groups match the input test_groups IDs."""
    test_groups = ["aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "11111111-2222-3333-4444-555555555555"]
    client = MockGraphClient(test_groups)
    result = await client.get_user_with_groups("user-id")

    group_ids = [g["id"] for g in result.groups]
    assert group_ids == test_groups


@pytest.mark.asyncio
async def test_empty_groups():
    """Works with empty test_groups list."""
    client = MockGraphClient([])
    result = await client.get_user_with_groups("user-id")

    assert result.groups == []


@pytest.mark.asyncio
async def test_close_is_noop():
    """close() doesn't raise."""
    client = MockGraphClient(["group-1"])
    await client.close()  # should not raise

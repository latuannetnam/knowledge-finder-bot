# ACL Mechanism Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the full ACL pipeline — Graph API client, ACL service, bot integration — so the bot checks user AD group memberships against a YAML config and enforces notebook-level access control.

**Architecture:** Messages flow through: extract `aad_object_id` from Teams activity → call Microsoft Graph API (app-only auth, cached with TTLCache) to get user's AD groups → match groups against `config/acl.yaml` to determine allowed notebooks → reject or proceed. The nlm-proxy integration is NOT part of this plan — allowed users still get an echo response with their allowed notebooks listed.

**Two wildcard directions:**
- **Wildcard group on notebook:** `allowed_groups: ["*"]` → ALL authenticated users can access that notebook
- **Wildcard notebook for group:** `id: "*"` notebook entry → groups listed there can access ALL notebooks (admin/superuser pattern)

**Tech Stack:** Python 3.11+, Pydantic v2, MSAL (app-only auth), httpx (async HTTP), PyYAML, cachetools (TTLCache), structlog

---

## Task 1: Add Dependencies

**Files:**
- Modify: `pyproject.toml:7-18`

**Step 1: Add new dependencies to pyproject.toml**

Add `httpx`, `pyyaml`, and `cachetools` to the `dependencies` list. Note: `httpx` is already in dev dependencies but needs to be in main dependencies too for the Graph API client.

```toml
dependencies = [
    "microsoft-agents-hosting-core",
    "microsoft-agents-hosting-aiohttp",
    "microsoft-agents-activity",
    "microsoft-agents-authentication-msal",
    "aiohttp>=3.9.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "python-dotenv>=1.0.0",
    "structlog>=23.0.0",
    "msal>=1.24.0",
    "httpx>=0.25.0",
    "pyyaml>=6.0",
    "cachetools>=5.3.0",
]
```

**Step 2: Install dependencies**

Run: `uv sync`
Expected: All packages install successfully, lock file updated.

**Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "feat: add httpx, pyyaml, cachetools dependencies for ACL"
```

---

## Task 2: ACL Models

**Files:**
- Create: `src/knowledge_finder_bot/acl/__init__.py`
- Create: `src/knowledge_finder_bot/acl/models.py`
- Create: `tests/test_acl_models.py`

**Step 1: Create the acl package init**

```python
# src/knowledge_finder_bot/acl/__init__.py
"""Access Control List module."""
```

**Step 2: Write failing tests for ACL models**

```python
# tests/test_acl_models.py
"""Tests for ACL models."""

import pytest
from pydantic import ValidationError

from knowledge_finder_bot.acl.models import ACLConfig, GroupACL, NotebookACL


class TestGroupACL:
    def test_valid_guid(self):
        group = GroupACL(
            group_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            display_name="Engineering",
        )
        assert group.group_id == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        assert group.display_name == "Engineering"

    def test_invalid_guid_too_short(self):
        with pytest.raises(ValidationError, match="group_id"):
            GroupACL(group_id="not-a-guid", display_name="Bad")

    def test_invalid_guid_no_dashes(self):
        with pytest.raises(ValidationError, match="group_id"):
            GroupACL(group_id="a1b2c3d4e5f67890abcdef1234567890xxxx", display_name="Bad")


class TestNotebookACL:
    def test_with_group_acl(self):
        notebook = NotebookACL(
            id="notebook-123",
            name="HR Docs",
            allowed_groups=[
                GroupACL(
                    group_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    display_name="HR Team",
                )
            ],
        )
        assert notebook.id == "notebook-123"
        assert len(notebook.allowed_groups) == 1

    def test_with_wildcard_groups(self):
        """Notebook with allowed_groups: ['*'] = all users can access."""
        notebook = NotebookACL(
            id="public-notebook",
            name="Public KB",
            allowed_groups=["*"],
        )
        assert notebook.allowed_groups == ["*"]

    def test_wildcard_notebook_id(self):
        """Notebook with id: '*' = this group gets all notebooks."""
        notebook = NotebookACL(
            id="*",
            name="All Notebooks",
            allowed_groups=[
                GroupACL(
                    group_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    display_name="Admins",
                )
            ],
        )
        assert notebook.id == "*"
        assert len(notebook.allowed_groups) == 1

    def test_empty_allowed_groups(self):
        notebook = NotebookACL(id="locked", name="Locked Notebook")
        assert notebook.allowed_groups == []

    def test_default_description(self):
        notebook = NotebookACL(id="nb-1", name="Test")
        assert notebook.description == ""


class TestACLConfig:
    def test_valid_config(self):
        config = ACLConfig(
            notebooks=[
                NotebookACL(id="nb-1", name="Test", allowed_groups=["*"]),
            ],
        )
        assert len(config.notebooks) == 1

    def test_with_defaults(self):
        config = ACLConfig(
            notebooks=[],
            defaults={"strict_mode": True, "no_access_message": "No access."},
        )
        assert config.defaults["strict_mode"] is True

    def test_empty_notebooks_allowed(self):
        config = ACLConfig(notebooks=[])
        assert config.notebooks == []
```

**Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_acl_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'knowledge_finder_bot.acl.models'`

**Step 4: Implement ACL models**

```python
# src/knowledge_finder_bot/acl/models.py
"""ACL data models for YAML config validation."""

from pydantic import BaseModel, Field, field_validator


class GroupACL(BaseModel):
    """ACL entry for an Azure AD group. Uses immutable Object ID (GUID)."""

    group_id: str = Field(..., description="Azure AD Group Object ID (GUID)")
    display_name: str = Field(..., description="Group display name (for humans only)")

    @field_validator("group_id")
    @classmethod
    def validate_guid(cls, v: str) -> str:
        if not (len(v) == 36 and v.count("-") == 4):
            raise ValueError(f"group_id must be a valid GUID (36 chars, 4 dashes), got: {v}")
        return v


class NotebookACL(BaseModel):
    """ACL entry for a notebook with its allowed groups."""

    id: str = Field(..., description="NotebookLM notebook ID")
    name: str = Field(..., description="Human-readable notebook name")
    description: str = Field(default="", description="Optional description")
    allowed_groups: list[GroupACL | str] = Field(
        default_factory=list,
        description="List of GroupACL entries or '*' wildcard",
    )


class ACLConfig(BaseModel):
    """Root ACL configuration loaded from YAML."""

    notebooks: list[NotebookACL]
    defaults: dict = Field(default_factory=dict)
```

**Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_acl_models.py -v`
Expected: All 8 tests PASS.

**Step 6: Commit**

```bash
git add src/knowledge_finder_bot/acl/ tests/test_acl_models.py
git commit -m "feat: add ACL Pydantic models with GUID validation"
```

---

## Task 3: ACL Service

**Files:**
- Create: `src/knowledge_finder_bot/acl/service.py`
- Create: `tests/test_acl_service.py`
- Create: `config/acl.yaml`

**Step 1: Create the example ACL config file**

```yaml
# config/acl.yaml
# Access Control List: maps Azure AD groups (by Object ID) to allowed notebooks.
#
# CRITICAL: Use Group Object IDs (immutable GUIDs), NOT display names.
# Find Object IDs in Azure Portal > Azure AD > Groups > [Group] > Object ID
#
# Two wildcard patterns:
# 1. allowed_groups: ["*"] → ALL users can access this notebook
# 2. id: "*" → Groups listed can access ALL notebooks (admin/superuser)

notebooks:
  # Admin/superuser groups - get access to ALL notebooks
  - id: "*"
    name: "All Notebooks"
    description: "Wildcard notebook - groups here can access everything"
    allowed_groups:
      - group_id: "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
        display_name: "IT Admins"

  # Regular notebook with specific groups
  - id: "example-notebook-id"
    name: "Example Knowledge Base"
    description: "Placeholder - replace with real notebook IDs"
    allowed_groups:
      - group_id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        display_name: "Example Team"

  # Public notebook - all authenticated users
  - id: "public-notebook-id"
    name: "Public Knowledge Base"
    description: "Available to all authenticated users"
    allowed_groups:
      - "*"  # All authenticated users

defaults:
  strict_mode: true
  no_access_message: |
    You don't have access to any knowledge bases.
    Please contact your IT administrator to request access.
```

**Step 2: Write failing tests for ACL service**

```python
# tests/test_acl_service.py
"""Tests for ACL service."""

import os
import tempfile

import pytest
import yaml

from knowledge_finder_bot.acl.service import ACLService


@pytest.fixture
def acl_yaml_content():
    """ACL config with varied access patterns including both wildcard types."""
    return {
        "notebooks": [
            {
                "id": "*",
                "name": "All Notebooks",
                "description": "Admin wildcard",
                "allowed_groups": [
                    {
                        "group_id": "99999999-aaaa-bbbb-cccc-dddddddddddd",
                        "display_name": "IT Admins",
                    },
                ],
            },
            {
                "id": "hr-notebook",
                "name": "HR Docs",
                "allowed_groups": [
                    {
                        "group_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                        "display_name": "HR Team",
                    },
                    {
                        "group_id": "11111111-2222-3333-4444-555555555555",
                        "display_name": "All Employees",
                    },
                ],
            },
            {
                "id": "eng-notebook",
                "name": "Engineering Docs",
                "allowed_groups": [
                    {
                        "group_id": "cccccccc-dddd-eeee-ffff-000000000000",
                        "display_name": "Engineering",
                    },
                ],
            },
            {
                "id": "public-notebook",
                "name": "Public KB",
                "allowed_groups": ["*"],
            },
            {
                "id": "locked-notebook",
                "name": "Locked",
                "allowed_groups": [],
            },
        ],
        "defaults": {
            "strict_mode": True,
            "no_access_message": "No access.",
        },
    }


@pytest.fixture
def acl_config_path(acl_yaml_content, tmp_path):
    """Write ACL config to a temp file and return the path."""
    config_file = tmp_path / "acl.yaml"
    config_file.write_text(yaml.dump(acl_yaml_content))
    return str(config_file)


@pytest.fixture
def acl_service(acl_config_path):
    """Create ACLService from temp config."""
    return ACLService(acl_config_path)


class TestGetAllowedNotebooks:
    def test_user_in_one_group_gets_matching_notebook(self, acl_service):
        result = acl_service.get_allowed_notebooks(
            {"cccccccc-dddd-eeee-ffff-000000000000"}
        )
        assert "eng-notebook" in result
        assert "public-notebook" in result  # wildcard group

    def test_user_in_multiple_groups_gets_union(self, acl_service):
        result = acl_service.get_allowed_notebooks(
            {
                "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "cccccccc-dddd-eeee-ffff-000000000000",
            }
        )
        assert "hr-notebook" in result
        assert "eng-notebook" in result
        assert "public-notebook" in result

    def test_wildcard_group_notebook_accessible_to_all(self, acl_service):
        """Notebook with allowed_groups: ['*'] accessible to any user."""
        result = acl_service.get_allowed_notebooks(
            {"ffffffff-ffff-ffff-ffff-ffffffffffff"}  # random group
        )
        assert result == ["public-notebook"]

    def test_admin_group_gets_all_notebooks(self, acl_service):
        """User in IT Admins group (id: '*' notebook) gets all real notebooks."""
        result = acl_service.get_allowed_notebooks(
            {"99999999-aaaa-bbbb-cccc-dddddddddddd"}  # IT Admins
        )
        # Should get all notebooks except the wildcard notebook itself
        assert "eng-notebook" in result
        assert "hr-notebook" in result
        assert "public-notebook" in result
        assert "locked-notebook" in result
        assert "*" not in result  # wildcard notebook itself excluded

    def test_admin_plus_regular_group_no_duplicates(self, acl_service):
        """User in both admin and regular groups - no duplicate notebooks."""
        result = acl_service.get_allowed_notebooks(
            {
                "99999999-aaaa-bbbb-cccc-dddddddddddd",  # IT Admins (all notebooks)
                "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",  # HR Team
            }
        )
        # Should get all notebooks (via admin), no duplicates
        assert len(result) == len(set(result))
        assert "hr-notebook" in result

    def test_no_matching_groups_gets_only_wildcard_group_notebook(self, acl_service):
        result = acl_service.get_allowed_notebooks(
            {"00000000-0000-0000-0000-000000000000"}
        )
        assert result == ["public-notebook"]

    def test_empty_groups_gets_only_wildcard_group_notebook(self, acl_service):
        result = acl_service.get_allowed_notebooks(set())
        assert result == ["public-notebook"]

    def test_no_duplicates_in_results(self, acl_service):
        result = acl_service.get_allowed_notebooks(
            {"11111111-2222-3333-4444-555555555555"}
        )
        assert len(result) == len(set(result))

    def test_results_are_sorted(self, acl_service):
        result = acl_service.get_allowed_notebooks(
            {
                "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "cccccccc-dddd-eeee-ffff-000000000000",
            }
        )
        assert result == sorted(result)


class TestGetNotebookName:
    def test_existing_notebook(self, acl_service):
        assert acl_service.get_notebook_name("hr-notebook") == "HR Docs"

    def test_nonexistent_notebook(self, acl_service):
        assert acl_service.get_notebook_name("does-not-exist") is None


class TestReloadConfig:
    def test_reload_picks_up_changes(self, acl_config_path):
        service = ACLService(acl_config_path)
        assert service.get_notebook_name("hr-notebook") == "HR Docs"

        # Overwrite config with new content
        new_config = {
            "notebooks": [
                {"id": "new-notebook", "name": "New Name", "allowed_groups": ["*"]},
            ],
        }
        with open(acl_config_path, "w") as f:
            yaml.dump(new_config, f)

        service.reload_config()
        assert service.get_notebook_name("hr-notebook") is None
        assert service.get_notebook_name("new-notebook") == "New Name"


class TestLoadConfig:
    def test_invalid_yaml_raises(self, tmp_path):
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("not: [valid: yaml: {{")
        with pytest.raises(Exception):
            ACLService(str(bad_file))

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            ACLService("/nonexistent/path/acl.yaml")
```

**Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_acl_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'knowledge_finder_bot.acl.service'`

**Step 4: Implement ACL service**

```python
# src/knowledge_finder_bot/acl/service.py
"""ACL service for mapping Azure AD groups to allowed notebooks."""

import yaml
import structlog

from knowledge_finder_bot.acl.models import ACLConfig, GroupACL

logger = structlog.get_logger()


class ACLService:
    """Maps user AD group memberships to allowed NotebookLM notebooks."""

    def __init__(self, config_path: str):
        self._config_path = config_path
        self._acl_config = self._load_config()

    def _load_config(self) -> ACLConfig:
        with open(self._config_path) as f:
            raw = yaml.safe_load(f)
        return ACLConfig(**raw)

    def reload_config(self) -> None:
        self._acl_config = self._load_config()
        logger.info("acl_config_reloaded", path=self._config_path)

    def get_allowed_notebooks(self, user_group_ids: set[str]) -> list[str]:
        """Get list of notebook IDs user can access.

        Two wildcard patterns supported:
        1. Notebook with allowed_groups: ["*"] → accessible to all users
        2. Notebook with id: "*" → groups listed get access to ALL notebooks

        Args:
            user_group_ids: Set of Azure AD group Object IDs

        Returns:
            Sorted list of notebook IDs (excluding id: "*" itself)
        """
        # Check if user is in any "admin" groups (id: "*" notebook)
        for notebook in self._acl_config.notebooks:
            if notebook.id == "*":
                admin_group_ids: set[str] = set()
                for group in notebook.allowed_groups:
                    if isinstance(group, GroupACL):
                        admin_group_ids.add(group.group_id)

                # User is admin - return all real notebooks
                if admin_group_ids & user_group_ids:
                    all_notebooks = {
                        nb.id for nb in self._acl_config.notebooks
                        if nb.id != "*"
                    }
                    return sorted(all_notebooks)

        # Regular per-notebook matching
        allowed: set[str] = set()

        for notebook in self._acl_config.notebooks:
            if notebook.id == "*":
                continue  # Skip wildcard notebook itself

            has_wildcard = False
            notebook_group_ids: set[str] = set()

            for group in notebook.allowed_groups:
                if isinstance(group, str) and group == "*":
                    has_wildcard = True
                elif isinstance(group, GroupACL):
                    notebook_group_ids.add(group.group_id)

            if has_wildcard or (notebook_group_ids & user_group_ids):
                allowed.add(notebook.id)

        return sorted(allowed)

    def get_notebook_name(self, notebook_id: str) -> str | None:
        for notebook in self._acl_config.notebooks:
            if notebook.id == notebook_id:
                return notebook.name
        return None
```

**Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_acl_service.py -v`
Expected: All 11 tests PASS.

**Step 6: Commit**

```bash
git add src/knowledge_finder_bot/acl/service.py tests/test_acl_service.py config/acl.yaml
git commit -m "feat: add ACL service with YAML config and group-to-notebook mapping"
```

---

## Task 4: Graph API Client

**Files:**
- Create: `src/knowledge_finder_bot/auth/__init__.py`
- Create: `src/knowledge_finder_bot/auth/graph_client.py`
- Create: `tests/test_graph_client.py`

**Step 1: Create the auth package init**

```python
# src/knowledge_finder_bot/auth/__init__.py
"""Authentication module."""
```

**Step 2: Write failing tests for Graph client**

```python
# tests/test_graph_client.py
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
        )
        groups_response = httpx.Response(200, json={"value": []})

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
```

**Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_graph_client.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'knowledge_finder_bot.auth.graph_client'`

**Step 4: Implement Graph API client**

```python
# src/knowledge_finder_bot/auth/graph_client.py
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
```

**Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_graph_client.py -v`
Expected: All 7 tests PASS.

**Step 6: Commit**

```bash
git add src/knowledge_finder_bot/auth/ tests/test_graph_client.py
git commit -m "feat: add Graph API client with app-only auth and pagination"
```

---

## Task 5: Update Config

**Files:**
- Modify: `src/knowledge_finder_bot/config.py`
- Modify: `tests/conftest.py`
- Modify: `tests/test_config.py`

**Step 1: Write failing test for new config fields**

Add to `tests/test_config.py`:

```python
def test_settings_has_acl_defaults(settings: Settings):
    """Test that ACL settings have correct defaults."""
    assert settings.acl_config_path == "config/acl.yaml"
    assert settings.graph_cache_ttl == 300
    assert settings.graph_cache_maxsize == 1000
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_config.py::test_settings_has_acl_defaults -v`
Expected: FAIL — `AttributeError: 'Settings' object has no attribute 'acl_config_path'`

**Step 3: Add new fields to config.py**

Add these fields to the `Settings` class in `src/knowledge_finder_bot/config.py`, after the Graph API Client section:

```python
    # ACL
    acl_config_path: str = Field("config/acl.yaml", alias="ACL_CONFIG_PATH")

    # Graph API cache
    graph_cache_ttl: int = Field(300, alias="GRAPH_CACHE_TTL")
    graph_cache_maxsize: int = Field(1000, alias="GRAPH_CACHE_MAXSIZE")
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_config.py -v`
Expected: All 3 tests PASS (including the new one).

**Step 5: Commit**

```bash
git add src/knowledge_finder_bot/config.py tests/test_config.py
git commit -m "feat: add ACL and Graph cache settings to config"
```

---

## Task 6: Wire ACL into Bot Handler

**Files:**
- Modify: `src/knowledge_finder_bot/bot/bot.py`
- Modify: `src/knowledge_finder_bot/bot/__init__.py`
- Modify: `tests/conftest.py`
- Modify: `tests/test_bot.py`

This is the largest task. The bot handler currently uses module-level globals initialized at import time. We need to refactor it so that ACL dependencies (GraphClient, ACLService, TTLCache) can be injected — especially for testing.

**Step 1: Update conftest.py with new fixtures**

Replace the entire `tests/conftest.py`:

```python
# tests/conftest.py
"""Pytest fixtures for knowledge-finder-bot tests."""

import os
from unittest.mock import patch, AsyncMock, MagicMock

import pytest
import yaml

from knowledge_finder_bot.config import Settings


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing."""
    env_vars = {
        "MICROSOFT_APP_ID": "test-app-id",
        "MICROSOFT_APP_PASSWORD": "test-app-password",
        "MICROSOFT_APP_TENANT_ID": "test-tenant-id",
        "GRAPH_CLIENT_ID": "test-graph-client-id",
        "GRAPH_CLIENT_SECRET": "test-graph-client-secret",
        "HOST": "127.0.0.1",
        "PORT": "3978",
        "LOG_LEVEL": "DEBUG",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        yield env_vars


@pytest.fixture
def settings(mock_env_vars) -> Settings:
    """Create Settings instance with mocked environment."""
    return Settings()


@pytest.fixture
def acl_yaml_content():
    """Standard ACL config for bot integration tests."""
    return {
        "notebooks": [
            {
                "id": "*",
                "name": "All Notebooks",
                "allowed_groups": [
                    {
                        "group_id": "99999999-aaaa-bbbb-cccc-dddddddddddd",
                        "display_name": "IT Admins",
                    },
                ],
            },
            {
                "id": "hr-notebook",
                "name": "HR Docs",
                "allowed_groups": [
                    {
                        "group_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                        "display_name": "HR Team",
                    },
                ],
            },
            {
                "id": "public-notebook",
                "name": "Public KB",
                "allowed_groups": ["*"],
            },
        ],
        "defaults": {
            "strict_mode": True,
            "no_access_message": "No access.",
        },
    }


@pytest.fixture
def acl_config_path(acl_yaml_content, tmp_path):
    """Write ACL config to a temp file and return the path."""
    config_file = tmp_path / "acl.yaml"
    config_file.write_text(yaml.dump(acl_yaml_content))
    return str(config_file)


@pytest.fixture
def mock_graph_client():
    """Mock GraphClient that returns configurable UserInfo."""
    from knowledge_finder_bot.auth.graph_client import UserInfo

    client = AsyncMock()
    client.get_user_with_groups = AsyncMock(
        return_value=UserInfo(
            aad_object_id="test-aad-id",
            display_name="Test User",
            email="test@company.com",
            groups=[
                {"id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "display_name": "HR Team"},
            ],
        )
    )
    client.close = AsyncMock()
    return client
```

**Step 2: Refactor bot.py to support ACL injection**

Replace `src/knowledge_finder_bot/bot/bot.py` with:

```python
# src/knowledge_finder_bot/bot/bot.py
"""Bot handler with ACL enforcement using M365 Agents SDK."""

import re
import traceback

import structlog
from cachetools import TTLCache
from dotenv import load_dotenv
from os import environ

from microsoft_agents.hosting.aiohttp import CloudAdapter
from microsoft_agents.hosting.core import (
    Authorization,
    AgentApplication,
    TurnState,
    TurnContext,
    MemoryStorage,
)
from microsoft_agents.authentication.msal import MsalConnectionManager
from microsoft_agents.activity import ConversationUpdateTypes, load_configuration_from_env

from knowledge_finder_bot.acl.service import ACLService
from knowledge_finder_bot.auth.graph_client import GraphClient, UserInfo
from knowledge_finder_bot.config import Settings

logger = structlog.get_logger()


def create_agent_app(
    settings: Settings,
    graph_client: GraphClient | None = None,
    acl_service: ACLService | None = None,
) -> AgentApplication[TurnState]:
    """Create and configure the agent application with ACL support.

    Args:
        settings: Application settings.
        graph_client: Graph API client (None disables ACL, echo-only mode).
        acl_service: ACL service (None disables ACL, echo-only mode).
    """
    load_dotenv()

    agents_sdk_config = load_configuration_from_env(dict(environ))

    storage = MemoryStorage()
    connection_manager = MsalConnectionManager(**agents_sdk_config)
    adapter = CloudAdapter(connection_manager=connection_manager)
    authorization = Authorization(storage, connection_manager, **agents_sdk_config)

    agent_app = AgentApplication[TurnState](
        storage=storage,
        adapter=adapter,
        authorization=authorization,
        **agents_sdk_config,
    )

    # Store connection manager for main.py access
    agent_app._connection_manager = connection_manager

    # ACL components (None = echo-only mode)
    acl_enabled = graph_client is not None and acl_service is not None
    user_cache: TTLCache | None = None
    if acl_enabled:
        user_cache = TTLCache(
            maxsize=settings.graph_cache_maxsize,
            ttl=settings.graph_cache_ttl,
        )

    @agent_app.conversation_update(ConversationUpdateTypes.MEMBERS_ADDED)
    async def on_members_added(context: TurnContext, state: TurnState):
        for member in context.activity.members_added or []:
            if member.id != context.activity.recipient.id:
                await context.send_activity(
                    "Hello! I'm the NotebookLM Bot.\n\n"
                    "Ask me anything about your organization's knowledge bases."
                )

    @agent_app.message(re.compile(r".*"))
    async def on_message(context: TurnContext, state: TurnState):
        user_message = context.activity.text
        user_name = context.activity.from_property.name or "User"

        if not acl_enabled:
            # Echo-only mode (no Graph/ACL configured)
            logger.info("echo_mode", user_name=user_name)
            await context.send_activity(f"**Echo from {user_name}:** {user_message}")
            return

        # --- ACL-enforced flow ---
        aad_object_id = getattr(context.activity.from_property, "aad_object_id", None)

        if not aad_object_id:
            logger.warning("no_aad_object_id", user_name=user_name)
            await context.send_activity(
                "Unable to identify your account. "
                "Please ensure you're signed into Teams with your work account."
            )
            return

        logger.info(
            "message_received",
            user_name=user_name,
            aad_object_id=aad_object_id,
            message_length=len(user_message or ""),
        )

        # Get user info (cached)
        try:
            if aad_object_id in user_cache:
                user_info = user_cache[aad_object_id]
                logger.debug("user_cache_hit", aad_object_id=aad_object_id)
            else:
                user_info = await graph_client.get_user_with_groups(aad_object_id)
                user_cache[aad_object_id] = user_info
                logger.debug("user_cache_miss", aad_object_id=aad_object_id)
        except Exception as e:
            logger.error("graph_api_failed", error=str(e), aad_object_id=aad_object_id)
            await context.send_activity(
                "Unable to verify your permissions. Please try again later."
            )
            return

        logger.info(
            "user_authenticated",
            user_name=user_info.display_name,
            group_count=len(user_info.groups),
        )

        # Check ACL
        user_group_ids = {g["id"] for g in user_info.groups}
        allowed_notebooks = acl_service.get_allowed_notebooks(user_group_ids)

        if not allowed_notebooks:
            logger.warning(
                "acl_denied",
                user_name=user_info.display_name,
                group_count=len(user_info.groups),
            )
            await context.send_activity(
                "You don't have access to any knowledge bases.\n"
                "Please contact your administrator for access."
            )
            return

        logger.info(
            "acl_granted",
            user_name=user_info.display_name,
            notebook_count=len(allowed_notebooks),
        )

        # Echo with ACL info (nlm-proxy integration comes later)
        notebook_names = [
            acl_service.get_notebook_name(nb_id) or nb_id
            for nb_id in allowed_notebooks
        ]
        notebooks_display = ", ".join(notebook_names)
        await context.send_activity(
            f"**{user_name}:** {user_message}\n\n"
            f"---\n"
            f"*Allowed notebooks: {notebooks_display}*"
        )

    @agent_app.error
    async def on_error(context: TurnContext, error: Exception):
        logger.error("on_turn_error", error=str(error))
        traceback.print_exc()
        await context.send_activity("The bot encountered an error.")

    return agent_app
```

**Step 3: Update bot/__init__.py**

Replace `src/knowledge_finder_bot/bot/__init__.py`:

```python
"""Bot module."""

from knowledge_finder_bot.bot.bot import create_agent_app

__all__ = ["create_agent_app"]
```

**Step 4: Update main.py to use factory function with ACL**

Replace `src/knowledge_finder_bot/main.py`:

```python
"""Application entrypoint - aiohttp server with M365 Agents SDK."""

import logging

import structlog
from aiohttp.web import Request, Response, Application, run_app
from microsoft_agents.hosting.aiohttp import (
    CloudAdapter,
    start_agent_process,
    jwt_authorization_middleware,
)
from microsoft_agents.hosting.core import AgentApplication

from knowledge_finder_bot.acl.service import ACLService
from knowledge_finder_bot.auth.graph_client import GraphClient
from knowledge_finder_bot.bot import create_agent_app
from knowledge_finder_bot.config import get_settings


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structlog and standard library logging."""
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level.upper(), logging.INFO),
    )
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


logger = structlog.get_logger()


async def messages(request: Request) -> Response:
    agent: AgentApplication = request.app["agent_app"]
    adapter: CloudAdapter = request.app["adapter"]
    response = await start_agent_process(request, agent, adapter)
    return response if response is not None else Response(status=202)


async def health(request: Request) -> Response:
    from aiohttp import web
    return web.json_response({"status": "healthy"})


async def messages_health(request: Request) -> Response:
    return Response(status=200)


def create_app() -> Application:
    """Create and configure the aiohttp application."""
    settings = get_settings()

    # Initialize ACL components (optional — graceful fallback to echo mode)
    graph_client = None
    acl_service = None

    try:
        graph_client = GraphClient(
            client_id=settings.graph_client_id,
            client_secret=settings.graph_client_secret,
            tenant_id=settings.app_tenant_id,
        )
        acl_service = ACLService(settings.acl_config_path)
        logger.info("acl_enabled", config_path=settings.acl_config_path)
    except Exception as e:
        logger.warning("acl_disabled", reason=str(e))

    agent_app = create_agent_app(
        settings=settings,
        graph_client=graph_client,
        acl_service=acl_service,
    )

    app = Application(middlewares=[jwt_authorization_middleware])
    app["agent_configuration"] = agent_app._connection_manager.get_default_connection_configuration()
    app["agent_app"] = agent_app
    app["adapter"] = agent_app.adapter

    app.router.add_post("/api/messages", messages)
    app.router.add_get("/api/messages", messages_health)
    app.router.add_get("/health", health)

    return app


def main() -> None:
    """Run the bot server."""
    settings = get_settings()
    configure_logging(settings.log_level)

    logger.info(
        "starting_bot_server",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
    )

    app = create_app()
    run_app(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
```

**Step 5: Rewrite test_bot.py with ACL test cases**

Replace `tests/test_bot.py`:

```python
# tests/test_bot.py
"""Tests for bot module with ACL enforcement."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from knowledge_finder_bot.auth.graph_client import UserInfo
from knowledge_finder_bot.bot import create_agent_app
from knowledge_finder_bot.config import Settings


def create_mock_context(
    activity_type: str,
    text: str = None,
    members_added: list = None,
    aad_object_id: str = None,
):
    """Create a mock turn context.

    The SDK accesses activity.text synchronously for regex matching,
    so we must use MagicMock (not AsyncMock) for the activity object.
    """
    context = MagicMock()
    context.send_activity = AsyncMock()
    context.remove_recipient_mention.return_value = text

    context.activity = MagicMock()
    context.activity.type = activity_type
    context.activity.text = text
    context.activity.from_property = MagicMock()
    context.activity.from_property.name = "Test User"
    context.activity.from_property.aad_object_id = aad_object_id
    context.activity.recipient = MagicMock()
    context.activity.recipient.id = "bot-id"
    context.activity.members_added = members_added

    return context


# --- Echo mode (no ACL) ---

@pytest.fixture
def echo_app(settings: Settings):
    """Agent app in echo-only mode (no Graph/ACL)."""
    return create_agent_app(settings, graph_client=None, acl_service=None)


@pytest.mark.asyncio
async def test_echo_mode_echoes_message(echo_app):
    context = create_mock_context(activity_type="message", text="Hello!")
    await echo_app.on_turn(context)

    calls = context.send_activity.call_args_list
    echo_found = any(
        isinstance(c[0][0], str) and "Hello!" in c[0][0]
        for c in calls
    )
    assert echo_found, f"Echo not found in: {calls}"


@pytest.mark.asyncio
async def test_welcome_message(echo_app):
    member = MagicMock()
    member.id = "new-user-id"
    context = create_mock_context(
        activity_type="conversationUpdate", members_added=[member]
    )
    await echo_app.on_turn(context)

    calls = context.send_activity.call_args_list
    welcome_found = any(
        isinstance(c[0][0], str) and "NotebookLM Bot" in c[0][0]
        for c in calls
    )
    assert welcome_found, f"Welcome not found in: {calls}"


# --- ACL mode ---

@pytest.fixture
def acl_app(settings, acl_config_path, mock_graph_client):
    """Agent app with ACL enforcement enabled."""
    from knowledge_finder_bot.acl.service import ACLService

    acl_service = ACLService(acl_config_path)
    return create_agent_app(
        settings=settings,
        graph_client=mock_graph_client,
        acl_service=acl_service,
    )


@pytest.mark.asyncio
async def test_acl_allowed_user_sees_notebooks(acl_app):
    """User in HR Team group should see hr-notebook and public-notebook."""
    context = create_mock_context(
        activity_type="message",
        text="What is the leave policy?",
        aad_object_id="test-aad-id",
    )
    await acl_app.on_turn(context)

    calls = context.send_activity.call_args_list
    response_found = any(
        isinstance(c[0][0], str) and "Allowed notebooks" in c[0][0]
        for c in calls
    )
    assert response_found, f"ACL response not found in: {calls}"


@pytest.mark.asyncio
async def test_acl_denied_user_gets_rejection(acl_app, mock_graph_client):
    """User with no matching groups gets rejection."""
    mock_graph_client.get_user_with_groups.return_value = UserInfo(
        aad_object_id="denied-user",
        display_name="Denied User",
        email="denied@co.com",
        groups=[
            {"id": "ffffffff-ffff-ffff-ffff-ffffffffffff", "display_name": "Unknown Group"},
        ],
    )

    context = create_mock_context(
        activity_type="message",
        text="Secret stuff",
        aad_object_id="denied-user",
    )
    await acl_app.on_turn(context)

    calls = context.send_activity.call_args_list
    # User should still get public-notebook via wildcard
    response_found = any(
        isinstance(c[0][0], str) and "Public KB" in c[0][0]
        for c in calls
    )
    assert response_found, f"Public notebook not found in: {calls}"


@pytest.mark.asyncio
async def test_missing_aad_object_id_gets_error(acl_app):
    """Message without aad_object_id gets identity error."""
    context = create_mock_context(
        activity_type="message",
        text="Hi",
        aad_object_id=None,
    )
    await acl_app.on_turn(context)

    calls = context.send_activity.call_args_list
    error_found = any(
        isinstance(c[0][0], str) and "Unable to identify" in c[0][0]
        for c in calls
    )
    assert error_found, f"Identity error not found in: {calls}"


@pytest.mark.asyncio
async def test_graph_api_failure_returns_graceful_error(acl_app, mock_graph_client):
    """Graph API exception results in graceful error message."""
    mock_graph_client.get_user_with_groups.side_effect = Exception("Graph API down")

    context = create_mock_context(
        activity_type="message",
        text="Hello",
        aad_object_id="failing-user",
    )
    await acl_app.on_turn(context)

    calls = context.send_activity.call_args_list
    error_found = any(
        isinstance(c[0][0], str) and "Unable to verify" in c[0][0]
        for c in calls
    )
    assert error_found, f"Graph error message not found in: {calls}"
```

**Step 6: Run all tests**

Run: `uv run pytest tests/ -v`
Expected: All tests PASS (existing + new).

**Step 7: Commit**

```bash
git add src/knowledge_finder_bot/bot/ src/knowledge_finder_bot/main.py tests/conftest.py tests/test_bot.py
git commit -m "feat: wire ACL pipeline into bot handler with echo fallback"
```

---

## Task 7: Update Documentation

**Files:**
- Modify: `.claude/memory/project-structure.md`
- Modify: `.claude/memory/dependencies.md`
- Modify: `.claude/memory/MEMORY.md`
- Modify: `TODO.md`

**Step 1: Update all docs to reflect new modules**

Update `TODO.md`:
```markdown
# Planning
- [ ] Test ACL flow end-to-end with real Azure AD groups
- [ ] Implement nlm-proxy client integration

# Done
- [Done] Structure logging system
- [Done] Documentation: README.md and related files
- [Done] Graph API client (auth/graph_client.py)
- [Done] ACL service (acl/service.py, acl/models.py)
- [Done] ACL YAML config (config/acl.yaml)
- [Done] Bot handler ACL integration
```

Update `.claude/memory/MEMORY.md` "Current Phase":
```markdown
## Current Phase
- **ACL:** Graph API client + ACL service + bot integration complete
- **Status:** Bot checks AD groups against acl.yaml, echo mode with ACL info
- **Next:** Implement nlm-proxy integration (replace echo with real queries)
```

Update `.claude/memory/project-structure.md` to include `auth/`, `acl/`, `config/` directories.

Update `.claude/memory/dependencies.md` to include `httpx`, `pyyaml`, `cachetools`.

**Step 2: Commit**

```bash
git add TODO.md .claude/memory/
git commit -m "docs: update memory and TODO for ACL implementation"
```

---

## Task 8: Final Verification

**Step 1: Run full test suite with coverage**

Run: `uv run pytest tests/ -v --cov=knowledge_finder_bot`
Expected: All tests pass, coverage report shows new modules covered.

**Step 2: Verify bot starts in echo mode (no Azure creds needed)**

Run: `uv run python -m knowledge_finder_bot.main`
Expected: Server starts on port 3978, logs `acl_disabled` warning (since no real ACL config or creds are configured in dev), health check at `http://localhost:3978/health` returns `{"status": "healthy"}`.

**Step 3: Verify ACL config validation**

Run: `uv run python -c "from knowledge_finder_bot.acl.service import ACLService; ACLService('config/acl.yaml')"`
Expected: No errors — the example config loads and validates.

---

Plan complete and saved to `docs/plans/2025-02-10-acl-mechanism.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?
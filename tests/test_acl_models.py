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

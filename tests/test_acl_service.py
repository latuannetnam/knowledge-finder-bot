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

    def test_admin_group_gets_wildcard_access(self, acl_service):
        """User in IT Admins group (id: '*' notebook) gets wildcard access."""
        result = acl_service.get_allowed_notebooks(
            {"99999999-aaaa-bbbb-cccc-dddddddddddd"}  # IT Admins
        )
        # Should return ["*"] sentinel for unrestricted access
        assert result == ["*"]
        assert ACLService.is_wildcard_access(result)

    def test_admin_plus_regular_group_gets_wildcard(self, acl_service):
        """User in both admin and regular groups - still gets wildcard."""
        result = acl_service.get_allowed_notebooks(
            {
                "99999999-aaaa-bbbb-cccc-dddddddddddd",  # IT Admins (all notebooks)
                "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",  # HR Team
            }
        )
        # Admin group takes precedence - returns wildcard
        assert result == ["*"]
        assert ACLService.is_wildcard_access(result)

    def test_is_wildcard_access_false_for_regular(self, acl_service):
        """is_wildcard_access returns False for regular notebook lists."""
        result = acl_service.get_allowed_notebooks(
            {"cccccccc-dddd-eeee-ffff-000000000000"}
        )
        assert not ACLService.is_wildcard_access(result)

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

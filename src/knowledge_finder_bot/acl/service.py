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

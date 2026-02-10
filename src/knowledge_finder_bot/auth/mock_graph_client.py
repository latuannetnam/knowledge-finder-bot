"""Mock Graph API client for testing in Agent Playground."""

import structlog

from knowledge_finder_bot.auth.graph_client import UserInfo

logger = structlog.get_logger()


class MockGraphClient:
    """Mock GraphClient that returns predefined user data for testing.

    This client is used in TEST_MODE to simulate Graph API responses
    without making real API calls. Perfect for Agent Playground testing
    where fake AAD Object IDs would cause 404 errors.
    """

    def __init__(self, test_groups: list[str]):
        """Initialize mock client with test group IDs.

        Args:
            test_groups: List of Azure AD group Object IDs to simulate
        """
        self.test_groups = test_groups
        logger.info("mock_graph_client_initialized", group_count=len(test_groups))

    async def get_user_with_groups(self, aad_object_id: str) -> UserInfo:
        """Return mock user info with configured test groups.

        Args:
            aad_object_id: Any AAD Object ID (can be fake from Agent Playground)

        Returns:
            UserInfo with predefined test groups
        """
        # Create mock groups from test configuration
        groups = [
            {"id": group_id, "display_name": f"Test Group {i+1}"}
            for i, group_id in enumerate(self.test_groups)
        ]

        logger.info(
            "mock_user_retrieved",
            aad_object_id=aad_object_id,
            group_count=len(groups),
        )

        return UserInfo(
            aad_object_id=aad_object_id,
            display_name="Test User (Agent Playground)",
            email="test@playground.local",
            groups=groups,
        )

    async def close(self) -> None:
        """No-op close method for compatibility with GraphClient interface."""
        pass

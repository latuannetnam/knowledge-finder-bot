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

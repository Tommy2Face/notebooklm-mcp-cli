"""Sharing service — shared business logic for notebook sharing and collaboration."""

from typing import TypedDict, Literal, Optional

from ..core.client import NotebookLMClient
from ..core.data_types import ShareStatus, Collaborator
from .errors import ValidationError, ServiceError


class CollaboratorInfo(TypedDict):
    """Collaborator details."""
    email: str
    role: str
    is_pending: bool
    display_name: Optional[str]


class ShareStatusResult(TypedDict):
    """Result of a share status check."""
    notebook_id: str
    is_public: bool
    access_level: str
    public_link: Optional[str]
    collaborators: list[CollaboratorInfo]
    collaborator_count: int


class PublicAccessResult(TypedDict):
    """Result of a public access change."""
    notebook_id: str
    is_public: bool
    public_link: Optional[str]
    message: str


class InviteResult(TypedDict):
    """Result of a collaborator invitation."""
    notebook_id: str
    email: str
    role: str
    message: str


def _collaborator_to_dict(c: Collaborator) -> CollaboratorInfo:
    """Convert a Collaborator dataclass to a dict."""
    return {
        "email": c.email,
        "role": c.role,
        "is_pending": c.is_pending,
        "display_name": c.display_name,
    }


def get_share_status(client: NotebookLMClient, notebook_id: str) -> ShareStatusResult:
    """Get sharing status and collaborators for a notebook.

    Args:
        client: Authenticated NotebookLM client
        notebook_id: Notebook UUID

    Returns:
        ShareStatusResult with collaborators and access info

    Raises:
        ServiceError: If the API call fails
    """
    try:
        status: ShareStatus = client.get_share_status(notebook_id)
        collaborators = [_collaborator_to_dict(c) for c in status.collaborators]
        return {
            "notebook_id": notebook_id,
            "is_public": status.is_public,
            "access_level": status.access_level,
            "public_link": status.public_link,
            "collaborators": collaborators,
            "collaborator_count": len(collaborators),
        }
    except Exception as e:
        raise ServiceError(f"Failed to get share status: {e}")


def set_public_access(
    client: NotebookLMClient,
    notebook_id: str,
    is_public: bool,
) -> PublicAccessResult:
    """Enable or disable public link access.

    Args:
        client: Authenticated NotebookLM client
        notebook_id: Notebook UUID
        is_public: True to enable, False to disable

    Returns:
        PublicAccessResult with link info

    Raises:
        ServiceError: If the API call fails
    """
    try:
        result = client.set_public_access(notebook_id, is_public)
        if is_public:
            return {
                "notebook_id": notebook_id,
                "is_public": True,
                "public_link": result,
                "message": "Public link access enabled.",
            }
        else:
            return {
                "notebook_id": notebook_id,
                "is_public": False,
                "public_link": None,
                "message": "Public link access disabled.",
            }
    except Exception as e:
        raise ServiceError(f"Failed to set public access: {e}")


def invite_collaborator(
    client: NotebookLMClient,
    notebook_id: str,
    email: str,
    role: str = "viewer",
) -> InviteResult:
    """Invite a collaborator by email.

    Args:
        client: Authenticated NotebookLM client
        notebook_id: Notebook UUID
        email: Email address to invite
        role: "viewer" or "editor"

    Returns:
        InviteResult with invitation details

    Raises:
        ValidationError: If role is invalid
        ServiceError: If invitation fails
    """
    clean_role = role.lower()
    if clean_role not in ("viewer", "editor"):
        raise ValidationError(
            f"Invalid role '{role}'. Must be 'viewer' or 'editor'.",
            user_message=f"Role must be 'viewer' or 'editor' (got '{role}')",
        )

    try:
        result = client.add_collaborator(notebook_id, email, clean_role)
        if result:
            return {
                "notebook_id": notebook_id,
                "email": email,
                "role": clean_role,
                "message": f"Invited {email} as {clean_role}.",
            }
        raise ServiceError(
            "Invitation returned falsy result",
            user_message="Invitation may have failed — no confirmation from API.",
        )
    except ServiceError:
        raise
    except Exception as e:
        raise ServiceError(f"Failed to invite collaborator: {e}")

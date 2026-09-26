"""
Role-Based Access Control (RBAC) Security Layer.
Enforces pre-retrieval role permission hierarchies.
"""

from typing import List, Dict

ROLE_HIERARCHY: Dict[str, List[str]] = {
    "PUBLIC_USER": ["PUBLIC_USER"],
    "INTERNAL_USER": ["PUBLIC_USER", "INTERNAL_USER"],
    "ADMIN": ["PUBLIC_USER", "INTERNAL_USER", "ADMIN"]
}

DEFAULT_ROLE = "PUBLIC_USER"

def get_allowed_access_levels(user_role: str) -> List[str]:
    """
    Returns list of document access levels accessible by the given user role.
    Defaults to PUBLIC_USER access if role is invalid or unspecified.
    """
    normalized_role = (user_role or DEFAULT_ROLE).strip().upper()
    return ROLE_HIERARCHY.get(normalized_role, ROLE_HIERARCHY[DEFAULT_ROLE])

def validate_user_access(user_role: str, document_access_level: str) -> bool:
    """
    Returns True if user_role is authorized to view content with document_access_level.
    """
    allowed_levels = get_allowed_access_levels(user_role)
    doc_level = (document_access_level or "PUBLIC_USER").strip().upper()
    return doc_level in allowed_levels

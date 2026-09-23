from typing import Any


def build_session_claims(userinfo: dict[str, Any]) -> dict[str, str]:
    """Picks the small, non-secret identity claims worth keeping in the
    session out of Helix's raw /userinfo/ response. Never includes tokens."""
    return {
        "sub": userinfo.get("sub", ""),
        "email": userinfo.get("email", ""),
        "first_name": userinfo.get("given_name", ""),
        "last_name": userinfo.get("family_name", ""),
    }

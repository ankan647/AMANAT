"""Role matrix (AMANAT_SPEC.md section 5.13) and auth dependencies.

Permission matrix (who may do what) — kept here as a single readable source of truth; routers
compose `require_roles(...)` from this table. Per-object checks (own institution, own bank) are
layered on top in the relevant service/router.
"""

from dataclasses import dataclass

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError, UnauthenticatedError
from app.core.security import decode_access_token
from app.db.models import User
from app.db.session import get_db

ACTION_ROLES: dict[str, set[str]] = {
    "lodge_fdr": {"institution", "scrutiny"},
    "create_bank_request": {"scrutiny", "senior_approver", "competent_authority"},
    "respond_bank_request": {"bank_officer"},
    "accept_reject_bank_response": {"scrutiny", "senior_approver", "competent_authority"},
    "flag_outcome": {"scrutiny", "senior_approver", "competent_authority"},
    "rule_draft": {"admin"},
    "rule_approve": {"admin"},
    "approve_release": {"senior_approver", "competent_authority"},
    "revoke_order_place_hold": {"competent_authority"},
    "read_audit": {"competent_authority", "auditor"},
    "advance_clock": {"scrutiny", "senior_approver", "competent_authority", "admin"},
}


@dataclass
class CurrentUser:
    id: int
    email: str
    name: str
    role: str
    bank_name: str | None
    institution_id: int | None
    active: bool


def get_current_user(request: Request, db: Session = Depends(get_db)) -> CurrentUser:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise UnauthenticatedError()
    token = auth_header.removeprefix("Bearer ").strip()
    try:
        claims = decode_access_token(token)
    except Exception as exc:  # noqa: BLE001
        raise UnauthenticatedError("Invalid or expired token.") from exc

    user = db.query(User).filter(User.email == claims.get("sub")).first()
    if user is None or not user.active:
        raise UnauthenticatedError("User not found or inactive.")

    return CurrentUser(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        bank_name=user.bank_name,
        institution_id=user.institution_id,
        active=user.active,
    )


def require_roles(*roles: str):  # type: ignore[no-untyped-def]
    allowed = set(roles)

    def _dependency(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.role not in allowed:
            raise ForbiddenError(
                f"Role '{current_user.role}' is not permitted to perform this action.",
                details={"allowed_roles": sorted(allowed)},
            )
        return current_user

    return _dependency


def require_action(action: str):  # type: ignore[no-untyped-def]
    return require_roles(*ACTION_ROLES[action])

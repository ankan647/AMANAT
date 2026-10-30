from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import UnauthenticatedError
from app.core.permissions import CurrentUser, get_current_user, require_roles
from app.core.security import create_access_token, verify_password
from app.db.models import User
from app.db.session import get_db

router = APIRouter(prefix="/api/v1", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


def _user_out(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "bank_name": user.bank_name,
        "institution_id": user.institution_id,
    }


@router.post("/auth/login")
def login(body: LoginRequest, db: Session = Depends(get_db)) -> dict:
    user = db.query(User).filter(User.email == body.email).first()
    if user is None or not user.active or not verify_password(body.password, user.password_hash):
        raise UnauthenticatedError("Invalid email or password.")
    token, expires_in = create_access_token(
        sub=user.email, role=user.role, bank_name=user.bank_name, institution_id=user.institution_id
    )
    return {
        "data": {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": expires_in,
            "user": _user_out(user),
        }
    }


@router.get("/auth/me")
def me(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    user = db.query(User).filter(User.id == current_user.id).first()
    return {"data": _user_out(user)}


@router.get("/auth/demo-accounts")
def demo_accounts(db: Session = Depends(get_db)) -> list[dict]:
    settings = get_settings()
    if not settings.DEMO_MODE:
        return []
    users = db.query(User).filter(User.active.is_(True)).order_by(User.role, User.email).all()
    return [
        {
            "email": u.email,
            "name": u.name,
            "role": u.role,
            "description": f"{u.role.replace('_', ' ').title()}"
            + (f" — {u.bank_name}" if u.bank_name else ""),
        }
        for u in users
    ]


@router.get("/officers")
def officers(
    current_user: CurrentUser = Depends(
        require_roles("senior_approver", "competent_authority", "admin")
    ),
    db: Session = Depends(get_db),
) -> dict:
    users = (
        db.query(User)
        .filter(User.role.in_(["scrutiny", "senior_approver", "competent_authority"]), User.active.is_(True))
        .all()
    )
    return {"data": [_user_out(u) for u in users]}

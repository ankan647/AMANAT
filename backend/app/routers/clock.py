from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core import audit, audit_anchor, clock
from app.core.permissions import CurrentUser, require_roles
from app.db.session import get_anchor_db, get_db
from app.services import escalation, reminders

router = APIRouter(prefix="/api/v1/clock", tags=["clock"])

ADVANCE_ROLES = ("scrutiny", "senior_approver", "competent_authority", "admin")


@router.get("")
def get_clock() -> dict:
    return {"data": {"simulated_now": clock.now().isoformat(), "is_simulated": clock.is_simulated()}}


class AdvanceRequest(BaseModel):
    days: int = Field(ge=1, le=400)


def _fire_all(db: Session, anchor_db: Session, new_now: date) -> dict:
    reminder_events = reminders.fire_due_reminders(db, new_now)
    bank_events = escalation.process_overdue_bank_requests(db, new_now)
    anchors_created = 0
    # Anchoring daily on the simulated clock: anchor once per advance when the day changed.
    audit_anchor.anchor_now(db, anchor_db)
    anchors_created = 1

    events = reminder_events + bank_events
    fired = {
        "reminders": len([e for e in reminder_events if not e["kind"].endswith("overdue")]),
        "escalations": len([e for e in bank_events if e["kind"] == "bank_escalation"])
        + len([e for e in reminder_events if "t_30" in e["kind"] or "t_7" in e["kind"] or "overdue" in e["kind"]]),
        "bank_overdue": len([e for e in bank_events if e["kind"] == "bank_overdue"]),
        "anchors": anchors_created,
    }
    return {"simulated_now": new_now.isoformat(), "fired": fired, "events": events}


@router.post("/advance")
def advance(
    body: AdvanceRequest,
    current_user: CurrentUser = Depends(require_roles(*ADVANCE_ROLES)),
    db: Session = Depends(get_db),
    anchor_db: Session = Depends(get_anchor_db),
) -> dict:
    new_now = clock.advance_days(body.days).date()
    audit.record(
        db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="clock_advance",
        entity_type="app_clock",
        entity_id=None,
        details={"days": body.days, "new_now": new_now.isoformat()},
    )
    return {"data": _fire_all(db, anchor_db, new_now)}


class SetDateRequest(BaseModel):
    date: date


@router.post("/set")
def set_date(
    body: SetDateRequest,
    current_user: CurrentUser = Depends(require_roles(*ADVANCE_ROLES)),
    db: Session = Depends(get_db),
    anchor_db: Session = Depends(get_anchor_db),
) -> dict:
    new_now = clock.set_date(body.date).date()
    audit.record(
        db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="clock_set",
        entity_type="app_clock",
        entity_id=None,
        details={"new_now": new_now.isoformat()},
    )
    return {"data": _fire_all(db, anchor_db, new_now)}


@router.post("/reset")
def reset(
    current_user: CurrentUser = Depends(require_roles(*ADVANCE_ROLES)),
    db: Session = Depends(get_db),
    anchor_db: Session = Depends(get_anchor_db),
) -> dict:
    new_now = clock.reset().date()
    audit.record(
        db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="clock_reset",
        entity_type="app_clock",
        entity_id=None,
        details={"new_now": new_now.isoformat()},
    )
    return {"data": {"simulated_now": new_now.isoformat(), "fired": {"reminders": 0, "escalations": 0, "bank_overdue": 0, "anchors": 0}, "events": []}}

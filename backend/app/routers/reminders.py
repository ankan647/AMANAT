from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationFieldsError
from app.core.permissions import CurrentUser, get_current_user
from app.db.models import Notification, Reminder
from app.db.session import get_db
from app.services import reminders as reminders_service

router = APIRouter(prefix="/api/v1", tags=["reminders"])


def _reminder_out(r: Reminder) -> dict:
    return {
        "id": r.id,
        "instrument_id": r.instrument_id,
        "kind": r.kind,
        "due_on": r.due_on.isoformat(),
        "fired_on": r.fired_on.isoformat() if r.fired_on else None,
        "paused": r.paused,
        "pause_reason": r.pause_reason,
        "escalation_level": r.escalation_level,
    }


@router.get("/reminders")
def list_reminders(
    state: str | None = None,
    instrument_id: int | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    query = db.query(Reminder)
    if instrument_id is not None:
        query = query.filter(Reminder.instrument_id == instrument_id)
    rows = query.all()
    if state == "sent":
        rows = [r for r in rows if r.fired_on is not None]
    elif state == "pending":
        rows = [r for r in rows if r.fired_on is None and not r.paused]
    elif state == "paused":
        rows = [r for r in rows if r.paused]
    return {"data": [_reminder_out(r) for r in rows], "meta": {"page": 1, "page_size": len(rows), "total": len(rows)}}


@router.post("/reminders/{reminder_id}/pause")
def pause(
    reminder_id: int,
    body: dict,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    reason = body.get("reason", "")
    if not reason:
        raise ValidationFieldsError([{"path": "reason", "message": "A reason is required."}])
    try:
        reminder = reminders_service.pause_reminder(db, reminder_id, reason)
    except ValueError as exc:
        raise NotFoundError(str(exc)) from exc
    return {"data": _reminder_out(reminder)}


@router.post("/reminders/{reminder_id}/resume")
def resume(
    reminder_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        reminder = reminders_service.resume_reminder(db, reminder_id)
    except ValueError as exc:
        raise NotFoundError(str(exc)) from exc
    return {"data": _reminder_out(reminder)}


def _notification_out(n: Notification) -> dict:
    return {
        "id": n.id,
        "kind": n.kind,
        "message": n.message,
        "entity_type": n.entity_type,
        "entity_id": n.entity_id,
        "created_at": n.created_at.isoformat(),
        "read_at": n.read_at.isoformat() if n.read_at else None,
    }


@router.get("/notifications")
def list_notifications(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    rows = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )
    return {"data": [_notification_out(n) for n in rows], "meta": {"page": 1, "page_size": len(rows), "total": len(rows)}}


@router.post("/notifications/{notification_id}/read")
def mark_read(
    notification_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    from app.core.clock import now as clock_now

    n = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == current_user.id).first()
    if n is None:
        raise NotFoundError("Notification not found.")
    n.read_at = clock_now()
    db.add(n)
    db.commit()
    db.refresh(n)
    return {"data": _notification_out(n)}


@router.post("/notifications/read-all")
def mark_all_read(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    from app.core.clock import now as clock_now

    rows = db.query(Notification).filter(Notification.user_id == current_user.id, Notification.read_at.is_(None)).all()
    for n in rows:
        n.read_at = clock_now()
        db.add(n)
    db.commit()
    return {"data": {"updated": len(rows)}}

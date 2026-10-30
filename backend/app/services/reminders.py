"""Reminders and escalation driven by the simulated clock (spec 5.9)."""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core import audit
from app.core.calendar import move_to_prev_working_day, next_working_day
from app.core.clock import now
from app.db.models import Instrument, Notification, Reminder, User

REMINDER_OFFSETS_DAYS = {"t_90": 90, "t_60": 60, "t_30": 30, "t_7": 7}

RECIPIENT_ROLES = {
    "t_90": ["scrutiny", "institution"],
    "t_60": ["scrutiny", "institution"],
    "t_30": ["scrutiny", "institution", "senior_approver"],
    "t_7": ["scrutiny", "institution", "competent_authority"],
    "overdue": ["scrutiny", "institution", "competent_authority"],
}

ESCALATION_LEVEL_BY_KIND = {
    "t_90": 0,
    "t_60": 0,
    "t_30": 1,
    "t_7": 2,
    "overdue": 2,
}


def create_reminders_for_instrument(db: Session, instrument: Instrument) -> list[Reminder]:
    rows = []
    for kind, offset in REMINDER_OFFSETS_DAYS.items():
        raw_due = instrument.maturity_date - timedelta(days=offset)
        due_on = move_to_prev_working_day(raw_due)
        rows.append(
            Reminder(
                instrument_id=instrument.id,
                kind=kind,
                due_on=due_on,
                fired_on=None,
                paused=False,
                pause_reason="",
                escalation_level=ESCALATION_LEVEL_BY_KIND[kind],
                recipient_roles_json=RECIPIENT_ROLES[kind],
            )
        )
    overdue_due = next_working_day(instrument.maturity_date)
    rows.append(
        Reminder(
            instrument_id=instrument.id,
            kind="overdue",
            due_on=overdue_due,
            fired_on=None,
            paused=False,
            pause_reason="",
            escalation_level=ESCALATION_LEVEL_BY_KIND["overdue"],
            recipient_roles_json=RECIPIENT_ROLES["overdue"],
        )
    )
    db.add_all(rows)
    db.commit()
    for row in rows:
        db.refresh(row)
    return rows


def _notify_role(db: Session, role: str, instrument: Instrument, message: str, kind: str) -> None:
    if role == "institution":
        recipients = db.query(User).filter(User.institution_id == instrument.institution_id).all()
    else:
        recipients = db.query(User).filter(User.role == role, User.active.is_(True)).all()
    for user in recipients:
        db.add(
            Notification(
                user_id=user.id,
                kind=kind,
                message=message,
                entity_type="instrument",
                entity_id=instrument.id,
                created_at=now(),
                read_at=None,
            )
        )
    db.commit()


def fire_due_reminders(db: Session, today: date) -> list[dict]:
    pending = (
        db.query(Reminder)
        .filter(Reminder.fired_on.is_(None), Reminder.paused.is_(False), Reminder.due_on <= today)
        .order_by(Reminder.due_on.asc(), Reminder.id.asc())
        .all()
    )
    events = []
    for reminder in pending:
        instrument = db.query(Instrument).filter(Instrument.id == reminder.instrument_id).first()
        if instrument is None:
            continue
        reminder.fired_on = reminder.due_on
        db.add(reminder)
        db.commit()

        label = "overdue (matured with no linked renewal)" if reminder.kind == "overdue" else reminder.kind.replace("_", "-").upper()
        message = (
            f"Reminder {label} fired for FDR {instrument.fdr_number} "
            f"(maturity {instrument.maturity_date.isoformat()})."
        )
        for role in reminder.recipient_roles_json or []:
            _notify_role(db, role, instrument, message, kind=f"reminder_{reminder.kind}")

        audit.record(
            db,
            actor_id=None,
            actor_role="system",
            action="reminder_fired",
            entity_type="reminder",
            entity_id=reminder.id,
            details={"kind": reminder.kind, "instrument_id": instrument.id, "due_on": reminder.due_on.isoformat()},
        )
        events.append(
            {
                "kind": f"reminder_{reminder.kind}",
                "instrument_id": instrument.id,
                "institution_id": instrument.institution_id,
                "message": message,
            }
        )
    return events


def pause_reminder(db: Session, reminder_id: int, reason: str) -> Reminder:
    if not reason or not reason.strip():
        raise ValueError("A reason is required to pause a reminder.")
    reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
    if reminder is None:
        raise ValueError("Reminder not found.")
    reminder.paused = True
    reminder.pause_reason = reason
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


def resume_reminder(db: Session, reminder_id: int) -> Reminder:
    reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
    if reminder is None:
        raise ValueError("Reminder not found.")
    reminder.paused = False
    reminder.pause_reason = ""
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


def cancel_pending_reminders_for_instrument(db: Session, instrument_id: int) -> int:
    pending = (
        db.query(Reminder)
        .filter(Reminder.instrument_id == instrument_id, Reminder.fired_on.is_(None))
        .all()
    )
    count = 0
    for reminder in pending:
        reminder.paused = True
        reminder.pause_reason = "Cancelled: renewal linked."
        db.add(reminder)
        count += 1
    db.commit()
    return count

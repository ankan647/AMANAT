"""Bank-request overdue escalation, driven by the simulated clock (spec 5.8)."""

from datetime import date

from sqlalchemy.orm import Session

from app.core import audit
from app.core.calendar import add_working_days
from app.core.clock import now
from app.db.models import BankRequest, Instrument, Notification, User

ROLE_BY_LEVEL = {1: "senior_approver", 2: "competent_authority"}


def _notify_role(db: Session, role: str, bank_request: BankRequest, message: str) -> None:
    recipients = db.query(User).filter(User.role == role, User.active.is_(True)).all()
    for user in recipients:
        db.add(
            Notification(
                user_id=user.id,
                kind="bank_overdue",
                message=message,
                entity_type="bank_request",
                entity_id=bank_request.id,
                created_at=now(),
                read_at=None,
            )
        )
    db.commit()


def process_overdue_bank_requests(db: Session, today: date) -> list[dict]:
    events: list[dict] = []
    pending = db.query(BankRequest).filter(BankRequest.outcome == "pending").all()
    for req in pending:
        if req.due_date > today:
            continue
        instrument = db.query(Instrument).filter(Instrument.id == req.instrument_id).first()

        due_plus_1 = add_working_days(req.due_date, 1)
        due_plus_3 = add_working_days(req.due_date, 3)
        due_plus_7 = add_working_days(req.due_date, 7)

        if req.reminders_sent == 0 and today >= due_plus_1:
            req.reminders_sent = 1
            message = f"Bank request {req.request_code} is overdue (due {req.due_date.isoformat()})."
            _notify_role(db, "scrutiny", req, message)
            audit.record(
                db,
                actor_id=None,
                actor_role="system",
                action="bank_request_overdue",
                entity_type="bank_request",
                entity_id=req.id,
                details={"request_code": req.request_code},
            )
            events.append(
                {
                    "kind": "bank_overdue",
                    "instrument_id": req.instrument_id,
                    "institution_id": instrument.institution_id if instrument else None,
                    "message": message,
                }
            )

        for level, threshold in ((1, due_plus_3), (2, due_plus_7)):
            if req.escalation_level < level and today >= threshold:
                req.escalation_level = level
                role = ROLE_BY_LEVEL[level]
                message = (
                    f"Bank request {req.request_code} escalated to level {level} "
                    f"({role.replace('_', ' ')}): still pending since {req.sent_date.isoformat()}."
                )
                _notify_role(db, role, req, message)
                audit.record(
                    db,
                    actor_id=None,
                    actor_role="system",
                    action="bank_request_escalated",
                    entity_type="bank_request",
                    entity_id=req.id,
                    details={"request_code": req.request_code, "level": level},
                )
                events.append(
                    {
                        "kind": "bank_escalation",
                        "instrument_id": req.instrument_id,
                        "institution_id": instrument.institution_id if instrument else None,
                        "message": message,
                    }
                )
        db.add(req)
        db.commit()
    return events

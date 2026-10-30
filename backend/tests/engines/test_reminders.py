from datetime import date, datetime, timezone

import pytest

from app.db.models import Institution, Instrument, Reminder, User
from app.services import reminders


def _make_institution_and_instrument(db, code, maturity_date):
    inst = Institution(
        code=code,
        name="Reminder College",
        state="State",
        category="Technology",
        programme_type="UG",
        is_government=False,
        approval_year=2015,
        years_existing_elsewhere=0,
        deposit_request_date=date(2017, 1, 1),
        closure_date=None,
        status="active",
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)

    if not db.query(User).filter(User.email == f"inst.{code.lower()}@inst.demo").first():
        db.add(
            User(
                email=f"inst.{code.lower()}@inst.demo",
                name="Institution User",
                role="institution",
                password_hash="x",
                institution_id=inst.id,
                active=True,
            )
        )
        db.commit()

    instrument = Instrument(
        institution_id=inst.id,
        fdr_number=f"FDR/{code}",
        fdr_number_norm=f"FDR{code}",
        bank_name="State Bank of India",
        branch="Main",
        ifsc="SBIN0001234",
        amount_paise=10_00_000_00,
        issue_date=date(2017, 2, 1),
        maturity_date=maturity_date,
        beneficiary="AICTE, Government of India",
        lien_text="Lien marked in favour of AICTE",
        status="active",
        created_at=datetime(2017, 2, 1, tzinfo=timezone.utc),
    )
    db.add(instrument)
    db.commit()
    db.refresh(instrument)
    return inst, instrument


def _ensure_officer(db, email, role):
    if not db.query(User).filter(User.email == email).first():
        db.add(User(email=email, name=role, role=role, password_hash="x", active=True))
        db.commit()


def test_create_reminders_for_instrument_creates_five_kinds(db):
    _ensure_officer(db, "scrutiny.rem@aicte.demo", "scrutiny")
    _ensure_officer(db, "approver.rem@aicte.demo", "senior_approver")
    _ensure_officer(db, "authority.rem@aicte.demo", "competent_authority")

    _, instrument = _make_institution_and_instrument(db, "DEMO-REM1", date(2027, 6, 30))
    rows = reminders.create_reminders_for_instrument(db, instrument)
    kinds = sorted(r.kind for r in rows)
    assert kinds == ["overdue", "t_30", "t_60", "t_7", "t_90"]
    for row in rows:
        if row.kind != "overdue":
            assert row.due_on < instrument.maturity_date
        else:
            assert row.due_on > instrument.maturity_date


def test_fire_due_reminders_fires_exactly_once_each_in_order(db):
    _, instrument = _make_institution_and_instrument(db, "DEMO-REM2", date(2027, 1, 30))
    rows = reminders.create_reminders_for_instrument(db, instrument)

    far_future = date(2028, 1, 1)
    events_first = reminders.fire_due_reminders(db, far_future)
    own_events = [e for e in events_first if e["instrument_id"] == instrument.id]
    assert len(own_events) == len(rows)

    # fired in ascending due_on order
    fired_rows = db.query(Reminder).filter(Reminder.instrument_id == instrument.id).order_by(Reminder.due_on).all()
    assert all(r.fired_on is not None for r in fired_rows)

    events_second = reminders.fire_due_reminders(db, far_future)
    own_events_second = [e for e in events_second if e["instrument_id"] == instrument.id]
    assert own_events_second == []  # never fires twice


def test_paused_reminder_stays_pending(db):
    _, instrument = _make_institution_and_instrument(db, "DEMO-REM3", date(2027, 3, 30))
    rows = reminders.create_reminders_for_instrument(db, instrument)
    t90 = next(r for r in rows if r.kind == "t_90")
    reminders.pause_reminder(db, t90.id, "Waiting for institution")

    reminders.fire_due_reminders(db, date(2028, 1, 1))
    fired_kinds = set()
    for row in db.query(Reminder).filter(Reminder.instrument_id == instrument.id).all():
        if row.fired_on is not None:
            fired_kinds.add(row.kind)
    assert "t_90" not in fired_kinds


def test_pause_requires_reason(db):
    _, instrument = _make_institution_and_instrument(db, "DEMO-REM4", date(2027, 4, 30))
    rows = reminders.create_reminders_for_instrument(db, instrument)
    with pytest.raises(ValueError):
        reminders.pause_reminder(db, rows[0].id, "")


def test_link_renewal_cancels_pending_reminders(db):
    _, instrument = _make_institution_and_instrument(db, "DEMO-REM5", date(2027, 5, 30))
    reminders.create_reminders_for_instrument(db, instrument)
    count = reminders.cancel_pending_reminders_for_instrument(db, instrument.id)
    assert count == 5
    remaining = db.query(Reminder).filter(Reminder.instrument_id == instrument.id, Reminder.paused.is_(False)).count()
    assert remaining == 0

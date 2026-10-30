from datetime import date, datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.db.models import Institution, Instrument, InstrumentAssignment, ReleaseRequest, User


def _ensure_user(db, user_id, role="scrutiny"):
    if not db.query(User).filter(User.id == user_id).first():
        db.add(User(id=user_id, email=f"sod{user_id}@aicte.demo", name="Sod User", role=role, password_hash="x", active=True))
        db.commit()


def test_db_trigger_blocks_raw_insert_violating_sod(db):
    _ensure_user(db, 70001, "scrutiny")
    inst = Institution(
        code="UNIT-SODTRIGGER", name="Trigger College", state="State", category="Technology",
        programme_type="UG", is_government=False, approval_year=2015, years_existing_elsewhere=0,
        deposit_request_date=date(2015, 1, 1), closure_date=None, status="active",
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)

    instrument = Instrument(
        institution_id=inst.id, fdr_number="SBI/FDR/TRIG/1", fdr_number_norm="SBIFDRTRIG1",
        bank_name="State Bank of India", branch="Main", ifsc="SBIN0001234", amount_paise=1000000,
        issue_date=date(2015, 1, 10), maturity_date=date(2025, 1, 10), beneficiary="AICTE, Government of India",
        lien_text="Lien marked in favour of AICTE, pledged", status="active",
        created_at=datetime(2015, 1, 10, tzinfo=timezone.utc),
    )
    db.add(instrument)
    db.commit()
    db.refresh(instrument)

    db.add(InstrumentAssignment(instrument_id=instrument.id, officer_id=70001, role="scrutiniser", assigned_at=datetime(2015, 1, 10, tzinfo=timezone.utc)))
    db.commit()

    rr = ReleaseRequest(instrument_id=instrument.id, requested_by=70001, requested_on=date(2025, 1, 11), status="ready", needs_second_approval=False)
    db.add(rr)
    db.commit()
    db.refresh(rr)

    # Raw INSERT, bypassing the Python service layer entirely.
    with pytest.raises(IntegrityError):
        db.execute(
            text(
                "INSERT INTO approval (release_request_id, approver_id, level, decision, remarks, decided_at) "
                "VALUES (:rr_id, :approver_id, 1, 'approved', '', :decided_at)"
            ),
            {"rr_id": rr.id, "approver_id": 70001, "decided_at": datetime(2026, 1, 1, tzinfo=timezone.utc)},
        )
        db.commit()
    db.rollback()

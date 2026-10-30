from datetime import date, datetime, timezone

import pytest

from app.core.errors import SodViolationError
from app.db.models import AuditLog, Institution, Instrument, InstrumentAssignment, ReleaseRequest, User
from app.services import release


def _ensure_user(db, user_id, role="scrutiny"):
    if not db.query(User).filter(User.id == user_id).first():
        db.add(User(id=user_id, email=f"sodaudit{user_id}@aicte.demo", name="Sod Audit User", role=role, password_hash="x", active=True))
        db.commit()


def test_blocked_sod_attempt_writes_audit_entry(db):
    _ensure_user(db, 80001, "scrutiny")
    inst = Institution(
        code="UNIT-SODAUDIT", name="Audit College", state="State", category="Technology",
        programme_type="UG", is_government=False, approval_year=2015, years_existing_elsewhere=0,
        deposit_request_date=date(2015, 1, 1), closure_date=None, status="active",
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)

    instrument = Instrument(
        institution_id=inst.id, fdr_number="SBI/FDR/AUDIT/1", fdr_number_norm="SBIFDRAUDIT1",
        bank_name="State Bank of India", branch="Main", ifsc="SBIN0001234", amount_paise=1000000,
        issue_date=date(2015, 1, 10), maturity_date=date(2025, 1, 10), beneficiary="AICTE, Government of India",
        lien_text="Lien marked in favour of AICTE, pledged", status="active",
        created_at=datetime(2015, 1, 10, tzinfo=timezone.utc),
    )
    db.add(instrument)
    db.commit()
    db.refresh(instrument)

    db.add(InstrumentAssignment(instrument_id=instrument.id, officer_id=80001, role="scrutiniser", assigned_at=datetime(2015, 1, 10, tzinfo=timezone.utc)))
    db.commit()

    rr = ReleaseRequest(instrument_id=instrument.id, requested_by=80001, requested_on=date(2025, 1, 11), status="ready", needs_second_approval=False)
    db.add(rr)
    db.commit()
    db.refresh(rr)

    before_count = db.query(AuditLog).filter(AuditLog.action == "sod_violation_blocked").count()

    with pytest.raises(SodViolationError):
        release.enforce_sod_for_approval(
            db, release_request=rr, instrument_id=instrument.id, approver_id=80001,
            approver_role="senior_approver", level=1,
        )

    after_count = db.query(AuditLog).filter(AuditLog.action == "sod_violation_blocked").count()
    assert after_count == before_count + 1

    last_entry = db.query(AuditLog).filter(AuditLog.action == "sod_violation_blocked").order_by(AuditLog.seq.desc()).first()
    assert last_entry.details_json["rule"] == "scrutiniser_cannot_approve"

from datetime import date, datetime, timezone

import pytest

from app.core.errors import SodViolationError
from app.db.models import (
    Approval,
    Document,
    Institution,
    Instrument,
    InstrumentAssignment,
    ReleaseRequest,
)
from app.db.models import User
from app.services import release


def _ensure_user(db, user_id, role="scrutiny"):
    if not db.query(User).filter(User.id == user_id).first():
        db.add(
            User(
                id=user_id,
                email=f"user{user_id}@aicte.demo",
                name=f"User {user_id}",
                role=role,
                password_hash="x",
                active=True,
            )
        )
        db.commit()


def _setup(db, code, scrutiniser_id, amount_paise=40_00_000_00, with_docs=True, with_hold=False):
    _ensure_user(db, scrutiniser_id)
    inst = Institution(
        code=code,
        name="Release College",
        state="State",
        category="Technology",
        programme_type="UG",
        is_government=False,
        approval_year=2010,
        years_existing_elsewhere=0,
        deposit_request_date=date(2015, 6, 1),
        closure_date=None,
        status="active",
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)

    instrument = Instrument(
        institution_id=inst.id,
        fdr_number=f"FDR/{code}",
        fdr_number_norm=f"FDR{code}",
        bank_name="State Bank of India",
        branch="Main",
        ifsc="SBIN0001234",
        amount_paise=amount_paise,
        issue_date=date(2015, 6, 10),
        maturity_date=date(2025, 6, 10),
        beneficiary="AICTE, Government of India",
        lien_text="Lien marked in favour of AICTE, pledged",
        status="active",
        created_at=datetime(2015, 6, 10, tzinfo=timezone.utc),
    )
    db.add(instrument)
    db.commit()
    db.refresh(instrument)

    db.add(
        InstrumentAssignment(
            instrument_id=instrument.id,
            officer_id=scrutiniser_id,
            role="scrutiniser",
            assigned_at=datetime(2015, 6, 10, tzinfo=timezone.utc),
        )
    )
    db.commit()

    if with_docs:
        for kind in ("fdr_scan", "affidavit", "release_application"):
            db.add(
                Document(
                    instrument_id=instrument.id,
                    kind=kind,
                    filename=f"{kind}.pdf",
                    sha256="0" * 64,
                    mime="application/pdf",
                    size=1,
                    ocr_text="",
                    pdf_metadata_json={},
                    scan_status="clean",
                    storage_path="/tmp/x.pdf",
                    created_at=datetime(2025, 6, 11, tzinfo=timezone.utc),
                )
            )
        db.commit()

    release_request = ReleaseRequest(
        instrument_id=instrument.id,
        requested_by=scrutiniser_id,
        requested_on=date(2025, 6, 11),
        reason="Term completed",
        status="ready",
        needs_second_approval=amount_paise > 5_00_000_00 * 100,
    )
    db.add(release_request)
    db.commit()
    db.refresh(release_request)

    if with_hold:
        from app.db.models import Hold

        db.add(
            Hold(
                institution_id=None,
                instrument_id=instrument.id,
                reason="Inquiry ref VIG/2026/114",
                source="vigilance",
                placed_by=scrutiniser_id,
                placed_on=date(2025, 6, 11),
                lifted_on=None,
            )
        )
        db.commit()

    return inst, instrument, release_request


def test_r1_precheck_eligible_single_approver(db):
    inst, instrument, rr = _setup(db, "DEMO-R1", scrutiniser_id=1001)
    result = release.run_precheck(
        db, institution=inst, instrument=instrument, term_years=10, exempt=False, on_date=date(2026, 10, 30)
    )
    assert result.verdict in ("eligible", "eligible_with_conditions")  # verification not confirmed yet


def test_r3_scrutiniser_cannot_approve(db):
    inst, instrument, rr = _setup(db, "DEMO-R3", scrutiniser_id=2001)
    with pytest.raises(SodViolationError) as exc_info:
        release.enforce_sod_for_approval(
            db,
            release_request=rr,
            instrument_id=instrument.id,
            approver_id=2001,
            approver_role="senior_approver",
            level=1,
        )
    assert exc_info.value.details["rule"] == "scrutiniser_cannot_approve"


def test_different_approver_passes_sod(db):
    inst, instrument, rr = _setup(db, "DEMO-R1B", scrutiniser_id=3001)
    _ensure_user(db, 4001)
    release.enforce_sod_for_approval(
        db,
        release_request=rr,
        instrument_id=instrument.id,
        approver_id=4001,
        approver_role="senior_approver",
        level=1,
    )  # should not raise


def test_r2_second_approver_must_differ(db):
    inst, instrument, rr = _setup(db, "DEMO-R2", scrutiniser_id=5001)
    _ensure_user(db, 6001)
    db.add(
        Approval(
            release_request_id=rr.id,
            approver_id=6001,
            level=1,
            decision="approved",
            decided_at=datetime(2026, 10, 30, tzinfo=timezone.utc),
        )
    )
    db.commit()
    with pytest.raises(SodViolationError) as exc_info:
        release.enforce_sod_for_approval(
            db,
            release_request=rr,
            instrument_id=instrument.id,
            approver_id=6001,
            approver_role="competent_authority",
            level=2,
        )
    assert exc_info.value.details["rule"] == "second_approver_must_differ"


def test_admin_cannot_approve(db):
    inst, instrument, rr = _setup(db, "DEMO-ADMIN", scrutiniser_id=7001)
    _ensure_user(db, 8001, role="admin")
    with pytest.raises(SodViolationError) as exc_info:
        release.enforce_sod_for_approval(
            db,
            release_request=rr,
            instrument_id=instrument.id,
            approver_id=8001,
            approver_role="admin",
            level=1,
        )
    assert exc_info.value.details["rule"] == "admin_cannot_approve"


def test_f_release_blocked_by_open_hold(db):
    inst, instrument, rr = _setup(db, "DEMO-F", scrutiniser_id=9001, with_hold=True)
    result = release.run_precheck(
        db, institution=inst, instrument=instrument, term_years=10, exempt=False, on_date=date(2026, 10, 30)
    )
    assert result.verdict == "blocked"
    assert len(result.holds) == 1


def test_blocked_when_term_not_complete(db):
    inst, instrument, rr = _setup(db, "DEMO-EARLY", scrutiniser_id=10001)
    result = release.run_precheck(
        db, institution=inst, instrument=instrument, term_years=10, exempt=False, on_date=date(2020, 1, 1)
    )
    assert result.verdict == "blocked"


def test_blocked_when_documents_missing(db):
    inst, instrument, rr = _setup(db, "DEMO-NODOCS", scrutiniser_id=11001, with_docs=False)
    result = release.run_precheck(
        db, institution=inst, instrument=instrument, term_years=10, exempt=False, on_date=date(2026, 10, 30)
    )
    assert result.verdict == "blocked"
    assert "fdr_scan" in result.missing_documents

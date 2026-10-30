"""Release workflow pre-check and separation-of-duties enforcement (spec 5.10)."""

from dataclasses import dataclass, field
from datetime import date

from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session

from app.core.errors import SodViolationError
from app.db.enums import FieldGrade
from app.services.confidence import get_fields, instrument_grade
from app.db.models import (
    Approval,
    Document,
    Hold,
    Institution,
    Instrument,
    InstrumentAssignment,
    ReleaseRequest,
)

REQUIRED_DOCUMENT_KINDS = {"fdr_scan", "affidavit", "release_application"}
PENALTY_GRACE_DAYS = 7
PENALTY_PERCENT = 10


def term_completed(institution: Institution, term_years: int, on_date: date) -> bool:
    if institution.closure_date is not None:
        return on_date >= institution.closure_date
    return on_date >= institution.deposit_request_date + relativedelta(years=term_years)


def release_request_allowed(institution: Institution, term_years: int, on_date: date) -> bool:
    if institution.closure_date is not None:
        return on_date >= institution.closure_date
    return term_completed(institution, term_years, on_date)


def scrutiniser_for(db: Session, instrument_id: int) -> int | None:
    row = (
        db.query(InstrumentAssignment)
        .filter(InstrumentAssignment.instrument_id == instrument_id, InstrumentAssignment.role == "scrutiniser")
        .order_by(InstrumentAssignment.assigned_at.desc())
        .first()
    )
    return row.officer_id if row else None


@dataclass
class PrecheckResult:
    verdict: str
    checks: list[dict] = field(default_factory=list)
    penalties: list[dict] = field(default_factory=list)
    holds: list[dict] = field(default_factory=list)
    missing_documents: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "checks": self.checks,
            "penalties": self.penalties,
            "holds": self.holds,
            "missing_documents": self.missing_documents,
        }


def run_precheck(
    db: Session,
    *,
    institution: Institution,
    instrument: Instrument,
    term_years: int,
    exempt: bool,
    on_date: date,
) -> PrecheckResult:
    checks: list[dict] = []
    blocking = False

    completed = term_completed(institution, term_years, on_date)
    checks.append(
        {
            "key": "term_or_closure",
            "label": "Term completed or institution closed",
            "passed": completed,
            "severity": "block",
            "detail": f"Checked against {on_date.isoformat()}.",
        }
    )
    if not completed:
        blocking = True

    penalties = []
    penalty_settled_check_passed = True
    if (
        not exempt
        and instrument.intimation_date is not None
        and instrument.proof_received_date is not None
    ):
        delay_days = (instrument.proof_received_date - instrument.intimation_date).days
        if delay_days > PENALTY_GRACE_DAYS:
            penalty_amount = instrument.amount_paise * PENALTY_PERCENT // 100
            penalties.append(
                {"kind": "late_proof", "percent": PENALTY_PERCENT, "amount_paise": penalty_amount}
            )
            penalty_settled_check_passed = instrument.penalty_settled
    checks.append(
        {
            "key": "penalty",
            "label": "Penalty for late proof (if any) is settled",
            "passed": penalty_settled_check_passed,
            "severity": "condition",
            "detail": "10% penalty applies when proof arrives more than 7 days after intimation.",
        }
    )

    documents = db.query(Document).filter(Document.instrument_id == instrument.id).all()
    present_kinds = {d.kind for d in documents}
    missing = sorted(REQUIRED_DOCUMENT_KINDS - present_kinds)
    checks.append(
        {
            "key": "documents",
            "label": "Required documents present",
            "passed": not missing,
            "severity": "block",
            "detail": f"Missing: {', '.join(missing)}" if missing else "All present.",
        }
    )
    if missing:
        blocking = True

    holds = (
        db.query(Hold)
        .filter(
            Hold.lifted_on.is_(None),
            (Hold.instrument_id == instrument.id) | (Hold.institution_id == institution.id),
        )
        .all()
    )
    hold_dicts = [
        {"id": h.id, "reason": h.reason, "source": h.source, "placed_on": h.placed_on.isoformat()}
        for h in holds
    ]
    checks.append(
        {
            "key": "holds",
            "label": "No open holds",
            "passed": not holds,
            "severity": "block",
            "detail": "Open hold(s) found." if holds else "None.",
        }
    )
    if holds:
        blocking = True

    fields = get_fields(db, instrument.id)
    grade = instrument_grade(fields) if fields else FieldGrade.claimed.value
    verification_ok = grade == FieldGrade.bank_confirmed.value
    checks.append(
        {
            "key": "verification",
            "label": "Instrument is bank-confirmed",
            "passed": verification_ok,
            "severity": "info",
            "detail": f"Current grade: {grade}.",
        }
    )

    if blocking:
        verdict = "blocked"
    elif not penalty_settled_check_passed or not verification_ok:
        verdict = "eligible_with_conditions"
    else:
        verdict = "eligible"

    return PrecheckResult(
        verdict=verdict, checks=checks, penalties=penalties, holds=hold_dicts, missing_documents=missing
    )


def enforce_sod_for_approval(
    db: Session,
    *,
    release_request: ReleaseRequest,
    instrument_id: int,
    approver_id: int,
    approver_role: str,
    level: int,
) -> None:
    if approver_role == "admin":
        raise SodViolationError(
            "Admins cannot approve or edit case records.", rule="admin_cannot_approve"
        )

    scrutiniser_id = scrutiniser_for(db, instrument_id)
    if scrutiniser_id is not None and approver_id == scrutiniser_id:
        raise SodViolationError(
            "You scrutinised this FDR, so you cannot approve its release.",
            rule="scrutiniser_cannot_approve",
        )

    if level == 2:
        existing = (
            db.query(Approval)
            .filter(Approval.release_request_id == release_request.id, Approval.level == 1)
            .first()
        )
        if existing is not None and existing.approver_id == approver_id:
            raise SodViolationError(
                "The level-2 approver must be different from the level-1 approver.",
                rule="second_approver_must_differ",
            )

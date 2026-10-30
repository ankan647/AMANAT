from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.clock import today as clock_today
from app.core.errors import ForbiddenError, NotFoundError
from app.core.permissions import CurrentUser, get_current_user
from app.db.models import (
    AnomalyFlag,
    BankRequest,
    Hold,
    Institution,
    Reminder,
)
from app.db.session import get_db
from app.services import coverage as coverage_service
from app.services import institution_view

router = APIRouter(prefix="/api/v1/institutions", tags=["institutions"])


def _assert_institution_access(current_user: CurrentUser, institution_id: int) -> None:
    if current_user.role == "institution" and current_user.institution_id != institution_id:
        raise ForbiddenError("You can only see your own institution's data.")


def _row_for(db: Session, inst: Institution, today) -> dict:
    view = institution_view.build_institution_view(db, inst, today)
    cov = view.coverage_result.as_dict()
    return {
        "id": inst.id,
        "code": inst.code,
        "name": inst.name,
        "state": inst.state,
        "category": inst.category,
        "coverage": cov,
        "confidence_pct": view.confidence_pct,
        "matrix_cell": view.matrix_cell,
        "next_action": institution_view.next_action_for(view.matrix_cell),
        "next_maturity": (
            institution_view.next_maturity_for(view.instruments, today).isoformat()
            if institution_view.next_maturity_for(view.instruments, today)
            else None
        ),
    }


@router.get("")
def list_institutions(
    status: str | None = None,
    state: str | None = None,
    category: str | None = None,
    matrix_cell: str | None = None,
    confidence_lt: int | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = Query(25, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    today = clock_today()
    query = db.query(Institution)
    if current_user.role == "institution":
        query = query.filter(Institution.id == current_user.institution_id)
    if state:
        query = query.filter(Institution.state == state)
    if category:
        query = query.filter(Institution.category == category)
    if q:
        query = query.filter(Institution.name.ilike(f"%{q}%") | Institution.code.ilike(f"%{q}%"))
    institutions = query.all()

    rows = [_row_for(db, inst, today) for inst in institutions]
    if status:
        rows = [r for r in rows if r["coverage"]["status"] == status]
    if matrix_cell:
        rows = [r for r in rows if r["matrix_cell"] == matrix_cell]
    if confidence_lt is not None:
        rows = [r for r in rows if r["confidence_pct"] is not None and r["confidence_pct"] < confidence_lt]

    total = len(rows)
    start = (page - 1) * page_size
    page_rows = rows[start : start + page_size]
    return {"data": page_rows, "meta": {"page": page, "page_size": page_size, "total": total}}


@router.get("/{institution_id}")
def get_institution(
    institution_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _assert_institution_access(current_user, institution_id)
    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if inst is None:
        raise NotFoundError("Institution not found.")
    today = clock_today()
    view = institution_view.build_institution_view(db, inst, today)

    instrument_ids = [i.id for i in view.instruments]
    open_flags = (
        db.query(AnomalyFlag)
        .filter(AnomalyFlag.instrument_id.in_(instrument_ids), AnomalyFlag.status == "open")
        .all()
        if instrument_ids
        else []
    )
    bank_requests = (
        db.query(BankRequest).filter(BankRequest.instrument_id.in_(instrument_ids)).all()
        if instrument_ids
        else []
    )
    reminders_rows = (
        db.query(Reminder).filter(Reminder.instrument_id.in_(instrument_ids)).all()
        if instrument_ids
        else []
    )
    holds = (
        db.query(Hold)
        .filter(
            Hold.lifted_on.is_(None),
            (Hold.institution_id == institution_id) | (Hold.instrument_id.in_(instrument_ids or [-1])),
        )
        .all()
    )

    rule_version = view.rule_result.rule_version
    rule_applied = None
    if rule_version is not None:
        from app.db.models import Rule

        rule = db.query(Rule).filter(Rule.id == rule_version.rule_id).first()
        rule_applied = {
            "rule_version_id": rule_version.id,
            "rule_key": rule.key if rule else None,
            "version": rule_version.version,
            "title": rule.title if rule else None,
            "reason_text": view.rule_result.reason_text,
        }

    return {
        "data": {
            "institution": {
                "id": inst.id,
                "code": inst.code,
                "name": inst.name,
                "state": inst.state,
                "category": inst.category,
                "programme_type": inst.programme_type,
                "is_government": inst.is_government,
                "approval_year": inst.approval_year,
                "years_existing_elsewhere": inst.years_existing_elsewhere,
                "deposit_request_date": inst.deposit_request_date.isoformat(),
                "closure_date": inst.closure_date.isoformat() if inst.closure_date else None,
                "status": inst.status,
                "coverage": view.coverage_result.as_dict(),
                "confidence_pct": view.confidence_pct,
            },
            "rule_applied": rule_applied,
            "instruments": [
                {
                    "id": i.id,
                    "fdr_number": i.fdr_number,
                    "bank_name": i.bank_name,
                    "amount_paise": i.amount_paise,
                    "issue_date": i.issue_date.isoformat(),
                    "maturity_date": i.maturity_date.isoformat(),
                    "status": i.status,
                }
                for i in view.instruments
            ],
            "open_flags": [{"id": f.id, "type": f.type, "title": f.title, "severity": f.severity} for f in open_flags],
            "bank_requests": [
                {"id": b.id, "request_code": b.request_code, "outcome": b.outcome, "due_date": b.due_date.isoformat()}
                for b in bank_requests
            ],
            "reminders": [
                {"id": r.id, "kind": r.kind, "due_on": r.due_on.isoformat(), "fired_on": r.fired_on.isoformat() if r.fired_on else None, "paused": r.paused}
                for r in reminders_rows
            ],
            "holds": [
                {"id": h.id, "reason": h.reason, "source": h.source, "placed_on": h.placed_on.isoformat()}
                for h in holds
            ],
        }
    }


@router.get("/{institution_id}/coverage-timeline")
def coverage_timeline(
    institution_id: int,
    from_: str | None = Query(None, alias="from"),
    to: str | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _assert_institution_access(current_user, institution_id)
    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if inst is None:
        raise NotFoundError("Institution not found.")
    today = clock_today()
    view = institution_view.build_institution_view(db, inst, today)
    rule_result = view.rule_result

    points = sorted(
        {today, rule_result.period_end}
        | {i.issue_date for i in view.instruments}
        | {i.maturity_date for i in view.instruments}
    )
    points = [p for p in points if today <= p <= rule_result.period_end]

    required_series = []
    valid_series = []
    for p in points:
        required_amount = rule_result.amount_paise if rule_result.period_start <= p < rule_result.period_end else 0
        required_series.append({"date": p.isoformat(), "paise": required_amount})
        contributing = coverage_service.contributing_instruments_on(view.instruments, p)
        valid_series.append(
            {
                "date": p.isoformat(),
                "paise": sum(i.amount_paise for i in contributing),
                "instruments": [{"id": i.id, "fdr_number": i.fdr_number, "paise": i.amount_paise} for i in contributing],
            }
        )

    return {
        "data": {
            "status": view.coverage_result.status,
            "required": required_series,
            "valid": valid_series,
            "gaps": [g.as_dict() for g in view.coverage_result.gaps],
            "today": today.isoformat(),
        }
    }


@router.get("/{institution_id}/why-rule")
def why_rule(
    institution_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _assert_institution_access(current_user, institution_id)
    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if inst is None:
        raise NotFoundError("Institution not found.")
    today = clock_today()
    view = institution_view.build_institution_view(db, inst, today)
    rule_result = view.rule_result

    steps = [
        {"label": "Deposit obligation date", "detail": f"Institution's deposit was requested on {inst.deposit_request_date.isoformat()}."},
        {"label": "Rule selected", "detail": rule_result.reason_text},
    ]
    if rule_result.exempt:
        steps.append({"label": "Exemption", "detail": rule_result.exempt_reason})
    else:
        steps.append(
            {
                "label": "Required amount",
                "detail": f"{rule_result.amount_paise} paise required from {rule_result.period_start.isoformat()} "
                f"to {rule_result.period_end.isoformat()}.",
            }
        )
    return {
        "data": {
            "steps": steps,
            "rule_version_id": rule_result.rule_version.id if rule_result.rule_version else None,
        }
    }

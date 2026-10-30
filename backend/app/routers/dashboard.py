from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.clock import today as clock_today
from app.core.config import get_settings
from app.core.permissions import CurrentUser, get_current_user
from app.db.models import AnomalyFlag, BankRequest, Institution, ReleaseRequest
from app.db.session import get_db
from app.services import dashboard as dashboard_service
from app.services import institution_view

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


def _build_rows(db: Session) -> list[dashboard_service.InstitutionRow]:
    today = clock_today()
    institutions = db.query(Institution).all()
    rows = []
    for inst in institutions:
        view = institution_view.build_institution_view(db, inst, today)
        bank_confirmed = institution_view.bank_confirmed_paise_for(db, _valid_now(view, today))
        open_flags_count = (
            db.query(AnomalyFlag)
            .filter(AnomalyFlag.status == "open")
            .filter(AnomalyFlag.instrument_id.in_([i.id for i in view.instruments]) if view.instruments else False)
            .count()
            if view.instruments
            else 0
        )
        overdue_count = (
            db.query(BankRequest)
            .filter(BankRequest.outcome == "pending")
            .filter(BankRequest.instrument_id.in_([i.id for i in view.instruments]) if view.instruments else False)
            .filter(BankRequest.due_date < today)
            .count()
            if view.instruments
            else 0
        )
        releases_pending_count = (
            db.query(ReleaseRequest)
            .filter(ReleaseRequest.status.in_(["ready", "approver1_done"]))
            .filter(ReleaseRequest.instrument_id.in_([i.id for i in view.instruments]) if view.instruments else False)
            .count()
            if view.instruments
            else 0
        )
        next_maturity = institution_view.next_maturity_for(view.instruments, today)
        rows.append(
            dashboard_service.InstitutionRow(
                institution_id=inst.id,
                status=view.coverage_result.status,
                confidence_pct=view.confidence_pct,
                required_paise=view.coverage_result.required_paise,
                valid_paise=view.coverage_result.valid_paise,
                bank_confirmed_paise=bank_confirmed,
                open_flags=open_flags_count,
                overdue_bank_requests=overdue_count,
                next_maturity_within_90d=bool(next_maturity and (next_maturity - today).days <= 90),
                releases_pending=releases_pending_count,
            )
        )
    return rows


def _valid_now(view, today):
    from app.services.coverage import contributing_instruments_on

    return contributing_instruments_on(view.instruments, today)


@router.get("/summary")
def summary(
    current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    rows = _build_rows(db)
    return {"data": dashboard_service.build_summary(rows, as_of=clock_today().isoformat())}


@router.get("/priority-matrix")
def priority_matrix(
    current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    settings = get_settings()
    rows = _build_rows(db)
    return {"data": dashboard_service.build_priority_matrix(rows, settings.CONFIDENCE_HIGH_THRESHOLD)}


@router.get("/activity")
def activity(
    limit: int = Query(20, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    from app.db.models import AuditLog

    rows = db.query(AuditLog).order_by(AuditLog.seq.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "ts": r.ts.isoformat(),
            "kind": r.action,
            "message": f"{r.action} on {r.entity_type} #{r.entity_id}" if r.entity_id else r.action,
            "institution_id": None,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
        }
        for r in rows
    ]

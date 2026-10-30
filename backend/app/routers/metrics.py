from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.clock import today as clock_today
from app.core.permissions import CurrentUser, get_current_user
from app.db.models import BankRequest, Institution, Instrument, ReleaseRequest
from app.db.session import get_db
from app.services import coverage as coverage_service
from app.services import institution_view
from app.services.metrics import KpiInputs, compute_kpis

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


@router.get("/kpis")
def kpis(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    today = clock_today()
    institutions = db.query(Institution).all()

    total_valid = 0
    total_confirmed = 0
    for inst in institutions:
        view = institution_view.build_institution_view(db, inst, today)
        valid_now = coverage_service.contributing_instruments_on(view.instruments, today)
        total_valid += sum(i.amount_paise for i in valid_now)
        total_confirmed += institution_view.bank_confirmed_paise_for(db, valid_now)
    confirmed_deposit_share_pct = round(total_confirmed / total_valid * 100, 1) if total_valid else 0.0

    responded = db.query(BankRequest).filter(BankRequest.outcome != "pending").all()
    days = [(r.response_date - r.sent_date).days for r in responded if r.response_date]
    avg_days_to_bank_confirmation = round(sum(days) / len(days), 1) if days else 0.0

    from app.db.models import AnomalyFlag

    decided_flags = db.query(AnomalyFlag).filter(AnomalyFlag.status != "open").all()
    confirmed_flags = [f for f in decided_flags if f.status in ("returned", "referred")]
    flags_confirmed_share_pct = (
        round(len(confirmed_flags) / len(decided_flags) * 100, 1) if decided_flags else 0.0
    )

    matured_instruments = db.query(Instrument).filter(Instrument.status.in_(["matured", "renewed", "released"])).all()
    handled_before_deadline = 0
    for i in matured_instruments:
        if i.linked_from_instrument_id is not None or i.status in ("renewed", "released"):
            handled_before_deadline += 1
    maturities_handled_before_deadline_pct = (
        round(handled_before_deadline / len(matured_instruments) * 100, 1) if matured_instruments else 0.0
    )

    decided_releases = db.query(ReleaseRequest).filter(ReleaseRequest.status.in_(["approved", "rejected"])).all()
    release_days = [(today - r.requested_on).days for r in decided_releases]
    avg_days_to_release_decision = round(sum(release_days) / len(release_days), 1) if release_days else 0.0

    return {
        "data": compute_kpis(
            KpiInputs(
                confirmed_deposit_share_pct=confirmed_deposit_share_pct,
                avg_days_to_bank_confirmation=avg_days_to_bank_confirmation,
                flags_confirmed_share_pct=flags_confirmed_share_pct,
                maturities_handled_before_deadline_pct=maturities_handled_before_deadline_pct,
                avg_days_to_release_decision=avg_days_to_release_decision,
            )
        )
    }

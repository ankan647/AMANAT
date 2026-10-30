from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core import audit
from app.core.clock import now as clock_now
from app.core.clock import today as clock_today
from app.core.errors import InvalidStateError, NotFoundError, ValidationFieldsError
from app.core.permissions import CurrentUser, get_current_user, require_roles
from app.db.models import (
    Approval,
    Hold,
    Institution,
    Instrument,
    ReleaseRequest,
)
from app.db.session import get_db
from app.services import orders as orders_service
from app.services import release as release_service
from app.services import rules_engine

router = APIRouter(prefix="/api/v1", tags=["releases"])


def _release_out(r: ReleaseRequest) -> dict:
    return {
        "id": r.id,
        "instrument_id": r.instrument_id,
        "requested_by": r.requested_by,
        "requested_on": r.requested_on.isoformat(),
        "reason": r.reason,
        "precheck_verdict": r.precheck_verdict,
        "status": r.status,
        "needs_second_approval": r.needs_second_approval,
    }


def _run_and_store_precheck(db: Session, release_request: ReleaseRequest, instrument: Instrument) -> release_service.PrecheckResult:
    institution = db.query(Institution).filter(Institution.id == instrument.institution_id).first()
    rule_result = rules_engine.resolve_for_institution(db, institution)
    result = release_service.run_precheck(
        db,
        institution=institution,
        instrument=instrument,
        term_years=10,
        exempt=rule_result.exempt,
        on_date=clock_today(),
    )
    release_request.precheck_verdict = result.verdict
    release_request.precheck_json = result.as_dict()
    release_request.status = "blocked" if result.verdict == "blocked" else release_request.status
    db.add(release_request)
    db.commit()
    return result


@router.post("/releases")
def create_release(
    body: dict,
    current_user: CurrentUser = Depends(require_roles("institution", "scrutiny")),
    db: Session = Depends(get_db),
) -> dict:
    instrument = db.query(Instrument).filter(Instrument.id == body["instrument_id"]).first()
    if instrument is None:
        raise NotFoundError("Instrument not found.")

    from app.core.config import get_settings

    settings = get_settings()
    rr = ReleaseRequest(
        instrument_id=instrument.id,
        requested_by=current_user.id,
        requested_on=clock_today(),
        reason=body.get("reason", ""),
        status="ready",
        needs_second_approval=instrument.amount_paise > settings.HIGH_VALUE_THRESHOLD_PAISE,
    )
    db.add(rr)
    db.commit()
    db.refresh(rr)

    _run_and_store_precheck(db, rr, instrument)

    audit.record(
        db, actor_id=current_user.id, actor_role=current_user.role, action="release_requested",
        entity_type="release_request", entity_id=rr.id, details={"instrument_id": instrument.id},
    )
    return {"data": _release_out(rr)}


@router.get("/releases")
def list_releases(
    status: str | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    query = db.query(ReleaseRequest)
    if status:
        query = query.filter(ReleaseRequest.status == status)
    rows = query.all()
    return {"data": [_release_out(r) for r in rows], "meta": {"page": 1, "page_size": len(rows), "total": len(rows)}}


@router.get("/releases/{release_id}")
def get_release(
    release_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    rr = db.query(ReleaseRequest).filter(ReleaseRequest.id == release_id).first()
    if rr is None:
        raise NotFoundError("Release request not found.")
    instrument = db.query(Instrument).filter(Instrument.id == rr.instrument_id).first()
    approvals = db.query(Approval).filter(Approval.release_request_id == rr.id).all()
    from app.db.models import SignedOrder

    order = db.query(SignedOrder).filter(SignedOrder.release_request_id == rr.id).first()

    scrutiniser_id = release_service.scrutiniser_for(db, instrument.id) if instrument else None
    blocked_for_current_user = current_user.role == "institution" or (
        scrutiniser_id is not None and current_user.id == scrutiniser_id
    )
    return {
        "data": {
            "release": _release_out(rr),
            "instrument": {"id": instrument.id, "fdr_number": instrument.fdr_number, "amount_paise": instrument.amount_paise} if instrument else None,
            "approvals": [
                {"approver_id": a.approver_id, "level": a.level, "decision": a.decision, "remarks": a.remarks}
                for a in approvals
            ],
            "precheck": rr.precheck_json,
            "order": {"id": order.id, "order_no": order.order_no, "status": order.status} if order else None,
            "sod": {
                "blocked_for_current_user": blocked_for_current_user,
                "reason": "You scrutinised this FDR, so you cannot approve its release." if blocked_for_current_user and current_user.role != "institution" else None,
            },
        }
    }


@router.get("/releases/{release_id}/precheck")
def get_precheck(
    release_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    rr = db.query(ReleaseRequest).filter(ReleaseRequest.id == release_id).first()
    if rr is None:
        raise NotFoundError("Release request not found.")
    instrument = db.query(Instrument).filter(Instrument.id == rr.instrument_id).first()
    result = _run_and_store_precheck(db, rr, instrument)
    return {"data": result.as_dict()}


@router.post("/releases/{release_id}/approve")
def approve(
    release_id: int,
    body: dict,
    current_user: CurrentUser = Depends(require_roles("senior_approver", "competent_authority")),
    db: Session = Depends(get_db),
) -> dict:
    rr = db.query(ReleaseRequest).filter(ReleaseRequest.id == release_id).first()
    if rr is None:
        raise NotFoundError("Release request not found.")
    if rr.status in ("approved", "rejected"):
        raise InvalidStateError("This release request has already been decided.")

    instrument = db.query(Instrument).filter(Instrument.id == rr.instrument_id).first()
    level = 2 if db.query(Approval).filter(Approval.release_request_id == rr.id, Approval.level == 1).first() else 1

    release_service.enforce_sod_for_approval(
        db,
        release_request=rr,
        instrument_id=instrument.id,
        approver_id=current_user.id,
        approver_role=current_user.role,
        level=level,
    )

    db.add(
        Approval(
            release_request_id=rr.id,
            approver_id=current_user.id,
            level=level,
            decision="approved",
            remarks=body.get("remarks", ""),
            decided_at=clock_now(),
        )
    )

    order = None
    next_required_level = None
    if level == 1 and rr.needs_second_approval:
        rr.status = "approver1_done"
        next_required_level = 2
    else:
        rr.status = "approved"
        instrument.status = "released"
        db.add(instrument)
        institution = db.query(Institution).filter(Institution.id == instrument.institution_id).first()
        order = orders_service.create_signed_order(
            db, institution=institution, instrument=instrument, release_request=rr, issued_on=clock_today()
        )

    db.add(rr)
    db.commit()
    db.refresh(rr)

    audit.record(
        db, actor_id=current_user.id, actor_role=current_user.role, action="release_approved",
        entity_type="release_request", entity_id=rr.id, details={"level": level},
    )
    return {
        "data": {
            "release": _release_out(rr),
            "next_required_level": next_required_level,
            "order": {"id": order.id, "order_no": order.order_no} if order else None,
        }
    }


@router.post("/releases/{release_id}/reject")
def reject(
    release_id: int,
    body: dict,
    current_user: CurrentUser = Depends(require_roles("senior_approver", "competent_authority")),
    db: Session = Depends(get_db),
) -> dict:
    rr = db.query(ReleaseRequest).filter(ReleaseRequest.id == release_id).first()
    if rr is None:
        raise NotFoundError("Release request not found.")
    rr.status = "rejected"
    db.add(rr)
    db.commit()
    audit.record(
        db, actor_id=current_user.id, actor_role=current_user.role, action="release_rejected",
        entity_type="release_request", entity_id=rr.id, details={"reason": body.get("reason", "")},
    )
    return {"data": _release_out(rr)}


def _hold_out(h: Hold) -> dict:
    return {
        "id": h.id,
        "institution_id": h.institution_id,
        "instrument_id": h.instrument_id,
        "reason": h.reason,
        "source": h.source,
        "placed_on": h.placed_on.isoformat(),
        "lifted_on": h.lifted_on.isoformat() if h.lifted_on else None,
    }


@router.post("/holds")
def create_hold(
    body: dict,
    current_user: CurrentUser = Depends(require_roles("competent_authority")),
    db: Session = Depends(get_db),
) -> dict:
    if not body.get("institution_id") and not body.get("instrument_id"):
        raise ValidationFieldsError([{"path": "institution_id", "message": "Provide institution_id or instrument_id."}])
    hold = Hold(
        institution_id=body.get("institution_id"),
        instrument_id=body.get("instrument_id"),
        reason=body["reason"],
        source=body.get("source", "manual"),
        placed_by=current_user.id,
        placed_on=clock_today(),
    )
    db.add(hold)
    db.commit()
    db.refresh(hold)
    audit.record(
        db, actor_id=current_user.id, actor_role=current_user.role, action="hold_placed",
        entity_type="hold", entity_id=hold.id, details={"reason": hold.reason},
    )
    return {"data": _hold_out(hold)}


@router.post("/holds/{hold_id}/lift")
def lift_hold(
    hold_id: int,
    current_user: CurrentUser = Depends(require_roles("competent_authority")),
    db: Session = Depends(get_db),
) -> dict:
    hold = db.query(Hold).filter(Hold.id == hold_id).first()
    if hold is None:
        raise NotFoundError("Hold not found.")
    hold.lifted_on = clock_today()
    db.add(hold)
    db.commit()
    db.refresh(hold)
    audit.record(
        db, actor_id=current_user.id, actor_role=current_user.role, action="hold_lifted",
        entity_type="hold", entity_id=hold.id, details={},
    )
    return {"data": _hold_out(hold)}


@router.get("/holds")
def list_holds(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    rows = db.query(Hold).all()
    return {"data": [_hold_out(h) for h in rows]}

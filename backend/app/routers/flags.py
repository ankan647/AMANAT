from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core import audit
from app.core.clock import now as clock_now
from app.core.errors import NotFoundError, ValidationFieldsError
from app.core.permissions import CurrentUser, require_roles
from app.db.models import AnomalyFlag, Instrument
from app.db.session import get_db
from app.services import anomalies as anomalies_service
from app.services.metrics import FlagRow, PlantedRow, compute_anomaly_metrics

router = APIRouter(prefix="/api/v1", tags=["flags"])


def _flag_out(f: AnomalyFlag) -> dict:
    return {
        "id": f.id,
        "instrument_id": f.instrument_id,
        "type": f.type,
        "title": f.title,
        "reasons": f.reasons_json,
        "evidence": f.evidence_json,
        "severity": f.severity,
        "status": f.status,
        "reviewer_id": f.reviewer_id,
        "outcome_reason": f.outcome_reason,
        "created_at": f.created_at.isoformat(),
    }


@router.get("/flags")
def list_flags(
    status: str | None = None,
    type: str | None = None,
    institution_id: int | None = None,
    severity: str | None = None,
    current_user: CurrentUser = Depends(require_roles("scrutiny", "senior_approver", "competent_authority", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    query = db.query(AnomalyFlag)
    if status:
        query = query.filter(AnomalyFlag.status == status)
    if type:
        query = query.filter(AnomalyFlag.type == type)
    if severity:
        query = query.filter(AnomalyFlag.severity == severity)
    rows = query.all()
    if institution_id is not None:
        instrument_ids = {
            i.id for i in db.query(Instrument).filter(Instrument.institution_id == institution_id).all()
        }
        rows = [r for r in rows if r.instrument_id in instrument_ids]
    return {"data": [_flag_out(r) for r in rows], "meta": {"page": 1, "page_size": len(rows), "total": len(rows)}}


@router.get("/flags/referrals")
def referrals(
    current_user: CurrentUser = Depends(require_roles("scrutiny", "senior_approver", "competent_authority", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    rows = db.query(AnomalyFlag).filter(AnomalyFlag.status == "referred").all()
    return {"data": [_flag_out(r) for r in rows]}


@router.get("/flags/{flag_id}")
def get_flag(
    flag_id: int,
    current_user: CurrentUser = Depends(require_roles("scrutiny", "senior_approver", "competent_authority", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    flag = db.query(AnomalyFlag).filter(AnomalyFlag.id == flag_id).first()
    if flag is None:
        raise NotFoundError("Flag not found.")
    instrument = db.query(Instrument).filter(Instrument.id == flag.instrument_id).first()
    related = []
    if flag.type == "duplicate_fdr_number":
        other_ids = flag.evidence_json.get("other_instrument_ids", [])
        related = db.query(Instrument).filter(Instrument.id.in_(other_ids)).all() if other_ids else []
    return {
        "data": {
            "flag": _flag_out(flag),
            "reasons": flag.reasons_json,
            "evidence": flag.evidence_json,
            "instrument": {"id": instrument.id, "fdr_number": instrument.fdr_number} if instrument else None,
            "related_instruments": [{"id": r.id, "fdr_number": r.fdr_number} for r in related],
        }
    }


@router.post("/flags/{flag_id}/outcome")
def flag_outcome(
    flag_id: int,
    body: dict,
    current_user: CurrentUser = Depends(require_roles("scrutiny", "senior_approver", "competent_authority")),
    db: Session = Depends(get_db),
) -> dict:
    flag = db.query(AnomalyFlag).filter(AnomalyFlag.id == flag_id).first()
    if flag is None:
        raise NotFoundError("Flag not found.")
    outcome = body.get("outcome")
    reason = body.get("reason")
    if outcome == "cleared" and not reason:
        raise ValidationFieldsError([{"path": "reason", "message": "A reason is required for cleared."}])

    status_map = {"cleared": "cleared", "return_for_correction": "returned", "refer_for_investigation": "referred"}
    flag.status = status_map[outcome]
    flag.outcome_reason = reason or ""
    flag.reviewer_id = current_user.id
    flag.decided_at = clock_now()
    db.add(flag)

    if outcome == "return_for_correction":
        instrument = db.query(Instrument).filter(Instrument.id == flag.instrument_id).first()
        if instrument is not None:
            instrument.status = "returned"
            db.add(instrument)

    db.commit()
    db.refresh(flag)

    audit.record(
        db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="flag_outcome_recorded",
        entity_type="anomaly_flag",
        entity_id=flag.id,
        details={"outcome": outcome, "reason": reason},
    )
    return {"data": _flag_out(flag)}


@router.post("/flags/scan")
def scan(
    current_user: CurrentUser = Depends(require_roles("scrutiny", "senior_approver", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    from app.db.models import Document
    from app.services import rules_engine
    from app.services.coverage import instrument_counts_on
    from app.core.clock import today as clock_today

    instruments = db.query(Instrument).all()
    new_flags = 0
    for instrument in instruments:
        existing_types = {
            f.type
            for f in db.query(AnomalyFlag).filter(AnomalyFlag.instrument_id == instrument.id).all()
        }
        documents = db.query(Document).filter(Document.instrument_id == instrument.id).all()
        other_instruments = [(i, i.institution_id) for i in instruments if i.id != instrument.id]
        other_docs = [
            (d, None)
            for d in db.query(Document).filter(Document.instrument_id != instrument.id).all()
        ]
        from app.db.models import Institution

        institution = db.query(Institution).filter(Institution.id == instrument.institution_id).first()
        rule_result = rules_engine.resolve_for_institution(db, institution) if institution else None
        other_valid = sum(
            i.amount_paise
            for i in instruments
            if i.institution_id == instrument.institution_id
            and i.id != instrument.id
            and instrument_counts_on(i, clock_today())
        )
        candidates = anomalies_service.run_lodge_checks(
            instrument=instrument,
            documents=documents,
            other_instruments=other_instruments,
            other_documents=other_docs,
            min_fdr_term_months=rule_result.min_fdr_term_months if rule_result else 12,
            required_paise=rule_result.amount_paise if rule_result else 0,
            other_valid_amount_paise=other_valid,
        )
        for candidate in candidates:
            if candidate.type in existing_types:
                continue
            flag = AnomalyFlag(
                instrument_id=instrument.id,
                type=candidate.type,
                title=candidate.title,
                reasons_json=candidate.reasons,
                evidence_json=candidate.evidence,
                severity=candidate.severity,
                status="open",
                created_at=clock_now(),
                is_planted_label=False,
            )
            db.add(flag)
            new_flags += 1
    db.commit()
    return {"data": {"scanned": len(instruments), "new_flags": new_flags}}


@router.get("/metrics/anomalies")
def anomaly_metrics(
    current_user: CurrentUser = Depends(require_roles("scrutiny", "senior_approver", "competent_authority", "admin", "auditor")),
    db: Session = Depends(get_db),
) -> dict:
    from app.db.models import PlantedLabel

    flags = db.query(AnomalyFlag).all()
    planted = db.query(PlantedLabel).all()
    flag_rows = [FlagRow(instrument_id=f.instrument_id, type=f.type, status=f.status) for f in flags]
    planted_rows = [PlantedRow(instrument_id=p.instrument_id, type=p.type) for p in planted]
    return {"data": compute_anomaly_metrics(flag_rows, planted_rows)}

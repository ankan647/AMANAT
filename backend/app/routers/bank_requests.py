from datetime import date

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core import audit
from app.core.clock import now as clock_now
from app.core.clock import today as clock_today
from app.core.errors import ForbiddenError, InvalidStateError, NotFoundError
from app.core.permissions import CurrentUser, get_current_user, require_roles
from app.db.enums import FieldGrade, FieldName
from app.db.models import BankRequest, Document, Instrument
from app.db.session import get_db
from app.services import anomalies, bank_channel, confidence

router = APIRouter(prefix="/api/v1/bank-requests", tags=["bank_requests"])


def _request_out(r: BankRequest) -> dict:
    return {
        "id": r.id,
        "request_code": r.request_code,
        "instrument_id": r.instrument_id,
        "bank_name": r.bank_name,
        "branch": r.branch,
        "sent_date": r.sent_date.isoformat(),
        "due_date": r.due_date.isoformat(),
        "response_date": r.response_date.isoformat() if r.response_date else None,
        "outcome": r.outcome,
        "differing_values": r.differing_values_json,
        "remarks": r.remarks,
        "escalation_level": r.escalation_level,
    }


@router.post("")
def create_bank_request(
    body: dict,
    current_user: CurrentUser = Depends(require_roles("scrutiny", "senior_approver", "competent_authority")),
    db: Session = Depends(get_db),
) -> dict:
    instrument = db.query(Instrument).filter(Instrument.id == body["instrument_id"]).first()
    if instrument is None:
        raise NotFoundError("Instrument not found.")

    sent_date = clock_today()
    due_date = date.fromisoformat(body["due_date"]) if body.get("due_date") else bank_channel.default_due_date(sent_date)
    year = sent_date.year
    count = db.query(BankRequest).filter(BankRequest.request_code.like(f"BR-{year}-%")).count()
    request_code = f"BR-{year}-{count + 1:04d}"

    req = BankRequest(
        request_code=request_code,
        instrument_id=instrument.id,
        bank_name=body.get("bank_name", instrument.bank_name),
        branch=body.get("branch", instrument.branch),
        sent_date=sent_date,
        due_date=due_date,
        method=body.get("method", "bank_screen"),
        aicte_officer_id=current_user.id,
        outcome="pending",
        differing_values_json={},
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    audit.record(
        db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="bank_request_created",
        entity_type="bank_request",
        entity_id=req.id,
        details={"request_code": request_code, "instrument_id": instrument.id},
    )
    return {"data": _request_out(req)}


@router.get("")
def list_bank_requests(
    status: str | None = None,
    overdue: bool | None = None,
    institution_id: int | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    query = db.query(BankRequest)
    if current_user.role == "bank_officer":
        query = query.filter(BankRequest.bank_name == current_user.bank_name)
    if status:
        query = query.filter(BankRequest.outcome == status)
    rows = query.all()
    if institution_id is not None:
        instrument_ids = {i.id for i in db.query(Instrument).filter(Instrument.institution_id == institution_id).all()}
        rows = [r for r in rows if r.instrument_id in instrument_ids]
    if overdue:
        today = clock_today()
        rows = [r for r in rows if r.outcome == "pending" and r.due_date < today]
    return {"data": [_request_out(r) for r in rows], "meta": {"page": 1, "page_size": len(rows), "total": len(rows)}}


@router.get("/{request_id}")
def get_bank_request(
    request_id: int, current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    req = db.query(BankRequest).filter(BankRequest.id == request_id).first()
    if req is None:
        raise NotFoundError("Bank request not found.")
    if current_user.role == "bank_officer" and req.bank_name != current_user.bank_name:
        raise ForbiddenError("You can only see requests for your own bank.")
    return {"data": _request_out(req)}


@router.post("/{request_id}/respond")
async def respond(
    request_id: int,
    outcome: str = Form(...),
    differing_values: str | None = Form(None),
    remarks: str | None = Form(None),
    letter: UploadFile | None = File(None),
    current_user: CurrentUser = Depends(require_roles("bank_officer")),
    db: Session = Depends(get_db),
) -> dict:
    req = db.query(BankRequest).filter(BankRequest.id == request_id).first()
    if req is None:
        raise NotFoundError("Bank request not found.")
    if req.bank_name != current_user.bank_name:
        raise ForbiddenError("You can only respond to requests for your own bank.")
    if req.outcome != "pending":
        raise InvalidStateError("This request has already been responded to.")

    import json

    diffs = json.loads(differing_values) if differing_values else {}
    req.outcome = outcome
    req.differing_values_json = diffs
    req.remarks = remarks or ""
    req.response_date = clock_today()
    req.bank_responder_id = current_user.id

    if letter is not None:
        from app.services import ingestion

        data = await letter.read()
        import os

        from app.core.config import get_settings

        settings = get_settings()
        os.makedirs(settings.STORAGE_DIR, exist_ok=True)
        storage_path = os.path.join(settings.STORAGE_DIR, f"letter_{req.id}_{letter.filename}")
        with open(storage_path, "wb") as fh:
            fh.write(data)
        doc = Document(
            instrument_id=req.instrument_id,
            kind="bank_letter",
            filename=letter.filename or "letter.pdf",
            sha256=ingestion.compute_sha256(data),
            mime=letter.content_type or "application/pdf",
            size=len(data),
            ocr_text="",
            pdf_metadata_json={},
            scan_status="clean",
            storage_path=storage_path,
            created_at=clock_now(),
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        req.letter_doc_id = doc.id

    db.add(req)
    db.commit()
    db.refresh(req)

    flag_raised = None
    if outcome == "details_differ" and diffs:
        instrument = db.query(Instrument).filter(Instrument.id == req.instrument_id).first()
        candidate = anomalies.check_bank_mismatch(instrument, diffs)
        if candidate is not None:
            from app.db.models import AnomalyFlag

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
            db.commit()
            db.refresh(flag)
            flag_raised = {"id": flag.id, "type": flag.type, "title": flag.title}

    audit.record(
        db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="bank_request_responded",
        entity_type="bank_request",
        entity_id=req.id,
        details={"outcome": outcome},
    )
    return {"data": {"request": _request_out(req), "flag_raised": flag_raised}}


def _upgraded_fields_preview(db: Session, req: BankRequest) -> list[dict]:
    instrument = db.query(Instrument).filter(Instrument.id == req.instrument_id).first()
    fields = confidence.get_fields(db, instrument.id)
    field_by_name = {f.field_name: f for f in fields}
    claimed = {
        FieldName.fdr_number.value: instrument.fdr_number,
        FieldName.bank.value: instrument.bank_name,
        FieldName.amount.value: str(instrument.amount_paise),
        FieldName.issue_date.value: instrument.issue_date.isoformat(),
        FieldName.maturity.value: instrument.maturity_date.isoformat(),
        FieldName.beneficiary.value: instrument.beneficiary,
        FieldName.lien.value: instrument.lien_text,
    }
    upgrades = []
    for field_name in claimed:
        current = field_by_name.get(field_name)
        if current is None or current.grade == FieldGrade.bank_confirmed.value:
            continue
        eligible = req.outcome == "confirmed" or (
            req.outcome == "details_differ" and (req.differing_values_json or {}).get(field_name) == claimed[field_name]
        )
        if eligible:
            upgrades.append({"field_name": field_name, "from_grade": current.grade, "to_grade": FieldGrade.bank_confirmed.value})
    return upgrades


@router.get("/{request_id}/accept-preview")
def accept_preview(
    request_id: int,
    current_user: CurrentUser = Depends(require_roles("scrutiny", "senior_approver", "competent_authority")),
    db: Session = Depends(get_db),
) -> dict:
    req = db.query(BankRequest).filter(BankRequest.id == request_id).first()
    if req is None:
        raise NotFoundError("Bank request not found.")
    upgrades = _upgraded_fields_preview(db, req)
    instrument = db.query(Instrument).filter(Instrument.id == req.instrument_id).first()
    from app.services.institution_view import build_institution_view

    institution_id = instrument.institution_id
    from app.db.models import Institution

    institution = db.query(Institution).filter(Institution.id == institution_id).first()
    previous_pct = build_institution_view(db, institution, clock_today()).confidence_pct
    return {"data": {"request": _request_out(req), "upgraded_fields": upgrades, "previous_confidence_pct": previous_pct}}


@router.post("/{request_id}/accept")
def accept(
    request_id: int,
    current_user: CurrentUser = Depends(require_roles("scrutiny", "senior_approver", "competent_authority")),
    db: Session = Depends(get_db),
) -> dict:
    req = db.query(BankRequest).filter(BankRequest.id == request_id).first()
    if req is None:
        raise NotFoundError("Bank request not found.")
    if req.outcome == "pending":
        raise InvalidStateError("This request has not been responded to yet.")

    instrument = db.query(Instrument).filter(Instrument.id == req.instrument_id).first()
    from app.db.models import Institution

    institution = db.query(Institution).filter(Institution.id == instrument.institution_id).first()

    from app.services.institution_view import build_institution_view

    previous_pct = build_institution_view(db, institution, clock_today()).confidence_pct

    upgrades = _upgraded_fields_preview(db, req)
    for upgrade in upgrades:
        confidence.upgrade_field(
            db, instrument.id, upgrade["field_name"], FieldGrade.bank_confirmed.value, f"bank_request:{req.request_code}"
        )

    req.accepted_by_id = current_user.id
    req.accepted_at = clock_now()
    db.add(req)
    db.commit()

    new_pct = build_institution_view(db, institution, clock_today()).confidence_pct

    audit.record(
        db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="bank_response_accepted",
        entity_type="bank_request",
        entity_id=req.id,
        details={"upgraded_fields": [u["field_name"] for u in upgrades]},
    )
    return {
        "data": {
            "request": _request_out(req),
            "upgraded_fields": upgrades,
            "institution_confidence_pct": new_pct,
            "previous_confidence_pct": previous_pct,
        }
    }


@router.post("/{request_id}/reject-response")
def reject_response(
    request_id: int,
    body: dict,
    current_user: CurrentUser = Depends(require_roles("scrutiny", "senior_approver", "competent_authority")),
    db: Session = Depends(get_db),
) -> dict:
    req = db.query(BankRequest).filter(BankRequest.id == request_id).first()
    if req is None:
        raise NotFoundError("Bank request not found.")
    req.rejected_reason = body.get("reason", "")
    db.add(req)
    db.commit()
    audit.record(
        db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="bank_response_rejected",
        entity_type="bank_request",
        entity_id=req.id,
        details={"reason": req.rejected_reason},
    )
    return {"data": _request_out(req)}

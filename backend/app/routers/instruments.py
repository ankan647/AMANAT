import json
from datetime import date

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core import audit
from app.core.clock import now as clock_now
from app.core.clock import today as clock_today
from app.core.config import get_settings
from app.core.errors import ForbiddenError, NotFoundError, ValidationFieldsError
from app.core.permissions import CurrentUser, get_current_user, require_roles
from app.db.enums import FieldGrade
from app.db.models import (
    AnomalyFlag,
    BankRequest,
    Document,
    Institution,
    Instrument,
    InstrumentAssignment,
    InstrumentField,
    User,
)
from app.db.session import get_db
from app.services import anomalies, confidence, coverage, ingestion, reminders, rules_engine

router = APIRouter(prefix="/api/v1", tags=["instruments"])


def _scrutiniser_round_robin(db: Session) -> User | None:
    officers = db.query(User).filter(User.role == "scrutiny", User.active.is_(True)).order_by(User.id).all()
    if not officers:
        return None
    count = db.query(InstrumentAssignment).filter(InstrumentAssignment.role == "scrutiniser").count()
    return officers[count % len(officers)]


@router.post("/instruments")
async def lodge_instrument(
    fdr: str = Form(...),
    documents: list[UploadFile] = File(default=[]),
    kinds: list[str] = Form(default=[]),
    current_user: CurrentUser = Depends(require_roles("institution", "scrutiny")),
    db: Session = Depends(get_db),
) -> dict:
    try:
        payload = json.loads(fdr)
    except json.JSONDecodeError as exc:
        raise ValidationFieldsError([{"path": "fdr", "message": "Invalid JSON."}]) from exc

    institution_id = payload["institution_id"]
    if current_user.role == "institution" and current_user.institution_id != institution_id:
        raise ForbiddenError("You can only lodge FDRs for your own institution.")

    institution = db.query(Institution).filter(Institution.id == institution_id).first()
    if institution is None:
        raise NotFoundError("Institution not found.")

    settings = get_settings()
    rule_result = rules_engine.resolve_for_institution(db, institution)

    instrument = Instrument(
        institution_id=institution_id,
        fdr_number=payload["fdr_number"],
        fdr_number_norm=anomalies.normalize_fdr_number(payload["fdr_number"]),
        bank_name=payload["bank_name"],
        branch=payload["branch"],
        ifsc=payload["ifsc"],
        amount_paise=payload["amount_paise"],
        issue_date=date.fromisoformat(payload["issue_date"]),
        maturity_date=date.fromisoformat(payload["maturity_date"]),
        beneficiary=payload["beneficiary"],
        lien_text=payload["lien_text"],
        intimation_date=date.fromisoformat(payload["intimation_date"]) if payload.get("intimation_date") else None,
        status="lodged",
        created_at=clock_now(),
    )
    db.add(instrument)
    db.commit()
    db.refresh(instrument)

    assigned_officer = _scrutiniser_round_robin(db)
    if assigned_officer is not None:
        db.add(
            InstrumentAssignment(
                instrument_id=instrument.id,
                officer_id=assigned_officer.id,
                role="scrutiniser",
                assigned_at=clock_now(),
            )
        )
        db.commit()

    fields = confidence.init_fields_for_instrument(db, instrument)

    stored_documents: list[Document] = []
    for idx, upload in enumerate(documents):
        data = await upload.read()
        sha256 = ingestion.compute_sha256(data)
        text, metadata = ingestion.extract_pdf_text_and_metadata(data)
        storage_dir = settings.STORAGE_DIR
        import os

        os.makedirs(storage_dir, exist_ok=True)
        storage_path = os.path.join(storage_dir, f"{instrument.id}_{idx}_{upload.filename}")
        with open(storage_path, "wb") as fh:
            fh.write(data)

        kind = kinds[idx] if idx < len(kinds) else "fdr_scan"
        doc = Document(
            instrument_id=instrument.id,
            kind=kind,
            filename=upload.filename or f"document_{idx}.pdf",
            sha256=sha256,
            mime=upload.content_type or "application/pdf",
            size=len(data),
            ocr_text=text,
            pdf_metadata_json=metadata,
            scan_status="clean",
            storage_path=storage_path,
            created_at=clock_now(),
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        stored_documents.append(doc)

        matches = ingestion.match_fields_against_text(instrument, text)
        for field_name, matched in matches.items():
            if matched:
                confidence.upgrade_field(
                    db, instrument.id, field_name, FieldGrade.document_checked.value, f"document:{doc.id}"
                )
        fields = confidence.get_fields(db, instrument.id)

    other_instruments = (
        db.query(Instrument).filter(Instrument.id != instrument.id).all()
    )
    other_pairs = [(i, i.institution_id) for i in other_instruments]
    other_documents = (
        db.query(Document).filter(Document.instrument_id != instrument.id).all()
    )
    other_doc_institution = {}
    for d in other_documents:
        inst_row = db.query(Instrument).filter(Instrument.id == d.instrument_id).first()
        other_doc_institution[d.id] = inst_row.institution_id if inst_row else None
    other_doc_pairs = [(d, other_doc_institution.get(d.id)) for d in other_documents]

    other_valid_amount = sum(
        i.amount_paise
        for i in other_instruments
        if i.institution_id == institution_id and coverage.instrument_counts_on(i, clock_today())
    )

    flag_candidates = anomalies.run_lodge_checks(
        instrument=instrument,
        documents=stored_documents,
        other_instruments=other_pairs,
        other_documents=other_doc_pairs,
        min_fdr_term_months=rule_result.min_fdr_term_months,
        required_paise=rule_result.amount_paise,
        other_valid_amount_paise=other_valid_amount,
    )
    raised_flags = []
    for candidate in flag_candidates:
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
        raised_flags.append(flag)

    reminders.create_reminders_for_instrument(db, instrument)

    audit.record(
        db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="instrument_lodged",
        entity_type="instrument",
        entity_id=instrument.id,
        details={"fdr_number": instrument.fdr_number, "flags_raised": len(raised_flags)},
    )

    return {
        "data": {
            "instrument": _instrument_summary(instrument),
            "fields": [_field_out(f) for f in fields],
            "flags_raised": [
                {"id": f.id, "type": f.type, "title": f.title, "severity": f.severity} for f in raised_flags
            ],
        }
    }


def _instrument_summary(i: Instrument) -> dict:
    return {
        "id": i.id,
        "institution_id": i.institution_id,
        "fdr_number": i.fdr_number,
        "bank_name": i.bank_name,
        "branch": i.branch,
        "ifsc": i.ifsc,
        "amount_paise": i.amount_paise,
        "issue_date": i.issue_date.isoformat(),
        "maturity_date": i.maturity_date.isoformat(),
        "beneficiary": i.beneficiary,
        "lien_text": i.lien_text,
        "status": i.status,
    }


def _field_out(f: InstrumentField) -> dict:
    return {
        "field_name": f.field_name,
        "value": f.value,
        "grade": f.grade,
        "source": f.source,
    }


@router.get("/instruments/{instrument_id}")
def get_instrument(
    instrument_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    instrument = db.query(Instrument).filter(Instrument.id == instrument_id).first()
    if instrument is None:
        raise NotFoundError("Instrument not found.")
    if current_user.role == "institution" and current_user.institution_id != instrument.institution_id:
        raise ForbiddenError("You can only see your own institution's data.")

    fields = confidence.get_fields(db, instrument_id)
    grade = confidence.instrument_grade(fields) if fields else FieldGrade.claimed.value
    weakest = next((f for f in fields if f.grade == grade), None)

    documents = db.query(Document).filter(Document.instrument_id == instrument_id).all()
    assignments = db.query(InstrumentAssignment).filter(InstrumentAssignment.instrument_id == instrument_id).all()
    flags = db.query(AnomalyFlag).filter(AnomalyFlag.instrument_id == instrument_id).all()
    bank_requests = db.query(BankRequest).filter(BankRequest.instrument_id == instrument_id).all()

    return {
        "data": {
            "instrument": _instrument_summary(instrument),
            "fields": [
                {
                    "field_name": f.field_name,
                    "value": f.value,
                    "grade": f.grade,
                    "source": f.source,
                    "supported_by": _supported_by(f.source),
                }
                for f in fields
            ],
            "confidence": {"grade": grade, "weakest_field": weakest.field_name if weakest else None},
            "documents": [
                {"id": d.id, "kind": d.kind, "filename": d.filename, "sha256": d.sha256, "ocr_text": d.ocr_text[:280]}
                for d in documents
            ],
            "assignments": [
                {"officer_id": a.officer_id, "role": a.role, "assigned_at": a.assigned_at.isoformat()}
                for a in assignments
            ],
            "linked_history": [],
            "flags": [{"id": f.id, "type": f.type, "title": f.title, "status": f.status, "severity": f.severity} for f in flags],
            "bank_requests": [
                {"id": b.id, "request_code": b.request_code, "outcome": b.outcome} for b in bank_requests
            ],
        }
    }


def _supported_by(source: str) -> dict | None:
    if source.startswith("document:"):
        return {"type": "document", "id": int(source.split(":")[1])}
    if source.startswith("bank_request:"):
        return {"type": "bank_request", "id": source.split(":")[1]}
    return None


@router.get("/instruments/{instrument_id}/documents/{doc_id}/download")
def download_document(
    instrument_id: int,
    doc_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    doc = db.query(Document).filter(Document.id == doc_id, Document.instrument_id == instrument_id).first()
    if doc is None:
        raise NotFoundError("Document not found.")
    with open(doc.storage_path, "rb") as fh:
        data = fh.read()
    return Response(content=data, media_type=doc.mime)


@router.post("/instruments/{instrument_id}/assign")
def assign_officer(
    instrument_id: int,
    body: dict,
    current_user: CurrentUser = Depends(require_roles("senior_approver", "competent_authority")),
    db: Session = Depends(get_db),
) -> dict:
    instrument = db.query(Instrument).filter(Instrument.id == instrument_id).first()
    if instrument is None:
        raise NotFoundError("Instrument not found.")
    db.add(
        InstrumentAssignment(
            instrument_id=instrument_id,
            officer_id=body["officer_id"],
            role="scrutiniser",
            assigned_at=clock_now(),
        )
    )
    db.commit()
    audit.record(
        db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="instrument_assigned",
        entity_type="instrument",
        entity_id=instrument_id,
        details={"officer_id": body["officer_id"]},
    )
    return {"data": {"instrument_id": instrument_id, "officer_id": body["officer_id"]}}


@router.post("/instruments/{instrument_id}/link-renewal")
def link_renewal(
    instrument_id: int,
    body: dict,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    new_instrument = db.query(Instrument).filter(Instrument.id == instrument_id).first()
    previous_instrument = db.query(Instrument).filter(Instrument.id == body["previous_instrument_id"]).first()
    if new_instrument is None or previous_instrument is None:
        raise NotFoundError("Instrument not found.")

    previous_instrument.status = "renewed"
    new_instrument.linked_from_instrument_id = previous_instrument.id
    db.add_all([previous_instrument, new_instrument])
    db.commit()

    cancelled = reminders.cancel_pending_reminders_for_instrument(db, previous_instrument.id)

    audit.record(
        db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="instrument_renewal_linked",
        entity_type="instrument",
        entity_id=instrument_id,
        details={"previous_instrument_id": previous_instrument.id, "cancelled_reminders": cancelled},
    )
    return {"data": {"instrument_id": instrument_id, "previous_instrument_id": previous_instrument.id}}


@router.get("/verification-queue")
def verification_queue(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    instruments = db.query(Instrument).all()
    if current_user.role == "institution":
        instruments = [i for i in instruments if i.institution_id == current_user.institution_id]

    rows = []
    for instrument in instruments:
        fields = confidence.get_fields(db, instrument.id)
        if not fields:
            continue
        grade = confidence.instrument_grade(fields)
        if grade == FieldGrade.bank_confirmed.value:
            continue
        institution = db.query(Institution).filter(Institution.id == instrument.institution_id).first()
        priority_score = instrument.amount_paise / 100 + (0 if grade == FieldGrade.claimed.value else -1000)
        rows.append(
            {
                "instrument_id": instrument.id,
                "institution_id": instrument.institution_id,
                "institution_name": institution.name if institution else "",
                "priority_score": priority_score,
                "reason": f"Instrument grade is {grade}; verify with the bank.",
                "coverage_status": None,
                "confidence_pct": None,
                "amount_paise": instrument.amount_paise,
            }
        )
    rows.sort(key=lambda r: r["priority_score"], reverse=True)
    return rows

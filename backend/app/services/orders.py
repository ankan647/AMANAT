"""Signed release order payload, numbering, and PDF/QR generation (spec 5.11)."""

import io
from datetime import date

import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.signing import sign_payload
from app.db.models import Institution, Instrument, ReleaseRequest, SignedOrder

ISSUING_AUTHORITY = "AICTE (demo)"
INTEREST_NOTE = "Accrued interest is credited to the Council."


def next_order_no(db: Session, year: int) -> str:
    count = (
        db.query(SignedOrder).filter(SignedOrder.order_no.like(f"ORD-{year}-%")).count()
    )
    return f"ORD-{year}-{count + 1:04d}"


def mask_instrument_ref(fdr_number: str) -> str:
    cleaned = fdr_number.strip()
    return f"****{cleaned[-4:]}" if len(cleaned) >= 4 else f"****{cleaned}"


def build_payload(
    *,
    order_no: str,
    institution: Institution,
    instrument: Instrument,
    amount_paise: int,
    issued_on: date,
    release_request_id: int,
) -> dict:
    return {
        "order_no": order_no,
        "institution_name": institution.name,
        "institution_code": institution.code,
        "amount_paise": amount_paise,
        "issued_on": issued_on.isoformat(),
        "issuing_authority": ISSUING_AUTHORITY,
        "release_request_id": release_request_id,
        "instrument_ref_masked": mask_instrument_ref(instrument.fdr_number),
        "interest_note": INTEREST_NOTE,
    }


def create_signed_order(
    db: Session,
    *,
    institution: Institution,
    instrument: Instrument,
    release_request: ReleaseRequest,
    issued_on: date,
) -> SignedOrder:
    order_no = next_order_no(db, issued_on.year)
    payload = build_payload(
        order_no=order_no,
        institution=institution,
        instrument=instrument,
        amount_paise=instrument.amount_paise,
        issued_on=issued_on,
        release_request_id=release_request.id,
    )
    signature_b64, public_key_b64 = sign_payload(payload)
    row = SignedOrder(
        order_no=order_no,
        release_request_id=release_request.id,
        payload_json=payload,
        signature_b64=signature_b64,
        public_key_b64=public_key_b64,
        status="valid",
        issued_on=issued_on,
        revoked_reason="",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def generate_order_pdf(order: SignedOrder) -> bytes:
    settings = get_settings()
    verify_url = f"{settings.FRONTEND_BASE}/verify/{order.order_no}"
    qr_img = qrcode.make(verify_url)
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    payload = order.payload_json
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 60, "AICTE Security Deposit Release Order")
    c.setFont("Helvetica", 11)
    lines = [
        f"Order No: {payload['order_no']}",
        f"Institution: {payload['institution_name']} ({payload['institution_code']})",
        f"Amount: {payload['amount_paise']} paise",
        f"Issued on: {payload['issued_on']}",
        f"Issuing authority: {payload['issuing_authority']}",
        f"Instrument reference: {payload['instrument_ref_masked']}",
        f"Note: {payload['interest_note']}",
        "",
        "Prototype - synthetic data - simulated bank - demo signing key",
    ]
    y = height - 100
    for line in lines:
        c.drawString(50, y, line)
        y -= 20

    from reportlab.lib.utils import ImageReader

    c.drawImage(ImageReader(qr_buffer), width - 180, height - 220, width=120, height=120)
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(50, 40, "ORDER SIGNED WITH DEMO KEY")
    c.showPage()
    c.save()
    return buffer.getvalue()

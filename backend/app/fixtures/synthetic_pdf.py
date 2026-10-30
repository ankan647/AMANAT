"""Synthetic FDR/affidavit PDFs for the seed data (spec section 7)."""

import io

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def _indian_grouping(n: int) -> str:
    s = str(n)
    if len(s) <= 3:
        return s
    last3 = s[-3:]
    rest = s[:-3]
    groups = []
    while len(rest) > 2:
        groups.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        groups.insert(0, rest)
    return ",".join(groups) + "," + last3


def generate_fdr_pdf(instrument, suspicious_metadata: dict | None = None) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    rupees = instrument.amount_paise // 100

    lines = [
        "FIXED DEPOSIT RECEIPT (synthetic, for demo use only)",
        f"FDR Number: {instrument.fdr_number}",
        f"Bank: {instrument.bank_name}",
        f"Branch: {instrument.branch}",
        f"IFSC: {instrument.ifsc}",
        f"Amount: Rs. {_indian_grouping(rupees)} ({rupees})",
        f"Issue Date: {instrument.issue_date.strftime('%d/%m/%Y')}",
        f"Maturity Date: {instrument.maturity_date.strftime('%d/%m/%Y')}",
        f"Beneficiary: {instrument.beneficiary}",
        f"Lien: {instrument.lien_text}",
    ]
    y = height - 80
    c.setFont("Helvetica", 11)
    for line in lines:
        c.drawString(50, y, line)
        y -= 22

    c.showPage()
    c.save()
    data = buffer.getvalue()

    if suspicious_metadata:
        data = _apply_suspicious_metadata(data, suspicious_metadata)
    return data


def _apply_suspicious_metadata(data: bytes, suspicious_metadata: dict) -> bytes:
    import fitz  # PyMuPDF

    doc = fitz.open(stream=data, filetype="pdf")
    meta = dict(doc.metadata)
    if "producer" in suspicious_metadata:
        meta["producer"] = suspicious_metadata["producer"]
    if "creator" in suspicious_metadata:
        meta["creator"] = suspicious_metadata["creator"]
    if "creation_date" in suspicious_metadata:
        raw = suspicious_metadata["creation_date"].replace("-", "")
        meta["creationDate"] = f"D:{raw}000000"
    doc.set_metadata(meta)
    out = doc.tobytes()
    doc.close()
    return out


def generate_affidavit_pdf(instrument) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica", 11)
    lines = [
        "AFFIDAVIT (synthetic, for demo use only)",
        f"Regarding FDR {instrument.fdr_number} held with {instrument.bank_name}.",
        f"Beneficiary: {instrument.beneficiary}",
        f"Lien: {instrument.lien_text}",
        "We affirm the above FDR is held in good faith as a security deposit.",
    ]
    y = height - 80
    for line in lines:
        c.drawString(50, y, line)
        y -= 22
    c.showPage()
    c.save()
    return buffer.getvalue()

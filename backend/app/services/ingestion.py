"""Document ingestion: hash, PDF text/metadata extraction, and field matching (spec 5.5, 2.4).

Falls back to a fixture `ocr_text` when a file has no extractable text layer (e.g. Tesseract is
unavailable) — see AMANAT_SPEC.md section 2.4.
"""

import hashlib
import re
from datetime import date, datetime

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover
    fitz = None

from app.db.enums import FieldGrade, FieldName
from app.services.coverage import beneficiary_ok

DATE_PATTERNS = [
    (r"(\d{2})/(\d{2})/(\d{4})", "%d/%m/%Y"),
    (r"(\d{2})-(\d{2})-(\d{4})", "%d-%m-%Y"),
    (r"(\d{4})-(\d{2})-(\d{2})", "%Y-%m-%d"),
]
MONTH_NAME_PATTERN = re.compile(
    r"(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+(\d{4})", re.IGNORECASE
)


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def extract_pdf_text_and_metadata(data: bytes, fallback_ocr_text: str = "") -> tuple[str, dict]:
    if fitz is None:
        return fallback_ocr_text, {}
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception:  # noqa: BLE001
        return fallback_ocr_text, {}
    text = "\n".join(page.get_text() for page in doc)
    metadata = {
        "creation_date": _parse_pdf_date(doc.metadata.get("creationDate")),
        "producer": doc.metadata.get("producer") or "",
        "creator": doc.metadata.get("creator") or "",
    }
    doc.close()
    if not text.strip():
        text = fallback_ocr_text
    return text, metadata


def _parse_pdf_date(raw: str | None) -> str | None:
    if not raw:
        return None
    match = re.match(r"D:(\d{4})(\d{2})(\d{2})", raw)
    if not match:
        return None
    year, month, day = match.groups()
    return f"{year}-{month}-{day}"


def normalize_reference(value: str) -> str:
    return re.sub(r"[\s/]", "", value or "").upper()


def reference_in_text(text: str, fdr_number: str) -> bool:
    norm_target = normalize_reference(fdr_number)
    norm_text = normalize_reference(text)
    return norm_target in norm_text


def amount_in_text(text: str, amount_paise: int) -> bool:
    rupees = amount_paise // 100
    candidates = {
        str(rupees),
        f"{rupees:,}",
        f"{rupees:.2f}",
        f"{rupees:,.2f}",
    }
    # Indian grouping, e.g. 1,25,00,000
    candidates.add(_indian_grouping(rupees))
    cleaned_text = text
    return any(candidate in cleaned_text for candidate in candidates)


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


def _extract_dates(text: str) -> set[date]:
    found: set[date] = set()
    for pattern, fmt in DATE_PATTERNS:
        for match in re.finditer(pattern, text):
            try:
                found.add(datetime.strptime(match.group(0), fmt).date())
            except ValueError:
                continue
    for match in MONTH_NAME_PATTERN.finditer(text):
        day, month_name, year = match.groups()
        try:
            found.add(datetime.strptime(f"{day} {month_name} {year}", "%d %b %Y").date())
        except ValueError:
            continue
    return found


def date_in_text(text: str, target: date) -> bool:
    return target in _extract_dates(text)


def beneficiary_in_text(text: str) -> bool:
    return beneficiary_ok(text)


def lien_in_text(text: str) -> bool:
    lowered = text.lower()
    return "aicte" in lowered and ("lien" in lowered or "pledged" in lowered)


def match_fields_against_text(instrument, text: str) -> dict[str, bool]:
    return {
        FieldName.fdr_number.value: reference_in_text(text, instrument.fdr_number),
        FieldName.bank.value: instrument.bank_name.lower() in text.lower(),
        FieldName.amount.value: amount_in_text(text, instrument.amount_paise),
        FieldName.issue_date.value: date_in_text(text, instrument.issue_date),
        FieldName.maturity.value: date_in_text(text, instrument.maturity_date),
        FieldName.beneficiary.value: beneficiary_in_text(text),
        FieldName.lien.value: lien_in_text(text),
    }


__all__ = [
    "compute_sha256",
    "extract_pdf_text_and_metadata",
    "match_fields_against_text",
    "FieldGrade",
]

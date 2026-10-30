"""Deterministic anomaly checks (spec 5.7). Never use the word "fraud" anywhere in output."""

import re
from dataclasses import dataclass, field
from datetime import date

from app.db.enums import FlagSeverity, FlagType
from app.db.models import Document, Instrument
from app.fixtures.ifsc_bank_codes import IFSC_PATTERN, IFSC_PREFIX_TO_BANK
from app.services.coverage import beneficiary_ok

EDITING_TOOL_NAMES = ("photoshop", "gimp", "canva", "illustrator", "paint")

SEVERITY_BY_TYPE = {
    FlagType.duplicate_fdr_number.value: FlagSeverity.high.value,
    FlagType.duplicate_file_hash.value: FlagSeverity.high.value,
    FlagType.bank_mismatch.value: FlagSeverity.high.value,
    FlagType.beneficiary_missing.value: FlagSeverity.high.value,
    FlagType.maturity_before_issue.value: FlagSeverity.medium.value,
    FlagType.term_too_short.value: FlagSeverity.medium.value,
    FlagType.amount_below_required.value: FlagSeverity.medium.value,
    FlagType.lien_missing.value: FlagSeverity.medium.value,
    FlagType.ifsc_invalid.value: FlagSeverity.medium.value,
    FlagType.ifsc_bank_mismatch.value: FlagSeverity.medium.value,
    FlagType.pdf_metadata_suspicious.value: FlagSeverity.low.value,
}


def normalize_fdr_number(value: str) -> str:
    return re.sub(r"[\s/]", "", value or "").upper()


@dataclass
class FlagCandidate:
    type: str
    title: str
    reasons: list[dict] = field(default_factory=list)
    evidence: dict = field(default_factory=dict)
    severity: str | None = None

    def __post_init__(self) -> None:
        if self.severity is None:
            self.severity = SEVERITY_BY_TYPE.get(self.type, FlagSeverity.low.value)


def _title(short_reason: str) -> str:
    return f"Anomaly: needs review - {short_reason}"


def check_duplicate_fdr_number(
    instrument: Instrument, other_instruments: list[tuple[Instrument, int]]
) -> FlagCandidate | None:
    """other_instruments: [(instrument, institution_id), ...] excluding `instrument` itself."""
    norm = normalize_fdr_number(instrument.fdr_number)
    dupes = [
        (other, inst_id)
        for other, inst_id in other_instruments
        if normalize_fdr_number(other.fdr_number) == norm
    ]
    if not dupes:
        return None
    return FlagCandidate(
        type=FlagType.duplicate_fdr_number.value,
        title=_title("duplicate FDR number used elsewhere"),
        reasons=[
            {
                "code": "duplicate_fdr_number",
                "text": f"FDR number '{instrument.fdr_number}' is also used by "
                f"{len(dupes)} other instrument(s).",
            }
        ],
        evidence={
            "fdr_number_norm": norm,
            "other_instrument_ids": [d[0].id for d in dupes],
            "other_institution_ids": [d[1] for d in dupes],
        },
    )


def check_duplicate_file_hash(
    documents: list[Document], other_documents: list[tuple[Document, int]]
) -> FlagCandidate | None:
    hashes = {d.sha256 for d in documents}
    dupes = [(other, inst_id) for other, inst_id in other_documents if other.sha256 in hashes]
    if not dupes:
        return None
    return FlagCandidate(
        type=FlagType.duplicate_file_hash.value,
        title=_title("same document reused under another institution"),
        reasons=[
            {
                "code": "duplicate_file_hash",
                "text": "One or more uploaded documents share a SHA-256 hash with a document "
                "already on file under another institution.",
            }
        ],
        evidence={
            "matching_document_ids": [d[0].id for d in dupes],
            "other_institution_ids": [d[1] for d in dupes],
        },
    )


def check_maturity_before_issue(instrument: Instrument) -> FlagCandidate | None:
    if instrument.maturity_date > instrument.issue_date:
        return None
    return FlagCandidate(
        type=FlagType.maturity_before_issue.value,
        title=_title("maturity date is not after issue date"),
        reasons=[
            {
                "code": "maturity_before_issue",
                "text": f"Maturity {instrument.maturity_date.isoformat()} is not after "
                f"issue {instrument.issue_date.isoformat()}.",
            }
        ],
        evidence={
            "issue_date": instrument.issue_date.isoformat(),
            "maturity_date": instrument.maturity_date.isoformat(),
        },
    )


def check_term_too_short(instrument: Instrument, min_fdr_term_months: int) -> FlagCandidate | None:
    months = (instrument.maturity_date.year - instrument.issue_date.year) * 12 + (
        instrument.maturity_date.month - instrument.issue_date.month
    )
    if instrument.maturity_date.day < instrument.issue_date.day:
        months -= 1
    if months >= min_fdr_term_months:
        return None
    return FlagCandidate(
        type=FlagType.term_too_short.value,
        title=_title("FDR term is shorter than required"),
        reasons=[
            {
                "code": "term_too_short",
                "text": f"Term is about {months} month(s); rule requires at least "
                f"{min_fdr_term_months}.",
            }
        ],
        evidence={"term_months": months, "min_fdr_term_months": min_fdr_term_months},
    )


def check_amount_below_required(
    instrument: Instrument, required_paise: int, other_valid_amount_paise: int
) -> FlagCandidate | None:
    if instrument.amount_paise >= required_paise:
        return None
    if instrument.amount_paise + other_valid_amount_paise >= required_paise:
        return None
    return FlagCandidate(
        type=FlagType.amount_below_required.value,
        title=_title("amount is below the required deposit"),
        reasons=[
            {
                "code": "amount_below_required",
                "text": f"Amount {instrument.amount_paise} paise is below the required "
                f"{required_paise} paise, and no other valid instrument closes the gap.",
            }
        ],
        evidence={
            "amount_paise": instrument.amount_paise,
            "required_paise": required_paise,
            "other_valid_amount_paise": other_valid_amount_paise,
        },
    )


def check_beneficiary_missing(instrument: Instrument) -> FlagCandidate | None:
    if beneficiary_ok(instrument.beneficiary):
        return None
    return FlagCandidate(
        type=FlagType.beneficiary_missing.value,
        title=_title("beneficiary text does not name AICTE and Government of India"),
        reasons=[
            {
                "code": "beneficiary_missing",
                "text": "Beneficiary text must mention AICTE (or its full name) and "
                "'Government of India'.",
            }
        ],
        evidence={"beneficiary": instrument.beneficiary},
    )


def check_lien_missing(instrument: Instrument) -> FlagCandidate | None:
    lowered = (instrument.lien_text or "").lower()
    has_aicte = "aicte" in lowered
    has_lien_word = "lien" in lowered or "pledged" in lowered
    if has_aicte and has_lien_word:
        return None
    return FlagCandidate(
        type=FlagType.lien_missing.value,
        title=_title("lien text does not mark AICTE's lien"),
        reasons=[
            {
                "code": "lien_missing",
                "text": "Lien text must mention AICTE and either 'lien' or 'pledged'.",
            }
        ],
        evidence={"lien_text": instrument.lien_text},
    )


def check_ifsc_invalid(instrument: Instrument) -> FlagCandidate | None:
    if re.match(IFSC_PATTERN, instrument.ifsc or ""):
        return None
    return FlagCandidate(
        type=FlagType.ifsc_invalid.value,
        title=_title("IFSC code is not a valid format"),
        reasons=[{"code": "ifsc_invalid", "text": f"'{instrument.ifsc}' is not a valid IFSC."}],
        evidence={"ifsc": instrument.ifsc},
    )


def check_ifsc_bank_mismatch(instrument: Instrument) -> FlagCandidate | None:
    ifsc = instrument.ifsc or ""
    if not re.match(IFSC_PATTERN, ifsc):
        return None  # ifsc_invalid already covers malformed codes
    prefix = ifsc[:4]
    expected_bank = IFSC_PREFIX_TO_BANK.get(prefix)
    if expected_bank is None or expected_bank == instrument.bank_name:
        return None
    return FlagCandidate(
        type=FlagType.ifsc_bank_mismatch.value,
        title=_title("IFSC prefix does not match the claimed bank"),
        reasons=[
            {
                "code": "ifsc_bank_mismatch",
                "text": f"IFSC prefix '{prefix}' maps to {expected_bank}, not the claimed "
                f"bank '{instrument.bank_name}'.",
            }
        ],
        evidence={"ifsc": ifsc, "claimed_bank": instrument.bank_name, "expected_bank": expected_bank},
    )


def check_pdf_metadata_suspicious(
    instrument: Instrument, documents: list[Document]
) -> FlagCandidate | None:
    for doc in documents:
        meta = doc.pdf_metadata_json or {}
        creation_date_raw = meta.get("creation_date")
        if creation_date_raw:
            try:
                creation_date = date.fromisoformat(creation_date_raw[:10])
            except ValueError:
                creation_date = None
            if creation_date and creation_date < instrument.issue_date:
                return FlagCandidate(
                    type=FlagType.pdf_metadata_suspicious.value,
                    title=_title("document metadata predates the claimed issue date"),
                    reasons=[
                        {
                            "code": "pdf_metadata_suspicious",
                            "text": f"Document '{doc.filename}' was created "
                            f"{creation_date_raw}, before the claimed issue date "
                            f"{instrument.issue_date.isoformat()}.",
                        }
                    ],
                    evidence={"document_id": doc.id, "creation_date": creation_date_raw},
                )
        for key in ("producer", "creator"):
            value = (meta.get(key) or "").lower()
            for tool in EDITING_TOOL_NAMES:
                if tool in value:
                    return FlagCandidate(
                        type=FlagType.pdf_metadata_suspicious.value,
                        title=_title("document metadata names an image-editing tool"),
                        reasons=[
                            {
                                "code": "pdf_metadata_suspicious",
                                "text": f"Document '{doc.filename}' {key} metadata mentions "
                                f"'{tool}'.",
                            }
                        ],
                        evidence={"document_id": doc.id, key: meta.get(key)},
                    )
    return None


def check_bank_mismatch(
    instrument: Instrument, differing_values: dict[str, str]
) -> FlagCandidate | None:
    if not differing_values:
        return None
    claimed = {
        "fdr_number": instrument.fdr_number,
        "bank": instrument.bank_name,
        "amount": str(instrument.amount_paise),
        "issue_date": instrument.issue_date.isoformat(),
        "maturity": instrument.maturity_date.isoformat(),
        "beneficiary": instrument.beneficiary,
        "lien": instrument.lien_text,
    }
    diffs = {
        field_name: {"claimed": claimed.get(field_name), "bank_value": bank_value}
        for field_name, bank_value in differing_values.items()
        if claimed.get(field_name) != bank_value
    }
    if not diffs:
        return None
    return FlagCandidate(
        type=FlagType.bank_mismatch.value,
        title=_title("bank response differs from claimed details"),
        reasons=[
            {
                "code": "bank_mismatch",
                "text": f"The bank reported a different value for: {', '.join(diffs.keys())}.",
            }
        ],
        evidence={"differences": diffs},
    )


def run_lodge_checks(
    *,
    instrument: Instrument,
    documents: list[Document],
    other_instruments: list[tuple[Instrument, int]],
    other_documents: list[tuple[Document, int]],
    min_fdr_term_months: int,
    required_paise: int,
    other_valid_amount_paise: int,
) -> list[FlagCandidate]:
    checks = [
        check_duplicate_fdr_number(instrument, other_instruments),
        check_duplicate_file_hash(documents, other_documents),
        check_maturity_before_issue(instrument),
        check_term_too_short(instrument, min_fdr_term_months),
        check_amount_below_required(instrument, required_paise, other_valid_amount_paise),
        check_beneficiary_missing(instrument),
        check_lien_missing(instrument),
        check_ifsc_invalid(instrument),
        check_ifsc_bank_mismatch(instrument),
        check_pdf_metadata_suspicious(instrument, documents),
    ]
    return [c for c in checks if c is not None]

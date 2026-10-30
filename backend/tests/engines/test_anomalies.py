from datetime import date

from app.db.models import Document, Instrument
from app.services import anomalies

GOOD_BENEFICIARY = "AICTE, Government of India"
GOOD_LIEN = "Lien marked in favour of AICTE and pledged accordingly."


def make_instrument(**overrides):
    base = dict(
        id=1,
        institution_id=1,
        fdr_number="SBI/FDR/2024/778812",
        fdr_number_norm="SBIFDR2024778812",
        bank_name="State Bank of India",
        branch="Main",
        ifsc="SBIN0001234",
        amount_paise=15_00_000_00,
        issue_date=date(2023, 1, 1),
        maturity_date=date(2033, 1, 1),
        beneficiary=GOOD_BENEFICIARY,
        lien_text=GOOD_LIEN,
        status="active",
    )
    base.update(overrides)
    return Instrument(**base)


def make_document(**overrides):
    base = dict(
        id=1,
        instrument_id=1,
        kind="fdr_scan",
        filename="fdr.pdf",
        sha256="a" * 64,
        mime="application/pdf",
        size=100,
        ocr_text="",
        pdf_metadata_json={},
        scan_status="clean",
        storage_path="/tmp/fdr.pdf",
    )
    base.update(overrides)
    return Document(**base)


def test_clean_instrument_raises_no_flags():
    instrument = make_instrument()
    flags = anomalies.run_lodge_checks(
        instrument=instrument,
        documents=[make_document()],
        other_instruments=[],
        other_documents=[],
        min_fdr_term_months=12,
        required_paise=15_00_000_00,
        other_valid_amount_paise=0,
    )
    assert flags == []


def test_duplicate_fdr_number():
    instrument = make_instrument(id=2)
    other = make_instrument(id=1, fdr_number="SBI / FDR / 2024 / 778812")
    flag = anomalies.check_duplicate_fdr_number(instrument, [(other, 99)])
    assert flag is not None
    assert flag.type == "duplicate_fdr_number"
    assert flag.severity == "high"


def test_duplicate_file_hash():
    doc = make_document(sha256="b" * 64)
    other_doc = make_document(sha256="b" * 64)
    flag = anomalies.check_duplicate_file_hash([doc], [(other_doc, 42)])
    assert flag is not None
    assert flag.type == "duplicate_file_hash"


def test_maturity_before_issue():
    instrument = make_instrument(issue_date=date(2025, 1, 1), maturity_date=date(2024, 1, 1))
    flag = anomalies.check_maturity_before_issue(instrument)
    assert flag is not None
    assert flag.type == "maturity_before_issue"


def test_term_too_short():
    instrument = make_instrument(issue_date=date(2026, 1, 1), maturity_date=date(2026, 6, 1))
    flag = anomalies.check_term_too_short(instrument, min_fdr_term_months=12)
    assert flag is not None
    assert flag.type == "term_too_short"


def test_amount_below_required_with_no_other_coverage():
    instrument = make_instrument(amount_paise=5_00_000_00)
    flag = anomalies.check_amount_below_required(instrument, required_paise=15_00_000_00, other_valid_amount_paise=0)
    assert flag is not None


def test_amount_below_required_cleared_by_other_instrument():
    instrument = make_instrument(amount_paise=5_00_000_00)
    flag = anomalies.check_amount_below_required(
        instrument, required_paise=15_00_000_00, other_valid_amount_paise=10_00_000_00
    )
    assert flag is None


def test_beneficiary_missing():
    instrument = make_instrument(beneficiary="Some Other College")
    flag = anomalies.check_beneficiary_missing(instrument)
    assert flag is not None
    assert flag.severity == "high"


def test_lien_missing():
    instrument = make_instrument(lien_text="No lien information provided.")
    flag = anomalies.check_lien_missing(instrument)
    assert flag is not None


def test_ifsc_invalid():
    instrument = make_instrument(ifsc="INVALID123")
    flag = anomalies.check_ifsc_invalid(instrument)
    assert flag is not None


def test_ifsc_bank_mismatch():
    instrument = make_instrument(ifsc="HDFC0001234", bank_name="State Bank of India")
    flag = anomalies.check_ifsc_bank_mismatch(instrument)
    assert flag is not None
    assert flag.evidence["expected_bank"] == "HDFC Bank"


def test_ifsc_bank_mismatch_not_raised_for_invalid_ifsc():
    instrument = make_instrument(ifsc="BAD", bank_name="State Bank of India")
    flag = anomalies.check_ifsc_bank_mismatch(instrument)
    assert flag is None


def test_pdf_metadata_suspicious_creation_date_before_issue():
    instrument = make_instrument(issue_date=date(2024, 6, 1))
    doc = make_document(pdf_metadata_json={"creation_date": "2024-01-01", "producer": "", "creator": ""})
    flag = anomalies.check_pdf_metadata_suspicious(instrument, [doc])
    assert flag is not None
    assert flag.severity == "low"


def test_pdf_metadata_suspicious_editing_tool():
    instrument = make_instrument()
    doc = make_document(pdf_metadata_json={"producer": "Adobe Photoshop 2024", "creator": ""})
    flag = anomalies.check_pdf_metadata_suspicious(instrument, [doc])
    assert flag is not None


def test_bank_mismatch_on_differing_values():
    instrument = make_instrument()
    flag = anomalies.check_bank_mismatch(instrument, {"maturity": "2034-03-15"})
    assert flag is not None
    assert flag.type == "bank_mismatch"


def test_bank_mismatch_none_when_values_equal_claimed():
    instrument = make_instrument()
    flag = anomalies.check_bank_mismatch(instrument, {"maturity": instrument.maturity_date.isoformat()})
    assert flag is None


def test_never_uses_the_word_fraud():
    instrument = make_instrument(beneficiary="bad")
    flag = anomalies.check_beneficiary_missing(instrument)
    text = flag.title + " ".join(r["text"] for r in flag.reasons)
    assert "fraud" not in text.lower()

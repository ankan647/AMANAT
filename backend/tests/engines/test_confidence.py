from datetime import date

from app.db.enums import FieldGrade
from app.db.models import Institution, Instrument
from app.services import confidence


def _make_institution(db, code="DEMO-CONF"):
    inst = Institution(
        code=code,
        name="Conf College",
        state="State",
        category="Technology",
        programme_type="UG",
        is_government=False,
        approval_year=2015,
        years_existing_elsewhere=0,
        deposit_request_date=date(2020, 1, 1),
        closure_date=None,
        status="active",
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return inst


def _make_instrument(db, institution_id, amount_paise=15_00_000_00, suffix="1"):
    from datetime import datetime, timezone

    instrument = Instrument(
        institution_id=institution_id,
        fdr_number=f"FDR/{suffix}",
        fdr_number_norm=f"FDR{suffix}",
        bank_name="State Bank of India",
        branch="Main",
        ifsc="SBIN0001234",
        amount_paise=amount_paise,
        issue_date=date(2023, 1, 1),
        maturity_date=date(2033, 1, 1),
        beneficiary="AICTE, Government of India",
        lien_text="Lien marked in favour of AICTE",
        status="active",
        created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
    )
    db.add(instrument)
    db.commit()
    db.refresh(instrument)
    return instrument


def test_init_fields_all_claimed(db):
    inst = _make_institution(db, "DEMO-CONF1")
    instrument = _make_instrument(db, inst.id, suffix="c1")
    fields = confidence.init_fields_for_instrument(db, instrument)
    assert len(fields) == 7
    assert all(f.grade == FieldGrade.claimed.value for f in fields)
    assert confidence.instrument_grade(fields) == FieldGrade.claimed.value


def test_upgrade_field_only_moves_forward(db):
    inst = _make_institution(db, "DEMO-CONF2")
    instrument = _make_instrument(db, inst.id, suffix="c2")
    confidence.init_fields_for_instrument(db, instrument)

    confidence.upgrade_field(db, instrument.id, "amount", FieldGrade.document_checked.value, "document:1")
    fields = confidence.get_fields(db, instrument.id)
    amount_field = next(f for f in fields if f.field_name == "amount")
    assert amount_field.grade == FieldGrade.document_checked.value

    # downgrade attempt is a no-op
    confidence.upgrade_field(db, instrument.id, "amount", FieldGrade.claimed.value, "document:1")
    fields = confidence.get_fields(db, instrument.id)
    amount_field = next(f for f in fields if f.field_name == "amount")
    assert amount_field.grade == FieldGrade.document_checked.value


def test_instrument_grade_is_weakest_field(db):
    inst = _make_institution(db, "DEMO-CONF3")
    instrument = _make_instrument(db, inst.id, suffix="c3")
    confidence.init_fields_for_instrument(db, instrument)
    for field_name in ["fdr_number", "bank", "amount", "issue_date", "maturity", "beneficiary"]:
        confidence.upgrade_field(db, instrument.id, field_name, FieldGrade.bank_confirmed.value, "bank_request:BR-2026-0001")
    fields = confidence.get_fields(db, instrument.id)
    assert confidence.instrument_grade(fields) == FieldGrade.claimed.value  # lien still claimed


def test_institution_confidence_pct_weighted_by_amount(db):
    inst = _make_institution(db, "DEMO-CONF4")
    i1 = _make_instrument(db, inst.id, amount_paise=10_00_000_00, suffix="c4a")
    i2 = _make_instrument(db, inst.id, amount_paise=10_00_000_00, suffix="c4b")
    confidence.init_fields_for_instrument(db, i1)
    confidence.init_fields_for_instrument(db, i2)
    for field_name in ["fdr_number", "bank", "amount", "issue_date", "maturity", "beneficiary", "lien"]:
        confidence.upgrade_field(db, i1.id, field_name, FieldGrade.bank_confirmed.value, "bank_request:BR-2026-0002")

    pct = confidence.institution_confidence_pct(db, [i1, i2], exempt=False)
    assert pct == 50


def test_confidence_is_zero_when_no_valid_instruments(db):
    pct = confidence.institution_confidence_pct(db, [], exempt=False)
    assert pct == 0


def test_confidence_is_null_when_exempt(db):
    pct = confidence.institution_confidence_pct(db, [], exempt=True)
    assert pct is None

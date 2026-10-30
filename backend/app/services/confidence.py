"""Verification Confidence: how much of the held deposit has the bank actually confirmed? (5.5)"""

from sqlalchemy.orm import Session

from app.core.clock import now
from app.db.enums import FIELD_GRADE_ORDER, FieldGrade, FieldName
from app.db.models import Instrument, InstrumentField

ALL_FIELD_NAMES = [f.value for f in FieldName]

FIELD_VALUE_GETTERS = {
    FieldName.fdr_number.value: lambda i: i.fdr_number,
    FieldName.bank.value: lambda i: i.bank_name,
    FieldName.amount.value: lambda i: str(i.amount_paise),
    FieldName.issue_date.value: lambda i: i.issue_date.isoformat(),
    FieldName.maturity.value: lambda i: i.maturity_date.isoformat(),
    FieldName.beneficiary.value: lambda i: i.beneficiary,
    FieldName.lien.value: lambda i: i.lien_text,
}


def init_fields_for_instrument(db: Session, instrument: Instrument) -> list[InstrumentField]:
    rows = []
    for field_name in ALL_FIELD_NAMES:
        row = InstrumentField(
            instrument_id=instrument.id,
            field_name=field_name,
            value=FIELD_VALUE_GETTERS[field_name](instrument),
            grade=FieldGrade.claimed.value,
            source="institution",
            updated_at=now(),
        )
        db.add(row)
        rows.append(row)
    db.commit()
    for row in rows:
        db.refresh(row)
    return rows


def get_fields(db: Session, instrument_id: int) -> list[InstrumentField]:
    return (
        db.query(InstrumentField)
        .filter(InstrumentField.instrument_id == instrument_id)
        .order_by(InstrumentField.field_name)
        .all()
    )


def instrument_grade(fields: list[InstrumentField]) -> str:
    if not fields:
        return FieldGrade.claimed.value
    weakest = min(fields, key=lambda f: FIELD_GRADE_ORDER[FieldGrade(f.grade)])
    return weakest.grade


def upgrade_field(
    db: Session, instrument_id: int, field_name: str, new_grade: str, source: str
) -> InstrumentField | None:
    row = (
        db.query(InstrumentField)
        .filter(
            InstrumentField.instrument_id == instrument_id,
            InstrumentField.field_name == field_name,
        )
        .first()
    )
    if row is None:
        return None
    if FIELD_GRADE_ORDER[FieldGrade(new_grade)] <= FIELD_GRADE_ORDER[FieldGrade(row.grade)]:
        return None
    row.grade = new_grade
    row.source = source
    row.updated_at = now()
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def institution_confidence_pct(
    db: Session, instruments_valid_today: list[Instrument], exempt: bool
) -> int | None:
    if exempt:
        return None
    if not instruments_valid_today:
        return 0
    total = sum(i.amount_paise for i in instruments_valid_today)
    if total == 0:
        return 0
    confirmed = 0
    for instrument in instruments_valid_today:
        fields = get_fields(db, instrument.id)
        if instrument_grade(fields) == FieldGrade.bank_confirmed.value:
            confirmed += instrument.amount_paise
    return round(confirmed / total * 100)

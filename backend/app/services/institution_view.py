"""Composes rules_engine + coverage + confidence for one institution (reused by several routers)."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Institution, Instrument
from app.services import confidence, coverage, dashboard, rules_engine


@dataclass
class InstitutionView:
    institution: Institution
    rule_result: rules_engine.InstitutionRuleResult
    coverage_result: coverage.CoverageResult
    confidence_pct: int | None
    matrix_cell: str | None
    instruments: list[Instrument]


def build_institution_view(db: Session, institution: Institution, today: date) -> InstitutionView:
    settings = get_settings()
    instruments = db.query(Instrument).filter(Instrument.institution_id == institution.id).all()

    rule_result = rules_engine.resolve_for_institution(db, institution)
    cov = coverage.compute_coverage(
        instruments=instruments,
        today=today,
        period_start=rule_result.period_start,
        period_end=rule_result.period_end,
        amount_paise=rule_result.amount_paise,
        exempt=rule_result.exempt,
        exempt_reason=rule_result.exempt_reason,
        expiring_window_days=settings.EXPIRING_WINDOW_DAYS,
    )
    valid_today_instruments = coverage.contributing_instruments_on(instruments, today)
    conf_pct = confidence.institution_confidence_pct(db, valid_today_instruments, rule_result.exempt)
    matrix_cell = dashboard.matrix_cell_for(cov.status, conf_pct, settings.CONFIDENCE_HIGH_THRESHOLD)

    return InstitutionView(
        institution=institution,
        rule_result=rule_result,
        coverage_result=cov,
        confidence_pct=conf_pct,
        matrix_cell=matrix_cell,
        instruments=instruments,
    )


def next_action_for(matrix_cell: str | None) -> dict:
    if matrix_cell is None:
        return {"key": None, "label": "No action: exempt"}
    return {"key": matrix_cell, "label": dashboard.MATRIX_LABELS[matrix_cell]}


def bank_confirmed_paise_for(db: Session, instruments_valid_today: list[Instrument]) -> int:
    from app.db.enums import FieldGrade
    from app.services.confidence import get_fields, instrument_grade

    total = 0
    for instrument in instruments_valid_today:
        fields = get_fields(db, instrument.id)
        if fields and instrument_grade(fields) == FieldGrade.bank_confirmed.value:
            total += instrument.amount_paise
    return total


def next_maturity_for(instruments: list[Instrument], today: date) -> date | None:
    future = [i.maturity_date for i in instruments if i.maturity_date >= today]
    return min(future) if future else None

"""Rules engine: applicability matching, version selection, required amount/period, impact preview.

See AMANAT_SPEC.md section 5.3.
"""

from dataclasses import dataclass
from datetime import date

from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session

from app.db.models import Institution, Rule, RuleApplication, RuleVersion

APPLICABILITY_KEYS = (
    "approval_year_min",
    "approval_year_max",
    "categories",
    "programme_types",
    "is_government",
    "years_existing_elsewhere_max",
)


def applicability_matches(applicability: dict, institution: Institution) -> bool:
    if "approval_year_min" in applicability:
        if institution.approval_year < applicability["approval_year_min"]:
            return False
    if "approval_year_max" in applicability:
        if institution.approval_year > applicability["approval_year_max"]:
            return False
    if "categories" in applicability:
        if institution.category not in applicability["categories"]:
            return False
    if "programme_types" in applicability:
        if institution.programme_type not in applicability["programme_types"]:
            return False
    if "is_government" in applicability:
        if institution.is_government != applicability["is_government"]:
            return False
    if "years_existing_elsewhere_max" in applicability:
        if institution.years_existing_elsewhere > applicability["years_existing_elsewhere_max"]:
            return False
    return True


def specificity(applicability: dict) -> int:
    return len(applicability)


def select_version(db: Session, rule_key: str, institution: Institution, on_date: date) -> RuleVersion | None:
    candidates = (
        db.query(RuleVersion)
        .join(Rule, Rule.id == RuleVersion.rule_id)
        .filter(Rule.key == rule_key)
        .filter(RuleVersion.status == "active")
        .filter(RuleVersion.effective_from <= on_date)
        .filter((RuleVersion.effective_to.is_(None)) | (RuleVersion.effective_to >= on_date))
        .all()
    )
    matching = [v for v in candidates if applicability_matches(v.applicability_json or {}, institution)]
    if not matching:
        return None
    matching.sort(
        key=lambda v: (specificity(v.applicability_json or {}), v.effective_from), reverse=True
    )
    return matching[0]


@dataclass
class ExemptionResult:
    exempt: bool
    reason: str | None
    rule_version: RuleVersion | None


def evaluate_exemption(db: Session, institution: Institution) -> ExemptionResult:
    version = select_version(db, "exemption", institution, institution.deposit_request_date)
    if version is None:
        return ExemptionResult(exempt=False, reason=None, rule_version=None)
    params = version.parameters_json or {}
    min_years = params.get("min_years", 10)
    government_exempt = params.get("government_exempt", False)

    if institution.years_existing_elsewhere >= min_years:
        reason = (
            f"Exempt: operating elsewhere for {institution.years_existing_elsewhere} years "
            f"(>= {min_years} required)."
        )
        return ExemptionResult(exempt=True, reason=reason, rule_version=version)
    if government_exempt and institution.is_government:
        reason = "Exempt: government institution (government exemption enabled)."
        return ExemptionResult(exempt=True, reason=reason, rule_version=version)
    return ExemptionResult(exempt=False, reason=None, rule_version=version)


@dataclass
class RequiredDepositResult:
    rule_version: RuleVersion
    amount_paise: int
    term_years: int
    min_fdr_term_months: int
    reason_text: str


def evaluate_required_deposit(db: Session, institution: Institution) -> RequiredDepositResult | None:
    version = select_version(
        db, "required_deposit", institution, institution.deposit_request_date
    )
    if version is None:
        return None
    params = version.parameters_json or {}
    amounts = params.get("amounts", {})
    amount_paise = amounts.get(institution.category, 0)
    to_year = version.effective_to.year if version.effective_to else "onward"
    reason_text = (
        f"Deposit requested {institution.deposit_request_date.isoformat()}; "
        f"rule v{version.version} ({version.effective_from.year}-{to_year}) applies; "
        f"category {institution.category}."
    )
    return RequiredDepositResult(
        rule_version=version,
        amount_paise=amount_paise,
        term_years=params.get("term_years", 10),
        min_fdr_term_months=params.get("min_fdr_term_months", 12),
        reason_text=reason_text,
    )


@dataclass
class InstitutionRuleResult:
    exempt: bool
    exempt_reason: str | None
    amount_paise: int
    period_start: date
    period_end: date
    min_fdr_term_months: int
    rule_version: RuleVersion | None
    reason_text: str


def resolve_for_institution(db: Session, institution: Institution) -> InstitutionRuleResult:
    exemption = evaluate_exemption(db, institution)
    if exemption.exempt:
        period_start = institution.deposit_request_date
        period_end = institution.closure_date or (period_start + relativedelta(years=10))
        return InstitutionRuleResult(
            exempt=True,
            exempt_reason=exemption.reason,
            amount_paise=0,
            period_start=period_start,
            period_end=period_end,
            min_fdr_term_months=12,
            rule_version=exemption.rule_version,
            reason_text=exemption.reason or "Exempt.",
        )

    required = evaluate_required_deposit(db, institution)
    if required is None:
        period_start = institution.deposit_request_date
        period_end = institution.closure_date or period_start
        return InstitutionRuleResult(
            exempt=False,
            exempt_reason=None,
            amount_paise=0,
            period_start=period_start,
            period_end=period_end,
            min_fdr_term_months=12,
            rule_version=None,
            reason_text="No applicable required-deposit rule found.",
        )

    period_start = institution.deposit_request_date
    natural_end = period_start + relativedelta(years=required.term_years)
    period_end = (
        min(natural_end, institution.closure_date) if institution.closure_date else natural_end
    )
    return InstitutionRuleResult(
        exempt=False,
        exempt_reason=None,
        amount_paise=required.amount_paise,
        period_start=period_start,
        period_end=period_end,
        min_fdr_term_months=required.min_fdr_term_months,
        rule_version=required.rule_version,
        reason_text=required.reason_text,
    )


def persist_application(db: Session, institution: Institution, result: InstitutionRuleResult, applied_on: date) -> RuleApplication | None:
    if result.rule_version is None:
        return None
    row = RuleApplication(
        instrument_id=None,
        institution_id=institution.id,
        rule_version_id=result.rule_version.id,
        reason_text=result.reason_text,
        applied_on=applied_on,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def recompute_applications_for_all(db: Session, applied_on: date) -> int:
    """Recompute rule_application rows for every institution (called when a version activates)."""
    institutions = db.query(Institution).all()
    count = 0
    for institution in institutions:
        result = resolve_for_institution(db, institution)
        if result.rule_version is not None:
            persist_application(db, institution, result, applied_on)
            count += 1
    return count

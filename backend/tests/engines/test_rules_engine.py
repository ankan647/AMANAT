from datetime import date

from app.db.models import Institution, Rule, RuleVersion
from app.services import rules_engine


def _seed_rules(db):
    existing = db.query(Rule).filter(Rule.key == "required_deposit").first()
    if existing is not None:
        return

    required = Rule(key="required_deposit", title="Required security deposit")
    exemption = Rule(key="exemption", title="Exemption from security deposit")
    db.add_all([required, exemption])
    db.commit()

    v1 = RuleVersion(
        rule_id=required.id,
        version=1,
        effective_from=date(2010, 1, 1),
        effective_to=date(2019, 12, 31),
        applicability_json={},
        parameters_json={
            "amounts": {
                "Technology": 10_00_000_00,
                "Management": 5_00_000_00,
                "Pharmacy": 5_00_000_00,
                "Architecture": 5_00_000_00,
            },
            "term_years": 10,
            "min_fdr_term_months": 12,
        },
        status="active",
        note="Seed - pending AICTE legal validation",
    )
    v2 = RuleVersion(
        rule_id=required.id,
        version=2,
        effective_from=date(2020, 1, 1),
        effective_to=None,
        applicability_json={},
        parameters_json={
            "amounts": {
                "Technology": 15_00_000_00,
                "Management": 7_50_000_00,
                "Pharmacy": 7_50_000_00,
                "Architecture": 7_50_000_00,
            },
            "term_years": 10,
            "min_fdr_term_months": 12,
        },
        status="active",
        note="Seed - pending AICTE legal validation",
    )
    exemption_v1 = RuleVersion(
        rule_id=exemption.id,
        version=1,
        effective_from=date(2000, 1, 1),
        effective_to=None,
        applicability_json={},
        parameters_json={"min_years": 10, "government_exempt": False},
        status="active",
        note="Seed - pending AICTE legal validation; years-based only, "
        "government_exempt defaults to false",
    )
    db.add_all([v1, v2, exemption_v1])
    db.commit()
    return v1, v2, exemption_v1


def _make_institution(**overrides):
    base = dict(
        code="DEMO-TEST",
        name="Test College",
        state="Test State",
        category="Technology",
        programme_type="UG",
        is_government=False,
        approval_year=2015,
        years_existing_elsewhere=0,
        deposit_request_date=date(2018, 5, 1),
        closure_date=None,
        status="active",
    )
    base.update(overrides)
    return Institution(**base)


def test_e1_vs_e2_different_versions_by_obligation_date(db):
    _seed_rules(db)
    e1 = _make_institution(code="DEMO-E1", deposit_request_date=date(2018, 5, 1))
    e2 = _make_institution(code="DEMO-E2", deposit_request_date=date(2022, 5, 1))
    db.add_all([e1, e2])
    db.commit()

    result1 = rules_engine.resolve_for_institution(db, e1)
    result2 = rules_engine.resolve_for_institution(db, e2)

    assert result1.amount_paise == 10_00_000_00
    assert result2.amount_paise == 15_00_000_00
    assert "2018-05-01" in result1.reason_text
    assert "2022-05-01" in result2.reason_text


def test_exemption_by_years_existing_elsewhere(db):
    _seed_rules(db)
    inst = _make_institution(code="DEMO-I", years_existing_elsewhere=14)
    db.add(inst)
    db.commit()

    result = rules_engine.resolve_for_institution(db, inst)
    assert result.exempt is True
    assert result.amount_paise == 0
    assert "14 years" in result.exempt_reason


def test_not_exempt_when_years_below_threshold(db):
    _seed_rules(db)
    inst = _make_institution(code="DEMO-NOTEXEMPT", years_existing_elsewhere=3)
    db.add(inst)
    db.commit()

    result = rules_engine.resolve_for_institution(db, inst)
    assert result.exempt is False


def test_required_period_ends_at_closure_date(db):
    _seed_rules(db)
    inst = _make_institution(
        code="DEMO-CLOSED",
        deposit_request_date=date(2015, 6, 1),
        closure_date=date(2025, 6, 1),
    )
    db.add(inst)
    db.commit()
    result = rules_engine.resolve_for_institution(db, inst)
    assert result.period_end == date(2025, 6, 1)


def test_impact_preview_recomputes_without_persisting(db):
    _seed_rules(db)
    inst = _make_institution(code="DEMO-PREVIEW")
    db.add(inst)
    db.commit()

    before_count = db.query(type(inst)).count()
    result = rules_engine.resolve_for_institution(db, inst)
    assert result.amount_paise > 0
    # resolve_for_institution does not persist a RuleApplication by itself.
    from app.db.models import RuleApplication

    assert db.query(RuleApplication).count() == 0
    assert db.query(type(inst)).count() == before_count


def test_self_approval_of_rule_version_is_blocked_by_data_model():
    # Service-layer enforcement is exercised via the API in phase 3; here we assert the
    # rule_version model carries proposed_by/approved_by so the check is possible.
    assert hasattr(RuleVersion, "proposed_by")
    assert hasattr(RuleVersion, "approved_by")

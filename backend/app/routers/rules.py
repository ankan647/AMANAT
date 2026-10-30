from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core import audit
from app.core.clock import today as clock_today
from app.core.errors import InvalidStateError, NotFoundError, SodViolationError
from app.core.permissions import CurrentUser, require_roles
from app.db.models import Institution, Rule, RuleVersion
from app.db.session import get_db
from app.services import coverage as coverage_service
from app.services import rules_engine

router = APIRouter(prefix="/api/v1", tags=["rules"])


def _version_out(v: RuleVersion) -> dict:
    return {
        "id": v.id,
        "rule_id": v.rule_id,
        "version": v.version,
        "effective_from": v.effective_from.isoformat(),
        "effective_to": v.effective_to.isoformat() if v.effective_to else None,
        "applicability": v.applicability_json,
        "parameters": v.parameters_json,
        "status": v.status,
        "proposed_by": v.proposed_by,
        "approved_by": v.approved_by,
        "note": v.note,
    }


@router.get("/rules")
def list_rules(db: Session = Depends(get_db), current_user: CurrentUser = Depends(require_roles(
    "institution", "scrutiny", "senior_approver", "competent_authority", "admin", "auditor", "bank_officer"
))) -> dict:
    rules = db.query(Rule).all()
    out = []
    for rule in rules:
        versions = db.query(RuleVersion).filter(RuleVersion.rule_id == rule.id).order_by(RuleVersion.version).all()
        out.append({"id": rule.id, "key": rule.key, "title": rule.title, "versions": [_version_out(v) for v in versions]})
    return {"data": out}


@router.post("/rules/{rule_id}/versions")
def create_version(
    rule_id: int,
    body: dict,
    current_user: CurrentUser = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    rule = db.query(Rule).filter(Rule.id == rule_id).first()
    if rule is None:
        raise NotFoundError("Rule not found.")
    max_version = db.query(RuleVersion).filter(RuleVersion.rule_id == rule_id).count()
    version = RuleVersion(
        rule_id=rule_id,
        version=max_version + 1,
        effective_from=date.fromisoformat(body["effective_from"]),
        effective_to=date.fromisoformat(body["effective_to"]) if body.get("effective_to") else None,
        applicability_json=body.get("applicability", {}),
        parameters_json=body.get("parameters", {}),
        status="draft",
        proposed_by=current_user.id,
        note=body.get("note", ""),
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    audit.record(
        db, actor_id=current_user.id, actor_role=current_user.role, action="rule_version_drafted",
        entity_type="rule_version", entity_id=version.id, details={"rule_id": rule_id},
    )
    return {"data": _version_out(version)}


@router.post("/rule-versions/{version_id}/impact-preview")
def impact_preview(
    version_id: int,
    current_user: CurrentUser = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    draft = db.query(RuleVersion).filter(RuleVersion.id == version_id).first()
    if draft is None:
        raise NotFoundError("Rule version not found.")

    original_status = draft.status
    institutions = db.query(Institution).all()

    # "before": draft left as-is (inactive, so it cannot be selected).
    before_results = {inst.id: rules_engine.resolve_for_institution(db, inst) for inst in institutions}

    # "after": temporarily flip the draft to active (in-memory only, never committed) so the
    # selection logic can consider it, then recompute for every institution.
    draft.status = "active"
    after_results = {inst.id: rules_engine.resolve_for_institution(db, inst) for inst in institutions}
    draft.status = original_status

    out = []
    unchanged = 0
    today = clock_today()
    for inst in institutions:
        before = before_results[inst.id]
        after = after_results[inst.id]
        before_cov = coverage_service.compute_coverage(
            instruments=[], today=today, period_start=before.period_start, period_end=before.period_end,
            amount_paise=before.amount_paise, exempt=before.exempt, exempt_reason=before.exempt_reason,
            expiring_window_days=60,
        )
        after_cov = coverage_service.compute_coverage(
            instruments=[], today=today, period_start=after.period_start, period_end=after.period_end,
            amount_paise=after.amount_paise, exempt=after.exempt, exempt_reason=after.exempt_reason,
            expiring_window_days=60,
        )
        if before.amount_paise == after.amount_paise and before_cov.status == after_cov.status:
            unchanged += 1
            continue
        out.append(
            {
                "institution_id": inst.id,
                "name": inst.name,
                "before_status": before_cov.status,
                "after_status": after_cov.status,
                "before_required_paise": before.amount_paise,
                "after_required_paise": after.amount_paise,
            }
        )
    return {"data": {"changes": out, "unchanged_count": unchanged}}


@router.post("/rule-versions/{version_id}/submit")
def submit(
    version_id: int,
    current_user: CurrentUser = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    version = db.query(RuleVersion).filter(RuleVersion.id == version_id).first()
    if version is None:
        raise NotFoundError("Rule version not found.")
    version.status = "pending_approval"
    db.add(version)
    db.commit()
    db.refresh(version)
    return {"data": _version_out(version)}


@router.post("/rule-versions/{version_id}/approve")
def approve(
    version_id: int,
    current_user: CurrentUser = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    version = db.query(RuleVersion).filter(RuleVersion.id == version_id).first()
    if version is None:
        raise NotFoundError("Rule version not found.")
    if version.status != "pending_approval":
        raise InvalidStateError("Rule version is not pending approval.")
    if version.proposed_by == current_user.id:
        audit.record(
            db, actor_id=current_user.id, actor_role=current_user.role, action="sod_violation_blocked",
            entity_type="rule_version", entity_id=version.id, details={"rule": "rule_self_approval"},
        )
        raise SodViolationError(
            "You proposed this rule version, so you cannot approve it.", rule="rule_self_approval"
        )
    version.status = "active"
    version.approved_by = current_user.id
    db.add(version)
    db.commit()
    db.refresh(version)

    applied_on = clock_today()
    rules_engine.recompute_applications_for_all(db, applied_on)

    audit.record(
        db, actor_id=current_user.id, actor_role=current_user.role, action="rule_version_approved",
        entity_type="rule_version", entity_id=version.id, details={},
    )
    return {"data": _version_out(version)}


@router.post("/rule-versions/{version_id}/reject")
def reject(
    version_id: int,
    body: dict,
    current_user: CurrentUser = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    version = db.query(RuleVersion).filter(RuleVersion.id == version_id).first()
    if version is None:
        raise NotFoundError("Rule version not found.")
    version.status = "rejected"
    version.note = (version.note + " | Rejected: " + body.get("reason", "")).strip()
    db.add(version)
    db.commit()
    db.refresh(version)
    return {"data": _version_out(version)}

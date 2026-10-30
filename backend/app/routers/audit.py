from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core import audit as audit_service
from app.core import audit_anchor
from app.core.config import get_settings
from app.core.errors import ForbiddenError
from app.core.permissions import CurrentUser, require_roles
from app.db.models import AuditAnchor, AuditLog
from app.db.session import get_anchor_db, get_db
from app.db.triggers import drop_audit_log_triggers, restore_audit_log_triggers

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("")
def list_audit(
    entity_type: str | None = None,
    actor_id: int | None = None,
    from_: str | None = None,
    to: str | None = None,
    current_user: CurrentUser = Depends(require_roles("auditor", "competent_authority")),
    db: Session = Depends(get_db),
) -> dict:
    query = db.query(AuditLog)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if actor_id is not None:
        query = query.filter(AuditLog.actor_id == actor_id)
    rows = query.order_by(AuditLog.seq.asc()).all()
    return {
        "data": [
            {
                "seq": r.seq,
                "ts": r.ts.isoformat(),
                "actor_id": r.actor_id,
                "actor_role": r.actor_role,
                "action": r.action,
                "entity_type": r.entity_type,
                "entity_id": r.entity_id,
                "details": r.details_json,
                "hash": r.hash,
                "prev_hash": r.prev_hash,
            }
            for r in rows
        ],
        "meta": {"page": 1, "page_size": len(rows), "total": len(rows)},
    }


@router.post("/verify")
def verify(
    current_user: CurrentUser = Depends(require_roles("auditor")),
    db: Session = Depends(get_db),
    anchor_db: Session = Depends(get_anchor_db),
) -> dict:
    ok, first_broken, checked = audit_service.verify_chain(db)
    anchor_result = audit_anchor.verify_anchors(db, anchor_db)
    return {
        "data": {
            "ok": ok and not anchor_result["anchor_mismatches"],
            "entries_checked": checked,
            "first_broken_seq": first_broken,
            "anchors_checked": anchor_result["anchors_checked"],
            "anchor_mismatches": anchor_result["anchor_mismatches"],
        }
    }


@router.post("/anchor")
def anchor(
    current_user: CurrentUser = Depends(require_roles("auditor")),
    db: Session = Depends(get_db),
    anchor_db: Session = Depends(get_anchor_db),
) -> dict:
    row = audit_anchor.anchor_now(db, anchor_db)
    return {"data": {"id": row.id, "anchored_at": row.anchored_at.isoformat(), "seq_upto": row.seq_upto, "head_hash": row.head_hash}}


@router.get("/anchors")
def list_anchors(
    current_user: CurrentUser = Depends(require_roles("auditor")),
    anchor_db: Session = Depends(get_anchor_db),
) -> dict:
    rows = anchor_db.query(AuditAnchor).order_by(AuditAnchor.seq_upto.asc()).all()
    return {
        "data": [
            {"id": r.id, "anchored_at": r.anchored_at.isoformat(), "seq_upto": r.seq_upto, "head_hash": r.head_hash}
            for r in rows
        ]
    }


@router.post("/dev/tamper")
def dev_tamper(
    body: dict,
    current_user: CurrentUser = Depends(require_roles("auditor", "admin")),
    db: Session = Depends(get_db),
    anchor_db: Session = Depends(get_anchor_db),
) -> dict:
    settings = get_settings()
    if not settings.DEMO_MODE:
        raise ForbiddenError("Only available in DEMO_MODE.")
    from app.db.session import get_engine

    seq = body["seq"]
    row = db.query(AuditLog).filter(AuditLog.seq == seq).first()
    if row is None:
        raise ForbiddenError("Entry not found.")
    original_details = row.details_json

    drop_audit_log_triggers(get_engine())
    row.details_json = body.get("new_details", {"tampered": True})
    db.add(row)
    db.commit()

    audit_anchor.record_side_log(anchor_db, "tamper", {"seq": seq, "original_details": original_details})
    return {"data": {"seq": seq, "tampered": True}}


@router.post("/dev/restore")
def dev_restore(
    body: dict,
    current_user: CurrentUser = Depends(require_roles("auditor", "admin")),
    db: Session = Depends(get_db),
    anchor_db: Session = Depends(get_anchor_db),
) -> dict:
    settings = get_settings()
    if not settings.DEMO_MODE:
        raise ForbiddenError("Only available in DEMO_MODE.")
    from app.db.session import get_engine

    seq = body["seq"]
    row = db.query(AuditLog).filter(AuditLog.seq == seq).first()
    if row is None:
        raise ForbiddenError("Entry not found.")
    row.details_json = body.get("original_details", {})
    db.add(row)
    db.commit()
    restore_audit_log_triggers(get_engine())

    audit_anchor.record_side_log(anchor_db, "restore", {"seq": seq})
    return {"data": {"seq": seq, "restored": True}}

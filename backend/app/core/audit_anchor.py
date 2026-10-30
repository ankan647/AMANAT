"""Daily anchoring of the audit hash chain into a SEPARATE SQLite file.

The main app has no update/delete path to `audit_anchor` — this module is the only writer, and it
writes through its own connection (`get_anchor_sessionmaker()`), never through the main session.
"""

from sqlalchemy.orm import Session

from app.core import audit
from app.core.clock import now
from app.db.models import AnchorSideLog, AuditAnchor


def anchor_now(main_db: Session, anchor_db: Session) -> AuditAnchor:
    seq_upto = audit.head_seq(main_db)
    head = audit.head_hash(main_db)
    row = AuditAnchor(anchored_at=now(), seq_upto=seq_upto, head_hash=head)
    anchor_db.add(row)
    anchor_db.commit()
    anchor_db.refresh(row)
    return row


def verify_anchors(main_db: Session, anchor_db: Session) -> dict:
    anchors = anchor_db.query(AuditAnchor).order_by(AuditAnchor.seq_upto.asc()).all()
    mismatches = []
    for anchor in anchors:
        expected = audit.hash_at_seq(main_db, anchor.seq_upto)
        if expected != anchor.head_hash:
            mismatches.append(
                {
                    "anchor_id": anchor.id,
                    "seq_upto": anchor.seq_upto,
                    "expected": expected,
                    "found": anchor.head_hash,
                }
            )
    return {"anchors_checked": len(anchors), "anchor_mismatches": mismatches}


def record_side_log(anchor_db: Session, action: str, details: dict) -> AnchorSideLog:
    row = AnchorSideLog(ts=now(), action=action, details_json=details)
    anchor_db.add(row)
    anchor_db.commit()
    anchor_db.refresh(row)
    return row

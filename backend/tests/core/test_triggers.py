import pytest
from sqlalchemy.exc import IntegrityError

from app.core import audit
from app.db.models import AuditAnchor


def test_audit_log_blocks_update(db):
    row = audit.record(
        db, actor_id=1, actor_role="admin", action="test_action", entity_type="test", entity_id=1
    )
    row.action = "tampered"
    db.add(row)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_audit_log_blocks_delete(db):
    row = audit.record(
        db, actor_id=1, actor_role="admin", action="test_action_2", entity_type="test", entity_id=2
    )
    db.delete(row)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_audit_anchor_blocks_update_and_delete(anchor_db):
    from datetime import datetime, timezone

    row = AuditAnchor(anchored_at=datetime.now(timezone.utc), seq_upto=1, head_hash="a" * 64)
    anchor_db.add(row)
    anchor_db.commit()

    row.seq_upto = 2
    anchor_db.add(row)
    with pytest.raises(IntegrityError):
        anchor_db.commit()
    anchor_db.rollback()

    anchor_db.refresh(row)
    anchor_db.delete(row)
    with pytest.raises(IntegrityError):
        anchor_db.commit()
    anchor_db.rollback()

from app.core import audit, audit_anchor


def test_chain_verifies_ok(db):
    audit.record(db, actor_id=1, actor_role="admin", action="a1", entity_type="t", entity_id=1)
    audit.record(db, actor_id=1, actor_role="admin", action="a2", entity_type="t", entity_id=2)
    audit.record(db, actor_id=2, actor_role="scrutiny", action="a3", entity_type="t", entity_id=3)

    ok, first_broken, checked = audit.verify_chain(db)
    assert ok is True
    assert first_broken is None
    assert checked >= 3


def test_genesis_prev_hash_is_64_zeros(db):
    from app.db.models import AuditLog

    row = db.query(AuditLog).order_by(AuditLog.seq.asc()).first()
    assert row.prev_hash == "0" * 64


def test_seq_strictly_increasing_no_gaps(db):
    from app.db.models import AuditLog

    rows = db.query(AuditLog).order_by(AuditLog.seq.asc()).all()
    seqs = [r.seq for r in rows]
    assert seqs == list(range(1, len(seqs) + 1))


def test_anchor_now_and_verify(db, anchor_db):
    audit.record(db, actor_id=1, actor_role="admin", action="pre_anchor", entity_type="t", entity_id=5)
    audit_anchor.anchor_now(db, anchor_db)
    result = audit_anchor.verify_anchors(db, anchor_db)
    assert result["anchor_mismatches"] == []

"""Append-only, hash-chained audit log. Every state-changing service call goes through `record()`."""

import hashlib
import json
from typing import Any

from sqlalchemy.orm import Session

from app.core.clock import now
from app.db.models import AuditLog

GENESIS_HASH = "0" * 64


def canonical_json(obj: Any) -> str:
    """Canonical JSON: sorted keys, no whitespace, UTF-8-safe string."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _compute_hash(prev_hash: str, entry_without_hash: dict[str, Any]) -> str:
    payload = prev_hash + canonical_json(entry_without_hash)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _ts_key(ts) -> str:  # type: ignore[no-untyped-def]
    # SQLite's DateTime column drops tzinfo on round-trip, so both the write path and the
    # verify-on-read path must hash the same naive-UTC representation of the timestamp.
    return ts.replace(tzinfo=None).isoformat()


def record(
    db: Session,
    *,
    actor_id: int | None,
    actor_role: str,
    action: str,
    entity_type: str,
    entity_id: int | None,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    last = db.query(AuditLog).order_by(AuditLog.seq.desc()).first()
    next_seq = (last.seq + 1) if last else 1
    prev_hash = last.hash if last else GENESIS_HASH

    ts = now()
    entry_without_hash = {
        "seq": next_seq,
        "ts": _ts_key(ts),
        "actor_id": actor_id,
        "actor_role": actor_role,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "details": details or {},
        "prev_hash": prev_hash,
    }
    entry_hash = _compute_hash(prev_hash, entry_without_hash)

    row = AuditLog(
        seq=next_seq,
        ts=ts,
        actor_id=actor_id,
        actor_role=actor_role,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details_json=details or {},
        prev_hash=prev_hash,
        hash=entry_hash,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def verify_chain(db: Session) -> tuple[bool, int | None, int]:
    """Recompute the whole chain. Returns (ok, first_broken_seq, entries_checked)."""
    rows = db.query(AuditLog).order_by(AuditLog.seq.asc()).all()
    prev_hash = GENESIS_HASH
    checked = 0
    for row in rows:
        entry_without_hash = {
            "seq": row.seq,
            "ts": _ts_key(row.ts),
            "actor_id": row.actor_id,
            "actor_role": row.actor_role,
            "action": row.action,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "details": row.details_json or {},
            "prev_hash": prev_hash,
        }
        expected_hash = _compute_hash(prev_hash, entry_without_hash)
        checked += 1
        if expected_hash != row.hash or row.prev_hash != prev_hash:
            return False, row.seq, checked
        prev_hash = row.hash
    return True, None, checked


def head_hash(db: Session) -> str:
    last = db.query(AuditLog).order_by(AuditLog.seq.desc()).first()
    return last.hash if last else GENESIS_HASH


def head_seq(db: Session) -> int:
    last = db.query(AuditLog).order_by(AuditLog.seq.desc()).first()
    return last.seq if last else 0


def hash_at_seq(db: Session, seq: int) -> str | None:
    row = db.query(AuditLog).filter(AuditLog.seq == seq).first()
    return row.hash if row else None

"""SQLite triggers enforcing append-only audit tables and DB-level separation of duties.

Applied with raw SQL via `sqlalchemy.event.listens_for(engine, "connect")`-style execution, or
explicitly via `install_triggers()` / `install_anchor_triggers()` after `create_all()`.
"""

from sqlalchemy import text
from sqlalchemy.engine import Engine

AUDIT_LOG_NO_UPDATE = """
CREATE TRIGGER IF NOT EXISTS trg_audit_log_no_update
BEFORE UPDATE ON audit_log
BEGIN
    SELECT RAISE(ABORT, 'AUDIT_APPEND_ONLY');
END;
"""

AUDIT_LOG_NO_DELETE = """
CREATE TRIGGER IF NOT EXISTS trg_audit_log_no_delete
BEFORE DELETE ON audit_log
BEGIN
    SELECT RAISE(ABORT, 'AUDIT_APPEND_ONLY');
END;
"""

AUDIT_ANCHOR_NO_UPDATE = """
CREATE TRIGGER IF NOT EXISTS trg_audit_anchor_no_update
BEFORE UPDATE ON audit_anchor
BEGIN
    SELECT RAISE(ABORT, 'AUDIT_APPEND_ONLY');
END;
"""

AUDIT_ANCHOR_NO_DELETE = """
CREATE TRIGGER IF NOT EXISTS trg_audit_anchor_no_delete
BEFORE DELETE ON audit_anchor
BEGIN
    SELECT RAISE(ABORT, 'AUDIT_APPEND_ONLY');
END;
"""

# Separation of duties, enforced at the DB layer too (service layer also enforces this).
# A new approval row may not be inserted by the same officer who scrutinised the instrument
# linked to its release_request.
SOD_SCRUTINISER_CANNOT_APPROVE = """
CREATE TRIGGER IF NOT EXISTS trg_sod_scrutiniser_cannot_approve
BEFORE INSERT ON approval
WHEN NEW.approver_id = (
    SELECT ia.officer_id
    FROM instrument_assignment ia
    JOIN release_request rr ON rr.instrument_id = ia.instrument_id
    WHERE rr.id = NEW.release_request_id AND ia.role = 'scrutiniser'
    ORDER BY ia.assigned_at DESC
    LIMIT 1
)
BEGIN
    SELECT RAISE(ABORT, 'SOD_VIOLATION');
END;
"""

ALL_MAIN_TRIGGERS = [
    AUDIT_LOG_NO_UPDATE,
    AUDIT_LOG_NO_DELETE,
    SOD_SCRUTINISER_CANNOT_APPROVE,
]

ALL_ANCHOR_TRIGGERS = [
    AUDIT_ANCHOR_NO_UPDATE,
    AUDIT_ANCHOR_NO_DELETE,
]


def install_triggers(engine: Engine) -> None:
    with engine.begin() as conn:
        for stmt in ALL_MAIN_TRIGGERS:
            conn.execute(text(stmt))


def install_anchor_triggers(engine: Engine) -> None:
    with engine.begin() as conn:
        for stmt in ALL_ANCHOR_TRIGGERS:
            conn.execute(text(stmt))


def drop_audit_log_triggers(engine: Engine) -> None:
    """DEMO_MODE only: temporarily drop audit_log append-only triggers for the tamper demo."""
    with engine.begin() as conn:
        conn.execute(text("DROP TRIGGER IF EXISTS trg_audit_log_no_update"))
        conn.execute(text("DROP TRIGGER IF EXISTS trg_audit_log_no_delete"))


def restore_audit_log_triggers(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text(AUDIT_LOG_NO_UPDATE))
        conn.execute(text(AUDIT_LOG_NO_DELETE))

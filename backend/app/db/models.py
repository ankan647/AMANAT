from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.db.base import Base


class Institution(Base):
    __tablename__ = "institution"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    state: Mapped[str] = mapped_column(String(80))
    category: Mapped[str] = mapped_column(String(40))
    programme_type: Mapped[str] = mapped_column(String(40))
    is_government: Mapped[bool] = mapped_column(Boolean, default=False)
    approval_year: Mapped[int] = mapped_column(Integer)
    years_existing_elsewhere: Mapped[int] = mapped_column(Integer, default=0)
    deposit_request_date: Mapped[date] = mapped_column(Date)
    closure_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")


class Instrument(Base):
    __tablename__ = "instrument"

    id: Mapped[int] = mapped_column(primary_key=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("institution.id"), index=True)
    fdr_number: Mapped[str] = mapped_column(String(80))
    fdr_number_norm: Mapped[str] = mapped_column(String(80), index=True)
    bank_name: Mapped[str] = mapped_column(String(120))
    branch: Mapped[str] = mapped_column(String(120))
    ifsc: Mapped[str] = mapped_column(String(11))
    amount_paise: Mapped[int] = mapped_column(Integer)
    issue_date: Mapped[date] = mapped_column(Date)
    maturity_date: Mapped[date] = mapped_column(Date)
    beneficiary: Mapped[str] = mapped_column(Text)
    lien_text: Mapped[str] = mapped_column(Text)
    intimation_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    proof_received_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    penalty_settled: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="lodged", index=True)
    linked_from_instrument_id: Mapped[int | None] = mapped_column(
        ForeignKey("instrument.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime)


class InstrumentAssignment(Base):
    __tablename__ = "instrument_assignment"

    id: Mapped[int] = mapped_column(primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instrument.id"), index=True)
    officer_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    role: Mapped[str] = mapped_column(String(20))
    assigned_at: Mapped[datetime] = mapped_column(DateTime)


class InstrumentField(Base):
    __tablename__ = "instrument_field"

    id: Mapped[int] = mapped_column(primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instrument.id"), index=True)
    field_name: Mapped[str] = mapped_column(String(30))
    value: Mapped[str] = mapped_column(Text)
    grade: Mapped[str] = mapped_column(String(20))
    source: Mapped[str] = mapped_column(String(80))
    updated_at: Mapped[datetime] = mapped_column(DateTime)

    __table_args__ = (UniqueConstraint("instrument_id", "field_name", name="uq_instrument_field"),)


class Document(Base):
    __tablename__ = "document"

    id: Mapped[int] = mapped_column(primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instrument.id"), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    filename: Mapped[str] = mapped_column(String(255))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    mime: Mapped[str] = mapped_column(String(80))
    size: Mapped[int] = mapped_column(Integer)
    ocr_text: Mapped[str] = mapped_column(Text, default="")
    pdf_metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    scan_status: Mapped[str] = mapped_column(String(20), default="clean")
    storage_path: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime)


class BankRequest(Base):
    __tablename__ = "bank_request"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instrument.id"), index=True)
    bank_name: Mapped[str] = mapped_column(String(120))
    branch: Mapped[str] = mapped_column(String(120))
    sent_date: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date)
    response_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    method: Mapped[str] = mapped_column(String(20), default="bank_screen")
    aicte_officer_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    bank_responder_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    outcome: Mapped[str] = mapped_column(String(20), default="pending")
    differing_values_json: Mapped[dict] = mapped_column(JSON, default=dict)
    remarks: Mapped[str] = mapped_column(Text, default="")
    letter_doc_id: Mapped[int | None] = mapped_column(ForeignKey("document.id"), nullable=True)
    accepted_by_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rejected_reason: Mapped[str] = mapped_column(Text, default="")
    reminders_sent: Mapped[int] = mapped_column(Integer, default=0)
    escalation_level: Mapped[int] = mapped_column(Integer, default=0)


class AnomalyFlag(Base):
    __tablename__ = "anomaly_flag"

    id: Mapped[int] = mapped_column(primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instrument.id"), index=True)
    type: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(200))
    reasons_json: Mapped[list] = mapped_column(JSON, default=list)
    evidence_json: Mapped[dict] = mapped_column(JSON, default=dict)
    severity: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    outcome_reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_planted_label: Mapped[bool] = mapped_column(Boolean, default=False)


class PlantedLabel(Base):
    __tablename__ = "planted_label"

    id: Mapped[int] = mapped_column(primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instrument.id"), index=True)
    type: Mapped[str] = mapped_column(String(40))

    __table_args__ = (UniqueConstraint("instrument_id", "type", name="uq_planted_label"),)


class Rule(Base):
    __tablename__ = "rule"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(40), unique=True)
    title: Mapped[str] = mapped_column(String(200))


class RuleVersion(Base):
    __tablename__ = "rule_version"

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("rule.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    applicability_json: Mapped[dict] = mapped_column(JSON, default=dict)
    parameters_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="active")
    proposed_by: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")


class RuleApplication(Base):
    __tablename__ = "rule_application"

    id: Mapped[int] = mapped_column(primary_key=True)
    instrument_id: Mapped[int | None] = mapped_column(ForeignKey("instrument.id"), nullable=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("institution.id"), index=True)
    rule_version_id: Mapped[int] = mapped_column(ForeignKey("rule_version.id"))
    reason_text: Mapped[str] = mapped_column(Text)
    applied_on: Mapped[date] = mapped_column(Date)


class CoverageSnapshot(Base):
    __tablename__ = "coverage_snapshot"

    id: Mapped[int] = mapped_column(primary_key=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("institution.id"), index=True)
    as_of_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20))
    required_paise: Mapped[int] = mapped_column(Integer)
    valid_paise: Mapped[int] = mapped_column(Integer)
    gap_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    gap_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    gap_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence_pct: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Reminder(Base):
    __tablename__ = "reminder"

    id: Mapped[int] = mapped_column(primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instrument.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    due_on: Mapped[date] = mapped_column(Date)
    fired_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    paused: Mapped[bool] = mapped_column(Boolean, default=False)
    pause_reason: Mapped[str] = mapped_column(Text, default="")
    escalation_level: Mapped[int] = mapped_column(Integer, default=0)
    recipient_roles_json: Mapped[list] = mapped_column(JSON, default=list)


class Notification(Base):
    __tablename__ = "notification"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    message: Mapped[str] = mapped_column(Text)
    entity_type: Mapped[str] = mapped_column(String(30))
    entity_id: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ReleaseRequest(Base):
    __tablename__ = "release_request"

    id: Mapped[int] = mapped_column(primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instrument.id"), index=True)
    requested_by: Mapped[int] = mapped_column(ForeignKey("user.id"))
    requested_on: Mapped[date] = mapped_column(Date)
    reason: Mapped[str] = mapped_column(Text, default="")
    precheck_verdict: Mapped[str | None] = mapped_column(String(30), nullable=True)
    precheck_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="ready")
    needs_second_approval: Mapped[bool] = mapped_column(Boolean, default=False)


class Hold(Base):
    __tablename__ = "hold"

    id: Mapped[int] = mapped_column(primary_key=True)
    institution_id: Mapped[int | None] = mapped_column(ForeignKey("institution.id"), nullable=True)
    instrument_id: Mapped[int | None] = mapped_column(ForeignKey("instrument.id"), nullable=True)
    reason: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(80))
    placed_by: Mapped[int] = mapped_column(ForeignKey("user.id"))
    placed_on: Mapped[date] = mapped_column(Date)
    lifted_on: Mapped[date | None] = mapped_column(Date, nullable=True)


class Approval(Base):
    __tablename__ = "approval"

    id: Mapped[int] = mapped_column(primary_key=True)
    release_request_id: Mapped[int] = mapped_column(ForeignKey("release_request.id"), index=True)
    approver_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    level: Mapped[int] = mapped_column(Integer)
    decision: Mapped[str] = mapped_column(String(20))
    remarks: Mapped[str] = mapped_column(Text, default="")
    decided_at: Mapped[datetime] = mapped_column(DateTime)


class SignedOrder(Base):
    __tablename__ = "signed_order"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_no: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    release_request_id: Mapped[int] = mapped_column(ForeignKey("release_request.id"))
    payload_json: Mapped[dict] = mapped_column(JSON)
    signature_b64: Mapped[str] = mapped_column(Text)
    public_key_b64: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="valid")
    issued_on: Mapped[date] = mapped_column(Date)
    revoked_reason: Mapped[str] = mapped_column(Text, default="")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    seq: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    ts: Mapped[datetime] = mapped_column(DateTime)
    actor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actor_role: Mapped[str] = mapped_column(String(30))
    action: Mapped[str] = mapped_column(String(80))
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details_json: Mapped[dict] = mapped_column(JSON, default=dict)
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64))


class AppClock(Base):
    __tablename__ = "app_clock"

    id: Mapped[int] = mapped_column(primary_key=True)
    simulated_now: Mapped[datetime] = mapped_column(DateTime)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=True)


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(30))
    password_hash: Mapped[str] = mapped_column(String(255))
    bank_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    institution_id: Mapped[int | None] = mapped_column(ForeignKey("institution.id"), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


# --- Anchor store (separate SQLite file, own Base, own connection) ---


class AnchorBase(DeclarativeBase):
    pass


class AuditAnchor(AnchorBase):
    __tablename__ = "audit_anchor"

    id: Mapped[int] = mapped_column(primary_key=True)
    anchored_at: Mapped[datetime] = mapped_column(DateTime)
    seq_upto: Mapped[int] = mapped_column(Integer)
    head_hash: Mapped[str] = mapped_column(String(64))


class AnchorSideLog(AnchorBase):
    """Hidden-when-not-DEMO_MODE log of dev tamper/restore actions, kept in the anchor store."""

    __tablename__ = "anchor_side_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime)
    action: Mapped[str] = mapped_column(String(40))
    details_json: Mapped[dict] = mapped_column(JSON, default=dict)

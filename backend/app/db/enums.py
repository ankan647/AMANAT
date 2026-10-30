from enum import Enum


class Role(str, Enum):
    institution = "institution"
    scrutiny = "scrutiny"
    senior_approver = "senior_approver"
    competent_authority = "competent_authority"
    admin = "admin"
    auditor = "auditor"
    bank_officer = "bank_officer"


class InstitutionStatus(str, Enum):
    active = "active"
    closed = "closed"


class InstrumentStatus(str, Enum):
    lodged = "lodged"
    under_scrutiny = "under_scrutiny"
    active = "active"
    returned = "returned"
    rejected = "rejected"
    held = "held"
    renewed = "renewed"
    matured = "matured"
    released = "released"


VALID_INSTRUMENT_STATUSES = {
    InstrumentStatus.lodged,
    InstrumentStatus.under_scrutiny,
    InstrumentStatus.active,
}


class AssignmentRole(str, Enum):
    scrutiniser = "scrutiniser"
    approver1 = "approver1"
    approver2 = "approver2"


class FieldName(str, Enum):
    fdr_number = "fdr_number"
    bank = "bank"
    amount = "amount"
    issue_date = "issue_date"
    maturity = "maturity"
    beneficiary = "beneficiary"
    lien = "lien"


class FieldGrade(str, Enum):
    claimed = "claimed"
    document_checked = "document_checked"
    bank_confirmed = "bank_confirmed"


FIELD_GRADE_ORDER = {
    FieldGrade.claimed: 0,
    FieldGrade.document_checked: 1,
    FieldGrade.bank_confirmed: 2,
}


class DocumentKind(str, Enum):
    fdr_scan = "fdr_scan"
    affidavit = "affidavit"
    release_application = "release_application"
    closure_doc = "closure_doc"
    bank_letter = "bank_letter"


class ScanStatus(str, Enum):
    clean = "clean"
    skipped = "skipped"


class BankOutcome(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    details_differ = "details_differ"
    cannot_confirm = "cannot_confirm"


class FlagType(str, Enum):
    duplicate_fdr_number = "duplicate_fdr_number"
    duplicate_file_hash = "duplicate_file_hash"
    maturity_before_issue = "maturity_before_issue"
    term_too_short = "term_too_short"
    amount_below_required = "amount_below_required"
    beneficiary_missing = "beneficiary_missing"
    lien_missing = "lien_missing"
    ifsc_invalid = "ifsc_invalid"
    ifsc_bank_mismatch = "ifsc_bank_mismatch"
    pdf_metadata_suspicious = "pdf_metadata_suspicious"
    bank_mismatch = "bank_mismatch"


class FlagSeverity(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class FlagStatus(str, Enum):
    open = "open"
    cleared = "cleared"
    returned = "returned"
    referred = "referred"


class FlagOutcome(str, Enum):
    cleared = "cleared"
    return_for_correction = "return_for_correction"
    refer_for_investigation = "refer_for_investigation"


class RuleVersionStatus(str, Enum):
    draft = "draft"
    pending_approval = "pending_approval"
    active = "active"
    rejected = "rejected"
    superseded = "superseded"


class CoverageStatus(str, Enum):
    covered = "covered"
    expiring_soon = "expiring_soon"
    shortfall = "shortfall"
    not_covered = "not_covered"
    exempt = "exempt"


class MatrixKey(str, Enum):
    routine_monitoring = "routine_monitoring"
    verify_next = "verify_next"
    send_renewal_notice = "send_renewal_notice"
    urgent_both = "urgent_both"


class ReminderKind(str, Enum):
    t_90 = "t_90"
    t_60 = "t_60"
    t_30 = "t_30"
    t_7 = "t_7"
    overdue = "overdue"
    bank_overdue = "bank_overdue"


class ReleaseStatus(str, Enum):
    ready = "ready"
    approver1_done = "approver1_done"
    approved = "approved"
    rejected = "rejected"
    on_hold = "on_hold"
    blocked = "blocked"


class ReleaseVerdict(str, Enum):
    eligible = "eligible"
    eligible_with_conditions = "eligible_with_conditions"
    blocked = "blocked"


class OrderStatus(str, Enum):
    valid = "valid"
    revoked = "revoked"
    superseded = "superseded"

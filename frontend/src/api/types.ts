export type CoverageStatus = "covered" | "expiring_soon" | "shortfall" | "not_covered" | "exempt";
export type FieldGrade = "claimed" | "document_checked" | "bank_confirmed";
export type MatrixKey = "routine_monitoring" | "verify_next" | "send_renewal_notice" | "urgent_both";
export type FlagStatus = "open" | "cleared" | "returned" | "referred";
export type FlagSeverity = "high" | "medium" | "low";
export type ReleaseVerdict = "eligible" | "eligible_with_conditions" | "blocked";
export type OrderStatus = "valid" | "revoked" | "superseded";
export type BankOutcome = "pending" | "confirmed" | "details_differ" | "cannot_confirm";

export interface CoverageInfo {
  status: CoverageStatus;
  required_paise: number;
  valid_paise: number;
  gap_start: string | null;
  gap_end: string | null;
  gap_days: number | null;
  exempt_reason: string | null;
}

export interface NextAction {
  key: MatrixKey | null;
  label: string;
}

export interface InstitutionRow {
  id: number;
  code: string;
  name: string;
  state: string;
  category: string;
  coverage: CoverageInfo;
  confidence_pct: number | null;
  matrix_cell: MatrixKey | null;
  next_action: NextAction;
  next_maturity: string | null;
}

export interface InstitutionListResponse {
  data: InstitutionRow[];
  meta: { page: number; page_size: number; total: number };
}

export interface InstrumentSummary {
  id: number;
  fdr_number: string;
  bank_name: string;
  amount_paise: number;
  issue_date: string;
  maturity_date: string;
  status: string;
}

export interface RuleApplied {
  rule_version_id: number;
  rule_key: string | null;
  version: number;
  title: string | null;
  reason_text: string;
}

export interface InstitutionDetail {
  institution: {
    id: number;
    code: string;
    name: string;
    state: string;
    category: string;
    programme_type: string;
    is_government: boolean;
    approval_year: number;
    years_existing_elsewhere: number;
    deposit_request_date: string;
    closure_date: string | null;
    status: string;
    coverage: CoverageInfo;
    confidence_pct: number | null;
  };
  rule_applied: RuleApplied | null;
  instruments: InstrumentSummary[];
  open_flags: { id: number; type: string; title: string; severity: FlagSeverity }[];
  bank_requests: { id: number; request_code: string; outcome: BankOutcome; due_date: string }[];
  reminders: { id: number; kind: string; due_on: string; fired_on: string | null; paused: boolean }[];
  holds: { id: number; reason: string; source: string; placed_on: string }[];
}

export interface CoverageTimelinePoint {
  date: string;
  paise: number;
  instruments?: { id: number; fdr_number: string; paise: number }[];
}

export interface CoverageGap {
  start: string;
  end: string;
  days: number;
}

export interface CoverageTimeline {
  status: CoverageStatus;
  required: CoverageTimelinePoint[];
  valid: CoverageTimelinePoint[];
  gaps: CoverageGap[];
  today: string;
}

export interface WhyRuleStep {
  label: string;
  detail: string | null;
}

export interface WhyRule {
  steps: WhyRuleStep[];
  rule_version_id: number | null;
}

export interface InstrumentField {
  field_name: string;
  value: string;
  grade: FieldGrade;
  source: string;
  supported_by?: { type: string; id: number | string } | null;
}

export interface DocumentOut {
  id: number;
  kind: string;
  filename: string;
  sha256: string;
  ocr_text: string;
}

export interface InstrumentDetail {
  instrument: {
    id: number;
    institution_id: number;
    fdr_number: string;
    bank_name: string;
    branch: string;
    ifsc: string;
    amount_paise: number;
    issue_date: string;
    maturity_date: string;
    beneficiary: string;
    lien_text: string;
    status: string;
  };
  fields: InstrumentField[];
  confidence: { grade: FieldGrade; weakest_field: string | null };
  documents: DocumentOut[];
  assignments: { officer_id: number; role: string; assigned_at: string }[];
  linked_history: unknown[];
  flags: { id: number; type: string; title: string; status: FlagStatus; severity: FlagSeverity }[];
  bank_requests: { id: number; request_code: string; outcome: BankOutcome }[];
}

export interface QueueRow {
  instrument_id: number;
  institution_id: number;
  institution_name: string;
  priority_score: number;
  reason: string;
  coverage_status: string | null;
  confidence_pct: number | null;
  amount_paise: number;
}

export interface BankRequestOut {
  id: number;
  request_code: string;
  instrument_id: number;
  bank_name: string;
  branch: string;
  sent_date: string;
  due_date: string;
  response_date: string | null;
  outcome: BankOutcome;
  differing_values: Record<string, string>;
  remarks: string;
  escalation_level: number;
}

export interface AcceptPreview {
  request: BankRequestOut;
  upgraded_fields: { field_name: string; from_grade: FieldGrade; to_grade: FieldGrade }[];
  previous_confidence_pct: number | null;
}

export interface AcceptResult extends AcceptPreview {
  institution_confidence_pct: number | null;
}

export interface FlagOut {
  id: number;
  instrument_id: number;
  type: string;
  title: string;
  reasons: { code: string; text: string }[];
  evidence: Record<string, unknown>;
  severity: FlagSeverity;
  status: FlagStatus;
  reviewer_id: number | null;
  outcome_reason: string;
  created_at: string;
}

export interface FlagDetail {
  flag: FlagOut;
  reasons: { code: string; text: string }[];
  evidence: Record<string, unknown>;
  instrument: { id: number; fdr_number: string } | null;
  related_instruments: { id: number; fdr_number: string }[];
}

export interface AnomalyMetrics {
  overall: { precision: number; recall: number; officer_confirmed_share: number };
  by_type: {
    type: string;
    planted: number;
    detected: number;
    false_positives: number;
    precision: number;
    recall: number | null;
  }[];
}

export interface RuleVersionOut {
  id: number;
  rule_id: number;
  version: number;
  effective_from: string;
  effective_to: string | null;
  applicability: Record<string, unknown>;
  parameters: Record<string, unknown>;
  status: string;
  proposed_by: number | null;
  approved_by: number | null;
  note: string;
}

export interface RuleOut {
  id: number;
  key: string;
  title: string;
  versions: RuleVersionOut[];
}

export interface ImpactPreview {
  changes: {
    institution_id: number;
    name: string;
    before_status: string;
    after_status: string;
    before_required_paise: number;
    after_required_paise: number;
  }[];
  unchanged_count: number;
}

export interface ReminderOut {
  id: number;
  instrument_id: number;
  kind: string;
  due_on: string;
  fired_on: string | null;
  paused: boolean;
  pause_reason: string;
  escalation_level: number;
}

export interface NotificationOut {
  id: number;
  kind: string;
  message: string;
  entity_type: string;
  entity_id: number;
  created_at: string;
  read_at: string | null;
}

export interface ReleaseOut {
  id: number;
  instrument_id: number;
  requested_by: number;
  requested_on: string;
  reason: string;
  precheck_verdict: ReleaseVerdict | null;
  status: string;
  needs_second_approval: boolean;
}

export interface PrecheckCheck {
  key: string;
  label: string;
  passed: boolean;
  severity: "block" | "condition" | "info";
  detail: string;
}

export interface PrecheckResult {
  verdict: ReleaseVerdict;
  checks: PrecheckCheck[];
  penalties: { kind: string; percent: number; amount_paise: number }[];
  holds: { id: number; reason: string; source: string; placed_on: string }[];
  missing_documents: string[];
}

export interface ReleaseDetail {
  release: ReleaseOut;
  instrument: { id: number; fdr_number: string; amount_paise: number } | null;
  approvals: { approver_id: number; level: number; decision: string; remarks: string }[];
  precheck: PrecheckResult | Record<string, never>;
  order: { id: number; order_no: string; status: OrderStatus } | null;
  sod: { blocked_for_current_user: boolean; reason: string | null };
}

export interface HoldOut {
  id: number;
  institution_id: number | null;
  instrument_id: number | null;
  reason: string;
  source: string;
  placed_on: string;
  lifted_on: string | null;
}

export interface OrderOut {
  id: number;
  order_no: string;
  release_request_id: number;
  payload: Record<string, unknown>;
  signature_b64: string;
  status: OrderStatus;
  issued_on: string;
  revoked_reason: string;
}

export interface PublicOrder {
  order_no: string;
  institution_name: string;
  amount_paise: number;
  issued_on: string;
  issuing_authority: string;
  status: OrderStatus;
  signature_valid: boolean;
  signed_at: string;
}

export interface AuditEntry {
  seq: number;
  ts: string;
  actor_id: number | null;
  actor_role: string;
  action: string;
  entity_type: string;
  entity_id: number | null;
  details: Record<string, unknown>;
  hash: string;
  prev_hash: string;
}

export interface AuditVerifyResult {
  ok: boolean;
  entries_checked: number;
  first_broken_seq: number | null;
  anchors_checked: number;
  anchor_mismatches: { anchor_id: number; seq_upto: number; expected: string | null; found: string }[];
}

export interface AuditAnchorOut {
  id: number;
  anchored_at: string;
  seq_upto: number;
  head_hash: string;
}

export interface DashboardSummary {
  as_of: string;
  institutions_total: number;
  by_status: Record<CoverageStatus, number>;
  required_paise: number;
  valid_paise: number;
  bank_confirmed_paise: number;
  confirmed_pct: number;
  open_flags: number;
  overdue_bank_requests: number;
  maturities_next_90d: number;
  releases_pending: number;
}

export interface PriorityMatrixCell {
  key: MatrixKey;
  label: string;
  count: number;
  institution_ids: number[];
}

export interface PriorityMatrixOut {
  cells: PriorityMatrixCell[];
  threshold: number;
}

export interface ActivityEvent {
  id: number;
  ts: string;
  kind: string;
  message: string;
  institution_id: number | null;
  entity_type: string;
  entity_id: number | null;
}

export interface DemoScenario {
  key: string;
  title: string;
  story: string;
  institution_code: string;
  institution_id: number | null;
  deep_link: string;
  expected: string;
}

export interface KpiOut {
  confirmed_deposit_share_pct: number;
  avg_days_to_bank_confirmation: number;
  flags_confirmed_share_pct: number;
  maturities_handled_before_deadline_pct: number;
  avg_days_to_release_decision: number;
}

export interface ClockOut {
  simulated_now: string;
  is_simulated: boolean;
}

export interface ClockAdvanceEvent {
  kind: string;
  instrument_id: number;
  institution_id: number | null;
  message: string;
}

export interface ClockAdvanceResult {
  simulated_now: string;
  fired: { reminders: number; escalations: number; bank_overdue: number; anchors: number };
  events: ClockAdvanceEvent[];
}

export interface DemoAccount {
  email: string;
  name: string;
  role: string;
  description: string;
}

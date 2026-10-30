# AMANAT: BUILD SPECIFICATION (SIH 2026, PS 26265, AICTE Security Deposit / FDR Portal)

## 0. MISSION
Build a complete, runnable, demo-ready prototype called AMANAT that manages the lifecycle of security-deposit FDRs held by AICTE: lodge -> check -> bank-confirm -> track -> renew -> release.

Core thesis, shown on the home screen for EVERY institution, as two separate indicators:
1. **Coverage Health**: is enough valid deposit held, today and on every future date?
2. **Verification Confidence**: how much of that deposit has the bank actually confirmed?

Audience: AICTE officials judging a live demo. The app must look calm, modern and trustworthy in 5 seconds, and every screen must answer "what should I do next?". Simple structure (sidebar + top bar + cards), polished visuals, tasteful motion.

Non-negotiables:
- Deterministic, explainable logic only. No AI/ML in any decision path.
- Never write the word "fraud" in the UI. Use "Anomaly: needs review".
- Everything is synthetic. The bank side is a SIMULATED bank screen. The signing key is a DEMO key. Every page shows the badge: "Prototype - synthetic data - simulated bank - demo signing key".
- The full lifecycle must work end to end before polish. If time or context runs short, cut P1 items first, never a lifecycle step.
- P1 (optional): SSE live events, CSV exports, PDF reports, dark-mode polish.

Definition of done: every item in section 12 passes, and you have run the commands to prove it.

---

## 1. HOW TO WORK (operating rules for Claude Code)
1. **First, create `CLAUDE.md`** in the repo root containing: project one-liner, the command list (section 2.3), repo layout (section 4), the domain rules summary (section 5 headings), the hard rules (section 13), and "Always re-read AMANAT_SPEC.md section N before starting phase N". This survives context compaction.
2. **Create `PROGRESS.md`**: a phase checklist (section 10), a "Deviations" list, a "Known gaps" list. Update it at the end of every phase.
3. Use your todo list to track the 8 phases. Work phase by phase. At each phase end: run the gate commands, fix failures, update PROGRESS.md, then `git add -A && git commit -m "phase N: ..."`.
4. Do not ask the user anything. Never stop at a plan. Install what you need.
5. **Failure policy**: when a command fails, read the error, fix the root cause, retry. After 3 failed attempts on the same problem, apply the documented fallback (section 2.4), log it under Deviations, and move on. Never delete a test to make it pass.
6. Keep context lean: use grep/glob and read only the files you need; do not paste large generated files back into the conversation; never print the openapi.json or lockfiles.
7. Run servers in the background for smoke tests (`make dev &`), always kill them afterwards.
8. **Single source of truth for "now"**: all backend code gets the date from `app/core/clock.py` (`clock.now()`, `clock.today()`). `datetime.now()`, `date.today()` and `datetime.utcnow()` are forbidden outside that file. Add a test that greps the codebase for them.
9. Money: integer paise everywhere in backend and API (`*_paise`). Format only in the frontend with `formatINR()` using Indian grouping (1,25,00,000).
10. Visual QA: after the frontend screens exist, use Playwright to screenshot every key screen into `/qa-screens/` and LOOK at them (view the image files). Fix overlaps, low contrast, empty states, broken charts before finishing.

---

## 2. ENVIRONMENT

### 2.1 Prerequisites (check in `make doctor`)
Node >= 20, npm, Python 3.12 (fall back to 3.11 and log it), pip/venv (or uv if present). Docker and Tesseract are optional.

### 2.2 Environment variables (`.env.example`, with defaults in code)
```
DEMO_MODE=true
JWT_SECRET=change-me-demo-only
JWT_EXPIRE_MINUTES=480
DATABASE_URL=sqlite:///./data/amanat.db
ANCHOR_DB_PATH=./data/anchor_store.db
STORAGE_DIR=./data/files
SIGNING_KEY_PATH=./data/demo_ed25519.pem
SIM_START_DATE=2026-10-30
EXPIRING_WINDOW_DAYS=60
CONFIDENCE_HIGH_THRESHOLD=80
HIGH_VALUE_THRESHOLD_PAISE=500000000
CORS_ORIGINS=http://localhost:5173
```

### 2.3 Makefile targets
`doctor`, `install` (backend venv + pip, frontend npm), `seed`, `dev` (backend :8000 and frontend :5173 together), `backend`, `frontend`, `test` (pytest + vitest), `e2e` (Playwright), `contract` (regenerate openapi.json + TS types), `build`, `docker-up`, `lint`, `qa-screens`.

### 2.4 Fallbacks
- Tesseract missing: skip OCR; synthetic PDFs have a text layer read by PyMuPDF; scanned images use fixture `ocr_text`.
- Docker unavailable: still write Dockerfiles and compose; mark "untested" in README.
- shadcn CLI fails: copy component source by hand following shadcn's published source.
- Python 3.12 unavailable: use 3.11.
- Playwright browser download blocked: keep the e2e test, mark it unverified in PROGRESS.md.

---

## 3. STACK
**Backend**: Python 3.12, FastAPI, Uvicorn, SQLAlchemy 2.x, Alembic, Pydantic v2 + pydantic-settings, PyJWT, bcrypt, python-multipart, cryptography (Ed25519), qrcode[pil], reportlab, PyMuPDF, APScheduler, pytest, pytest-asyncio, httpx, ruff.
**Database**: SQLite for the demo with WAL mode; models stay Postgres-compatible (no SQLite-only types). Append-only enforced with triggers. README states "production: PostgreSQL with row-level security".
**Frontend**: React 18, TypeScript (strict), Vite, Tailwind CSS (follow the current shadcn Vite installation docs), **shadcn/ui as the primary component system**, Apache ECharts (echarts-for-react), React Router 6, TanStack Query, framer-motion, sonner, cmdk, lucide-react, react-hook-form + zod, date-fns, openapi-typescript + openapi-fetch, vitest + Testing Library, Playwright.
Pin versions in lockfiles.

---

## 4. REPO LAYOUT
```
/AMANAT_SPEC.md  /CLAUDE.md  /PROGRESS.md  /README.md  /Makefile  /docker-compose.yml  /.env.example
/docs/api-contract.md  /docs/openapi.json
/backend
  pyproject.toml  alembic.ini  Dockerfile
  /alembic/versions
  /app
    main.py  seed.py  /core (config.py clock.py security.py permissions.py errors.py audit.py audit_anchor.py signing.py calendar.py)
    /db (base.py models.py session.py triggers.py)
    /schemas (one module per domain, Pydantic models with examples)
    /services (rules_engine.py coverage.py confidence.py anomalies.py ingestion.py reminders.py escalation.py bank_channel.py release.py orders.py metrics.py dashboard.py)
    /routers (auth clock dashboard institutions instruments bank_requests flags rules reminders releases orders public audit metrics demo)
    /fixtures (synthetic pdf generator, ifsc_bank_codes.py, holidays.py)
  /tests (core, engines, api, scenarios, security, contract)
/frontend
  package.json  vite.config.ts  components.json  Dockerfile
  /src
    main.tsx  App.tsx  routes.tsx  /api (schema.d.ts client.ts hooks/*)  /lib (formatINR.ts dates.ts roles.ts utils.ts)
    /components/ui (shadcn)  /components/amanat (StatCard CoverageBadge GradeBadge ConfidenceBar MoneyText EmptyState PageHeader RoleGate SimulatedBadge ExplainDrawer PriorityMatrix ClockControl NotificationBell ActivityFeed CoverageTimelineChart)
    /layouts (AppShell PublicShell BankShell)
    /pages (Login Dashboard InstitutionDetail InstrumentDetail Queue BankPortal BankRequests Flags FlagDetail Rules Reminders Releases ReleaseDetail OrderDetail Verify Audit Metrics Demo)
  /e2e  /qa-screens
```

---

## 5. DOMAIN RULES (implement exactly)

### 5.1 Clock and calendar
- `app_clock` stores simulated now. Default `SIM_START_DATE`. Endpoints can advance, set, reset.
- Working days: Monday to Friday excluding the demo holiday list: 2026-12-25, 2027-01-26, 2027-03-04, 2027-08-15, 2027-10-02, 2027-12-25 (illustrative). Helpers: `add_working_days`, `prev_working_day`, `is_working_day`.

### 5.2 Valid instrument
An instrument counts toward coverage on date d when ALL are true: status in {lodged, under_scrutiny, active}; `issue_date <= d < maturity_date`; beneficiary text contains ("AICTE" or "All India Council for Technical Education") AND "Government of India" (case-insensitive). Unverified deposits still count on paper; that is exactly why Verification Confidence is separate. Instruments with status returned, rejected, held, matured, released, renewed (superseded) do not count.

### 5.3 Rules engine
- `rule` + `rule_version`. A version has `effective_from`, `effective_to` (nullable), `applicability_json` and `parameters_json`.
- Applicability keys (all optional, all must match): `approval_year_min/max`, `categories[]`, `programme_types[]`, `is_government` (bool), `years_existing_elsewhere_max`.
- Selection: for an institution, pick the active version whose effective window contains the institution's `deposit_request_date` (the date the obligation arose, NOT today) and whose applicability matches. Most specific match wins (more applicability keys), then latest effective_from. Persist a `rule_application` row (version, reason text e.g. "Deposit requested 2018-05-01; rule v1 (2010-2019) applies; category Technology"). Recompute applications when a rule version is activated.
- Seed rules (all labelled "Seed - pending AICTE legal validation", illustrative amounts):
  - `required_deposit` v1: effective 2010-01-01 to 2019-12-31. Technology 10,00,000; Management 5,00,000; Pharmacy 5,00,000; Architecture 5,00,000. `term_years`=10, `min_fdr_term_months`=12.
  - `required_deposit` v2: effective 2020-01-01 onward. Technology 15,00,000; Management 7,50,000; Pharmacy 7,50,000; Architecture 7,50,000. Same term and min FDR term.
  - `exemption` v1: exempt when `years_existing_elsewhere >= 10` (parameter `min_years=10`) or `is_government` is true? NO: only years-based, plus a separate government flag parameter that defaults to false. Document this in the rule text.
  - `proof_window` v1: 7 days from intimation; penalty 10% of deposit amount.
  - `release` v1: release allowed after term completion or documented closure.
- Required period for an institution: `[deposit_request_date, deposit_request_date + term_years)` or until `closure_date` if set. Required amount is constant in the period. Exempt institutions require 0.
- Impact preview: recompute coverage for every institution under a draft version and return before/after status and required amount without persisting.
- A rule version in `pending_approval` can be approved only by an admin who is not `proposed_by`.

### 5.4 Coverage Health (per institution, evaluated from simulated today to the end of the required period)
Compute `valid(d)` and `required(d)` for each date; compress into change-points (only dates where either value changes). Gaps are maximal date ranges where `valid(d) < required(d)`; each gap has `start`, `end` (inclusive), `days`.
Status precedence (first match wins):
1. `exempt`: exemption rule applies. Show reason.
2. `not_covered`: required > 0 and valid(today) == 0.
3. `shortfall`: valid(today) < required(today), OR a future gap exists whose start is MORE than `EXPIRING_WINDOW_DAYS` after today (a known future shortfall; report its range and days).
4. `expiring_soon`: coverage is met today and the first future gap starts within `EXPIRING_WINDOW_DAYS` of today.
5. `covered`: no gap in the remaining required period.
Return the first gap (or all gaps) with `gap_start`, `gap_end`, `gap_days`.

### 5.5 Verification Confidence
Fields per instrument: reference (FDR number), bank, amount, issue_date, maturity, beneficiary, lien. Grades: claimed < document_checked < bank_confirmed.
- On lodge every field is `claimed`.
- Ingestion upgrades a field to `document_checked` ONLY when the value is found in the document text (normalised: strip spaces/slashes for the reference, accept amount with or without commas/decimals, parse dates in dd/mm/yyyy, dd-mm-yyyy, yyyy-mm-dd, "15 Feb 2034"; beneficiary and lien by keyword match). Source recorded as `document:<doc_id>`.
- A field becomes `bank_confirmed` ONLY when an officer accepts a bank response whose outcome is `confirmed`, or whose `details_differ` values equal the claimed value for that field. Source `bank_request:<code>`.
- Instrument grade = weakest of its 7 fields. Institution `confidence_pct` = (sum of amounts of instruments valid today AND instrument-grade bank_confirmed) / (sum of amounts valid today) x 100, rounded to integer; 0 if no valid instrument; null if exempt.

### 5.6 Priority matrix and next action
Coverage axis: top row = `covered`; bottom row = `shortfall`, `expiring_soon`, `not_covered`. Confidence axis: high when `confidence_pct >= CONFIDENCE_HIGH_THRESHOLD`. Exempt institutions are excluded from the matrix (next action "No action: exempt").
- covered + high: key `routine_monitoring`, "Routine monitoring"
- covered + low: `verify_next`, "Verify next"
- shortfall/expiring + high: `send_renewal_notice`, "Send renewal notice"
- shortfall/expiring/not_covered + low: `urgent_both`, "Urgent: both problems"
- not_covered with high confidence cannot occur (confidence 0).

### 5.7 Anomaly checks (deterministic; each returns code + plain-language reason + evidence)
Run automatically on lodge and on bank response; also via portfolio scan. Types:
1. `duplicate_fdr_number`: same normalised FDR number under another institution (or another active instrument).
2. `duplicate_file_hash`: same document SHA-256 used under another institution.
3. `maturity_before_issue`.
4. `term_too_short`: (maturity - issue) < `min_fdr_term_months` from the applicable rule.
5. `amount_below_required`: amount < required amount AND no other valid instrument closes the gap.
6. `beneficiary_missing`: fails 5.2 beneficiary test.
7. `lien_missing`: lien text lacks "AICTE" or lacks ("lien" or "pledged").
8. `ifsc_invalid`: not matching `^[A-Z]{4}0[A-Z0-9]{6}$`.
9. `ifsc_bank_mismatch`: first four letters do not match the claimed bank (table: SBIN=State Bank of India, HDFC=HDFC Bank, ICIC=ICICI Bank, PUNB=Punjab National Bank, UBIN=Union Bank of India, CNRB=Canara Bank, BARB=Bank of Baroda, UTIB=Axis Bank, KKBK=Kotak Mahindra Bank, IDIB=Indian Bank).
10. `pdf_metadata_suspicious`: PDF CreationDate earlier than the claimed issue date, or Producer/Creator contains an editing tool name (Photoshop, GIMP, Canva, Illustrator, Paint).
11. `bank_mismatch`: bank response `details_differ` values differ from claimed values.
Flag severity: high for duplicates, bank_mismatch, beneficiary_missing; medium for date and amount logic; low for metadata. Never use the word "fraud". Flag title format: "Anomaly: needs review - <short reason>".
Outcomes (exactly one, reviewer required, reason required for cleared): `cleared`, `return_for_correction` (instrument status -> returned, notify institution), `refer_for_investigation` (appears in Vigilance referrals list; instrument status unchanged unless officer also holds).
Metrics (computed live over flags with `is_planted_label` data): precision = planted-detected / all flags raised on planted instruments; recall by type = detected / planted. Also officer-confirmed share = (returned + referred outcomes) / (flags with any outcome).

### 5.8 Bank verification
- `BankChannel` abstract interface: `send_request(req)`, `fetch_response(req)`. Implement `SimulatedBankScreenChannel` (the bank officer responds in the /bank UI). Add `ApiChannel` and `SfmsChannel` stubs raising NotImplementedError with docstrings explaining a real adapter would plug in here.
- Request code format `BR-<year>-<4 digit seq>`. Default due date = sent date + 7 working days.
- Bank officers see only requests where `bank_name` equals their `user.bank_name`.
- Outcomes: `confirmed`, `details_differ` (with `differing_values` map field -> bank's value), `cannot_confirm`. Optional letter upload.
- AICTE officer must `accept` (or `reject-response` with reason) before any field upgrade. Accept returns the list of upgraded fields and the new institution confidence.
- `details_differ` immediately creates a `bank_mismatch` flag (claimed vs bank value in evidence).
- Overdue: due date passed and still pending -> reminder at due+1 working day (`bank_overdue`, level 0), escalation level 1 (Senior Approver) at due+3 working days, level 2 (Competent Authority) at due+7 working days.

### 5.9 Reminders and escalation (driven by the simulated clock)
- When an instrument becomes active (or on seed), create reminders T-90, T-60, T-30, T-7 (calendar days before maturity, moved to the previous working day) and `overdue` (first working day after maturity if no renewal linked).
- `clock/advance` fires every reminder with `due_on <= new_now` and not yet fired, exactly once, in date order; skips paused reminders (they stay pending). Each firing creates notifications for the responsible officer and the institution user and an audit entry.
- Escalation for maturity without a linked renewal: T-30 reminder also notifies Senior Approver (level 1); T-7 and overdue notify Competent Authority (level 2).
- Linking a renewal instrument (`link-renewal`) marks the old one `renewed`, cancels its pending reminders and recomputes coverage.
- Pause requires a reason (e.g. "Waiting for institution").

### 5.10 Release workflow
- Request allowed when term completed (`today >= deposit_request_date + term_years`) or institution `closure_date` set with a closure document.
- Pre-check (computed on demand and stored on request) returns a verdict and checks:
  1. `term_or_closure`: passed/failed with date detail.
  2. `penalty`: if `proof_received_date - intimation_date > 7 days` then a 10% penalty (amount_paise) is due unless exempt; failed until recorded as settled.
  3. `documents`: required documents present (FDR scan, affidavit, release application) else list missing.
  4. `holds`: any open hold (instrument or institution) blocks.
  5. `verification`: warns when instrument grade is below bank_confirmed (condition, not block).
  Verdict: `blocked` if any of 1, 3 (if mandatory docs missing), 4 fail; `eligible_with_conditions` if penalty unsettled or verification warning; else `eligible`.
- Approval levels: Level 1 by `senior_approver` or `competent_authority`. If `amount_paise > HIGH_VALUE_THRESHOLD_PAISE` (default 50,00,000 rupees) a Level 2 approval is required by `competent_authority`, a different user from both the scrutiniser and the Level 1 approver.
- Separation of duties (enforce in service layer AND DB triggers):
  - The scrutiniser of the instrument (assignment history) can never approve its release (`scrutiniser_cannot_approve`).
  - Level 2 approver must differ from scrutiniser and Level 1 approver (`second_approver_must_differ`).
  - Admins cannot approve or edit case records (`admin_cannot_approve`).
  - Institution and bank users have no officer permissions.
  - An admin cannot approve a rule version they proposed.
  Violations -> HTTP 403, error code `SOD_VIOLATION`, `details.rule` set, and an audit entry `sod_violation_blocked`.
  DB trigger example (SQLite): BEFORE INSERT ON approval, abort with 'SOD_VIOLATION' when NEW.approver_id equals the scrutiniser of the related instrument.
- Final approval creates the signed order and sets the instrument `released`.
- Accrued interest goes to the Council: the order payload carries `interest_note: "Accrued interest is credited to the Council."` (no interest calculation).

### 5.11 Signed order and public verification
- Payload (canonical JSON: sorted keys, no whitespace, UTF-8): `{order_no, institution_name, institution_code, amount_paise, issued_on, issuing_authority:"AICTE (demo)", release_request_id, instrument_ref_masked, interest_note}`. `instrument_ref_masked` shows only the last 4 characters of the FDR number.
- Sign with Ed25519 (demo key created on first run at `SIGNING_KEY_PATH`). Store signature (base64) and public key. Order number `ORD-<year>-<4 digit seq>`.
- PDF order with QR code encoding `<FRONTEND_BASE>/verify/<order_no>`, plus an "ORDER SIGNED WITH DEMO KEY" footer.
- Public API verifies the stored payload against the signature on every request and returns `signature_valid`. Public responses contain: order_no, institution_name, amount_paise, issued_on, issuing_authority, status, signature_valid, signed_at. NOTHING else (no bank account, no remarks, no personal data, no officer names).
- `POST /public/orders/verify` accepts an arbitrary payload + signature so the tamper box can show "Signature invalid" after any edit.
- Revoke/supersede by Competent Authority with reason; status shown publicly.

### 5.12 Audit
- Every state-changing service call writes `audit_log` through one `audit.record()` function (actor, role, action, entity, details).
- Hash chain: `hash = sha256(prev_hash + canonical_json(entry_without_hash))`, genesis prev_hash = 64 zeros, `seq` strictly increasing with no gaps.
- SQLite triggers `BEFORE UPDATE` and `BEFORE DELETE` on `audit_log` and on `audit_anchor` call `RAISE(ABORT,'AUDIT_APPEND_ONLY')`.
- Anchoring: `anchor_now()` inserts `(seq_upto, head_hash, anchored_at)` into a SEPARATE SQLite file (`ANCHOR_DB_PATH`) through its own connection; the main app has no update/delete path to it. APScheduler anchors daily on the simulated clock (advancing the clock across a day boundary anchors automatically) plus a manual endpoint.
- `verify`: recompute the whole chain; compare head hash at each anchor's `seq_upto` with the anchor; return ok, first broken seq, mismatches.
- DEMO_MODE only: `POST /audit/dev/tamper` edits one row's details with the trigger temporarily dropped; `POST /audit/dev/restore` reinstalls the trigger and restores the original row. Both are audit-logged to the anchor store's side log, hidden when DEMO_MODE=false.

### 5.13 Permission matrix (enforce in `require_roles` and per-object checks)
| Action | institution | scrutiny | senior_approver | competent_authority | admin | auditor | bank_officer |
|---|---|---|---|---|---|---|---|
| Lodge FDR (own institution only) | yes | yes | no | no | no | no | no |
| Create bank request | no | yes | yes | yes | no | no | no |
| Respond to bank request (own bank only) | no | no | no | no | no | no | yes |
| Accept/reject bank response | no | yes | yes | yes | no | no | no |
| Flag outcome | no | yes | yes | yes | no | no | no |
| Rule draft / approve | no | no | no | no | yes (approver != proposer) | no | no |
| Approve release | no | no | yes | yes | no | no | no |
| Revoke order / place hold | no | no | no | yes | no | no | no |
| Read audit / verify | no | no | no | read | no | yes | no |
| Advance clock | no | yes | yes | yes | yes | no | no |
Institution users see only their own institution's data. Everyone else sees all institutions.

---

## 6. DATA MODEL (SQLAlchemy models + one Alembic migration)
institution(id, code UNIQUE, name, state, category, programme_type, is_government, approval_year, years_existing_elsewhere, deposit_request_date, closure_date NULL, status)
instrument(id, institution_id, fdr_number, fdr_number_norm, bank_name, branch, ifsc, amount_paise, issue_date, maturity_date, beneficiary, lien_text, intimation_date NULL, proof_received_date NULL, penalty_settled BOOL, status[lodged|under_scrutiny|active|returned|rejected|held|renewed|matured|released], linked_from_instrument_id NULL, created_at)
instrument_assignment(id, instrument_id, officer_id, role[scrutiniser|approver1|approver2], assigned_at)   -- assignment history
instrument_field(id, instrument_id, field_name, value, grade, source, updated_at)
document(id, instrument_id, kind[fdr_scan|affidavit|release_application|closure_doc|bank_letter], filename, sha256, mime, size, ocr_text, pdf_metadata_json, scan_status[clean|skipped], storage_path)
bank_request(id, request_code UNIQUE, instrument_id, bank_name, branch, sent_date, due_date, response_date, method, aicte_officer_id, bank_responder_id, outcome, differing_values_json, remarks, letter_doc_id, accepted_by_id, accepted_at, rejected_reason, reminders_sent, escalation_level)
anomaly_flag(id, instrument_id, type, title, reasons_json, evidence_json, severity, status[open|cleared|returned|referred], reviewer_id, outcome_reason, created_at, decided_at, is_planted_label BOOL)
rule(id, key, title); rule_version(id, rule_id, version, effective_from, effective_to, applicability_json, parameters_json, status, proposed_by, approved_by, note)
rule_application(id, instrument_id NULL, institution_id, rule_version_id, reason_text, applied_on)
coverage_snapshot(id, institution_id, as_of_date, status, required_paise, valid_paise, gap_start, gap_end, gap_days, confidence_pct)
reminder(id, instrument_id, kind, due_on, fired_on, paused, pause_reason, escalation_level, recipient_roles_json)
notification(id, user_id, kind, message, entity_type, entity_id, created_at, read_at)
release_request(id, instrument_id, requested_by, requested_on, reason, precheck_verdict, precheck_json, status[ready|approver1_done|approved|rejected|on_hold|blocked], needs_second_approval BOOL)
hold(id, institution_id NULL, instrument_id NULL, reason, source, placed_by, placed_on, lifted_on NULL)
approval(id, release_request_id, approver_id, level, decision, remarks, decided_at)
signed_order(id, order_no UNIQUE, release_request_id, payload_json, signature_b64, public_key_b64, status, issued_on, revoked_reason)
audit_log(id, seq UNIQUE, ts, actor_id, actor_role, action, entity_type, entity_id, details_json, prev_hash, hash)
audit_anchor(id, anchored_at, seq_upto, head_hash)   -- in anchor_store.db
app_clock(id, simulated_now, is_simulated)
user(id, email UNIQUE, name, role, password_hash, bank_name NULL, institution_id NULL, active)

---

## 7. SEED DATA (deterministic; `random.Random(2026)`; idempotent reset)
Users: as section 4 of the earlier plan: all passwords `Demo@123`:
scrutiny1@aicte.demo (Asha Verma), scrutiny2@aicte.demo (Rohit Nair), approver1@aicte.demo (Meera Iyer, Senior Approver), authority@aicte.demo (Dr. K. Rao, Competent Authority), admin1@aicte.demo, admin2@aicte.demo, auditor@aicte.demo, bank.sbi@bank.demo (bank_name "State Bank of India"), bank.hdfc@bank.demo (bank_name "HDFC Bank"), and `inst.<code lowercase>@inst.demo` for every institution.
24 FICTIONAL institutions across ~10 states (names clearly invented, codes `DEMO-<STATE>-NNN`); scenario institutions below get codes `DEMO-A`, `DEMO-B`, etc. for easy lookup (and sensible fictional names). Filler institutions (about 12) get a random but valid mix of statuses; every filler FDR must pass all anomaly checks except the planted ones.
Synthetic PDFs: generate with reportlab (text layer containing FDR number, bank, branch, IFSC, amount, issue, maturity, beneficiary, lien lines), plus an affidavit PDF. Planted PDFs get suspicious metadata where required.

### 7.1 Scenario fixtures (today = 2026-10-30; tests assert these exactly)
| Key | Institution | Setup | Expected result |
|---|---|---|---|
| A Shortfall ahead | DEMO-A, Technology, deposit_request_date 2017-02-23 (rule v1, required 10,00,000, period ends 2027-02-23) | One FDR 10,00,000, issue 2017-03-10, maturity 2027-01-13, SBI, some fields document_checked | status `shortfall`, gap 2027-01-13 to 2027-02-22 inclusive, `gap_days`=41, confidence 0 or low, matrix cell `urgent_both` or `send_renewal_notice` per confidence |
| B Covered but unverified | DEMO-B, Technology, request 2023-04-01 (v2, 15,00,000) | One FDR 15,00,000, issue 2023-04-10, maturity 2033-04-10; fields claimed/document_checked only | `covered`, confidence 0, cell `verify_next` |
| C Duplicate | DEMO-C1 and DEMO-C2 | Same FDR number `SBI/FDR/2024/778812` lodged under both (C2 lodged later) | both get `duplicate_fdr_number` flag, high severity, evidence names both institutions |
| D Bank differs | DEMO-D, request 2024-02-15 (v2) | Pending request `BR-2026-0001` to State Bank of India; claimed maturity 2034-02-15 | When SBI officer responds `details_differ` with maturity 2034-03-15, a `bank_mismatch` flag is created and the request awaits acceptance |
| E Different rules | DEMO-E1 request 2018-05-01 vs DEMO-E2 request 2022-05-01, both Technology | Each has an FDR equal to its requirement | E1 required 10,00,000 (v1), E2 required 15,00,000 (v2), each with reason text |
| F Release on hold | DEMO-F, request 2015-06-01 (term complete 2025-06-01) | Active FDR 10,00,000 bank_confirmed; open hold "Inquiry ref VIG/2026/114" | release pre-check verdict `blocked`, hold listed |
| G Signed orders | DEMO-G1 and DEMO-G2 | Released FDRs; `ORD-2026-0001` valid, `ORD-2026-0002` revoked | public page shows valid and revoked, signature_valid true |
| H Healthy | DEMO-H, request 2023-09-01 (v2) | FDR 15,00,000 with all 7 fields bank_confirmed | `covered`, confidence 100, `routine_monitoring` |
| I Exempt | DEMO-I, years_existing_elsewhere 14 | no deposit required | `exempt`, reason shown |
| J Not covered | DEMO-J, request 2024-08-01 | no instruments | `not_covered`, confidence 0 |
| K Expiring soon | DEMO-K, Technology, request 2017-01-20 (v1, period ends 2027-01-20) | One FDR 10,00,000 maturing 2026-11-24, issue 2017-02-01 | `expiring_soon`, gap 2026-11-24 to 2027-01-19, gap_days 57 |
| R1 Release (single approver) | DEMO-R1 | term complete, FDR 40,00,000 bank_confirmed, scrutinised by scrutiny1, all docs present | `eligible`; approver1 approves, order created |
| R2 Release (two approvers) | DEMO-R2 | FDR 60,00,000 (above threshold), scrutinised by scrutiny1 | needs approver1 then authority |
| R3 SOD demo | DEMO-R3 | FDR 30,00,000, scrutiniser = **approver1** | approver1 gets 403 `SOD_VIOLATION`; authority can approve |
Also seed: a few pre-decided flags for the Vigilance list, ~25 notifications, reminders for every active FDR, 3 overdue-ready bank requests (due dates within 10 days of today so advancing the clock demonstrates escalation).
### 7.2 Planted anomalies
Plant exactly 2 instances of each of these 10 types: duplicate_fdr_number (C counts as one pair), duplicate_file_hash, maturity_before_issue, term_too_short, beneficiary_missing, lien_missing, ifsc_invalid, ifsc_bank_mismatch, pdf_metadata_suspicious, amount_below_required. Mark those instruments' flags with `is_planted_label=true` (stored on a `planted_labels` table keyed by instrument + type so recall can be computed even if detection fails). Add about 20 clean control instruments. Assert recall >= 0.9 per type overall.

---

## 8. API CONTRACT (build exactly this; contract-first)
Write `/docs/api-contract.md` and generate `/docs/openapi.json` from the Pydantic schemas BEFORE implementing routers; then run `openapi-typescript` to produce `frontend/src/api/schema.d.ts`; create ONE typed client `frontend/src/api/client.ts` (openapi-fetch) and TanStack Query hooks in `frontend/src/api/hooks`. The frontend must never call fetch/axios directly and must never use `any` for API data. `make contract` regenerates both; a test fails if the committed openapi.json is stale.

### 8.1 Conventions
- Base path `/api/v1`. JSON (multipart for uploads). Dates `YYYY-MM-DD`; timestamps UTC ISO-8601 with `Z`. Money in integer `*_paise`. Integer ids; human codes as strings.
- Auth: `Authorization: Bearer <jwt>`; claims `sub`, `role`, `exp`, `bank_name?`, `institution_id?`.
- Every response carries `X-Request-Id` (echo or generated) and `X-Simulated-Now`.
- Single: `{ "data": {...} }`. List: `{ "data": [...], "meta": { "page": 1, "page_size": 25, "total": 137 } }`. List params: `page`, `page_size` (max 100), `sort` (`field` or `-field`), `q`, plus endpoint filters.
- Error envelope for every non-2xx:
```json
{ "error": { "code": "SOD_VIOLATION", "message": "You scrutinised this FDR, so you cannot approve its release.", "details": { "rule": "scrutiniser_cannot_approve" }, "request_id": "01HZ..." } }
```
Codes: UNAUTHENTICATED 401, FORBIDDEN 403, SOD_VIOLATION 403, NOT_FOUND 404, VALIDATION_ERROR 422 (`details.fields[{path,message}]`), CONFLICT 409, INVALID_STATE 409, RATE_LIMITED 429, INTERNAL 500.
- Optional `Idempotency-Key` header on state-changing POSTs.
- Shared enums defined once: Role, CoverageStatus [covered|expiring_soon|shortfall|not_covered|exempt], FieldGrade [claimed|document_checked|bank_confirmed], FieldName, InstrumentStatus, BankOutcome [pending|confirmed|details_differ|cannot_confirm], FlagStatus [open|cleared|returned|referred], FlagOutcome [cleared|return_for_correction|refer_for_investigation], FlagType (11 types in 5.7), ReleaseVerdict [eligible|eligible_with_conditions|blocked], ReleaseStatus, OrderStatus [valid|revoked|superseded], ReminderKind, MatrixKey [routine_monitoring|verify_next|send_renewal_notice|urgent_both].

### 8.2 Endpoints
`R:` lists permitted roles (any = any authenticated; public = no auth).

**System**
- `GET /health` public -> `{status:"ok", simulated_now, demo_mode}`
- `GET /demo/scenarios` any -> `[{key,title,story,institution_id,institution_code,deep_link,expected}]`
- `POST /demo/reset` R: admin, DEMO_MODE only -> reseeds DB and resets clock

**Auth**
- `POST /auth/login` public `{email,password}` -> `{data:{access_token,token_type:"bearer",expires_in,user:User}}`
- `GET /auth/me` any -> `{data:User}` where `User={id,name,email,role,bank_name,institution_id}`
- `GET /auth/demo-accounts` public, DEMO_MODE -> `[{email,name,role,description}]`
- `GET /officers` R: approver, authority, admin -> users who can be assigned

**Clock**
- `GET /clock` any -> `{data:{simulated_now,is_simulated}}`
- `POST /clock/advance` R: scrutiny, approver, authority, admin; body `{days:int(1..400)}` -> `{data:{simulated_now, fired:{reminders,escalations,bank_overdue,anchors}, events:[{kind,instrument_id,institution_id,institution_name,message}]}}`
- `POST /clock/set` `{date}`; `POST /clock/reset` same roles

**Dashboard**
- `GET /dashboard/summary` -> `{data:{as_of, institutions_total, by_status:{covered,expiring_soon,shortfall,not_covered,exempt}, required_paise, valid_paise, bank_confirmed_paise, confirmed_pct, open_flags, overdue_bank_requests, maturities_next_90d, releases_pending}}`
- `GET /dashboard/priority-matrix` -> `{data:{cells:[{key:MatrixKey,label,count,institution_ids:[int]}], threshold}}`
- `GET /dashboard/activity?limit=20` -> `[{id,ts,kind,message,institution_id,entity_type,entity_id}]`

**Institutions**
- `GET /institutions` filters `status`, `state`, `category`, `matrix_cell`, `confidence_lt`, `q` -> rows:
```json
{ "id": 7, "code": "DEMO-A", "name": "Nilgiri College of Engineering", "state": "Tamil Nadu", "category": "Technology",
  "coverage": { "status": "shortfall", "required_paise": 100000000, "valid_paise": 100000000, "gap_start": "2027-01-13", "gap_end": "2027-02-22", "gap_days": 41, "exempt_reason": null },
  "confidence_pct": 0, "matrix_cell": "urgent_both", "next_action": { "key": "urgent_both", "label": "Urgent: both problems" }, "next_maturity": "2027-01-13" }
```
- `GET /institutions/{id}` -> detail: institution, `rule_applied:{rule_version_id,rule_key,version,title,reason_text}`, instruments[], open_flags[], bank_requests[], reminders[], holds[]
- `GET /institutions/{id}/coverage-timeline?from&to` -> `{data:{status, required:[{date,paise}], valid:[{date,paise,instruments:[{id,fdr_number,paise}]}], gaps:[{start,end,days}], today}}` (step series; each point is a change date)
- `GET /institutions/{id}/why-rule` -> `{data:{steps:[{label,detail}], rule_version_id}}` plain-English explanation

**Instruments**
- `POST /instruments` R: institution (own), scrutiny; multipart: JSON part `fdr` (`institution_id,fdr_number,bank_name,branch,ifsc,amount_paise,issue_date,maturity_date,beneficiary,lien_text,intimation_date?`) + `documents[]` (+ `kinds[]`) -> `{data:{instrument, fields[], flags_raised[]}}` (runs ingestion + anomaly checks synchronously, assigns scrutiniser round-robin)
- `GET /instruments/{id}` -> `{data:{instrument, fields:[{field_name,value,grade,source,supported_by:{type,id}|null}], confidence:{grade,weakest_field}, documents[], assignments[], linked_history[], flags[], bank_requests[]}}`
- `GET /instruments/{id}/documents/{doc_id}/download`
- `POST /instruments/{id}/assign` R: approver, authority `{officer_id}`
- `POST /instruments/{id}/link-renewal` `{previous_instrument_id}`
- `GET /verification-queue` -> `[{instrument_id,institution_id,institution_name,priority_score,reason,coverage_status,confidence_pct,amount_paise}]` sorted by `priority_score` desc

**Bank requests**
- `POST /bank-requests` R: scrutiny, approver, authority `{instrument_id,bank_name,branch,due_date?,method:"bank_screen"}` -> request
- `GET /bank-requests` filters `status`, `overdue`, `institution_id`; bank role auto-filtered to own bank
- `GET /bank-requests/{id}`
- `POST /bank-requests/{id}/respond` R: bank_officer; JSON `{outcome, differing_values?:{field:value}, remarks?}` or multipart with `letter` -> `{data:{request, flag_raised|null}}`
- `POST /bank-requests/{id}/accept` -> `{data:{request, upgraded_fields:[{field_name,from_grade,to_grade}], institution_confidence_pct, previous_confidence_pct}}`
- `POST /bank-requests/{id}/reject-response` `{reason}`
- `GET /bank-requests/{id}/accept-preview` -> same shape as accept without persisting (used by the UI "3 fields will become Bank-confirmed; confidence 0% to 62%")

**Anomaly flags**
- `GET /flags` filters `status`, `type`, `institution_id`, `severity`
- `GET /flags/{id}` -> `{data:{flag, reasons:[{code,text}], evidence, instrument, related_instruments[]}}`
- `POST /flags/{id}/outcome` `{outcome, reason?}` (reason required for cleared)
- `POST /flags/scan` R: scrutiny, approver, admin -> `{data:{scanned,new_flags}}`
- `GET /flags/referrals` -> Vigilance referrals list
- `GET /metrics/anomalies` -> `{data:{overall:{precision,recall,officer_confirmed_share}, by_type:[{type,planted,detected,false_positives,precision,recall}]}}`

**Rules**
- `GET /rules` -> rules with versions
- `POST /rules/{rule_id}/versions` R: admin `{effective_from,effective_to?,applicability,parameters,note}` -> draft
- `POST /rule-versions/{id}/impact-preview` -> `{data:{changes:[{institution_id,name,before_status,after_status,before_required_paise,after_required_paise}], unchanged_count}}`
- `POST /rule-versions/{id}/submit`; `POST /rule-versions/{id}/approve` (403 SOD_VIOLATION if approver == proposer); `POST /rule-versions/{id}/reject {reason}`

**Reminders and notifications**
- `GET /reminders` filters `state[sent|pending|paused]`, `instrument_id`
- `POST /reminders/{id}/pause {reason}`; `POST /reminders/{id}/resume`
- `GET /notifications` (current user); `POST /notifications/{id}/read`; `POST /notifications/read-all`

**Releases and holds**
- `POST /releases` R: institution, scrutiny `{instrument_id, reason}`
- `GET /releases` filters `status`; `GET /releases/{id}` -> release, instrument, approvals[], precheck, order|null, `sod:{blocked_for_current_user,reason}`
- `GET /releases/{id}/precheck` -> `{data:{verdict, checks:[{key,label,passed,severity:"block"|"condition"|"info",detail}], penalties:[{kind,percent,amount_paise}], holds:[{id,reason,source,placed_on}], missing_documents:[kind]}}`
- `POST /releases/{id}/approve` R: approver, authority `{remarks}` -> `{data:{release, next_required_level: 2|null, order|null}}`; 403 `SOD_VIOLATION` with `details.rule` in [scrutiniser_cannot_approve, second_approver_must_differ, admin_cannot_approve]
- `POST /releases/{id}/reject {reason}`
- `POST /holds` R: authority `{institution_id?|instrument_id?, reason, source}`; `POST /holds/{id}/lift`; `GET /holds`

**Orders**
- `GET /orders/{id}`; `GET /orders/{id}/pdf` (application/pdf with QR)
- `POST /orders/{id}/revoke` R: authority `{reason}`; `POST /orders/{id}/supersede`
- **Public (no auth, rate-limited)**: `GET /public/orders/{order_no}` -> `{data:{order_no,institution_name,amount_paise,issued_on,issuing_authority,status,signature_valid,signed_at}}`; `GET /public/signing-key` -> `{data:{algorithm:"Ed25519",public_key_b64,demo_key:true}}`; `POST /public/orders/verify {payload, signature_b64}` -> `{data:{signature_valid}}`

**Audit**
- `GET /audit` R: auditor, authority; filters `entity_type`, `actor_id`, `from`, `to`
- `POST /audit/verify` R: auditor -> `{data:{ok,entries_checked,first_broken_seq,anchors_checked,anchor_mismatches:[{anchor_id,seq_upto,expected,found}]}}`
- `POST /audit/anchor` R: auditor; `GET /audit/anchors`
- `POST /audit/dev/tamper`, `POST /audit/dev/restore` (DEMO_MODE only, R: auditor/admin)

**Metrics**
- `GET /metrics/kpis` -> `{data:{confirmed_deposit_share_pct, avg_days_to_bank_confirmation, flags_confirmed_share_pct, maturities_handled_before_deadline_pct, avg_days_to_release_decision}}`
- P1: `GET /reports/coverage.csv`, `GET /reports/anomalies.csv`

---

## 9. FRONTEND SPEC

### 9.1 Look and feel
"Calm government-tech": light by default (dark mode supported), generous whitespace, `rounded-xl` cards, soft shadows, subtle gradients, a single indigo-to-teal accent family. One hero visual per page. Never overload.

### 9.2 Tokens (configure in the theme format shadcn's init generates; map these values)
- Brand gradient: `linear-gradient(135deg, #1e1b4b 0%, #3730a3 45%, #0d9488 100%)` (Tailwind `bg-gradient-to-br from-indigo-950 via-indigo-700 to-teal-600`). Used on: login hero, dashboard hero banner, sidebar header, primary button hover glow.
- Page background: light `bg-gradient-to-b from-slate-50 via-white to-indigo-50/40`; dark `from-slate-950 via-slate-900 to-indigo-950/40`.
- Card accent: 1px gradient border (`from-indigo-500/30 via-teal-500/30 to-transparent`) on hero and matrix cards only.
- Status styles (always colour + icon + text, never colour alone):
  covered emerald-600 CheckCircle2; expiring_soon amber-500 Clock; shortfall rose-600 AlertTriangle; not_covered slate-700 XCircle; exempt sky-600 ShieldCheck.
  Grades: claimed slate-400 CircleDashed; document_checked amber-500 FileCheck; bank_confirmed emerald-600 BadgeCheck.
- Matrix tiles: routine_monitoring emerald gradient; verify_next amber/yellow gradient; send_renewal_notice orange gradient; urgent_both rose-to-red gradient.
- Confidence bar: fill gradient rose-500 -> amber-400 -> emerald-500, animated width.
- Charts: requirement = stepped indigo-600 line; valid = stacked areas in teal/cyan/violet shades; gap = rose-500/20 area with dashed rose border and a label "41-day gap".
- Typography: Inter, `tabular-nums` for money and dates, headings `font-semibold tracking-tight`.
- Bank portal theme: distinct blue-grey palette with a persistent amber banner "SIMULATED BANK SCREEN".
- Public verify page: clean white/gradient branded page with a large animated seal (green VALID, red REVOKED, grey SUPERSEDED).

### 9.3 shadcn/ui components (install via CLI and use everywhere; do not hand-roll equivalents)
button, card, badge, table, tabs, dialog, sheet, drawer, dropdown-menu, command, popover, tooltip, select, input, textarea, form, label, checkbox, switch, radio-group, calendar, progress, skeleton, separator, scroll-area, accordion, alert, alert-dialog, avatar, breadcrumb, hover-card, pagination, sonner, toggle-group, sidebar, chart helpers.
Build composites from them: StatCard, CoverageBadge, GradeBadge, ConfidenceBar, MoneyText, EmptyState, PageHeader, RoleGate, SimulatedBadge, ExplainDrawer ("Why this?"), PriorityMatrix, ClockControl, NotificationBell, ActivityFeed, CoverageTimelineChart.

### 9.4 Dynamic behaviour (all required, tasteful, respect `prefers-reduced-motion`)
- framer-motion: page fade/slide (150-250 ms), staggered card entrance, layout animation on filter/sort, count-up KPI numbers, animated confidence-bar fill, one-time pulse when a status chip changes.
- Skeletons for every fetch; loading, empty and error states for every list; optimistic updates for flag outcomes and accepts; sonner toasts (with undo where safe).
- **Clock control** (header popover: +1 day, +7, +30, set date, reset): animates the date, calls the API, shows a toast "3 reminders fired, 1 escalation", bounces the bell badge, briefly highlights affected rows, refetches dashboard data. Show events in a sheet.
- Command palette (Cmd/Ctrl+K): search institutions, FDR numbers, request codes, order numbers; actions like "Advance clock +30 days", "Go to Verification Queue".
- Activity feed polls every 10 s (P1: SSE).
- ECharts timeline with a draggable "as of" marker and tooltip listing contributing instruments; every chart has a "View as table" toggle.
- Role-aware UI via `RoleGate`: forbidden actions render disabled with a tooltip explaining the rule (e.g. "You scrutinised this FDR, so you cannot approve it"); the server still enforces.
- Demo helpers (DEMO_MODE): header role switcher that logs in as another demo account in one click.

### 9.5 Layout
Sidebar (gradient header with logo "Amanat" and tagline "Every deposit covered, every claim checked, every date watched"), items filtered by role: Dashboard, Verification Queue, Anomalies, Bank Requests, Reminders, Releases, Rules, Audit, Metrics, Demo Scenarios. Collapsible. Top bar: breadcrumb, command trigger, ClockControl, NotificationBell, user menu, theme toggle. Footer badge on every page. Role home routes: institution -> own institution page; bank_officer -> /bank; auditor -> /audit; others -> /.

### 9.6 Screens
1. **/login**: split gradient screen, pitch left, demo-account cards right (role, name, one-click).
2. **/ Dashboard**: gradient hero explaining the two indicators; 4-6 animated StatCards; clickable **Priority Matrix** (2x2 gradient tiles, count + label, filter the table); institutions table (CoverageBadge + ConfidenceBar side by side, next-action chip, search, filters, sort, pagination); ActivityFeed; "Demo scenarios" strip.
3. **/institutions/:id**: header (name, CoverageBadge, rule badge with "Why this rule?" opening ExplainDrawer); tabs Overview (timeline chart with gap shading, KPIs), Instruments, Evidence (field grades), Bank requests, Flags, Reminders, History.
4. **/instruments/:id**: 7-field grade table (GradeBadge + source + supporting document/request), documents with SHA-256 and text snippet, linked renewal stepper, assignment history, actions (Request bank confirmation, Raise release, Link renewal).
5. **/queue**: priority-ordered verification queue with reason chips, "Send bank request" dialog.
6. **/bank**: SIMULATED BANK SCREEN (BankShell layout): bank's requests only; large Confirm / Details differ / Cannot confirm cards; details-differ form with per-field values; optional letter upload; success animation.
7. **/bank-requests**: table with status timeline (sent -> due -> responded -> accepted), accept/reject drawer showing the accept-preview.
8. **/flags** and **/flags/:id**: claimed-vs-found evidence side by side, three outcome buttons, Vigilance referrals tab. Wording "Anomaly: needs review".
9. **/rules**: version timeline, applicability chips, draft editor (react-hook-form + zod), impact-preview table (before -> after status arrows), approval with self-approval disabled and explained.
10. **/reminders**: calendar + list, pause/resume, escalation chips.
11. **/releases**, **/releases/:id**: pre-check checklist (pass/fail rows by severity), penalties and holds, approval stepper (Scrutiny -> Approver 1 -> Approver 2), separation-of-duties banner, approve/reject, generated order card with QR and PDF download.
12. **/verify/:orderNo** (PUBLIC, PublicShell): branded page, animated seal, signature result, minimal fields only, "Verify another order", tamper-test box (paste payload/signature).
13. **/audit**: chain visualisation (blocks with short hashes), anchors list, "Verify now" with animated progress and result, DEMO_MODE tamper/restore buttons.
14. **/metrics**: anomaly precision/recall by type (bar chart), five pilot KPIs.
15. **/demo**: scenario cards A-K and R1-R3 with the story, expected outcome and an "Open" button; "Reset demo data" button (DEMO_MODE).

### 9.7 Frontend quality rules
Strict TypeScript, no `any` for API data; data via generated client and query hooks; forms via react-hook-form + zod; API error envelope mapped to toasts and inline field errors; keyboard accessible with visible focus rings; WCAG AA contrast; aria labels and data-table fallback on charts; `formatINR` and date helpers shared; no inline styles for colours (use tokens).

---

## 10. PHASES (follow in order; each ends with its gate, a PROGRESS.md update and a git commit)

**Phase 0: Bootstrap.** Repo skeleton, CLAUDE.md, PROGRESS.md, `.env.example`, Makefile, backend venv, frontend scaffold, `make doctor`.
Gate: `make doctor` passes; `git log` shows the first commit.

**Phase 1: Backend core.** Settings, clock + calendar, DB models + Alembic migration, SQLite WAL, append-only triggers, auth (JWT, bcrypt), permission layer with the matrix in 5.13, error envelope, request-id middleware, audit logger with hash chain and anchor store.
Gate: `pytest tests/core` (clock, triggers block UPDATE/DELETE, chain verifies, auth works, no forbidden `datetime.now` usage).

**Phase 2: Domain engines.** rules_engine, coverage, confidence, anomalies, ingestion (PDF text/metadata/hash), bank_channel, reminders + escalation, release pre-check + SOD, orders + signing, metrics, dashboard aggregation. Unit tests with hand-checked tables.
Gate: `pytest tests/engines` green, including scenarios A and K numbers from 7.1.

**Phase 3: Seed + API + contract.** Seed script (7), Pydantic schemas with examples, all routers per section 8, `docs/api-contract.md`, `docs/openapi.json`, generated TS types.
Gate: `make seed && make backend &` then a curl smoke script (`scripts/smoke.sh`) hits every endpoint family as the right role and checks status codes; `pytest tests/api tests/scenarios tests/contract` green; `make contract` produces no diff.

**Phase 4: Frontend foundation.** Vite + Tailwind + shadcn init, tokens (9.2), AppShell/PublicShell/BankShell, auth + role routing, generated client + hooks, composites (9.3), ClockControl, command palette, theme toggle.
Gate: `npm run typecheck && npm run lint && npm run build`; screenshots of /login and an empty AppShell look right.

**Phase 5: Frontend screens.** Build in lifecycle order: Login, Dashboard (+matrix), Institution detail (+timeline), Instrument detail, Queue, Bank portal, Bank requests, Flags, Rules, Reminders, Releases, Order + Verify, Audit, Metrics, Demo.
Gate: build passes; Playwright smoke visits every route for each relevant role without console errors.

**Phase 6: Dynamic polish and QA.** Motion, count-ups, toasts, clock effects, highlights, empty/error states, accessibility pass, dark mode, `make qa-screens` to capture `/qa-screens/*.png`, view them and fix visual issues.
Gate: all screenshots reviewed and fixed; no console errors; reduced-motion respected.

**Phase 7: E2E, packaging, docs.** Playwright full lifecycle test, Dockerfiles + compose (build if Docker available), README (run steps, demo logins, 5-minute demo script, Mermaid architecture, "What is simulated"), final acceptance run.
Gate: `make test && make e2e` green; section 12 checklist fully ticked in PROGRESS.md.

---

## 11. TESTS
- **Contract**: committed openapi.json equals regenerated; sample responses validate against schemas; every error path returns the error envelope; envelope headers present.
- **Coverage**: at least 15 hand-checked cases including A (gap exactly 41 days), K (57 days, expiring_soon), exempt, not_covered, covered, future shortfall beyond window, two overlapping FDRs closing a gap, a returned instrument excluded.
- **Rules**: E1 vs E2 different versions by obligation date; impact preview before/after; self-approval of a rule blocked.
- **Confidence**: weakest-field logic, accept-only upgrade, `details_differ` equal-value upgrade, institution percentage rounding.
- **Anomalies**: each of the 11 types detected on a crafted instrument; no false flags on clean controls; recall >= 0.9 on planted labels; no UI/API string contains "fraud" (grep test).
- **Reminders**: advancing the clock fires T-90/60/30/7/overdue exactly once each in order, never on a non-working day, paused ones stay pending; bank overdue reminder and escalations at +1/+3/+7 working days.
- **SOD**: R3 approver1 gets 403 `SOD_VIOLATION`; R2 second approver same as first approver blocked; scrutiny/admin/bank/institution approval blocked; DB trigger blocks a raw insert violating SOD; every blocked attempt writes an audit entry.
- **Audit**: UPDATE/DELETE on audit tables aborted; with the trigger bypassed in a test, `verify` finds the first broken seq; anchor mismatch detected after tamper; restore returns ok.
- **Signing**: valid order verifies; payload change fails; public endpoint returns only the allowed keys (snapshot test) and never any bank/remark/personal field.
- **Clock hygiene**: grep test forbidding `datetime.now`, `date.today`, `utcnow` outside `core/clock.py`.
- **Frontend**: vitest for `formatINR`, `RoleGate`, `ConfidenceBar`, `CoverageBadge`.
- **Playwright E2E**: login as institution -> lodge FDR (scenario file) -> login scrutiny, see flag and record outcome -> send bank request -> login bank officer, confirm -> scrutiny accepts and sees confidence rise -> advance clock +30 days and see toast -> raise release for R1 -> approver1 approves -> open public /verify page and see VALID -> tamper box shows invalid for an edited payload -> auditor verify OK.

---

## 12. ACCEPTANCE CHECKLIST (tick each in PROGRESS.md with the command or screenshot that proves it)
[ ] `make install && make seed && make dev` works from a clean clone; `docker compose up` written (tested if Docker available)
[ ] openapi.json + generated TS client exist; frontend has zero direct fetch calls
[ ] Dashboard: gradient hero, animated KPIs, Coverage chip AND Confidence bar side by side, clickable 2x2 Priority Matrix
[ ] shadcn components used across all screens; light and dark themes look good (screenshots reviewed)
[ ] Scenarios A-K and R1-R3 reachable from /demo and match the expected values in 7.1
[ ] Bank portal is a separate visibly labelled route scoped by bank; fields upgrade only after officer acceptance with preview
[ ] Flags use "needs review" wording with three outcomes; Vigilance list works
[ ] Rule change requires a second admin; impact preview works
[ ] Clock advance fires reminders and escalations with toasts and highlights
[ ] Separation-of-duties violations blocked in API and DB, explained in UI, logged
[ ] Signed QR order and PDF; public verify page validates signature live, shows no private data, tamper box works
[ ] Auditor verify OK; tamper demo detected; restore works; anchors visible
[ ] Anomaly metrics page shows real precision/recall on planted data
[ ] README has run steps, demo logins, 5-minute demo script and the honest "What is simulated" section
[ ] `make test` and `make e2e` pass

---

## 13. HARD RULES (also copy into CLAUDE.md)
- Never claim live bank integration, real AICTE data, real e-sign or legally validated rules. Label in UI and README: synthetic data, simulated bank screen, demo signing key, seed rules pending legal validation, example savings are planning assumptions per 1,000 instruments. Never invent AICTE volumes.
- Never use the word "fraud" in any UI string or API message.
- Money is integer paise; time comes from `core/clock.py` only.
- The frontend only talks to the API through the generated typed client.
- No AI/ML in decisions. Every status, flag and verdict must carry a plain-language reason.
- Do not weaken tests, triggers or permission checks to get green builds.

## 14. FINAL REPORT (print when done)
1. What was built, per phase, with commit hashes.
2. The commands to run it (`make dev`, demo logins, URLs).
3. Test and e2e results (counts and pass/fail).
4. Checklist from section 12 with a tick or a reason for each item.
5. Deviations and known gaps from PROGRESS.md.
6. The anomaly precision and recall numbers measured on the planted data (to quote in the pitch).
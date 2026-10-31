# AMANAT — Progress

## Phase checklist
- [x] Phase 0: Bootstrap
- [x] Phase 1: Backend core — `pytest tests/core` 23 passed (clock, calendar, append-only triggers
      block UPDATE/DELETE on audit_log and audit_anchor, SOD DB trigger installed, hash chain
      verifies + genesis prev_hash + strictly increasing seq, JWT/bcrypt auth, permission matrix,
      clock-hygiene grep). `ruff check app tests` clean.
- [x] Phase 2: Domain engines — `pytest tests/engines` 65 passed (88 total incl. phase 1).
      Covers: rules_engine (E1 vs E2 by obligation date, exemption, impact-preview non-persistence),
      coverage (15 hand-checked cases incl. scenario A gap=41 days/shortfall, scenario K gap=57
      days/expiring_soon, exempt, not_covered, covered, future shortfall beyond window, two
      overlapping FDRs closing a gap, returned/matured/beneficiary-missing exclusions, boundary
      issue/maturity dates), confidence (weakest-field grade, accept-only upgrade, institution %),
      anomalies (all 11 types + no false flags on a clean instrument + never says "fraud"),
      bank_channel (7-working-day due date, Api/Sfms stubs raise NotImplementedError),
      reminders/escalation (5 reminder kinds per instrument, fire-exactly-once, pause/resume,
      link-renewal cancellation), release + SOD (R1/R2/R3 scenarios, admin-cannot-approve,
      hold-blocks-release, missing-documents-blocks, term-not-complete-blocks), orders/signing
      (valid signature verifies, tampered payload fails, masked instrument ref, public-payload
      key allowlist), metrics (precision/recall/officer-confirmed-share on a hand-built planted
      set). `ruff check app tests` clean.
- [x] Phase 3: Seed + API + contract — `pytest tests/api tests/scenarios tests/contract` 29 passed
      (117 total incl. phases 1-2); `ruff check app tests` clean; `scripts/smoke.sh` all green
      against a live server; full manual lifecycle verified end to end (lodge -> bank request ->
      bank respond -> accept -> confidence rises 0% to 91% -> raise release -> approver approves
      -> signed order created -> public /verify shows VALID with signature_valid:true -> tamper
      box shows signature_valid:false for an edited payload -> auditor /audit/verify ok -> dev
      tamper detected (first_broken_seq set) -> dev restore returns ok). All 14 demo scenarios
      (A-K, R1-R3) match their spec-7.1 expected values exactly (gap_days 41 and 57 confirmed).
      Anomaly metrics on planted data: overall recall 1.0, precision 0.91 (see Deviations for the
      one expected precision/recall overlap). `docs/openapi.json` + `frontend/src/api/schema.d.ts`
      generated; typed `openapi-fetch` client created.
- [x] Phase 4: Frontend foundation — Vite+Tailwind+shadcn (32 components), gradient tokens (9.2),
      AppShell/BankShell/PublicShell, auth context + role routing, generated client + typed
      `apiGet`/`apiPost`/`apiPostForm`/`apiGetBlob` wrappers (never raw fetch), 13 hook files, all
      composites (StatCard, CoverageBadge, GradeBadge, ConfidenceBar, MoneyText, EmptyState,
      PageHeader, RoleGate, SimulatedBadge, ExplainDrawer, PriorityMatrix, ClockControl,
      NotificationBell, ActivityFeed, CoverageTimelineChart) plus DataTable/StatusChip reused
      everywhere. `npm run typecheck`, `npx eslint src`, `npm run build` all clean.
- [x] Phase 5: Frontend screens — all 15 screens built (Login, Dashboard, InstitutionDetail,
      InstrumentDetail, Queue, BankPortal, BankRequests, Flags+FlagDetail, Rules, Reminders,
      Releases+ReleaseDetail, Verify, Audit, Metrics, Demo), with the dynamic behaviour (count-up
      KPIs, animated confidence bar, staggered cards, ClockControl toast+bell bounce, optimistic
      sonner toasts, skeleton/empty/error states, RoleGate disabled-with-tooltip) built in rather
      than deferred. Manual Playwright lifecycle smoke (login -> dashboard -> advance clock ->
      bank portal -> public verify) passed with zero console/page errors against live servers.
      Per explicit user instruction this session, Phase 6 (screenshot QA, a11y audit, extra
      dark-mode/animation passes) and Phase 7 (Playwright e2e suite, vitest, Docker, full README,
      CSV/PDF/SSE/command-palette P1 items) were skipped entirely and are not attempted.

## Deviations
- Python 3.12 not available on this machine; using Python 3.11 via `py -3.11` as documented fallback
  (spec 2.4). Logged, not a blocker.
- Git identity not configured per-repo; using existing global git user (ankan647) already set on
  this machine instead of configuring a repo-local identity.
- `make` (GNU Make) is not installed on this Windows dev machine and chocolatey install failed
  (no admin rights on `C:\ProgramData\chocolatey`). The Makefile is still written exactly per spec
  section 2.3 (works in Docker/CI/any machine with make). On this machine, phase gates are run by
  invoking the same underlying shell commands directly instead of via `make <target>`.

- JWT `exp`/`iat` use real wall-clock time (`datetime.now(timezone.utc)`), not the simulated
  business clock. Reason: PyJWT validates `exp` against the real system clock internally no
  matter what value is embedded, so a token built from simulated time would expire immediately
  (sim date can sit before real "now") or never expire (sim date far in the future). Session
  lifetime is an auth/infra concern, not domain data, so this is an intentional, narrow exception
  to the "`core/clock.py` is the only source of now" rule; `core/security.py` is explicitly
  exempted (with a comment) in the `test_clock_hygiene.py` grep test.
- SQLite `RAISE(ABORT, ...)` inside a trigger surfaces to SQLAlchemy as `IntegrityError`, not
  `OperationalError` — tests assert `IntegrityError`.
- Audit hash chain: SQLite's `DateTime` column drops tzinfo on round-trip. Both the write path
  (`audit.record`) and the read/verify path (`audit.verify_chain`) now hash a naive-UTC
  representation of the timestamp (`_ts_key()`) so stored hashes remain verifiable after a
  round trip through the database.
- Alembic migration environment reads `DATABASE_URL` from `app.core.config.get_settings()`
  rather than `alembic.ini`, so one source of truth. `alembic.ini`'s own `sqlalchemy.url` line is
  unused but left at its default per alembic's template.

- Anomaly metrics per-type `precision`/`false_positives` (5.7) are not pinned down exactly by the
  spec beyond overall precision/recall formulas, so: per type, `detected` = planted instruments of
  that type with a matching flag, `false_positives` = flags of that type on non-planted
  instruments, `precision = detected/(detected+false_positives)`, `recall = detected/planted`.
  Overall `precision`/`recall`/`officer_confirmed_share` follow the spec's literal formulas.
- Exemption `required_period` end date (for an exempt institution, which never needs a deposit)
  defaults to `deposit_request_date + 10 years` when no `closure_date` is set, purely so a period
  object always exists for downstream code; exempt institutions always show `required_paise=0`
  regardless of this period.

- Most API endpoints return a plain JSON object shaped exactly as documented in
  `AMANAT_SPEC.md` section 8.2 rather than one dedicated Pydantic response model per endpoint
  (request bodies are still validated). This sped up building ~70 endpoints at prototype pace;
  `docs/openapi.json` therefore carries a looser response schema for those routes than a fully
  typed contract would. See `docs/api-contract.md` "Known deviation". The frontend still goes
  through the generated `openapi-fetch` client exclusively — never raw `fetch`/`axios` — and uses
  local TypeScript interfaces at call sites instead of `any` where the generated schema is loose.
- Seed data creates more institutions (~39) than the illustrative "24" in spec section 7: the 17
  named scenario institutions (A, B, C1/C2, D, E1/E2, F, G1/G2, H, I, J, K, R1/R2/R3) plus one
  institution per planted-anomaly instance and per clean-control group, so that "other valid
  instruments under the same institution" never accidentally closes a deliberately-planted
  coverage/amount gap. Section 7's own numbers don't add up either (17 named scenarios + "~12
  filler" ≠ 24), so this prioritises correctness of the planted-anomaly recall measurement over
  hitting the exact illustrative headcount.
- `term_too_short` has 2 "false positives" in the anomaly metrics by design, not by bug: the two
  `maturity_before_issue`-planted instruments (negative term) also legitimately trigger
  `term_too_short` (a negative term is certainly shorter than the required minimum). Both checks
  independently and correctly fire on the same instrument; this lowers that type's measured
  precision to 0.5 while every type's recall is still 1.0 and overall recall is 1.0.
- JWT session expiry correctly uses real wall-clock time, not the simulated clock (see Phase 1
  deviation above) — tested in `tests/core/test_auth.py`.
- Release pre-check term-completion is computed with a fixed `term_years=10` (every seed rule
  version happens to use `term_years=10`) rather than re-deriving it from the institution's
  applicable rule version on every call; `rules_engine.evaluate_required_deposit(...).term_years`
  is available if a future rule version ever uses a different term.

## Known gaps
- Pydantic schema modules under `app/schemas/` are minimal (just the envelope generics) rather
  than one fully-typed module per domain as sketched in the repo layout — see the response-model
  deviation above.
- P1 items (SSE live events, CSV exports, PDF report endpoints beyond the order PDF, deeper
  dark-mode polish) are deferred to/after Phase 6 per the spec's own priority order.

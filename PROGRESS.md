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
- [ ] Phase 3: Seed + API + contract
- [ ] Phase 4: Frontend foundation
- [ ] Phase 5: Frontend screens
- [ ] Phase 6: Dynamic polish and QA
- [ ] Phase 7: E2E, packaging, docs

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

## Known gaps
(updated as phases proceed)

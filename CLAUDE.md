# AMANAT

AICTE Security Deposit / FDR Portal prototype (SIH 2026, PS 26265). Manages the lifecycle of
security-deposit FDRs held by AICTE: lodge -> check -> bank-confirm -> track -> renew -> release.
Shows, per institution, two separate indicators: **Coverage Health** (is enough valid deposit held,
today and on every future date) and **Verification Confidence** (how much of that deposit has the
bank actually confirmed). Deterministic, explainable logic only — no AI/ML in any decision path.
Everything is synthetic: simulated bank screen, demo signing key, seed rules pending legal validation.
Never use the word "fraud" anywhere in the UI/API — use "Anomaly: needs review".

Always re-read `AMANAT_SPEC.md` section N before starting phase N.

## Commands (Makefile)
- `make doctor` — check prerequisites (Node>=20, npm, Python 3.12/3.11 fallback, pip/venv)
- `make install` — backend venv + pip install, frontend npm install
- `make seed` — run backend seed script (deterministic, `random.Random(2026)`)
- `make dev` — backend :8000 + frontend :5173 together
- `make backend` / `make frontend` — run one side only
- `make test` — pytest + vitest
- `make e2e` — Playwright
- `make contract` — regenerate `docs/openapi.json` + frontend TS types; fails on diff if stale
- `make build` — production build (frontend)
- `make docker-up` — docker compose up
- `make lint` — ruff (backend) + eslint (frontend)
- `make qa-screens` — Playwright screenshots of key screens into `/qa-screens/`

## Repo layout
```
/AMANAT_SPEC.md  /CLAUDE.md  /PROGRESS.md  /README.md  /Makefile  /docker-compose.yml  /.env.example
/docs/api-contract.md  /docs/openapi.json
/backend  (pyproject.toml, alembic, app/{core,db,schemas,services,routers,fixtures}, tests)
/frontend (package.json, vite, src/{api,lib,components,layouts,pages}, e2e, qa-screens)
```

## Domain rules summary (see AMANAT_SPEC.md section 5 for exact definitions)
1. Clock and calendar — simulated `now`, working-day helpers, demo holiday list.
2. Valid instrument — status/date/beneficiary-text test for counting toward coverage.
3. Rules engine — versioned rules with applicability matching; `rule_application` records reason.
4. Coverage Health — valid(d) vs required(d), change-points, gaps, status precedence (exempt >
   not_covered > shortfall > expiring_soon > covered).
5. Verification Confidence — per-field grades claimed < document_checked < bank_confirmed;
   instrument grade = weakest field; institution confidence_pct over valid instruments.
6. Priority matrix — coverage axis x confidence axis -> next action.
7. Anomaly checks — 11 deterministic checks, severity, flag outcomes, precision/recall metrics.
8. Bank verification — simulated bank channel, request/response/accept flow, overdue escalation.
9. Reminders and escalation — T-90/60/30/7/overdue, escalation levels 1/2.
10. Release workflow — pre-check, approval levels, strict separation of duties (SOD).
11. Signed order and public verification — Ed25519 demo key, canonical JSON payload, QR, public API.
12. Audit — append-only hash-chain log with a separate anchor store.
13. Permission matrix — enforced in `require_roles` + per-object checks (see spec 5.13 table).

## Hard rules (non-negotiable)
- Never claim live bank integration, real AICTE data, real e-sign, or legally validated rules.
  Every page shows: "Prototype - synthetic data - simulated bank - demo signing key".
- Never use the word "fraud" in any UI string or API message — use "Anomaly: needs review".
- Money is integer paise everywhere in backend/API (`*_paise`); format only in frontend (`formatINR`).
- Time comes from `app/core/clock.py` only (`clock.now()`, `clock.today()`); `datetime.now()`,
  `date.today()`, `datetime.utcnow()` are forbidden elsewhere — enforced by a grep test.
- The frontend only talks to the API through the generated typed client (openapi-fetch); no `any`
  for API data; no direct `fetch`/`axios` calls.
- No AI/ML in decisions. Every status, flag and verdict carries a plain-language reason.
- Do not weaken tests, triggers, or permission checks to get green builds.
- Full lifecycle (lodge -> check -> bank-confirm -> track -> renew -> release) must work end to end
  before polish. If time/context is short, cut P1 items first (SSE, CSV exports, PDF reports, extra
  dark-mode polish) — never a lifecycle step.

## Working rules for this repo
- Work phase by phase per AMANAT_SPEC.md section 10. At each phase end: run the gate commands, fix
  failures, update PROGRESS.md, commit, then `git push origin main`.
- After 3 failed attempts on the same problem, apply the documented fallback (spec 2.4), log it
  under PROGRESS.md Deviations, and move on. Never delete a test to make it pass.
- Keep context lean: grep/glob, read only needed files; never print openapi.json or lockfiles in full.

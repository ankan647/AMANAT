# AMANAT

AICTE Security Deposit / FDR Portal — SIH 2026 prototype (PS 26265).

**Run it:**
```
cd backend && py -3.11 -m venv .venv && ./.venv/Scripts/pip install -e ".[dev]"
./.venv/Scripts/python -m app.seed          # seeds users, institutions, demo scenarios
./.venv/Scripts/python -m uvicorn app.main:app --port 8000
cd ../frontend && npm install && npm run dev   # http://localhost:5173
```

**Demo logins** (password `Demo@123`): `scrutiny1@aicte.demo`, `approver1@aicte.demo`,
`authority@aicte.demo`, `admin1@aicte.demo`, `auditor@aicte.demo`, `bank.sbi@bank.demo` — or just
click any card on the login page.

**Suggested walkthrough:** Dashboard (priority matrix) → open `DEMO-A` or `DEMO-K` for a coverage
gap → `/queue` → `/bank` as `bank.sbi@bank.demo` → `/bank-requests` to accept → `/releases` for
`DEMO-R1`/`R3` (SOD demo) → `/verify/ORD-2024-0001` → `/audit`.

Everything is synthetic: simulated bank screen, demo Ed25519 signing key, seed rules pending legal
validation. See `PROGRESS.md` for phase status and deviations; Phase 6 (QA polish) and Phase 7
(e2e, Docker, full docs) were explicitly skipped this session per instruction.

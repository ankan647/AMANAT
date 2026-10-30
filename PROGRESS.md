# AMANAT — Progress

## Phase checklist
- [x] Phase 0: Bootstrap
- [ ] Phase 1: Backend core
- [ ] Phase 2: Domain engines
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

## Known gaps
(updated as phases proceed)

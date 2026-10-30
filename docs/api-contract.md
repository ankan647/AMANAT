# AMANAT API contract

Canonical reference: `AMANAT_SPEC.md` section 8 (endpoints, conventions, enums). This file is the
quick-reference companion; the generated `docs/openapi.json` (via `make contract` /
`python -m app.export_openapi`) is the machine-readable source of truth consumed by
`openapi-typescript` to produce `frontend/src/api/schema.d.ts`.

## Conventions
- Base path: `/api/v1`. Public (no-auth) routes live under `/api/v1/public`.
- Auth: `Authorization: Bearer <jwt>`. Demo accounts: see `GET /api/v1/auth/demo-accounts`.
- Every response carries `X-Request-Id` and `X-Simulated-Now` headers.
- Single-resource responses: `{ "data": {...} }`. List responses: `{ "data": [...], "meta": { "page", "page_size", "total" } }`.
- Errors: `{ "error": { "code", "message", "details", "request_id" } }` — codes: `UNAUTHENTICATED`
  (401), `FORBIDDEN` (403), `SOD_VIOLATION` (403), `NOT_FOUND` (404), `VALIDATION_ERROR` (422),
  `CONFLICT` / `INVALID_STATE` (409), `RATE_LIMITED` (429), `INTERNAL` (500).
- Money: integer paise (`*_paise`). Dates: `YYYY-MM-DD`. Timestamps: UTC ISO-8601.

## Endpoint families (see spec 8.2 for full detail)
System, Auth, Clock, Dashboard, Institutions, Instruments, Bank requests, Anomaly flags, Rules,
Reminders/Notifications, Releases/Holds, Orders (+ Public), Audit, Metrics, Demo.

## Known deviation from "schema per response"
For build-speed in this prototype, most endpoints return a plain JSON object shaped exactly as
documented in spec 8.2, rather than one dedicated Pydantic response model per endpoint. Request
bodies for state-changing endpoints are validated inline. This means `docs/openapi.json` carries a
looser response schema for those routes than a fully-typed contract would. See `PROGRESS.md`
"Deviations" for the reasoning; the frontend typed client still goes through the generated
`openapi-fetch` client exclusively (no raw `fetch`/`axios`, no `any`) — local TypeScript interfaces
are written at the call site for the response shapes that the generated schema can't pin down.

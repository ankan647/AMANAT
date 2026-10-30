#!/usr/bin/env bash
# Smoke-tests every AMANAT endpoint family against a running backend, each as the right role.
# Usage: BASE=http://localhost:8000 bash scripts/smoke.sh
set -uo pipefail
BASE="${BASE:-http://localhost:8000}"
FAIL=0

check() {
  local desc="$1" expected="$2" actual="$3"
  if [ "$actual" = "$expected" ]; then
    echo "OK   $desc ($actual)"
  else
    echo "FAIL $desc (expected $expected, got $actual)"
    FAIL=1
  fi
}

login() {
  local email="$1"
  curl -s -X POST "$BASE/api/v1/auth/login" -H 'Content-Type: application/json' \
    -d "{\"email\":\"$email\",\"password\":\"Demo@123\"}" | python -c "import sys,json; print(json.load(sys.stdin)['data']['access_token'])"
}

code() {
  curl -s -o /dev/null -w "%{http_code}" "$@"
}

echo "== health / public =="
check "GET /health" 200 "$(code "$BASE/api/v1/health")"
check "GET /public/signing-key" 200 "$(code "$BASE/api/v1/public/signing-key")"

echo "== auth =="
SCRUTINY_TOKEN=$(login scrutiny1@aicte.demo)
APPROVER_TOKEN=$(login approver1@aicte.demo)
AUTHORITY_TOKEN=$(login authority@aicte.demo)
ADMIN_TOKEN=$(login admin1@aicte.demo)
AUDITOR_TOKEN=$(login auditor@aicte.demo)
BANK_TOKEN=$(login bank.sbi@bank.demo)
check "auth/me scrutiny" 200 "$(code -H "Authorization: Bearer $SCRUTINY_TOKEN" "$BASE/api/v1/auth/me")"
check "auth/demo-accounts" 200 "$(code "$BASE/api/v1/auth/demo-accounts")"
check "unauthenticated request rejected" 401 "$(code "$BASE/api/v1/auth/me")"

echo "== clock =="
check "GET /clock" 200 "$(code "$BASE/api/v1/clock")"
check "POST /clock/advance as scrutiny" 200 "$(code -X POST -H "Authorization: Bearer $SCRUTINY_TOKEN" -H 'Content-Type: application/json' -d '{"days":1}' "$BASE/api/v1/clock/advance")"
check "POST /clock/advance forbidden for bank_officer" 403 "$(code -X POST -H "Authorization: Bearer $BANK_TOKEN" -H 'Content-Type: application/json' -d '{"days":1}' "$BASE/api/v1/clock/advance")"
check "POST /clock/reset" 200 "$(code -X POST -H "Authorization: Bearer $ADMIN_TOKEN" "$BASE/api/v1/clock/reset")"

echo "== dashboard =="
check "GET /dashboard/summary" 200 "$(code -H "Authorization: Bearer $SCRUTINY_TOKEN" "$BASE/api/v1/dashboard/summary")"
check "GET /dashboard/priority-matrix" 200 "$(code -H "Authorization: Bearer $SCRUTINY_TOKEN" "$BASE/api/v1/dashboard/priority-matrix")"
check "GET /dashboard/activity" 200 "$(code -H "Authorization: Bearer $SCRUTINY_TOKEN" "$BASE/api/v1/dashboard/activity")"

echo "== institutions =="
check "GET /institutions" 200 "$(code -H "Authorization: Bearer $SCRUTINY_TOKEN" "$BASE/api/v1/institutions")"
INST_ID=$(curl -s -H "Authorization: Bearer $SCRUTINY_TOKEN" "$BASE/api/v1/institutions?q=DEMO-A" | python -c "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])")
check "GET /institutions/{id}" 200 "$(code -H "Authorization: Bearer $SCRUTINY_TOKEN" "$BASE/api/v1/institutions/$INST_ID")"
check "GET /institutions/{id}/coverage-timeline" 200 "$(code -H "Authorization: Bearer $SCRUTINY_TOKEN" "$BASE/api/v1/institutions/$INST_ID/coverage-timeline")"
check "GET /institutions/{id}/why-rule" 200 "$(code -H "Authorization: Bearer $SCRUTINY_TOKEN" "$BASE/api/v1/institutions/$INST_ID/why-rule")"

echo "== instruments / verification queue =="
check "GET /verification-queue" 200 "$(code -H "Authorization: Bearer $SCRUTINY_TOKEN" "$BASE/api/v1/verification-queue")"
INSTR_ID=$(curl -s -H "Authorization: Bearer $SCRUTINY_TOKEN" "$BASE/api/v1/institutions/$INST_ID" | python -c "import sys,json; d=json.load(sys.stdin)['data']; print(d['instruments'][0]['id'])")
check "GET /instruments/{id}" 200 "$(code -H "Authorization: Bearer $SCRUTINY_TOKEN" "$BASE/api/v1/instruments/$INSTR_ID")"

echo "== bank requests =="
check "GET /bank-requests" 200 "$(code -H "Authorization: Bearer $SCRUTINY_TOKEN" "$BASE/api/v1/bank-requests")"
check "GET /bank-requests (bank role scoped)" 200 "$(code -H "Authorization: Bearer $BANK_TOKEN" "$BASE/api/v1/bank-requests")"

echo "== flags =="
check "GET /flags" 200 "$(code -H "Authorization: Bearer $SCRUTINY_TOKEN" "$BASE/api/v1/flags")"
check "GET /flags/referrals" 200 "$(code -H "Authorization: Bearer $SCRUTINY_TOKEN" "$BASE/api/v1/flags/referrals")"
check "GET /metrics/anomalies" 200 "$(code -H "Authorization: Bearer $SCRUTINY_TOKEN" "$BASE/api/v1/metrics/anomalies")"

echo "== rules =="
check "GET /rules" 200 "$(code -H "Authorization: Bearer $ADMIN_TOKEN" "$BASE/api/v1/rules")"

echo "== reminders / notifications =="
check "GET /reminders" 200 "$(code -H "Authorization: Bearer $SCRUTINY_TOKEN" "$BASE/api/v1/reminders")"
check "GET /notifications" 200 "$(code -H "Authorization: Bearer $SCRUTINY_TOKEN" "$BASE/api/v1/notifications")"

echo "== releases / holds =="
check "GET /releases" 200 "$(code -H "Authorization: Bearer $SCRUTINY_TOKEN" "$BASE/api/v1/releases")"
check "GET /holds" 200 "$(code -H "Authorization: Bearer $SCRUTINY_TOKEN" "$BASE/api/v1/holds")"

echo "== audit (auditor only) =="
check "GET /audit as auditor" 200 "$(code -H "Authorization: Bearer $AUDITOR_TOKEN" "$BASE/api/v1/audit")"
check "GET /audit forbidden for scrutiny" 403 "$(code -H "Authorization: Bearer $SCRUTINY_TOKEN" "$BASE/api/v1/audit")"
check "POST /audit/verify" 200 "$(code -X POST -H "Authorization: Bearer $AUDITOR_TOKEN" "$BASE/api/v1/audit/verify")"

echo "== metrics =="
check "GET /metrics/kpis" 200 "$(code -H "Authorization: Bearer $SCRUTINY_TOKEN" "$BASE/api/v1/metrics/kpis")"

echo "== demo =="
check "GET /demo/scenarios" 200 "$(code -H "Authorization: Bearer $SCRUTINY_TOKEN" "$BASE/api/v1/demo/scenarios")"

if [ "$FAIL" = "1" ]; then
  echo "SMOKE TEST: FAILURES FOUND"
  exit 1
else
  echo "SMOKE TEST: ALL PASSED"
fi

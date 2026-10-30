from tests._helpers import auth_headers, login


def test_health_public(seeded_client):
    resp = seeded_client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["demo_mode"] is True


def test_health_has_request_id_and_simulated_now_headers(seeded_client):
    resp = seeded_client.get("/api/v1/health")
    assert "X-Request-Id" in resp.headers
    assert "X-Simulated-Now" in resp.headers


def test_login_success(seeded_client):
    resp = seeded_client.post(
        "/api/v1/auth/login", json={"email": "scrutiny1@aicte.demo", "password": "Demo@123"}
    )
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["user"]["role"] == "scrutiny"
    assert body["token_type"] == "bearer"


def test_login_wrong_password_returns_error_envelope(seeded_client):
    resp = seeded_client.post(
        "/api/v1/auth/login", json={"email": "scrutiny1@aicte.demo", "password": "wrong"}
    )
    assert resp.status_code == 401
    body = resp.json()
    assert body["error"]["code"] == "UNAUTHENTICATED"
    assert "request_id" in body["error"]


def test_unauthenticated_request_rejected(seeded_client):
    resp = seeded_client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_institution_role_sees_only_own_institution(seeded_client):
    token = login(seeded_client, "inst.demo-a@inst.demo")
    resp = seeded_client.get("/api/v1/institutions", headers=auth_headers(token))
    assert resp.status_code == 200
    rows = resp.json()["data"]
    assert all(r["code"] == "DEMO-A" for r in rows)


def test_advance_clock_forbidden_for_bank_officer(seeded_client):
    token = login(seeded_client, "bank.sbi@bank.demo")
    resp = seeded_client.post("/api/v1/clock/advance", json={"days": 1}, headers=auth_headers(token))
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


def test_audit_forbidden_for_scrutiny(seeded_client):
    token = login(seeded_client, "scrutiny1@aicte.demo")
    resp = seeded_client.get("/api/v1/audit", headers=auth_headers(token))
    assert resp.status_code == 403


def test_validation_error_envelope_on_flag_outcome_missing_reason(seeded_client):
    token = login(seeded_client, "scrutiny1@aicte.demo")
    flags = seeded_client.get("/api/v1/flags", headers=auth_headers(token)).json()["data"]
    flag_id = flags[0]["id"]
    resp = seeded_client.post(
        f"/api/v1/flags/{flag_id}/outcome", json={"outcome": "cleared"}, headers=auth_headers(token)
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"
    assert resp.json()["error"]["details"]["fields"][0]["path"] == "reason"


def test_public_order_verify_never_leaks_private_fields(seeded_client):
    resp = seeded_client.get("/api/v1/public/orders/ORD-2024-0001")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert set(data.keys()) == {
        "order_no", "institution_name", "amount_paise", "issued_on", "issuing_authority",
        "status", "signature_valid", "signed_at",
    }
    assert data["signature_valid"] is True


def test_public_order_revoked_shows_revoked_status(seeded_client):
    resp = seeded_client.get("/api/v1/public/orders/ORD-2024-0002")
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "revoked"


def test_never_says_fraud_anywhere_in_responses(seeded_client):
    token = login(seeded_client, "scrutiny1@aicte.demo")
    for path in ["/api/v1/flags", "/api/v1/dashboard/summary", "/api/v1/demo/scenarios"]:
        resp = seeded_client.get(path, headers=auth_headers(token))
        assert "fraud" not in resp.text.lower()

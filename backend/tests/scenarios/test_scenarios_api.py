from tests._helpers import auth_headers, login


def _institution_row(client, token, code):
    resp = client.get(f"/api/v1/institutions?q={code}", headers=auth_headers(token))
    rows = resp.json()["data"]
    return next(r for r in rows if r["code"] == code)


def test_scenario_a_shortfall_gap_41_days(seeded_client):
    token = login(seeded_client, "scrutiny1@aicte.demo")
    row = _institution_row(seeded_client, token, "DEMO-A")
    assert row["coverage"]["status"] == "shortfall"
    assert row["coverage"]["gap_start"] == "2027-01-13"
    assert row["coverage"]["gap_end"] == "2027-02-22"
    assert row["coverage"]["gap_days"] == 41


def test_scenario_k_expiring_soon_gap_57_days(seeded_client):
    token = login(seeded_client, "scrutiny1@aicte.demo")
    row = _institution_row(seeded_client, token, "DEMO-K")
    assert row["coverage"]["status"] == "expiring_soon"
    assert row["coverage"]["gap_days"] == 57


def test_scenario_b_covered_unverified(seeded_client):
    token = login(seeded_client, "scrutiny1@aicte.demo")
    row = _institution_row(seeded_client, token, "DEMO-B")
    assert row["coverage"]["status"] == "covered"
    assert row["confidence_pct"] == 0
    assert row["matrix_cell"] == "verify_next"


def test_scenario_h_healthy(seeded_client):
    token = login(seeded_client, "scrutiny1@aicte.demo")
    row = _institution_row(seeded_client, token, "DEMO-H")
    assert row["coverage"]["status"] == "covered"
    assert row["confidence_pct"] == 100
    assert row["matrix_cell"] == "routine_monitoring"


def test_scenario_i_exempt(seeded_client):
    token = login(seeded_client, "scrutiny1@aicte.demo")
    row = _institution_row(seeded_client, token, "DEMO-I")
    assert row["coverage"]["status"] == "exempt"
    assert row["coverage"]["exempt_reason"] is not None


def test_scenario_j_not_covered(seeded_client):
    token = login(seeded_client, "scrutiny1@aicte.demo")
    row = _institution_row(seeded_client, token, "DEMO-J")
    assert row["coverage"]["status"] == "not_covered"
    assert row["confidence_pct"] == 0


def test_scenario_c_duplicate_fdr_flag_on_both(seeded_client):
    token = login(seeded_client, "scrutiny1@aicte.demo")
    resp = seeded_client.get(
        "/api/v1/flags?type=duplicate_fdr_number", headers=auth_headers(token)
    )
    flags = resp.json()["data"]
    assert len(flags) >= 2
    assert all(f["severity"] == "high" for f in flags)


def test_scenario_e1_vs_e2_different_required_amounts(seeded_client):
    token = login(seeded_client, "scrutiny1@aicte.demo")
    row1 = _institution_row(seeded_client, token, "DEMO-E1")
    row2 = _institution_row(seeded_client, token, "DEMO-E2")
    assert row1["coverage"]["required_paise"] == 10_00_000_00
    assert row2["coverage"]["required_paise"] == 15_00_000_00


def test_scenario_f_release_blocked_by_hold(seeded_client):
    token = login(seeded_client, "scrutiny1@aicte.demo")
    resp = seeded_client.get("/api/v1/holds", headers=auth_headers(token))
    holds = resp.json()["data"]
    assert any("VIG/2026/114" in h["reason"] for h in holds)


def test_scenario_g_public_orders_valid_and_revoked(seeded_client):
    valid = seeded_client.get("/api/v1/public/orders/ORD-2024-0001")
    revoked = seeded_client.get("/api/v1/public/orders/ORD-2024-0002")
    assert valid.json()["data"]["status"] == "valid"
    assert valid.json()["data"]["signature_valid"] is True
    assert revoked.json()["data"]["status"] == "revoked"


def test_scenario_r3_sod_violation_on_approve(seeded_client):
    scrutiny_token = login(seeded_client, "scrutiny1@aicte.demo")
    row = _institution_row(seeded_client, scrutiny_token, "DEMO-R3")
    inst_detail = seeded_client.get(
        f"/api/v1/institutions/{row['id']}", headers=auth_headers(scrutiny_token)
    ).json()["data"]
    instrument_id = inst_detail["instruments"][0]["id"]

    release_resp = seeded_client.post(
        "/api/v1/releases",
        json={"instrument_id": instrument_id, "reason": "Term completed"},
        headers=auth_headers(scrutiny_token),
    )
    release_id = release_resp.json()["data"]["id"]

    approver1_token = login(seeded_client, "approver1@aicte.demo")
    approve_resp = seeded_client.post(
        f"/api/v1/releases/{release_id}/approve",
        json={"remarks": "test"},
        headers=auth_headers(approver1_token),
    )
    assert approve_resp.status_code == 403
    assert approve_resp.json()["error"]["code"] == "SOD_VIOLATION"
    assert approve_resp.json()["error"]["details"]["rule"] == "scrutiniser_cannot_approve"

    authority_token = login(seeded_client, "authority@aicte.demo")
    approve_resp2 = seeded_client.post(
        f"/api/v1/releases/{release_id}/approve",
        json={"remarks": "authority approves"},
        headers=auth_headers(authority_token),
    )
    assert approve_resp2.status_code == 200


def test_scenario_r1_release_single_approver(seeded_client):
    scrutiny_token = login(seeded_client, "scrutiny1@aicte.demo")
    row = _institution_row(seeded_client, scrutiny_token, "DEMO-R1")
    inst_detail = seeded_client.get(
        f"/api/v1/institutions/{row['id']}", headers=auth_headers(scrutiny_token)
    ).json()["data"]
    instrument_id = inst_detail["instruments"][0]["id"]

    release_resp = seeded_client.post(
        "/api/v1/releases",
        json={"instrument_id": instrument_id, "reason": "Term completed"},
        headers=auth_headers(scrutiny_token),
    )
    assert release_resp.json()["data"]["precheck_verdict"] == "eligible"
    release_id = release_resp.json()["data"]["id"]

    approver1_token = login(seeded_client, "approver1@aicte.demo")
    approve_resp = seeded_client.post(
        f"/api/v1/releases/{release_id}/approve",
        json={"remarks": "approved"},
        headers=auth_headers(approver1_token),
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["data"]["order"] is not None


def test_scenario_r2_needs_two_approvers(seeded_client):
    scrutiny_token = login(seeded_client, "scrutiny1@aicte.demo")
    row = _institution_row(seeded_client, scrutiny_token, "DEMO-R2")
    inst_detail = seeded_client.get(
        f"/api/v1/institutions/{row['id']}", headers=auth_headers(scrutiny_token)
    ).json()["data"]
    instrument_id = inst_detail["instruments"][0]["id"]

    release_resp = seeded_client.post(
        "/api/v1/releases",
        json={"instrument_id": instrument_id, "reason": "Term completed"},
        headers=auth_headers(scrutiny_token),
    )
    assert release_resp.json()["data"]["needs_second_approval"] is True
    release_id = release_resp.json()["data"]["id"]

    approver1_token = login(seeded_client, "approver1@aicte.demo")
    approve1 = seeded_client.post(
        f"/api/v1/releases/{release_id}/approve",
        json={"remarks": "level 1"},
        headers=auth_headers(approver1_token),
    )
    assert approve1.status_code == 200
    assert approve1.json()["data"]["next_required_level"] == 2
    assert approve1.json()["data"]["order"] is None

    # same approver again at level 2 must be blocked (second_approver_must_differ)
    approve_same = seeded_client.post(
        f"/api/v1/releases/{release_id}/approve",
        json={"remarks": "trying again"},
        headers=auth_headers(approver1_token),
    )
    assert approve_same.status_code == 403
    assert approve_same.json()["error"]["details"]["rule"] == "second_approver_must_differ"

    authority_token = login(seeded_client, "authority@aicte.demo")
    approve2 = seeded_client.post(
        f"/api/v1/releases/{release_id}/approve",
        json={"remarks": "level 2"},
        headers=auth_headers(authority_token),
    )
    assert approve2.status_code == 200
    assert approve2.json()["data"]["order"] is not None

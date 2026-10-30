from app.core.permissions import ACTION_ROLES


def test_lodge_fdr_matches_spec():
    assert ACTION_ROLES["lodge_fdr"] == {"institution", "scrutiny"}


def test_approve_release_matches_spec():
    assert ACTION_ROLES["approve_release"] == {"senior_approver", "competent_authority"}


def test_read_audit_matches_spec():
    assert ACTION_ROLES["read_audit"] == {"competent_authority", "auditor"}


def test_advance_clock_matches_spec():
    assert ACTION_ROLES["advance_clock"] == {
        "scrutiny",
        "senior_approver",
        "competent_authority",
        "admin",
    }


def test_respond_bank_request_is_bank_officer_only():
    assert ACTION_ROLES["respond_bank_request"] == {"bank_officer"}


def test_revoke_order_place_hold_is_authority_only():
    assert ACTION_ROLES["revoke_order_place_hold"] == {"competent_authority"}

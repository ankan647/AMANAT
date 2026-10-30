import pytest

from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_roundtrip():
    h = hash_password("Demo@123")
    assert verify_password("Demo@123", h) is True
    assert verify_password("wrong", h) is False


def test_jwt_roundtrip():
    token, expires_in = create_access_token(sub="scrutiny1@aicte.demo", role="scrutiny")
    assert expires_in > 0
    claims = decode_access_token(token)
    assert claims["sub"] == "scrutiny1@aicte.demo"
    assert claims["role"] == "scrutiny"


def test_jwt_carries_bank_name_and_institution_id():
    token, _ = create_access_token(
        sub="bank.sbi@bank.demo", role="bank_officer", bank_name="State Bank of India"
    )
    claims = decode_access_token(token)
    assert claims["bank_name"] == "State Bank of India"

    token2, _ = create_access_token(sub="inst.demo-a@inst.demo", role="institution", institution_id=7)
    claims2 = decode_access_token(token2)
    assert claims2["institution_id"] == 7


def test_invalid_token_raises():
    with pytest.raises(Exception):
        decode_access_token("not-a-valid-token")

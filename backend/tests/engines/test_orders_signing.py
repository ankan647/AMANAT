from datetime import date

from app.core.signing import sign_payload, verify_payload
from app.services.orders import build_payload, mask_instrument_ref


def test_signed_payload_verifies():
    payload = {"order_no": "ORD-2026-0001", "amount_paise": 123}
    signature_b64, public_key_b64 = sign_payload(payload)
    assert verify_payload(payload, signature_b64, public_key_b64) is True


def test_tampered_payload_fails_verification():
    payload = {"order_no": "ORD-2026-0001", "amount_paise": 123}
    signature_b64, public_key_b64 = sign_payload(payload)
    tampered = dict(payload)
    tampered["amount_paise"] = 999
    assert verify_payload(tampered, signature_b64, public_key_b64) is False


def test_mask_instrument_ref_shows_last_4_only():
    assert mask_instrument_ref("SBI/FDR/2024/778812") == "****8812"


def test_build_payload_contains_only_allowed_keys():
    class Inst:
        name = "Test College"
        code = "DEMO-X"

    class Instrument:
        fdr_number = "SBI/FDR/2024/778812"

    payload = build_payload(
        order_no="ORD-2026-0001",
        institution=Inst(),
        instrument=Instrument(),
        amount_paise=1000,
        issued_on=date(2026, 10, 30),
        release_request_id=5,
    )
    assert set(payload.keys()) == {
        "order_no",
        "institution_name",
        "institution_code",
        "amount_paise",
        "issued_on",
        "issuing_authority",
        "release_request_id",
        "instrument_ref_masked",
        "interest_note",
    }
    assert payload["instrument_ref_masked"] == "****8812"
    assert payload["interest_note"] == "Accrued interest is credited to the Council."

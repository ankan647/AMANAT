"""Ed25519 demo signing key and canonical-payload signing (spec 5.11). DEMO KEY ONLY."""

import base64
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
    load_pem_private_key,
)

from app.core.audit import canonical_json
from app.core.config import get_settings


def _load_or_create_key() -> Ed25519PrivateKey:
    settings = get_settings()
    path = Path(settings.SIGNING_KEY_PATH)
    if path.exists():
        return load_pem_private_key(path.read_bytes(), password=None)  # type: ignore[return-value]
    key = Ed25519PrivateKey.generate()
    path.write_bytes(
        key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    )
    return key


def get_public_key_b64() -> str:
    key = _load_or_create_key()
    public_key: Ed25519PublicKey = key.public_key()
    raw = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
    return base64.b64encode(raw).decode("ascii")


def sign_payload(payload: dict) -> tuple[str, str]:
    """Returns (signature_b64, public_key_b64) for the canonical JSON of `payload`."""
    key = _load_or_create_key()
    message = canonical_json(payload).encode("utf-8")
    signature = key.sign(message)
    return base64.b64encode(signature).decode("ascii"), get_public_key_b64()


def verify_payload(payload: dict, signature_b64: str, public_key_b64: str) -> bool:
    try:
        raw_key = base64.b64decode(public_key_b64)
        public_key = Ed25519PublicKey.from_public_bytes(raw_key)
        signature = base64.b64decode(signature_b64)
        message = canonical_json(payload).encode("utf-8")
        public_key.verify(signature, message)
        return True
    except Exception:  # noqa: BLE001
        return False

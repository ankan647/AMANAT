from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core import audit
from app.core.errors import NotFoundError
from app.core.permissions import CurrentUser, get_current_user, require_roles
from app.core.signing import get_public_key_b64, verify_payload
from app.db.models import SignedOrder
from app.db.session import get_db
from app.services import orders as orders_service

router = APIRouter(prefix="/api/v1", tags=["orders"])


def _order_out(o: SignedOrder) -> dict:
    return {
        "id": o.id,
        "order_no": o.order_no,
        "release_request_id": o.release_request_id,
        "payload": o.payload_json,
        "signature_b64": o.signature_b64,
        "status": o.status,
        "issued_on": o.issued_on.isoformat(),
        "revoked_reason": o.revoked_reason,
    }


@router.get("/orders/{order_id}")
def get_order(order_id: int, current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    o = db.query(SignedOrder).filter(SignedOrder.id == order_id).first()
    if o is None:
        raise NotFoundError("Order not found.")
    return {"data": _order_out(o)}


@router.get("/orders/{order_id}/pdf")
def get_order_pdf(order_id: int, current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    o = db.query(SignedOrder).filter(SignedOrder.id == order_id).first()
    if o is None:
        raise NotFoundError("Order not found.")
    pdf_bytes = orders_service.generate_order_pdf(o)
    return Response(content=pdf_bytes, media_type="application/pdf")


@router.post("/orders/{order_id}/revoke")
def revoke(
    order_id: int,
    body: dict,
    current_user: CurrentUser = Depends(require_roles("competent_authority")),
    db: Session = Depends(get_db),
) -> dict:
    o = db.query(SignedOrder).filter(SignedOrder.id == order_id).first()
    if o is None:
        raise NotFoundError("Order not found.")
    o.status = "revoked"
    o.revoked_reason = body.get("reason", "")
    db.add(o)
    db.commit()
    db.refresh(o)
    audit.record(
        db, actor_id=current_user.id, actor_role=current_user.role, action="order_revoked",
        entity_type="signed_order", entity_id=o.id, details={"reason": o.revoked_reason},
    )
    return {"data": _order_out(o)}


@router.post("/orders/{order_id}/supersede")
def supersede(
    order_id: int,
    current_user: CurrentUser = Depends(require_roles("competent_authority")),
    db: Session = Depends(get_db),
) -> dict:
    o = db.query(SignedOrder).filter(SignedOrder.id == order_id).first()
    if o is None:
        raise NotFoundError("Order not found.")
    o.status = "superseded"
    db.add(o)
    db.commit()
    db.refresh(o)
    audit.record(
        db, actor_id=current_user.id, actor_role=current_user.role, action="order_superseded",
        entity_type="signed_order", entity_id=o.id, details={},
    )
    return {"data": _order_out(o)}


# --- Public, no auth ---

public_router = APIRouter(prefix="/api/v1/public", tags=["public"])


@public_router.get("/orders/{order_no}")
def public_get_order(order_no: str, db: Session = Depends(get_db)) -> dict:
    o = db.query(SignedOrder).filter(SignedOrder.order_no == order_no).first()
    if o is None:
        raise NotFoundError("Order not found.")
    signature_valid = verify_payload(o.payload_json, o.signature_b64, o.public_key_b64)
    payload = o.payload_json
    return {
        "data": {
            "order_no": payload["order_no"],
            "institution_name": payload["institution_name"],
            "amount_paise": payload["amount_paise"],
            "issued_on": payload["issued_on"],
            "issuing_authority": payload["issuing_authority"],
            "status": o.status,
            "signature_valid": signature_valid,
            "signed_at": o.issued_on.isoformat(),
        }
    }


@public_router.get("/signing-key")
def public_signing_key() -> dict:
    return {"data": {"algorithm": "Ed25519", "public_key_b64": get_public_key_b64(), "demo_key": True}}


@public_router.post("/orders/verify")
def public_verify(body: dict) -> dict:
    valid = verify_payload(body["payload"], body["signature_b64"], body.get("public_key_b64") or get_public_key_b64())
    return {"data": {"signature_valid": valid}}

from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.core.errors import ForbiddenError
from app.core.permissions import CurrentUser, get_current_user, require_roles

router = APIRouter(prefix="/api/v1/demo", tags=["demo"])

SCENARIOS = [
    {"key": "A", "title": "Shortfall ahead", "story": "Coverage is fine today but a 41-day gap is coming after the FDR matures, well beyond the 60-day window.", "institution_code": "DEMO-A"},
    {"key": "B", "title": "Covered but unverified", "story": "Deposit is fully covered, but the bank hasn't confirmed anything yet.", "institution_code": "DEMO-B"},
    {"key": "C", "title": "Duplicate FDR", "story": "The same FDR number was lodged under two different institutions.", "institution_code": "DEMO-C1"},
    {"key": "D", "title": "Bank differs", "story": "The bank reports a different maturity date than claimed, raising a mismatch flag.", "institution_code": "DEMO-D"},
    {"key": "E", "title": "Different rules", "story": "Two institutions with the same category but different obligation dates get different required amounts.", "institution_code": "DEMO-E1"},
    {"key": "F", "title": "Release on hold", "story": "Term is complete but a Vigilance hold blocks the release.", "institution_code": "DEMO-F"},
    {"key": "G", "title": "Signed orders", "story": "One valid, one revoked signed release order, both publicly verifiable.", "institution_code": "DEMO-G1"},
    {"key": "H", "title": "Healthy", "story": "Fully covered and fully bank-confirmed — routine monitoring only.", "institution_code": "DEMO-H"},
    {"key": "I", "title": "Exempt", "story": "Fourteen years operating elsewhere — no deposit required.", "institution_code": "DEMO-I"},
    {"key": "J", "title": "Not covered", "story": "No instruments lodged at all.", "institution_code": "DEMO-J"},
    {"key": "K", "title": "Expiring soon", "story": "A 57-day gap starts in 25 days — well inside the warning window.", "institution_code": "DEMO-K"},
    {"key": "R1", "title": "Release (single approver)", "story": "Term complete, fully confirmed, one approver signs off.", "institution_code": "DEMO-R1"},
    {"key": "R2", "title": "Release (two approvers)", "story": "A high-value release needs a second, different approver.", "institution_code": "DEMO-R2"},
    {"key": "R3", "title": "Separation of duties", "story": "The officer who scrutinised the FDR cannot also approve its release.", "institution_code": "DEMO-R3"},
]


@router.get("/scenarios")
def scenarios(current_user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    out = []
    for s in SCENARIOS:
        out.append(
            {
                **s,
                "institution_id": None,
                "deep_link": f"/institutions?code={s['institution_code']}",
                "expected": s["story"],
            }
        )
    return out


@router.post("/reset")
def reset(current_user: CurrentUser = Depends(require_roles("admin"))) -> dict:
    settings = get_settings()
    if not settings.DEMO_MODE:
        raise ForbiddenError("Only available in DEMO_MODE.")
    from app.seed import run_seed

    run_seed(reset=True)
    return {"data": {"reseeded": True}}

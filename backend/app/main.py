from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.clock import now
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.middleware import RequestContextMiddleware
from app.db.init_db import init_anchor_db, init_main_db
from app.db.session import get_anchor_engine, get_engine
from app.routers import (
    audit,
    auth,
    bank_requests,
    clock as clock_router,
    dashboard,
    demo,
    flags,
    institutions,
    instruments,
    metrics,
    orders,
    releases,
    reminders,
    rules,
)

settings = get_settings()

app = FastAPI(title="AMANAT API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestContextMiddleware)

register_exception_handlers(app)

app.include_router(auth.router)
app.include_router(clock_router.router)
app.include_router(dashboard.router)
app.include_router(institutions.router)
app.include_router(instruments.router)
app.include_router(bank_requests.router)
app.include_router(flags.router)
app.include_router(rules.router)
app.include_router(reminders.router)
app.include_router(releases.router)
app.include_router(orders.router)
app.include_router(orders.public_router)
app.include_router(audit.router)
app.include_router(metrics.router)
app.include_router(demo.router)


@app.on_event("startup")
def on_startup() -> None:
    init_main_db(get_engine())
    init_anchor_db(get_anchor_engine())


@app.get("/api/v1/health")
def health() -> dict:
    return {"status": "ok", "simulated_now": now().isoformat(), "demo_mode": settings.DEMO_MODE}

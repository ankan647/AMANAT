from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.clock import now
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.middleware import RequestContextMiddleware
from app.db.init_db import init_anchor_db, init_main_db
from app.db.session import get_anchor_engine, get_engine

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


@app.on_event("startup")
def on_startup() -> None:
    init_main_db(get_engine())
    init_anchor_db(get_anchor_engine())


@app.get("/api/v1/health")
def health() -> dict:
    return {"status": "ok", "simulated_now": now().isoformat(), "demo_mode": settings.DEMO_MODE}

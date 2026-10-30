import os
import tempfile
from pathlib import Path

_TMP_DIR = Path(tempfile.mkdtemp(prefix="amanat_test_"))
os.environ["DEMO_MODE"] = "true"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["DATABASE_URL"] = f"sqlite:///{(_TMP_DIR / 'test.db').as_posix()}"
os.environ["ANCHOR_DB_PATH"] = (_TMP_DIR / "anchor_test.db").as_posix()
os.environ["STORAGE_DIR"] = (_TMP_DIR / "files").as_posix()
os.environ["SIGNING_KEY_PATH"] = (_TMP_DIR / "demo_ed25519.pem").as_posix()
os.environ["SIM_START_DATE"] = "2026-10-30"

import pytest  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.init_db import init_anchor_db, init_main_db  # noqa: E402
from app.db.session import (  # noqa: E402
    get_anchor_engine,
    get_anchor_sessionmaker,
    get_engine,
    get_sessionmaker,
)

get_settings()


@pytest.fixture(scope="session", autouse=True)
def _setup_databases():
    init_main_db(get_engine())
    init_anchor_db(get_anchor_engine())
    yield


@pytest.fixture()
def db():
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def anchor_db():
    session = get_anchor_sessionmaker()()
    try:
        yield session
    finally:
        session.close()

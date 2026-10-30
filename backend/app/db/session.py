from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    )
    if "sqlite" in settings.DATABASE_URL:
        _enable_sqlite_pragmas(engine)
    return engine


@lru_cache
def get_anchor_engine() -> Engine:
    settings = get_settings()
    url = f"sqlite:///{settings.ANCHOR_DB_PATH}"
    engine = create_engine(url, connect_args={"check_same_thread": False})
    _enable_sqlite_pragmas(engine)
    return engine


def _enable_sqlite_pragmas(engine: Engine) -> None:
    @event.listens_for(engine, "connect")
    def _set_pragmas(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


@lru_cache
def get_anchor_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_anchor_engine(), autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = get_sessionmaker()()
    try:
        yield db
    finally:
        db.close()


def get_anchor_db() -> Generator[Session, None, None]:
    db = get_anchor_sessionmaker()()
    try:
        yield db
    finally:
        db.close()

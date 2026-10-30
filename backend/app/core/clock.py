"""Single source of truth for "now" in AMANAT.

Every other module MUST get the current date/time through `now()` / `today()` here.
`datetime.now()`, `date.today()` and `datetime.utcnow()` are forbidden elsewhere in `app/`
(enforced by `tests/core/test_clock_hygiene.py`, which greps the codebase).
"""

from datetime import date, datetime, timezone

from app.core.config import get_settings
from app.db.models import AppClock


def _session():  # type: ignore[no-untyped-def]
    from app.db.session import get_sessionmaker

    return get_sessionmaker()()


def _get_or_create_row(db) -> AppClock:  # type: ignore[no-untyped-def]
    row = db.query(AppClock).first()
    if row is None:
        settings = get_settings()
        start = datetime.combine(settings.SIM_START_DATE, datetime.min.time(), tzinfo=timezone.utc)
        row = AppClock(simulated_now=start, is_simulated=True)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def now() -> datetime:
    db = _session()
    try:
        row = _get_or_create_row(db)
        value = row.simulated_now
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value
    finally:
        db.close()


def today() -> date:
    return now().date()


def is_simulated() -> bool:
    db = _session()
    try:
        return _get_or_create_row(db).is_simulated
    finally:
        db.close()


def advance_days(days: int) -> datetime:
    """Move the simulated clock forward by `days` calendar days. Returns the new now."""
    if days < 1 or days > 400:
        raise ValueError("days must be between 1 and 400")
    db = _session()
    try:
        row = _get_or_create_row(db)
        current = row.simulated_now
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        new_value = current + _timedelta_days(days)
        row.simulated_now = new_value
        db.add(row)
        db.commit()
        return new_value
    finally:
        db.close()


def set_date(target: date) -> datetime:
    db = _session()
    try:
        row = _get_or_create_row(db)
        new_value = datetime.combine(target, datetime.min.time(), tzinfo=timezone.utc)
        row.simulated_now = new_value
        db.add(row)
        db.commit()
        return new_value
    finally:
        db.close()


def reset() -> datetime:
    settings = get_settings()
    return set_date(settings.SIM_START_DATE)


def _timedelta_days(days: int):  # type: ignore[no-untyped-def]
    from datetime import timedelta

    return timedelta(days=days)

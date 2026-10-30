"""Working-day calendar helpers (Mon-Fri, excluding the demo holiday list)."""

from datetime import date, timedelta

HOLIDAYS: set[date] = {
    date(2026, 12, 25),
    date(2027, 1, 26),
    date(2027, 3, 4),
    date(2027, 8, 15),
    date(2027, 10, 2),
    date(2027, 12, 25),
}


def is_working_day(d: date) -> bool:
    return d.weekday() < 5 and d not in HOLIDAYS


def next_working_day(d: date) -> date:
    cursor = d + timedelta(days=1)
    while not is_working_day(cursor):
        cursor += timedelta(days=1)
    return cursor


def prev_working_day(d: date) -> date:
    cursor = d - timedelta(days=1)
    while not is_working_day(cursor):
        cursor -= timedelta(days=1)
    return cursor


def add_working_days(d: date, n: int) -> date:
    """Add n working days to d (n may be negative)."""
    cursor = d
    step = 1 if n >= 0 else -1
    remaining = abs(n)
    while remaining > 0:
        cursor = cursor + timedelta(days=step)
        if is_working_day(cursor):
            remaining -= 1
    return cursor


def move_to_prev_working_day(d: date) -> date:
    """Return d if it's a working day, else the previous working day."""
    return d if is_working_day(d) else prev_working_day(d)

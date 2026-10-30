from datetime import date

from app.core import clock
from app.core.calendar import add_working_days, is_working_day, prev_working_day


def test_initial_now_is_sim_start_date():
    clock.reset()
    assert clock.today() == date(2026, 10, 30)


def test_advance_days_moves_clock_forward():
    clock.reset()
    clock.advance_days(5)
    assert clock.today() == date(2026, 11, 4)


def test_set_and_reset():
    clock.set_date(date(2027, 1, 1))
    assert clock.today() == date(2027, 1, 1)
    clock.reset()
    assert clock.today() == date(2026, 10, 30)


def test_advance_days_rejects_out_of_range():
    import pytest

    clock.reset()
    with pytest.raises(ValueError):
        clock.advance_days(0)
    with pytest.raises(ValueError):
        clock.advance_days(401)


def test_working_day_helpers():
    # 2026-10-30 is a Friday
    assert is_working_day(date(2026, 10, 30)) is True
    assert is_working_day(date(2026, 10, 31)) is False  # Saturday
    assert is_working_day(date(2026, 11, 1)) is False  # Sunday
    assert is_working_day(date(2027, 12, 25)) is False  # holiday
    assert prev_working_day(date(2026, 11, 2)) == date(2026, 10, 30)
    assert add_working_days(date(2026, 10, 30), 1) == date(2026, 11, 2)

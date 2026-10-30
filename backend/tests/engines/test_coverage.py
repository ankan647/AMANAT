from datetime import date

from app.services.coverage import compute_coverage

TODAY = date(2026, 10, 30)
GOOD_BENEFICIARY = "AICTE, Government of India"


def make_instrument(id, amount_paise, issue_date, maturity_date, status="active", beneficiary=GOOD_BENEFICIARY):
    class Instr:
        pass

    i = Instr()
    i.id = id
    i.amount_paise = amount_paise
    i.issue_date = issue_date
    i.maturity_date = maturity_date
    i.status = status
    i.beneficiary = beneficiary
    return i


REQUIRED_1M = 10_00_000_00  # paise


def test_scenario_a_shortfall_gap_41_days():
    instruments = [make_instrument(1, REQUIRED_1M, date(2017, 3, 10), date(2027, 1, 13))]
    result = compute_coverage(
        instruments=instruments,
        today=TODAY,
        period_start=date(2017, 2, 23),
        period_end=date(2027, 2, 23),
        amount_paise=REQUIRED_1M,
        exempt=False,
        exempt_reason=None,
        expiring_window_days=60,
    )
    assert result.status == "shortfall"
    gap = result.first_gap
    assert gap.start == date(2027, 1, 13)
    assert gap.end == date(2027, 2, 22)
    assert gap.days == 41


def test_scenario_k_expiring_soon_gap_57_days():
    instruments = [make_instrument(1, REQUIRED_1M, date(2017, 2, 1), date(2026, 11, 24))]
    result = compute_coverage(
        instruments=instruments,
        today=TODAY,
        period_start=date(2017, 1, 20),
        period_end=date(2027, 1, 20),
        amount_paise=REQUIRED_1M,
        exempt=False,
        exempt_reason=None,
        expiring_window_days=60,
    )
    assert result.status == "expiring_soon"
    gap = result.first_gap
    assert gap.start == date(2026, 11, 24)
    assert gap.end == date(2027, 1, 19)
    assert gap.days == 57


def test_scenario_b_covered_but_unverified():
    instruments = [make_instrument(1, 15_00_000_00, date(2023, 4, 10), date(2033, 4, 10))]
    result = compute_coverage(
        instruments=instruments,
        today=TODAY,
        period_start=date(2023, 4, 1),
        period_end=date(2033, 4, 1),
        amount_paise=15_00_000_00,
        exempt=False,
        exempt_reason=None,
        expiring_window_days=60,
    )
    assert result.status == "covered"
    assert result.first_gap is None


def test_scenario_h_healthy_fully_covered():
    instruments = [make_instrument(1, 15_00_000_00, date(2023, 9, 10), date(2033, 9, 10))]
    result = compute_coverage(
        instruments=instruments,
        today=TODAY,
        period_start=date(2023, 9, 1),
        period_end=date(2033, 9, 1),
        amount_paise=15_00_000_00,
        exempt=False,
        exempt_reason=None,
        expiring_window_days=60,
    )
    assert result.status == "covered"


def test_scenario_i_exempt():
    result = compute_coverage(
        instruments=[],
        today=TODAY,
        period_start=date(2020, 1, 1),
        period_end=date(2030, 1, 1),
        amount_paise=0,
        exempt=True,
        exempt_reason="Exempt: operating elsewhere for 14 years (>= 10 required).",
        expiring_window_days=60,
    )
    assert result.status == "exempt"
    assert result.exempt_reason is not None


def test_scenario_j_not_covered_no_instruments():
    result = compute_coverage(
        instruments=[],
        today=TODAY,
        period_start=date(2024, 8, 1),
        period_end=date(2034, 8, 1),
        amount_paise=15_00_000_00,
        exempt=False,
        exempt_reason=None,
        expiring_window_days=60,
    )
    assert result.status == "not_covered"
    assert result.required_paise == 15_00_000_00
    assert result.valid_paise == 0


def test_future_shortfall_beyond_window_is_shortfall_not_expiring():
    # gap starts > 60 days after today
    instruments = [make_instrument(1, REQUIRED_1M, date(2020, 1, 1), date(2027, 3, 1))]
    result = compute_coverage(
        instruments=instruments,
        today=TODAY,
        period_start=date(2020, 1, 1),
        period_end=date(2030, 1, 1),
        amount_paise=REQUIRED_1M,
        exempt=False,
        exempt_reason=None,
        expiring_window_days=60,
    )
    assert result.status == "shortfall"
    assert result.first_gap.start == date(2027, 3, 1)


def test_gap_within_window_is_expiring_soon():
    instruments = [make_instrument(1, REQUIRED_1M, date(2020, 1, 1), date(2026, 12, 1))]
    result = compute_coverage(
        instruments=instruments,
        today=TODAY,
        period_start=date(2020, 1, 1),
        period_end=date(2030, 1, 1),
        amount_paise=REQUIRED_1M,
        exempt=False,
        exempt_reason=None,
        expiring_window_days=60,
    )
    assert result.status == "expiring_soon"


def test_two_overlapping_fdrs_close_the_gap():
    instruments = [
        make_instrument(1, REQUIRED_1M, date(2020, 1, 1), date(2026, 12, 1)),
        make_instrument(2, REQUIRED_1M, date(2026, 11, 1), date(2030, 1, 1)),
    ]
    result = compute_coverage(
        instruments=instruments,
        today=TODAY,
        period_start=date(2020, 1, 1),
        period_end=date(2030, 1, 1),
        amount_paise=REQUIRED_1M,
        exempt=False,
        exempt_reason=None,
        expiring_window_days=60,
    )
    assert result.status == "covered"
    assert result.first_gap is None


def test_returned_instrument_excluded_from_coverage():
    instruments = [
        make_instrument(1, REQUIRED_1M, date(2020, 1, 1), date(2030, 1, 1), status="returned"),
    ]
    result = compute_coverage(
        instruments=instruments,
        today=TODAY,
        period_start=date(2020, 1, 1),
        period_end=date(2030, 1, 1),
        amount_paise=REQUIRED_1M,
        exempt=False,
        exempt_reason=None,
        expiring_window_days=60,
    )
    assert result.status == "not_covered"
    assert result.valid_paise == 0


def test_matured_instrument_excluded():
    instruments = [
        make_instrument(1, REQUIRED_1M, date(2020, 1, 1), date(2030, 1, 1), status="matured"),
    ]
    result = compute_coverage(
        instruments=instruments,
        today=TODAY,
        period_start=date(2020, 1, 1),
        period_end=date(2030, 1, 1),
        amount_paise=REQUIRED_1M,
        exempt=False,
        exempt_reason=None,
        expiring_window_days=60,
    )
    assert result.valid_paise == 0


def test_beneficiary_missing_excludes_instrument():
    instruments = [
        make_instrument(
            1, REQUIRED_1M, date(2020, 1, 1), date(2030, 1, 1), beneficiary="Some Other College"
        ),
    ]
    result = compute_coverage(
        instruments=instruments,
        today=TODAY,
        period_start=date(2020, 1, 1),
        period_end=date(2030, 1, 1),
        amount_paise=REQUIRED_1M,
        exempt=False,
        exempt_reason=None,
        expiring_window_days=60,
    )
    assert result.status == "not_covered"


def test_shortfall_today_already_in_gap():
    instruments = [make_instrument(1, REQUIRED_1M // 2, date(2020, 1, 1), date(2030, 1, 1))]
    result = compute_coverage(
        instruments=instruments,
        today=TODAY,
        period_start=date(2020, 1, 1),
        period_end=date(2030, 1, 1),
        amount_paise=REQUIRED_1M,
        exempt=False,
        exempt_reason=None,
        expiring_window_days=60,
    )
    assert result.status == "shortfall"
    assert result.first_gap.start == TODAY


def test_boundary_issue_date_counts():
    instruments = [make_instrument(1, REQUIRED_1M, TODAY, date(2030, 1, 1))]
    result = compute_coverage(
        instruments=instruments,
        today=TODAY,
        period_start=date(2020, 1, 1),
        period_end=date(2030, 1, 1),
        amount_paise=REQUIRED_1M,
        exempt=False,
        exempt_reason=None,
        expiring_window_days=60,
    )
    assert result.valid_paise == REQUIRED_1M


def test_boundary_maturity_date_excludes():
    instruments = [make_instrument(1, REQUIRED_1M, date(2020, 1, 1), TODAY)]
    result = compute_coverage(
        instruments=instruments,
        today=TODAY,
        period_start=date(2020, 1, 1),
        period_end=date(2030, 1, 1),
        amount_paise=REQUIRED_1M,
        exempt=False,
        exempt_reason=None,
        expiring_window_days=60,
    )
    assert result.valid_paise == 0

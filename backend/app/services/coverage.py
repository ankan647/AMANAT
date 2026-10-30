"""Coverage Health: is enough valid deposit held, today and on every future date? (spec 5.2, 5.4)"""

from dataclasses import dataclass, field
from datetime import date, timedelta

from app.db.enums import VALID_INSTRUMENT_STATUSES, CoverageStatus
from app.db.models import Instrument

BENEFICIARY_AICTE_TOKENS = ("aicte", "all india council for technical education")
BENEFICIARY_GOI_TOKEN = "government of india"


def beneficiary_ok(text: str | None) -> bool:
    if not text:
        return False
    lowered = text.lower()
    has_aicte = any(token in lowered for token in BENEFICIARY_AICTE_TOKENS)
    has_goi = BENEFICIARY_GOI_TOKEN in lowered
    return has_aicte and has_goi


def instrument_counts_on(instrument: Instrument, d: date) -> bool:
    if instrument.status not in {s.value for s in VALID_INSTRUMENT_STATUSES}:
        return False
    if not (instrument.issue_date <= d < instrument.maturity_date):
        return False
    return beneficiary_ok(instrument.beneficiary)


def valid_amount_on(instruments: list[Instrument], d: date) -> int:
    return sum(i.amount_paise for i in instruments if instrument_counts_on(i, d))


def contributing_instruments_on(instruments: list[Instrument], d: date) -> list[Instrument]:
    return [i for i in instruments if instrument_counts_on(i, d)]


@dataclass
class Gap:
    start: date
    end: date

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    def as_dict(self) -> dict:
        return {"start": self.start.isoformat(), "end": self.end.isoformat(), "days": self.days}


@dataclass
class CoverageResult:
    status: str
    required_paise: int
    valid_paise: int
    gaps: list[Gap] = field(default_factory=list)
    exempt_reason: str | None = None

    @property
    def first_gap(self) -> Gap | None:
        return self.gaps[0] if self.gaps else None

    def as_dict(self) -> dict:
        first = self.first_gap
        return {
            "status": self.status,
            "required_paise": self.required_paise,
            "valid_paise": self.valid_paise,
            "gap_start": first.start.isoformat() if first else None,
            "gap_end": first.end.isoformat() if first else None,
            "gap_days": first.days if first else None,
            "exempt_reason": self.exempt_reason,
        }


def _required_amount_on(d: date, period_start: date, period_end: date, amount_paise: int) -> int:
    return amount_paise if period_start <= d < period_end else 0


def find_gaps(
    instruments: list[Instrument],
    today: date,
    period_start: date,
    period_end: date,
    amount_paise: int,
) -> list[Gap]:
    """Gaps in [today, period_end) where valid(d) < required(d)."""
    if period_end <= today:
        return []

    change_points: set[date] = {today}
    for instrument in instruments:
        if today < instrument.issue_date < period_end:
            change_points.add(instrument.issue_date)
        if today < instrument.maturity_date < period_end:
            change_points.add(instrument.maturity_date)
    change_points.add(period_end)
    points = sorted(p for p in change_points if today <= p <= period_end)

    gaps: list[Gap] = []
    open_gap_start: date | None = None
    for i in range(len(points) - 1):
        seg_start = points[i]
        required = _required_amount_on(seg_start, period_start, period_end, amount_paise)
        valid = valid_amount_on(instruments, seg_start)
        is_gap = valid < required
        if is_gap and open_gap_start is None:
            open_gap_start = seg_start
        elif not is_gap and open_gap_start is not None:
            gaps.append(Gap(start=open_gap_start, end=seg_start - timedelta(days=1)))
            open_gap_start = None
    if open_gap_start is not None:
        gaps.append(Gap(start=open_gap_start, end=period_end - timedelta(days=1)))
    return gaps


def compute_coverage(
    *,
    instruments: list[Instrument],
    today: date,
    period_start: date,
    period_end: date,
    amount_paise: int,
    exempt: bool,
    exempt_reason: str | None,
    expiring_window_days: int,
) -> CoverageResult:
    if exempt:
        valid_today = valid_amount_on(instruments, today)
        return CoverageResult(
            status=CoverageStatus.exempt.value,
            required_paise=0,
            valid_paise=valid_today,
            gaps=[],
            exempt_reason=exempt_reason,
        )

    required_today = _required_amount_on(today, period_start, period_end, amount_paise)
    valid_today = valid_amount_on(instruments, today)
    gaps = find_gaps(instruments, today, period_start, period_end, amount_paise)

    if required_today > 0 and valid_today == 0:
        status = CoverageStatus.not_covered.value
    elif valid_today < required_today:
        status = CoverageStatus.shortfall.value
    else:
        future_gaps = [g for g in gaps if g.start > today]
        if not future_gaps:
            status = CoverageStatus.covered.value
        else:
            days_until = (future_gaps[0].start - today).days
            status = (
                CoverageStatus.expiring_soon.value
                if days_until <= expiring_window_days
                else CoverageStatus.shortfall.value
            )

    return CoverageResult(
        status=status,
        required_paise=required_today,
        valid_paise=valid_today,
        gaps=gaps,
        exempt_reason=None,
    )

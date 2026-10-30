"""Priority matrix (5.6) and dashboard summary aggregation, built from per-institution rows."""

from dataclasses import dataclass

from app.db.enums import CoverageStatus, MatrixKey

MATRIX_LABELS = {
    MatrixKey.routine_monitoring.value: "Routine monitoring",
    MatrixKey.verify_next.value: "Verify next",
    MatrixKey.send_renewal_notice.value: "Send renewal notice",
    MatrixKey.urgent_both.value: "Urgent: both problems",
}

COVERAGE_BAD_STATUSES = {
    CoverageStatus.shortfall.value,
    CoverageStatus.expiring_soon.value,
    CoverageStatus.not_covered.value,
}


def matrix_cell_for(status: str, confidence_pct: int | None, threshold: int) -> str | None:
    """Returns the MatrixKey, or None for exempt institutions (excluded from the matrix)."""
    if status == CoverageStatus.exempt.value or confidence_pct is None:
        return None
    high = confidence_pct >= threshold
    if status == CoverageStatus.covered.value:
        return MatrixKey.routine_monitoring.value if high else MatrixKey.verify_next.value
    # shortfall / expiring_soon / not_covered
    return MatrixKey.send_renewal_notice.value if high else MatrixKey.urgent_both.value


NEXT_ACTION_LABELS = {
    **MATRIX_LABELS,
    None: "No action: exempt",
}


@dataclass
class InstitutionRow:
    institution_id: int
    status: str
    confidence_pct: int | None
    required_paise: int
    valid_paise: int
    bank_confirmed_paise: int
    open_flags: int = 0
    overdue_bank_requests: int = 0
    next_maturity_within_90d: bool = False
    releases_pending: int = 0


def build_priority_matrix(rows: list[InstitutionRow], threshold: int) -> dict:
    cells: dict[str, list[int]] = {k: [] for k in MATRIX_LABELS}
    for row in rows:
        key = matrix_cell_for(row.status, row.confidence_pct, threshold)
        if key is not None:
            cells[key].append(row.institution_id)
    return {
        "cells": [
            {
                "key": key,
                "label": MATRIX_LABELS[key],
                "count": len(ids),
                "institution_ids": ids,
            }
            for key, ids in cells.items()
        ],
        "threshold": threshold,
    }


def build_summary(rows: list[InstitutionRow], as_of: str) -> dict:
    by_status: dict[str, int] = {s.value: 0 for s in CoverageStatus}
    required_paise = 0
    valid_paise = 0
    bank_confirmed_paise = 0
    open_flags = 0
    overdue_bank_requests = 0
    maturities_next_90d = 0
    releases_pending = 0

    for row in rows:
        by_status[row.status] = by_status.get(row.status, 0) + 1
        required_paise += row.required_paise
        valid_paise += row.valid_paise
        bank_confirmed_paise += row.bank_confirmed_paise
        open_flags += row.open_flags
        overdue_bank_requests += row.overdue_bank_requests
        if row.next_maturity_within_90d:
            maturities_next_90d += 1
        releases_pending += row.releases_pending

    confirmed_pct = round(bank_confirmed_paise / valid_paise * 100) if valid_paise else 0

    return {
        "as_of": as_of,
        "institutions_total": len(rows),
        "by_status": by_status,
        "required_paise": required_paise,
        "valid_paise": valid_paise,
        "bank_confirmed_paise": bank_confirmed_paise,
        "confirmed_pct": confirmed_pct,
        "open_flags": open_flags,
        "overdue_bank_requests": overdue_bank_requests,
        "maturities_next_90d": maturities_next_90d,
        "releases_pending": releases_pending,
    }

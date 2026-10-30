"""Anomaly precision/recall over planted labels, and the five pilot KPIs (spec 5.7, 8.2)."""

from dataclasses import dataclass

from app.db.enums import FlagType


@dataclass
class FlagRow:
    instrument_id: int
    type: str
    status: str  # open|cleared|returned|referred


@dataclass
class PlantedRow:
    instrument_id: int
    type: str


def compute_anomaly_metrics(flags: list[FlagRow], planted: list[PlantedRow]) -> dict:
    planted_keys = {(p.instrument_id, p.type) for p in planted}
    planted_instrument_ids = {p.instrument_id for p in planted}

    flags_on_planted_instruments = [f for f in flags if f.instrument_id in planted_instrument_ids]
    planted_detected_flags = [f for f in flags if (f.instrument_id, f.type) in planted_keys]

    overall_precision = (
        round(len(planted_detected_flags) / len(flags_on_planted_instruments), 4)
        if flags_on_planted_instruments
        else 0.0
    )

    detected_keys = {(f.instrument_id, f.type) for f in planted_detected_flags}
    overall_recall = round(len(detected_keys) / len(planted_keys), 4) if planted_keys else 0.0

    decided = [f for f in flags if f.status != "open"]
    confirmed = [f for f in decided if f.status in ("returned", "referred")]
    officer_confirmed_share = round(len(confirmed) / len(decided), 4) if decided else 0.0

    by_type = []
    for flag_type in FlagType:
        type_planted = {p.instrument_id for p in planted if p.type == flag_type.value}
        type_flags = [f for f in flags if f.type == flag_type.value]
        detected_instrument_ids = {f.instrument_id for f in type_flags if f.instrument_id in type_planted}
        false_positive_flags = [f for f in type_flags if f.instrument_id not in type_planted]

        detected = len(detected_instrument_ids)
        planted_count = len(type_planted)
        false_positives = len(false_positive_flags)
        denom = detected + false_positives
        precision = round(detected / denom, 4) if denom else (1.0 if planted_count == 0 else 0.0)
        recall = round(detected / planted_count, 4) if planted_count else None

        by_type.append(
            {
                "type": flag_type.value,
                "planted": planted_count,
                "detected": detected,
                "false_positives": false_positives,
                "precision": precision,
                "recall": recall,
            }
        )

    return {
        "overall": {
            "precision": overall_precision,
            "recall": overall_recall,
            "officer_confirmed_share": officer_confirmed_share,
        },
        "by_type": by_type,
    }


@dataclass
class KpiInputs:
    confirmed_deposit_share_pct: float
    avg_days_to_bank_confirmation: float
    flags_confirmed_share_pct: float
    maturities_handled_before_deadline_pct: float
    avg_days_to_release_decision: float


def compute_kpis(inputs: KpiInputs) -> dict:
    return {
        "confirmed_deposit_share_pct": inputs.confirmed_deposit_share_pct,
        "avg_days_to_bank_confirmation": inputs.avg_days_to_bank_confirmation,
        "flags_confirmed_share_pct": inputs.flags_confirmed_share_pct,
        "maturities_handled_before_deadline_pct": inputs.maturities_handled_before_deadline_pct,
        "avg_days_to_release_decision": inputs.avg_days_to_release_decision,
    }

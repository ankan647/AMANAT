from app.services.metrics import FlagRow, PlantedRow, compute_anomaly_metrics


def test_recall_and_precision_on_planted_data():
    planted = [
        PlantedRow(instrument_id=1, type="duplicate_fdr_number"),
        PlantedRow(instrument_id=2, type="duplicate_fdr_number"),
        PlantedRow(instrument_id=3, type="ifsc_invalid"),
    ]
    flags = [
        FlagRow(instrument_id=1, type="duplicate_fdr_number", status="returned"),
        FlagRow(instrument_id=3, type="ifsc_invalid", status="cleared"),
        FlagRow(instrument_id=99, type="lien_missing", status="open"),  # unrelated clean flag
    ]
    metrics = compute_anomaly_metrics(flags, planted)

    assert metrics["overall"]["recall"] == round(2 / 3, 4)

    dup_entry = next(e for e in metrics["by_type"] if e["type"] == "duplicate_fdr_number")
    assert dup_entry["planted"] == 2
    assert dup_entry["detected"] == 1
    assert dup_entry["recall"] == 0.5

    ifsc_entry = next(e for e in metrics["by_type"] if e["type"] == "ifsc_invalid")
    assert ifsc_entry["recall"] == 1.0


def test_officer_confirmed_share():
    planted = []
    flags = [
        FlagRow(instrument_id=1, type="lien_missing", status="returned"),
        FlagRow(instrument_id=2, type="lien_missing", status="cleared"),
        FlagRow(instrument_id=3, type="lien_missing", status="referred"),
        FlagRow(instrument_id=4, type="lien_missing", status="open"),
    ]
    metrics = compute_anomaly_metrics(flags, planted)
    # decided = 3 (returned, cleared, referred); confirmed = 2 (returned, referred)
    assert metrics["overall"]["officer_confirmed_share"] == round(2 / 3, 4)

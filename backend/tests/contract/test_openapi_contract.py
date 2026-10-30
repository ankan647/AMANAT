import json
from pathlib import Path

from app.main import app

DOCS_OPENAPI = Path(__file__).resolve().parents[2].parent / "docs" / "openapi.json"


def test_committed_openapi_matches_regenerated():
    regenerated = json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"
    committed = DOCS_OPENAPI.read_text(encoding="utf-8")
    assert regenerated == committed, (
        "docs/openapi.json is stale — run `python -m app.export_openapi` (or `make contract`) "
        "and commit the result."
    )


def test_api_contract_doc_exists():
    doc = DOCS_OPENAPI.parent / "api-contract.md"
    assert doc.exists()

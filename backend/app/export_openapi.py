"""Regenerates docs/openapi.json from the live FastAPI app (`make contract`)."""

import json
from pathlib import Path

from app.main import app

OUT_PATH = Path(__file__).resolve().parents[2] / "docs" / "openapi.json"


def main() -> None:
    schema = app.openapi()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()

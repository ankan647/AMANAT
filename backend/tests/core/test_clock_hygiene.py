"""Forbid datetime.now() / date.today() / datetime.utcnow() anywhere in app/ except clock.py."""

import re
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[2] / "app"
# security.py is exempt: JWT exp/iat are intentionally real wall-clock time (see comment there) —
# PyJWT itself validates `exp` against the real system clock, so simulated time cannot be used.
ALLOWED_FILES = {APP_DIR / "core" / "clock.py", APP_DIR / "core" / "security.py"}

FORBIDDEN_PATTERNS = [
    re.compile(r"datetime\.now\("),
    re.compile(r"\bdate\.today\("),
    re.compile(r"datetime\.utcnow\("),
]


def test_no_forbidden_time_calls_outside_clock_module():
    violations = []
    for path in APP_DIR.rglob("*.py"):
        if path.resolve() in {f.resolve() for f in ALLOWED_FILES}:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.search(text):
                violations.append(f"{path.relative_to(APP_DIR.parent)}: {pattern.pattern}")
    assert violations == [], f"Forbidden time calls found: {violations}"

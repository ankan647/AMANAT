"""Re-exports the demo holiday list; the single source of truth lives in app.core.calendar."""

from app.core.calendar import HOLIDAYS

__all__ = ["HOLIDAYS"]

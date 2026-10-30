"""Bank verification channel abstraction (spec 5.8). Only SimulatedBankScreenChannel is wired up
in this prototype — AICTE has no live bank integration. ApiChannel and SfmsChannel are stubs
showing where a real adapter would plug in.
"""

from abc import ABC, abstractmethod
from datetime import date

from app.core.calendar import add_working_days
from app.db.models import BankRequest


class BankChannel(ABC):
    @abstractmethod
    def send_request(self, req: BankRequest) -> None:
        """Dispatch the verification request to the bank."""

    @abstractmethod
    def fetch_response(self, req: BankRequest) -> dict | None:
        """Poll for a response. Returns None while still pending."""


class SimulatedBankScreenChannel(BankChannel):
    """The 'bank' is a person using the /bank portal in this demo — there is nothing to send or
    poll over the wire. `send_request` only computes the due date; responses arrive via
    `POST /bank-requests/{id}/respond`, handled directly by the bank_requests router."""

    def send_request(self, req: BankRequest) -> None:
        if req.due_date is None:
            req.due_date = add_working_days(req.sent_date, 7)

    def fetch_response(self, req: BankRequest) -> dict | None:
        if req.outcome == "pending":
            return None
        return {
            "outcome": req.outcome,
            "differing_values": req.differing_values_json,
            "remarks": req.remarks,
        }


class ApiChannel(BankChannel):
    """Stub: a real deployment would call the bank's verification API here (e.g. a core-banking
    confirmation API) instead of a human responding in a simulated screen."""

    def send_request(self, req: BankRequest) -> None:
        raise NotImplementedError(
            "ApiChannel is a placeholder for a real bank API integration; not implemented in "
            "this prototype."
        )

    def fetch_response(self, req: BankRequest) -> dict | None:
        raise NotImplementedError(
            "ApiChannel is a placeholder for a real bank API integration; not implemented in "
            "this prototype."
        )


class SfmsChannel(BankChannel):
    """Stub: a real deployment could route verification requests over SFMS (Structured
    Financial Messaging System), the RBI-operated interbank messaging network."""

    def send_request(self, req: BankRequest) -> None:
        raise NotImplementedError(
            "SfmsChannel is a placeholder for a real SFMS integration; not implemented in this "
            "prototype."
        )

    def fetch_response(self, req: BankRequest) -> dict | None:
        raise NotImplementedError(
            "SfmsChannel is a placeholder for a real SFMS integration; not implemented in this "
            "prototype."
        )


def default_due_date(sent_date: date) -> date:
    return add_working_days(sent_date, 7)

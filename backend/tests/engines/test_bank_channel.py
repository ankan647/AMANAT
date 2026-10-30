from datetime import date

import pytest

from app.services.bank_channel import ApiChannel, SfmsChannel, default_due_date


def test_default_due_date_is_7_working_days_later():
    # 2026-10-30 is a Friday
    assert default_due_date(date(2026, 10, 30)) == date(2026, 11, 10)


def test_stub_channels_raise_not_implemented():
    api = ApiChannel()
    with pytest.raises(NotImplementedError):
        api.send_request(None)
    sfms = SfmsChannel()
    with pytest.raises(NotImplementedError):
        sfms.fetch_response(None)

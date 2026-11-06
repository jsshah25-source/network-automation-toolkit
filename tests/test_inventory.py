from pathlib import Path

import pytest

from netauto import inventory
from netauto.meraki_client import MerakiClient, MerakiError, OfflineMerakiClient

DATA = Path(__file__).resolve().parents[1] / "samples" / "meraki"


@pytest.fixture
def records():
    return inventory.build_inventory(OfflineMerakiClient(DATA), "500001")


def test_inventory_joins_names_and_status(records):
    assert len(records) == 10
    ewr = next(r for r in records if r.name == "ewr-mx-01")
    assert ewr.network == "Clinic-Newark"
    assert ewr.status == "offline"


def test_health_summary_sorts_worst_network_first(records):
    health = inventory.summarize_health(records)
    assert health[0].network == "Clinic-Newark"
    assert health[0].availability_pct == pytest.approx(33.3)
    assert {h.network: h.total for h in health}["HQ-Philadelphia"] == 4


def test_firmware_drift_detected(records):
    drift = inventory.find_firmware_drift(records)
    assert drift["MS390-48"] == {"MS 16.7", "MS 16.8"}
    assert "MR46" not in drift


def test_reports_render(records):
    md = inventory.to_markdown(records)
    assert "Devices needing attention" in md
    assert "ewr-mr-exam" in md
    csv_text = inventory.to_csv(records)
    assert csv_text.splitlines()[0].startswith("network,name,serial")


def test_live_client_requires_api_key(monkeypatch):
    monkeypatch.delenv("MERAKI_API_KEY", raising=False)
    with pytest.raises(MerakiError):
        MerakiClient()


class _FakeResponse:
    def __init__(self, status, payload=None, headers=None):
        self.status_code = status
        self._payload = payload
        self.headers = headers or {}

    def json(self):
        return self._payload


class _FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.headers = {}
        self.calls = 0

    def get(self, url, timeout):
        self.calls += 1
        return self.responses.pop(0)


def test_live_client_retries_on_rate_limit(monkeypatch):
    monkeypatch.setattr("netauto.meraki_client.time.sleep", lambda s: None)
    session = _FakeSession([_FakeResponse(429, headers={"Retry-After": "1"}), _FakeResponse(200, [{"id": "1"}])])
    client = MerakiClient(api_key="test-key", session=session)
    assert client.get_organizations() == [{"id": "1"}]
    assert session.calls == 2
    assert session.headers["Authorization"] == "Bearer test-key"

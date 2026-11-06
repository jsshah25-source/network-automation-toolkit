"""Minimal client for the Cisco Meraki Dashboard API v1.

Only the read-only calls the toolkit needs are implemented. The API key is read
from the MERAKI_API_KEY environment variable and is never logged or written out.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import requests

BASE_URL = "https://api.meraki.com/api/v1"


class MerakiError(RuntimeError):
    """Raised when the Meraki API returns an error we cannot recover from."""


class MerakiClient:
    """Read-only Meraki Dashboard client with simple retry on rate limiting (HTTP 429)."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = BASE_URL,
        max_retries: int = 3,
        session: requests.Session | None = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("MERAKI_API_KEY")
        if not self.api_key:
            raise MerakiError("No API key. Set MERAKI_API_KEY or use --offline sample data.")
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json",
            }
        )

    def _get(self, path: str) -> Any:
        url = f"{self.base_url}{path}"
        for attempt in range(self.max_retries + 1):
            resp = self.session.get(url, timeout=30)
            if resp.status_code == 429 and attempt < self.max_retries:
                wait = int(resp.headers.get("Retry-After", "1"))
                time.sleep(wait)
                continue
            if resp.status_code >= 400:
                raise MerakiError(f"GET {path} failed with HTTP {resp.status_code}")
            return resp.json()
        raise MerakiError(f"GET {path} still rate limited after {self.max_retries} retries")

    def get_organizations(self) -> list[dict]:
        return self._get("/organizations")

    def get_networks(self, org_id: str) -> list[dict]:
        return self._get(f"/organizations/{org_id}/networks")

    def get_devices(self, org_id: str) -> list[dict]:
        return self._get(f"/organizations/{org_id}/devices")

    def get_device_statuses(self, org_id: str) -> list[dict]:
        return self._get(f"/organizations/{org_id}/devices/statuses")


class OfflineMerakiClient:
    """Serves the same calls from JSON files, so demos and tests need no API key or network."""

    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)

    def _load(self, name: str) -> Any:
        with open(self.data_dir / f"{name}.json", encoding="utf-8") as fh:
            return json.load(fh)

    def get_organizations(self) -> list[dict]:
        return self._load("organizations")

    def get_networks(self, org_id: str) -> list[dict]:
        return [n for n in self._load("networks") if n.get("organizationId") == org_id]

    def get_devices(self, org_id: str) -> list[dict]:
        return self._load("devices")

    def get_device_statuses(self, org_id: str) -> list[dict]:
        return self._load("device_statuses")

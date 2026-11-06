"""Build a device inventory and a per-network health summary from Meraki data."""

from __future__ import annotations

import csv
import io
from collections import Counter, defaultdict
from dataclasses import dataclass, field

STATUS_ORDER = ("online", "alerting", "offline", "dormant")


@dataclass
class DeviceRecord:
    name: str
    serial: str
    model: str
    network: str
    status: str
    lan_ip: str | None = None
    firmware: str | None = None


@dataclass
class NetworkHealth:
    network: str
    counts: Counter = field(default_factory=Counter)

    @property
    def total(self) -> int:
        return sum(self.counts.values())

    @property
    def availability_pct(self) -> float:
        if not self.total:
            return 0.0
        return round(100.0 * self.counts.get("online", 0) / self.total, 1)


def build_inventory(client, org_id: str) -> list[DeviceRecord]:
    """Join devices, statuses and network names into one flat inventory."""
    networks = {n["id"]: n["name"] for n in client.get_networks(org_id)}
    statuses = {s["serial"]: s for s in client.get_device_statuses(org_id)}

    records = []
    for dev in client.get_devices(org_id):
        status = statuses.get(dev["serial"], {})
        records.append(
            DeviceRecord(
                name=dev.get("name") or dev["serial"],
                serial=dev["serial"],
                model=dev.get("model", "unknown"),
                network=networks.get(dev.get("networkId"), "unassigned"),
                status=status.get("status", "unknown"),
                lan_ip=dev.get("lanIp") or status.get("lanIp"),
                firmware=dev.get("firmware"),
            )
        )
    return sorted(records, key=lambda r: (r.network, r.name))


def summarize_health(records: list[DeviceRecord]) -> list[NetworkHealth]:
    by_network: dict[str, NetworkHealth] = defaultdict(lambda: NetworkHealth(network=""))
    for rec in records:
        health = by_network[rec.network]
        health.network = rec.network
        health.counts[rec.status] += 1
    return sorted(by_network.values(), key=lambda h: (h.availability_pct, h.network))


def find_firmware_drift(records: list[DeviceRecord]) -> dict[str, set[str]]:
    """Return models running more than one firmware version (a common upgrade-readiness gap)."""
    versions: dict[str, set[str]] = defaultdict(set)
    for rec in records:
        if rec.firmware:
            versions[rec.model].add(rec.firmware)
    return {model: vers for model, vers in versions.items() if len(vers) > 1}


def to_csv(records: list[DeviceRecord]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["network", "name", "serial", "model", "status", "lan_ip", "firmware"])
    for r in records:
        writer.writerow([r.network, r.name, r.serial, r.model, r.status, r.lan_ip or "", r.firmware or ""])
    return buf.getvalue()


def to_markdown(records: list[DeviceRecord]) -> str:
    health = summarize_health(records)
    drift = find_firmware_drift(records)

    lines = ["# Network Health Report", "", "## Availability by network", ""]
    lines.append("| Network | Devices | " + " | ".join(s.title() for s in STATUS_ORDER) + " | Availability |")
    lines.append("|---|---|" + "---|" * len(STATUS_ORDER) + "---|")
    for h in health:
        cols = " | ".join(str(h.counts.get(s, 0)) for s in STATUS_ORDER)
        lines.append(f"| {h.network} | {h.total} | {cols} | {h.availability_pct}% |")

    problems = [r for r in records if r.status in ("offline", "alerting")]
    lines += ["", "## Devices needing attention", ""]
    if problems:
        for r in problems:
            lines.append(f"- **{r.name}** ({r.model}, {r.network}): {r.status}")
    else:
        lines.append("- None. All devices online.")

    lines += ["", "## Firmware drift", ""]
    if drift:
        for model, vers in sorted(drift.items()):
            lines.append(f"- {model}: {', '.join(sorted(vers))}")
    else:
        lines.append("- None. Each model runs a single firmware version.")
    return "\n".join(lines) + "\n"

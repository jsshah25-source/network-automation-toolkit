"""Check Cisco IOS / IOS-XE running configs against a security and operations baseline.

Each rule is a small, readable check so a network team can add its own standards
without touching the engine.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Rule:
    rule_id: str
    description: str
    severity: str  # "high", "medium" or "low"
    check: Callable[[str], bool]


@dataclass
class Finding:
    device: str
    rule_id: str
    description: str
    severity: str
    passed: bool


def _has(pattern: str) -> Callable[[str], bool]:
    regex = re.compile(pattern, re.MULTILINE)
    return lambda cfg: bool(regex.search(cfg))


def _lacks(pattern: str) -> Callable[[str], bool]:
    regex = re.compile(pattern, re.MULTILINE)
    return lambda cfg: not regex.search(cfg)


def _vty_ssh_only(cfg: str) -> bool:
    """Every 'line vty' block must restrict input to SSH."""
    blocks = re.findall(r"^line vty.*?(?=^\S|\Z)", cfg, re.MULTILINE | re.DOTALL)
    if not blocks:
        return False
    return all(re.search(r"^\s+transport input ssh\s*$", b, re.MULTILINE) for b in blocks)


BASELINE: list[Rule] = [
    Rule("SEC-01", "AAA new-model is enabled", "high", _has(r"^aaa new-model")),
    Rule("SEC-02", "VTY lines accept SSH only (no Telnet)", "high", _vty_ssh_only),
    Rule("SEC-03", "SSH version 2 is enforced", "high", _has(r"^ip ssh version 2")),
    Rule("SEC-04", "HTTP server is disabled", "medium", _lacks(r"^ip http server")),
    Rule("SEC-05", "Passwords are encrypted in the config", "medium", _has(r"^service password-encryption")),
    Rule("SEC-06", "Enable secret is used instead of enable password", "high", _lacks(r"^enable password")),
    Rule("SEC-07", "Login banner is configured", "low", _has(r"^banner (login|motd)")),
    Rule("OPS-01", "NTP server is configured", "medium", _has(r"^ntp server \S+")),
    Rule("OPS-02", "Remote syslog host is configured", "medium", _has(r"^logging host \S+")),
    Rule(
        "OPS-03",
        "SNMP community 'public' or 'private' is not used",
        "high",
        _lacks(r"^snmp-server community (public|private)\b"),
    ),
]


def hostname_of(cfg: str, fallback: str) -> str:
    match = re.search(r"^hostname (\S+)", cfg, re.MULTILINE)
    return match.group(1) if match else fallback


def check_config(cfg: str, device: str, rules: list[Rule] = BASELINE) -> list[Finding]:
    return [Finding(device, r.rule_id, r.description, r.severity, r.check(cfg)) for r in rules]


def check_files(paths: list[Path], rules: list[Rule] = BASELINE) -> list[Finding]:
    findings: list[Finding] = []
    for path in paths:
        cfg = path.read_text(encoding="utf-8")
        findings.extend(check_config(cfg, hostname_of(cfg, path.stem), rules))
    return findings


def score(findings: list[Finding]) -> dict[str, float]:
    """Percent of rules passed per device."""
    totals: dict[str, list[int]] = {}
    for f in findings:
        passed, total = totals.setdefault(f.device, [0, 0])
        totals[f.device] = [passed + int(f.passed), total + 1]
    return {dev: round(100.0 * p / t, 1) for dev, (p, t) in totals.items()}


def to_markdown(findings: list[Finding]) -> str:
    scores = score(findings)
    lines = ["# Config Compliance Report", "", "| Device | Score | Failed rules |", "|---|---|---|"]
    for dev in sorted(scores):
        failed = [f.rule_id for f in findings if f.device == dev and not f.passed]
        lines.append(f"| {dev} | {scores[dev]}% | {', '.join(failed) or 'none'} |")

    failures = [f for f in findings if not f.passed]
    lines += ["", "## Findings", ""]
    if not failures:
        lines.append("- All devices pass the baseline.")
    for f in sorted(failures, key=lambda f: (f.severity != "high", f.device, f.rule_id)):
        lines.append(f"- [{f.severity.upper()}] {f.device} {f.rule_id}: expected {f.description}")
    return "\n".join(lines) + "\n"

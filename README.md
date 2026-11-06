# Network Automation Toolkit

[![CI](https://github.com/jsshah25-source/network-automation-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/jsshah25-source/network-automation-toolkit/actions/workflows/ci.yml)
[![CodeQL](https://github.com/jsshah25-source/network-automation-toolkit/actions/workflows/codeql.yml/badge.svg)](https://github.com/jsshah25-source/network-automation-toolkit/actions/workflows/codeql.yml)

Python tools that answer two questions every network team gets asked on Monday morning:

1. **"Is the network healthy?"** Pull device inventory and status from the Cisco Meraki Dashboard API and produce a per-site availability report, a list of devices needing attention, and firmware drift across models.
2. **"Are our devices configured to standard?"** Check Cisco IOS / IOS-XE configs against a security and operations baseline (AAA, SSH-only VTY, SNMP, NTP, syslog, and more), score each device, and fail a pipeline when high-severity rules break.

Everything runs as code, is tested on every push, and is scanned for security issues, so network changes can move through the same CI/CD workflow as application code.

## Why this exists

In 30 years of enterprise networking (Merrill Lynch, Roche, Becton Dickinson's 140+ sites, and 100+ Cisco customer accounts), the same two problems came up constantly: nobody had a current picture of device health, and configuration standards drifted site by site. This toolkit turns both into repeatable, reviewable code instead of spreadsheets and manual audits.

## Quick start

```bash
git clone https://github.com/jsshah25-source/network-automation-toolkit.git
cd network-automation-toolkit
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Health report from bundled sample data (no API key needed)
netauto inventory --offline

# Compliance report for the sample configs
netauto compliance samples/configs/*.cfg

# Use it as a CI gate: exit 1 if any high-severity rule fails
netauto compliance samples/configs/*.cfg --fail-on high
```

### Against a live Meraki organization

```bash
cp .env.example .env              # add your key; .env is git-ignored
export MERAKI_API_KEY=...         # a free read-only key is available from Cisco DevNet
netauto inventory --org <org_id> -o health-report.md
netauto inventory --org <org_id> --format csv -o inventory.csv
```

The client is read-only, retries automatically on Meraki rate limits (HTTP 429), and never logs the API key.

## Sample output

```
| Network          | Devices | Online | Alerting | Offline | Availability |
|------------------|---------|--------|----------|---------|--------------|
| Clinic-Newark    | 3       | 1      | 0        | 2       | 33.3%        |
| HQ-Philadelphia  | 4       | 3      | 1        | 0       | 75.0%        |
| Branch-Allentown | 3       | 3      | 0        | 0       | 100.0%       |

Firmware drift
- MS390-48: MS 16.7, MS 16.8
- MX68: MX 17.10, MX 18.211
```

## Compliance baseline

| Rule | Check | Severity |
|---|---|---|
| SEC-01 | AAA new-model enabled | High |
| SEC-02 | Every VTY block accepts SSH only (no Telnet) | High |
| SEC-03 | SSH version 2 enforced | High |
| SEC-04 | HTTP server disabled | Medium |
| SEC-05 | service password-encryption | Medium |
| SEC-06 | enable secret, never enable password | High |
| SEC-07 | Login banner present | Low |
| OPS-01 | NTP server configured | Medium |
| OPS-02 | Remote syslog host configured | Medium |
| OPS-03 | No default SNMP communities (public/private) | High |

Rules live in `src/netauto/compliance.py` as small, readable checks, so a team can add its own standards in a few lines.

## CI/CD and security

| Workflow | What it does |
|---|---|
| **CI** (`.github/workflows/ci.yml`) | On every push and pull request: lint with ruff, run pytest with coverage on Python 3.10 and 3.12, then generate the health and compliance reports, publish them to the run summary, and keep them as build artifacts. |
| **CodeQL** (`.github/workflows/codeql.yml`) | GitHub Advanced Security code scanning for Python on every push, every pull request and weekly. |
| **Dependabot** (`.github/dependabot.yml`) | Weekly update PRs for Python packages and GitHub Actions. |
| **Secret scanning and push protection** | Enabled in repository settings, so an API key can't be committed by accident. |

See [docs/architecture.md](docs/architecture.md) for how the pieces fit together.

## Project layout

```
src/netauto/
  meraki_client.py   Read-only Meraki Dashboard API client (+ offline client for demos and tests)
  inventory.py       Inventory join, health summary, firmware drift, Markdown/CSV reports
  compliance.py      IOS config baseline rules, scoring, Markdown report
  cli.py             `netauto inventory` and `netauto compliance` commands
samples/             Sample Meraki API data and IOS configs (no real customer data)
tests/               pytest suite, no network access required
```

## Roadmap

- Catalyst Center (DNA Center) inventory and assurance health via its REST API
- Compliance rules loaded from YAML so non-developers can maintain them
- GitHub Actions job that runs compliance on configs changed in a pull request and comments the result
- AI-assisted remediation suggestions for failed rules

## Author

**Jignesh (Jay) Shah** · [LinkedIn](https://www.linkedin.com/in/jignesshah)
Enterprise networking, presales and automation. Cisco Certified Network Programmability Developer Specialist (DEVOPS), Cisco Certified AI Technical Practitioner.

## License

MIT

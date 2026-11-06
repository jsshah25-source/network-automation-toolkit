"""Command line entry point: `netauto inventory ...` and `netauto compliance ...`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from netauto import compliance, inventory
from netauto.meraki_client import MerakiClient, OfflineMerakiClient

SAMPLE_DATA = Path(__file__).resolve().parents[2] / "samples" / "meraki"


def _write(text: str, output: str | None) -> None:
    if output:
        Path(output).write_text(text, encoding="utf-8")
        print(f"Wrote {output}")
    else:
        sys.stdout.write(text)


def cmd_inventory(args: argparse.Namespace) -> int:
    client = OfflineMerakiClient(args.data_dir) if args.offline else MerakiClient()
    org_id = args.org or client.get_organizations()[0]["id"]
    records = inventory.build_inventory(client, org_id)
    text = inventory.to_csv(records) if args.format == "csv" else inventory.to_markdown(records)
    _write(text, args.output)
    return 0


def cmd_compliance(args: argparse.Namespace) -> int:
    paths = [Path(p) for p in args.configs]
    findings = compliance.check_files(paths)
    _write(compliance.to_markdown(findings), args.output)

    if args.fail_on:
        levels = {"high": {"high"}, "medium": {"high", "medium"}, "low": {"high", "medium", "low"}}[args.fail_on]
        if any(not f.passed and f.severity in levels for f in findings):
            return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="netauto", description="Network automation toolkit")
    sub = parser.add_subparsers(dest="command", required=True)

    inv = sub.add_parser("inventory", help="Meraki device inventory and health report")
    inv.add_argument("--org", help="Meraki organization ID (defaults to the first one)")
    inv.add_argument("--format", choices=["md", "csv"], default="md")
    inv.add_argument("--offline", action="store_true", help="Use bundled sample data instead of the API")
    inv.add_argument("--data-dir", default=str(SAMPLE_DATA), help="Folder of sample JSON for --offline")
    inv.add_argument("--output", "-o", help="Write to a file instead of stdout")
    inv.set_defaults(func=cmd_inventory)

    comp = sub.add_parser("compliance", help="Check IOS configs against the security baseline")
    comp.add_argument("configs", nargs="+", help="Config files to check")
    comp.add_argument(
        "--fail-on",
        choices=["high", "medium", "low"],
        help="Exit 1 if a rule at this severity or above fails",
    )
    comp.add_argument("--output", "-o", help="Write to a file instead of stdout")
    comp.set_defaults(func=cmd_compliance)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

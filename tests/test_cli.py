from pathlib import Path

from netauto.cli import main

ROOT = Path(__file__).resolve().parents[1]
CONFIGS = [str(p) for p in sorted((ROOT / "samples" / "configs").glob("*.cfg"))]


def test_inventory_offline_markdown(capsys):
    assert main(["inventory", "--offline"]) == 0
    assert "# Network Health Report" in capsys.readouterr().out


def test_inventory_offline_csv_to_file(tmp_path):
    out = tmp_path / "inventory.csv"
    assert main(["inventory", "--offline", "--format", "csv", "-o", str(out)]) == 0
    assert out.read_text().startswith("network,name,serial")


def test_compliance_reports_without_failing_by_default(capsys):
    assert main(["compliance", *CONFIGS]) == 0
    assert "branch-sw-legacy" in capsys.readouterr().out


def test_compliance_fail_on_high_returns_nonzero():
    assert main(["compliance", *CONFIGS, "--fail-on", "high"]) == 1


def test_compliance_hardened_config_passes_gate():
    hardened = [c for c in CONFIGS if c.endswith("hq-core-rtr.cfg")]
    assert main(["compliance", *hardened, "--fail-on", "low"]) == 0

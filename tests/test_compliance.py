from pathlib import Path

from netauto import compliance

SAMPLES = Path(__file__).resolve().parents[1] / "samples" / "configs"


def _by_rule(findings):
    return {f.rule_id: f.passed for f in findings}


def test_hardened_config_passes_every_rule():
    cfg = (SAMPLES / "hq-core-rtr.cfg").read_text()
    findings = compliance.check_config(cfg, "hq-core-rtr")
    assert all(f.passed for f in findings), [f.rule_id for f in findings if not f.passed]


def test_legacy_config_fails_the_expected_rules():
    cfg = (SAMPLES / "branch-sw-legacy.cfg").read_text()
    results = _by_rule(compliance.check_config(cfg, "branch-sw-legacy"))
    for rule_id in ("SEC-01", "SEC-02", "SEC-03", "SEC-04", "SEC-06", "OPS-01", "OPS-03"):
        assert results[rule_id] is False, rule_id


def test_telnet_on_any_vty_block_fails():
    cfg = "line vty 0 4\n transport input ssh\nline vty 5 15\n transport input telnet\n"
    assert _by_rule(compliance.check_config(cfg, "x"))["SEC-02"] is False


def test_hostname_falls_back_to_filename():
    assert compliance.hostname_of("no hostname here", "fallback") == "fallback"
    assert compliance.hostname_of("hostname edge-01\n", "fallback") == "edge-01"


def test_score_and_report():
    findings = compliance.check_files(sorted(SAMPLES.glob("*.cfg")))
    scores = compliance.score(findings)
    assert scores["hq-core-rtr"] == 100.0
    assert scores["branch-sw-legacy"] < 50
    report = compliance.to_markdown(findings)
    assert "# Config Compliance Report" in report
    assert "[HIGH] branch-sw-legacy SEC-02" in report

"""Feature 22: value signal from Agentic Earned Value (AEV). No network needed."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest
import yaml

import aev_value

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demo" / "lakeshore"
CFG = yaml.safe_load((ROOT / "initiatives" / "lakeshore-supplier-portal" / "config.yml").read_text())


def results(name="after"):
    return json.loads((DEMO / f"aev-{name}-revert.json").read_text())


def load_script(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_aev_is_opt_in():
    assert aev_value.aev_settings({"name": "x"})["enabled"] is False
    assert aev_value.aev_settings({"aev": None})["enabled"] is True  # bare "aev:" line
    assert aev_value.aev_settings({"aev": {"enabled": False}})["enabled"] is False
    assert aev_value.aev_settings({"aev": {"enabled": True}})["results_path"] == ".aev/aev.json"
    assert aev_value.aev_settings(CFG)["enabled"] is True


def test_parse_results_checks_schema():
    with pytest.raises(aev_value.AevError):
        aev_value.parse_results('{"schema": "something-else"}', "x")
    with pytest.raises(aev_value.AevError):
        aev_value.parse_results("not json", "x")
    assert aev_value.parse_results(json.dumps(results()), "x")["as_of"] == "2026-11-10"


def test_local_override_and_missing_file(tmp_path):
    assert aev_value.load_results(CFG, None, str(DEMO / "aev-after-revert.json"))["summary"]["cpi"] == 0.9601
    with pytest.raises(aev_value.AevError):
        aev_value.load_results(CFG, None, str(tmp_path / "missing.json"))
    assert aev_value.load_results({"name": "x"}, None) is None


def test_pods_use_program_hub_names():
    cfg = {**CFG, "pods": [{"slug": "p", "label": "POD-PORTAL", "name": "Portal Pod"}]}
    pods = {(s["pod"], s["class"]): s["cpi"] for s in aev_value.pod_slices(cfg, results())}
    assert pods[("Portal Pod", "A")] == 1.6
    assert pods[("Integrations", "A")] == 0.6  # no matching pod: AEV's team name is kept


def test_health_flips_on_stage():
    assert aev_value.value_health(results("before")) == "🟢 Green"
    assert aev_value.value_health(results("after")) == "🟡 Amber"


def test_attention_items():
    before = aev_value.attention_items(CFG, results("before"), delivery_health="🟢 Green")
    after = aev_value.attention_items(CFG, results("after"), delivery_health="🟢 Green")
    assert not any("delivery looks green" in a for a in before)
    assert "delivery looks green, but value does not" in after[0]
    assert any("Integrations**: agent-authored work has CPI 0.60" in a for a in after)
    assert any("15.9% of work marked done was taken back ($20,000" in a for a in after)
    assert any("classic EVM says CPI 1.45" in a for a in after)
    # Portal agent work is healthy, and unlinked cost is never flagged as a weak slice.
    assert not any("/ Portal" in a or "not linked" in a for a in after)


def test_dashboard_rows_and_value_page():
    rows = aev_value.dashboard_rows([{"cfg": CFG, "results": results()},
                                     {"cfg": {"name": "Other"}, "results": None}])
    text = "\n".join(rows)
    assert "| Lakeshore Supplier Quality Portal | 🟡 Amber | 0.96 | 0.88 | 15.9% | $249,962 / $240,000 | 64.4% | 2026-11-10 |" in text
    assert "| Other | ⚪ Not set up |" in text

    page = aev_value.render_value_md(CFG, results())
    assert "| Integrations | Agent-authored | 2 | $18,000 | $30,000 | 0.60 |" in page
    assert "| CPI (value per $1 spent) | 1.45 | 0.96 |" in page
    assert "lakeshore-supplier-portal-demo/issues/125) | Post nonconformance reports (NCR) to ERP | $8,000 | PR #173 reverted |" in page
    assert "AEV is not set up" in aev_value.render_value_md(CFG, None)


def test_briefing_facts_and_template():
    facts = aev_value.briefing_facts(CFG, results())
    assert "AEV CPI 0.96 (classic EVM would say 1.45)" in facts
    assert "Integrations agent-authored CPI 0.60" in facts
    assert "agent spend plus human review of it $23,400" in facts
    briefing = load_script("ai/feature-21-pm-briefing/pm-briefing.py", "pm_briefing")
    assert "**" not in briefing.template_briefing(aev_value.attention_items(CFG, results()))
    assert "No value signals" in briefing.template_briefing([])


def test_dashboard_script_offline(tmp_path, monkeypatch):
    dash = load_script("scripts/update-program-dashboard.py", "dashboard")
    (tmp_path / "initiatives").symlink_to(ROOT / "initiatives")
    (tmp_path / "program").mkdir()
    monkeypatch.setattr(dash, "ROOT", tmp_path)
    monkeypatch.setattr(aev_value, "ROOT", ROOT)
    monkeypatch.setattr(dash, "gh_search_count", lambda token, q: 0 if "label:" in q else 14)
    monkeypatch.setenv("GITHUB_TOKEN", "test")
    monkeypatch.setattr(sys, "argv", ["x", "--aev-json",
                                      f"lakeshore-supplier-portal={DEMO / 'aev-after-revert.json'}"])
    dash.main()
    text = (tmp_path / "program" / "PROGRAM-DASHBOARD.md").read_text()
    assert "| Delivery Health | Value Health |" in text
    assert "| 14 | 0 | 🟢 Green | 🟡 Amber | 2026-12-22 |" in text
    assert "## Value (Agentic Earned Value)" in text
    assert "delivery looks green, but value does not" in text
    # The example initiative has no aev block, so it gets no value row.
    assert "| Example Initiative | ⚪" not in text

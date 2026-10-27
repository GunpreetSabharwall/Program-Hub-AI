"""Hub mode: Program Hub runs AEV on each initiative's source repo (scripts/run_aev.py)."""

import importlib.util
import os
from pathlib import Path

import pytest
import yaml

import aev_value
import run_aev

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((ROOT / "initiatives" / "lakeshore-supplier-portal" / "config.yml").read_text())
AEV_HOME = Path(os.environ.get("AEV_HOME", ROOT.parent / "agentic-earned-value"))


def test_settings_come_from_the_initiative_config():
    s = run_aev.aev_settings_for(CFG)
    assert s["start_date"] == "2026-09-29" and s["end_date"] == "2026-12-22"  # week_start + 12 weeks
    assert s["teams"] == {"Portal": "pod-portal", "Integrations": "pod-integrations"}  # from pods
    assert s["budget_at_completion"] == 240000 and s["agent_label"] == "aev-agent"


def test_explicit_dates_win_and_missing_fields_are_named():
    cfg = {**CFG, "aev": {**CFG["aev"], "start_date": "2026-10-01", "end_date": "2026-11-01"}}
    assert run_aev.aev_settings_for(cfg)["end_date"] == "2026-11-01"
    with pytest.raises(run_aev.SetupError, match="hourly_rate"):
        run_aev.aev_settings_for({**CFG, "aev": {"budget_at_completion": 1, "value_per_point": 1}})
    with pytest.raises(run_aev.SetupError, match="week_start"):
        run_aev.aev_settings_for({**CFG, "week_start": None})


def test_command_reads_any_repo_and_writes_into_the_initiative_folder():
    cmd = run_aev.aev_command(CFG, Path("s.yml"), "2026-11-10")
    folder = str(aev_value.hub_folder(CFG))
    assert cmd[cmd.index("--repo") + 1] == "GunpreetSabharwall/lakeshore-supplier-portal-demo"
    assert cmd[cmd.index("--hours") + 1] == folder + "/hours.csv"
    assert cmd[cmd.index("--json") + 1] == folder + "/aev.json"
    assert cmd[-2:] == ["--as-of", "2026-11-10"]


def test_modes():
    assert aev_value.aev_settings(CFG)["mode"] == "hub"
    assert aev_value.aev_settings({"aev": {"mode": "repo"}})["mode"] == "repo"
    with pytest.raises(aev_value.AevError):
        aev_value.aev_settings({"aev": {"mode": "elsewhere"}})


@pytest.mark.skipif(not (AEV_HOME / "src" / "aev").is_dir(), reason="needs an AEV checkout (AEV_HOME)")
def test_end_to_end_offline(tmp_path, monkeypatch):
    """run_aev writes aev.json into the initiative folder; aev_value then reads it with no override."""
    monkeypatch.setattr(aev_value, "ROOT", tmp_path)
    (tmp_path / "initiatives" / "lakeshore-supplier-portal" / "aev").mkdir(parents=True)
    src = ROOT / "initiatives" / "lakeshore-supplier-portal"
    (tmp_path / "initiatives" / "lakeshore-supplier-portal" / "config.yml").write_text((src / "config.yml").read_text())
    for name in ("hours.csv", "agent-costs.csv"):
        (tmp_path / "initiatives" / "lakeshore-supplier-portal" / "aev" / name).write_text((src / "aev" / name).read_text())
    monkeypatch.setenv("AEV_HOME", str(AEV_HOME))
    snapshot = AEV_HOME / "examples" / "lakeshore" / "issues-after-revert.json"
    assert run_aev.main(["--only", "lakeshore-supplier-portal", "--as-of", "2026-11-10",
                         "--snapshot", str(snapshot)]) == 0
    results = aev_value.load_results(CFG, None)
    assert results["summary"]["cpi"] == 0.9601 and results["summary"]["health"] == "yellow"

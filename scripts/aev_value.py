#!/usr/bin/env python3
"""Value signal from Agentic Earned Value (AEV): Feature 22.

Program Hub reports *delivery* health (issues, blockers, risks). AEV
(https://github.com/GunpreetSabharwall/agentic-earned-value) measures
*value*: what the work earned for what it cost, including agent spend,
human review of agent work, and work taken back when it did not stick.

The two stay separate products. They meet in one file: AEV writes
`.aev/aev.json` (schema "aev-results/1") into the initiative's source repo,
and this module reads it to:

* add a Value Health column and a value section to PROGRAM-DASHBOARD.md
* write initiatives/<slug>/VALUE.md, broken down by this initiative's pods
* raise "PM attention" items when value and delivery disagree

Run on its own to write every VALUE.md:

    python scripts/aev_value.py                       # reads aev.json from each source repo
    python scripts/aev_value.py --aev-json SLUG=PATH  # read a local file instead (offline)

Turn it on for an initiative by adding an `aev:` block to its config.yml
(initiatives without one are left alone). The defaults are shown:

    aev:
      enabled: true
      results_path: .aev/aev.json   # path inside source_repo
      results_file: ""              # local file, relative to this repo; used instead of GitHub
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

import yaml

ROOT = Path(__file__).parent.parent
SCHEMA = "aev-results/1"
AEV_URL = "https://github.com/GunpreetSabharwall/agentic-earned-value"

# AEV's own health colours (from its CPI badge), in Program Hub's wording.
HEALTH = {
    "brightgreen": "🟢 Green",
    "yellow": "🟡 Amber",
    "red": "🔴 Red",
    "lightgrey": "⚪ n/a",
}

# Thresholds for PM attention items. Kept here so they are easy to find and tune.
WEAK_SLICE_CPI = 0.80        # a pod x authorship slice earning under $0.80 per $1
WEAK_SLICE_MIN_SHARE = 0.05  # ...and holding at least 5% of the initiative's cost
REWORK_ALERT = 0.10          # more than 10% of "done" work taken back
CLASSIC_GAP_ALERT = 0.30     # classic EVM CPI overstates AEV CPI by this much or more

CLASS_NAMES = {"A": "agent-authored", "H": "human-authored", "M": "mixed",
               "Unassigned": "not linked to an issue"}


class AevError(RuntimeError):
    pass


# --- Loading ------------------------------------------------------------------

def aev_settings(cfg: dict) -> dict:
    if "aev" not in cfg:
        raw = {"enabled": False}
    else:
        raw = cfg.get("aev") or {}  # a bare "aev:" line turns it on with the defaults
    return {
        "enabled": bool(raw.get("enabled", True)),
        "results_path": raw.get("results_path") or ".aev/aev.json",
        "results_file": raw.get("results_file") or "",
    }


def parse_results(text: str, source: str) -> dict:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AevError(f"{source} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise AevError(f"{source} is not an AEV results file (expected schema '{SCHEMA}').")
    return data


def github_get(url: str, token: Optional[str], params: Optional[dict] = None):
    """GET from the GitHub API, retrying without the token if it is refused.

    The built-in GITHUB_TOKEN of a workflow only reaches its own repository,
    so reading another (public) repository with it returns 404. Public
    repositories can be read without a token, so retry anonymously. For
    private source repositories set the OCTO_PAT secret.
    """
    import requests

    headers = {"Accept": "application/vnd.github+json"}
    if token:
        resp = requests.get(url, headers={**headers, "Authorization": f"token {token}"},
                            params=params, timeout=30)
        if resp.status_code not in (401, 403, 404):
            return resp
    return requests.get(url, headers=headers, params=params, timeout=30)


def fetch_results(repo: str, path: str, token: Optional[str]) -> Optional[dict]:
    """Read aev.json from a GitHub repo. Returns None if the file does not exist yet."""
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    resp = github_get(url, token)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    content = base64.b64decode(resp.json()["content"]).decode("utf-8")
    return parse_results(content, f"{repo}/{path}")


def load_results(cfg: dict, token: Optional[str], override: Optional[str] = None) -> Optional[dict]:
    """AEV results for one initiative, or None if AEV is not set up for it."""
    settings = aev_settings(cfg)
    if not settings["enabled"]:
        return None
    local = override or settings["results_file"]
    if local:
        path = Path(local)
        if not path.is_absolute():
            path = ROOT / path
        if not path.exists():
            raise AevError(f"AEV results file not found: {path}")
        return parse_results(path.read_text(encoding="utf-8"), str(path))
    return fetch_results(cfg["source_repo"], settings["results_path"], token)


# --- Formatting -----------------------------------------------------------------

def money(value: Optional[float], symbol: str = "$") -> str:
    if value is None:
        return "n/a"
    sign = "-" if value < 0 else ""
    return f"{sign}{symbol}{abs(value):,.0f}"


def ratio(value: Optional[float]) -> str:
    return "n/a" if value is None else f"{value:.2f}"


def percent(value: Optional[float]) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def value_health(results: dict) -> str:
    return HEALTH.get(results["summary"].get("health"), HEALTH["lightgrey"])


def symbol_of(results: dict) -> str:
    return results.get("config", {}).get("currency_symbol", "$")


# --- Pods -------------------------------------------------------------------------

def pod_slices(cfg: dict, results: dict) -> List[dict]:
    """AEV results per pod and authorship class, using this initiative's pod names.

    AEV's teams are matched to Program Hub pods by label (any case). Teams
    with no matching pod keep AEV's name.
    """
    pods = {str(p.get("label", "")).lower(): p.get("name") or p.get("slug") for p in cfg.get("pods") or []}
    slices = []
    for team in results.get("by_team") or []:
        pod = pods.get(str(team.get("label") or "").lower()) or team["name"]
        for cls, c in team["by_class"].items():
            if c["ev"] or c["ac"] or c["items_accepted"]:
                slices.append({"pod": pod, "class": cls, **c})
    return slices


# --- Attention ------------------------------------------------------------------------

def attention_items(cfg: dict, results: dict, delivery_health: Optional[str] = None) -> List[str]:
    """Plain-English items for the PM Attention section, most important first."""
    s = symbol_of(results)
    name = cfg["name"]
    summary, classic, ind = results["summary"], results["classic"], results["indicators"]
    items = []

    cpi = summary.get("cpi")
    health = value_health(results)
    if delivery_health and "Green" in delivery_health and "Green" not in health and cpi is not None:
        items.append(
            f"**{name}**: delivery looks green, but value does not: earning {s}{cpi:.2f} "
            f"for every {s}1 spent (AEV CPI {ratio(cpi)})."
        )
    elif cpi is not None and cpi < 1.0:
        items.append(f"**{name}**: earning {s}{cpi:.2f} for every {s}1 spent (AEV CPI {ratio(cpi)}).")

    total_ac = summary.get("ac") or 0
    for sl in sorted(pod_slices(cfg, results), key=lambda x: (x["cpi"] if x["cpi"] is not None else 99)):
        if sl["class"] == "Unassigned" or sl["cpi"] is None:
            continue
        if sl["cpi"] < WEAK_SLICE_CPI and total_ac and sl["ac"] / total_ac >= WEAK_SLICE_MIN_SHARE:
            items.append(
                f"**{name} / {sl['pod']}**: {CLASS_NAMES.get(sl['class'], sl['class'])} work has CPI "
                f"{ratio(sl['cpi'])} ({money(sl['ev'], s)} earned for {money(sl['ac'], s)} spent)."
            )

    rework = ind.get("rework_rate")
    if rework is not None and rework > REWORK_ALERT:
        items.append(
            f"**{name}**: {percent(rework)} of work marked done was taken back "
            f"({money(results['value']['clawback'], s)} reverted or reopened)."
        )

    if classic.get("cpi") is not None and cpi is not None and classic["cpi"] - cpi >= CLASSIC_GAP_ALERT:
        items.append(
            f"**{name}**: classic EVM says CPI {ratio(classic['cpi'])}; with agent cost, review and "
            f"rework it is {ratio(cpi)}. Do not report the classic number."
        )
    return items


# --- Dashboard section ---------------------------------------------------------------

def dashboard_rows(entries: List[dict]) -> List[str]:
    """Rows for the 'Value (Agentic Earned Value)' table. entries: [{cfg, results}]."""
    lines = [
        "## Value (Agentic Earned Value)",
        "",
        f"From each initiative's `.aev/aev.json`, written by [AEV]({AEV_URL}). "
        "Delivery health counts blockers; value health asks what the work earned for what it cost.",
        "",
        "| Initiative | Value Health | CPI | SPI | Rework | Forecast (EAC) / Budget | Agent PRs | AEV as of |",
        "|------------|--------------|-----|-----|--------|-------------------------|-----------|-----------|",
    ]
    for e in entries:
        cfg, r = e["cfg"], e["results"]
        if r is None:
            lines.append(f"| {cfg['name']} | ⚪ Not set up | | | | | | |")
            continue
        s = symbol_of(r)
        sm, ind, act = r["summary"], r["indicators"], r["activity"]
        lines.append(
            f"| {cfg['name']} | {value_health(r)} | {ratio(sm['cpi'])} | {ratio(sm['spi'])} | "
            f"{percent(ind['rework_rate'])} | {money(sm['eac'], s)} / {money(sm['bac'], s)} | "
            f"{percent(act['agent_pr_share'])} | {r['as_of']} |"
        )
    lines.append("")
    return lines


# --- VALUE.md --------------------------------------------------------------------------

def render_value_md(cfg: dict, results: Optional[dict]) -> str:
    slug = cfg["slug"]
    lines = [
        "<!-- AUTO-REGENERATED by scripts/aev_value.py — do not edit data rows manually -->",
        "",
        f"# Value — {cfg['name']}",
        "",
    ]
    if results is None:
        lines += [
            "AEV is not set up for this initiative yet. Add the AEV GitHub Action to "
            f"`{cfg['source_repo']}` ({AEV_URL}); this page fills in after its first run.",
            "",
        ]
        return "\n".join(lines)

    s = symbol_of(results)
    sm, cl, ind, act, val = (results[k] for k in ("summary", "classic", "indicators", "activity", "value"))
    lines += [
        f"**Value health:** {value_health(results)} &nbsp;|&nbsp; **AEV as of:** {results['as_of']} "
        f"&nbsp;|&nbsp; **Source:** `{cfg['source_repo']}`",
        "",
        f"> {sm['what_this_means']}",
        "",
        "## Summary",
        "",
        "| Indicator | Classic EVM | AEV |",
        "|-----------|-------------|-----|",
        f"| Earned value | {money(cl['ev'], s)} | {money(sm['ev'], s)} |",
        f"| Actual cost | {money(cl['ac'], s)} | {money(sm['ac'], s)} |",
        f"| CPI (value per {s}1 spent) | {ratio(cl['cpi'])} | {ratio(sm['cpi'])} |",
        f"| SPI (schedule) | {ratio(cl['spi'])} | {ratio(sm['spi'])} |",
        f"| Forecast total cost | {money(cl['eac'], s)} | {money(sm['eac'], s)} |",
        "",
        f"Budget {money(sm['bac'], s)}; planned value to date {money(sm['pv'], s)}.",
        "",
        "## AI activity vs. value",
        "",
        "| Activity | | Value | |",
        "|----------|--|-------|--|",
        f"| Merged PRs | {act['merged_prs']} | Issues done that stuck | {act['items_that_stuck']} |",
        f"| Share by agents | {percent(act['agent_pr_share'])} | Rework Rate | {percent(ind['rework_rate'])} |",
        f"| Issues closed | {act['items_closed']} | Work taken back | {money(val['clawback'], s)} |",
        f"| Agent spend | {money(act['agent_spend'], s)} | Agent spend + human review | "
        f"{money(results['cost']['ac_agent'] + results['cost']['ac_review'], s)} |",
        "",
    ]

    slices = pod_slices(cfg, results)
    if slices:
        lines += [
            "## By pod and who did the work",
            "",
            "| Pod | Work | Items earning value | EV | AC | CPI |",
            "|-----|------|---------------------|----|----|-----|",
        ]
        for sl in slices:
            lines.append(
                f"| {sl['pod']} | {CLASS_NAMES.get(sl['class'], sl['class']).capitalize()} | "
                f"{sl['items_accepted']} | {money(sl['ev'], s)} | {money(sl['ac'], s)} | {ratio(sl['cpi'])} |"
            )
        lines.append("")

    clawed = [i for i in results.get("items") or [] if i.get("clawback")]
    lines += ["## Work taken back", ""]
    if clawed:
        repo = cfg["source_repo"]
        lines += ["| # | Title | Value | Reason |", "|---|-------|-------|--------|"]
        for item in clawed:
            reasons = "; ".join(e["reason"] for e in item["episodes"] if e.get("reason"))
            title = item["title"].replace("|", "\\|")
            lines.append(f"| [{item['number']}](https://github.com/{repo}/issues/{item['number']}) | "
                         f"{title} | {money(item['clawback'], s)} | {reasons} |")
    else:
        lines.append("None.")
    lines.append("")

    attention = attention_items(cfg, results)
    lines += ["## PM attention", ""]
    lines += [f"- {a}" for a in attention] or ["None at this time."]
    lines += ["", f"Full report: `AEV-REPORT.md` in `{cfg['source_repo']}`. Initiative: [{slug}](config.yml).", ""]
    return "\n".join(lines)


# --- Briefing facts ------------------------------------------------------------------------

def briefing_facts(cfg: dict, results: dict) -> str:
    """A short, exact summary of one initiative's value, for the AI PM briefing."""
    s = symbol_of(results)
    sm, cl, ind, act = results["summary"], results["classic"], results["indicators"], results["activity"]
    lines = [
        f"{cfg['name']} (AEV as of {results['as_of']}): value health {value_health(results)}; "
        f"AEV CPI {ratio(sm['cpi'])} (classic EVM would say {ratio(cl['cpi'])}); SPI {ratio(sm['spi'])}; "
        f"forecast total cost {money(sm['eac'], s)} against a budget of {money(sm['bac'], s)}.",
        f"Activity: {act['merged_prs']} merged PRs, {percent(act['agent_pr_share'])} by agents, "
        f"agent spend {money(act['agent_spend'], s)}; agent spend plus human review of it "
        f"{money(results['cost']['ac_agent'] + results['cost']['ac_review'], s)}.",
        f"Rework: {percent(ind['rework_rate'])} of done work taken back "
        f"({money(results['value']['clawback'], s)}).",
    ]
    slices = [sl for sl in pod_slices(cfg, results) if sl["class"] != "Unassigned"]
    if slices:
        lines.append("By pod: " + "; ".join(
            f"{sl['pod']} {CLASS_NAMES.get(sl['class'], sl['class'])} CPI {ratio(sl['cpi'])}" for sl in slices) + ".")
    return "\n".join(lines)


def load_all(overrides: Dict[str, str], token: Optional[str]) -> List[dict]:
    """[{cfg, results}] for every initiative with AEV turned on. Raises AevError on bad files."""
    out = []
    for cfg in load_configs():
        if aev_settings(cfg)["enabled"]:
            out.append({"cfg": cfg, "results": load_results(cfg, token, overrides.get(cfg["slug"]))})
    return out


# --- CLI ---------------------------------------------------------------------------------

def parse_overrides(pairs: List[str]) -> Dict[str, str]:
    out = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise SystemExit(f"--aev-json expects SLUG=PATH, got {pair!r}")
        slug, path = pair.split("=", 1)
        out[slug.strip()] = path.strip()
    return out


def load_configs() -> List[dict]:
    return [yaml.safe_load(p.read_text()) for p in sorted((ROOT / "initiatives").glob("*/config.yml"))]


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Write initiatives/<slug>/VALUE.md from AEV results.")
    parser.add_argument("--aev-json", action="append", metavar="SLUG=PATH",
                        help="Read this initiative's AEV results from a local file (repeatable).")
    args = parser.parse_args(argv)
    overrides = parse_overrides(args.aev_json)
    token = os.environ.get("OCTO_PAT") or os.environ.get("GITHUB_TOKEN")

    failed = False
    for cfg in load_configs():
        if not aev_settings(cfg)["enabled"]:
            continue
        try:
            results = load_results(cfg, token, overrides.get(cfg["slug"]))
        except Exception as exc:  # fail loud, but finish the other initiatives
            print(f"{cfg['slug']}: could not read AEV results: {exc}", file=sys.stderr)
            failed = True
            continue
        if not aev_settings(cfg)["enabled"]:
            continue
        out = ROOT / "initiatives" / cfg["slug"] / "VALUE.md"
        out.write_text(render_value_md(cfg, results), encoding="utf-8")
        print(f"Wrote {out}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()

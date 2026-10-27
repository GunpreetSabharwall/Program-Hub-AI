#!/usr/bin/env python3
"""Read all initiative configs; write PROGRAM-DASHBOARD.md.

Delivery health comes from GitHub Issues (blockers). Value health comes from
each initiative's AEV results (.aev/aev.json); see scripts/aev_value.py.

    python scripts/update-program-dashboard.py
    python scripts/update-program-dashboard.py --aev-json SLUG=PATH   # local AEV file
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml
import requests

import aev_value

ROOT = Path(__file__).parent.parent


def gh_headers(token: str) -> dict:
    return {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}


def gh_open_counts(token: str, repo: str, blocked_label: str) -> tuple:
    """(open issues, open blocked issues) in one repo.

    Uses the issues list rather than the search API: search refuses the
    workflow's built-in GITHUB_TOKEN for other repositories, while the issues
    of a public repo can always be listed (see aev_value.github_get).
    """
    open_count = blocked_count = 0
    url = f"https://api.github.com/repos/{repo}/issues"
    params = {"state": "open", "per_page": 100, "page": 1}
    blocked = blocked_label.lower()
    while True:
        resp = aev_value.github_get(url, token, params=params)
        resp.raise_for_status()
        page = resp.json()
        for issue in page:
            if "pull_request" in issue:  # the issues list also returns PRs
                continue
            open_count += 1
            if any(label["name"].lower() == blocked for label in issue.get("labels", [])):
                blocked_count += 1
        if len(page) < params["per_page"]:
            return open_count, blocked_count
        params["page"] += 1


def week_number(week_start) -> tuple:
    if isinstance(week_start, str):
        week_start = datetime.fromisoformat(week_start).date()
    today = datetime.now(timezone.utc).date()
    delta = (today - week_start).days
    return max(1, delta // 7 + 1)


def health_signal(blocked_count: int) -> str:
    if blocked_count == 0:
        return "🟢 Green"
    elif blocked_count <= 2:
        return "🟡 Amber"
    else:
        return "🔴 Red"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--aev-json", action="append", metavar="SLUG=PATH",
                        help="Read this initiative's AEV results from a local file (repeatable).")
    args = parser.parse_args()
    aev_overrides = aev_value.parse_overrides(args.aev_json)

    token = os.environ.get("OCTO_PAT") or os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("Error: OCTO_PAT or GITHUB_TOKEN env var required.")

    initiatives_dir = ROOT / "initiatives"
    configs = []
    for config_path in sorted(initiatives_dir.glob("*/config.yml")):
        cfg = yaml.safe_load(config_path.read_text())
        configs.append(cfg)

    as_of = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    rows = []
    attention = []
    value_entries = []

    for cfg in configs:
        repo = cfg["source_repo"]
        blocked_label = cfg["labels"]["blocked"]
        slug = cfg["slug"]

        print(f"Querying {repo}...")
        try:
            open_count, blocked_count = gh_open_counts(token, repo, blocked_label)
        except requests.RequestException as exc:
            # Fail loud, but do not let one unreachable repo stop the whole dashboard.
            print(f"::warning::Could not query {repo}: {exc}")
            open_count = blocked_count = "?"
            attention.append(f"- **{cfg['name']}**: could not read `{repo}` from GitHub ({exc.__class__.__name__}); check `source_repo` in its config.")

        week_start = cfg.get("week_start", "")
        duration = cfg.get("duration_weeks", 8)
        current_week = week_number(str(week_start)) if week_start else "?"
        health = health_signal(blocked_count) if blocked_count != "?" else "⚠️ Unknown"
        showcase = cfg.get("showcase_date", "TBD")

        try:
            aev_results = aev_value.load_results(cfg, token, aev_overrides.get(slug))
        except Exception as exc:
            aev_results = None
            attention.append(f"- **{cfg['name']}**: AEV results could not be read ({exc})")
        if aev_value.aev_settings(cfg)["enabled"]:
            value_entries.append({"cfg": cfg, "results": aev_results})

        rows.append({
            "name": cfg["name"],
            "owner": cfg["owner"],
            "week": f"{current_week} / {duration}",
            "open": open_count,
            "blocked": blocked_count,
            "health": health,
            "showcase": showcase,
            "slug": slug,
            "value": aev_value.value_health(aev_results) if aev_results else "—",
        })

        if blocked_count != "?" and blocked_count > 0:
            attention.append(f"- **{cfg['name']}**: {blocked_count} open blocker(s) — see [risk register](../initiatives/{slug}/RISK-REGISTER.md)")
        if aev_results:
            for item in aev_value.attention_items(cfg, aev_results, delivery_health=health):
                attention.append(f"- {item} See [value](../initiatives/{slug}/VALUE.md).")

    # Preserve PM narrative
    dash_path = ROOT / "program" / "PROGRAM-DASHBOARD.md"
    pm_narrative = "*No narrative added yet.*"
    if dash_path.exists():
        text = dash_path.read_text()
        marker = "<!-- PM: add cross-initiative narrative here"
        if marker in text:
            parts = text.split(marker)
            if len(parts) > 1:
                after = parts[1]
                end = after.find("-->")
                if end != -1:
                    narrative_block = after[end + 3:].strip()
                    if narrative_block:
                        pm_narrative = narrative_block

    lines = [
        "<!-- AUTO-REGENERATED by scripts/update-program-dashboard.py — do not edit data rows manually -->",
        "",
        "# Program Dashboard",
        "",
        f"**As of:** {as_of}",
        "",
        "## Initiative Health",
        "",
        "| Initiative | Owner | Week | Open Issues | Blockers | Delivery Health | Value Health | Showcase Date |",
        "|------------|-------|------|-------------|----------|-----------------|--------------|---------------|",
    ]

    for row in rows:
        lines.append(
            f"| {row['name']} | {row['owner']} | {row['week']} | "
            f"{row['open']} | {row['blocked']} | {row['health']} | {row['value']} | {row['showcase']} |"
        )

    if value_entries:
        lines += [""] + aev_value.dashboard_rows(value_entries)[:-1]

    lines += ["", "## PM Attention Required", ""]
    if attention:
        lines.extend(attention)
    else:
        lines.append("None at this time.")

    lines += [
        "",
        "---",
        "<!-- PM: add cross-initiative narrative here — preserved on regeneration -->",
        pm_narrative,
    ]

    dash_path.write_text("\n".join(lines) + "\n")
    print(f"Wrote {dash_path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Read PROGRAM-RISKS.md; write 4-sentence executive summary of top 3 risks."""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import anthropic

ROOT = Path(__file__).parent.parent.parent
MODEL = "claude-sonnet-4-6"


def main() -> None:
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if not anthropic_key:
        sys.exit("Error: ANTHROPIC_API_KEY required.")

    risks_path = ROOT / "program" / "PROGRAM-RISKS.md"
    if not risks_path.exists():
        sys.exit("PROGRAM-RISKS.md not found.")

    risks_text = risks_path.read_text()
    client = anthropic.Anthropic(api_key=anthropic_key)

    message = client.messages.create(
        model=MODEL,
        max_tokens=400,
        messages=[
            {
                "role": "user",
                "content": (
                    f"You are a program manager writing an executive summary.\n\n"
                    f"Below is a program risk table:\n\n{risks_text}\n\n"
                    f"Write exactly 4 sentences summarising the top 3 risks for a VP-level reader. "
                    f"Focus on business impact and urgency, not technical detail. "
                    f"Name the specific initiatives and issues involved. "
                    f"Output only the 4 sentences, no headings or bullet points."
                ),
            }
        ],
    )

    summary = message.content[0].text.strip()
    as_of = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    pm_digest = (
        f"## PM Digest\n\n"
        f"*AI-generated executive summary — {as_of}*\n\n"
        f"{summary}\n\n"
        f"---\n\n"
    )

    # Prepend PM Digest above the risk table, replacing existing one if present
    marker = "## PM Digest"
    if marker in risks_text:
        start = risks_text.index(marker)
        # Find the cross-initiative table section
        table_start = risks_text.find("## Cross-Initiative Risk Table")
        if table_start != -1:
            risks_text = risks_text[:start] + pm_digest + risks_text[table_start:]
        else:
            risks_text = risks_text[:start] + pm_digest
    else:
        # Insert after the header block
        table_marker = "## Cross-Initiative Risk Table"
        if table_marker in risks_text:
            idx = risks_text.index(table_marker)
            risks_text = risks_text[:idx] + pm_digest + risks_text[idx:]
        else:
            risks_text = pm_digest + risks_text

    risks_path.write_text(risks_text)
    print(f"Wrote PM Digest to {risks_path}")


if __name__ == "__main__":
    main()

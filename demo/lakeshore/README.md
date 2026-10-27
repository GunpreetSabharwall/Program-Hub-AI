# Lakeshore demo: AEV results

Copies of the AEV results for the Lakeshore Components demo program (fictional),
made by `examples/lakeshore/build_dataset.py` in
[agentic-earned-value](https://github.com/GunpreetSabharwall/agentic-earned-value).

| File | What it is |
|------|------------|
| `aev-before-revert.json` | Week 6 (10 Nov 2026), before the agent PR for issue #125 is reverted on stage |
| `aev-after-revert.json`  | The same week, after the revert |

Use them to run Program Hub's value features offline:

```bash
python scripts/aev_value.py --aev-json lakeshore-supplier-portal=demo/lakeshore/aev-after-revert.json
python ai/feature-21-pm-briefing/pm-briefing.py --print --no-ai \
  --aev-json lakeshore-supplier-portal=demo/lakeshore/aev-after-revert.json
```

"""Judge-configuration check (amendment A9): does grammar-constrained decoding
suppress gpt-oss reasoning and collapse Completeness labels?

    vendor/deer-flow-1x/.venv/bin/python experiments/judge_config_check.py

Runs only the Completeness call on two baseline reports under three judge
settings and writes analysis/judge_config_check.json. Nothing here feeds a replay
comparison; the chosen setting is then fixed for every evaluation.
"""

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from boundary_probe.boundary import load_run  # noqa: E402
from boundary_probe.evaluate import Judge, completeness  # noqa: E402
from boundary_probe.settings import ANALYSIS_DIR, RUNS_DIR, load_config, load_queries  # noqa: E402

RUNS = ["q01-r02-20260930T201622", "q01-r03-20260930T204051"]
SETTINGS = {
    "format+think_low": {"structured_output": True, "think": "low"},
    "free+think_low": {"structured_output": False, "think": "low"},
    "free+think_medium": {"structured_output": False, "think": "medium"},
}

cfg0, queries = load_config(), load_queries()
out = []
for name, overrides in SETTINGS.items():
    cfg = copy.deepcopy(cfg0)
    cfg["judge"].update(overrides)
    for rid in RUNS:
        run = load_run(RUNS_DIR / rid)
        judge = Judge(cfg)
        res = completeness(judge, run["report"], queries[run["manifest"]["query_id"]])
        row = {"setting": name, "run_id": rid, "labels": {x["id"]: x["label"] for x in res["labels"]},
               "unverified_quotes": [x["id"] for x in res["labels"] if not x["quote_verified"]],
               "score": res["score"], "score_lenient": res["score_lenient"], "usage": judge.usage}
        out.append(row)
        print(json.dumps({k: row[k] for k in ("setting", "run_id", "labels", "unverified_quotes", "score")}),
              judge.usage, flush=True)
(ANALYSIS_DIR / "judge_config_check.json").write_text(json.dumps(out, indent=1))

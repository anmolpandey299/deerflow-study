"""Test-retest of the P3 judge on unchanged reports.

    vendor/deer-flow-1x/.venv/bin/python experiments/judge_retest.py

The three probe reports were each scored twice with identical inputs and settings
(A9): once as the probe set's "original" (analysis/probes/<run>/original.json) and
once as the run's baseline (analysis/evals/<run>/baseline.json). Any difference is
judge noise. Writes analysis/judge_retest.json.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
rows = []
for d in sorted((ROOT / "analysis" / "probes").glob("q*")):
    a_path, b_path = d / "original.json", ROOT / "analysis" / "evals" / d.name / "baseline.json"
    if not (a_path.exists() and b_path.exists()):
        continue
    a, b = json.loads(a_path.read_text())["p3"], json.loads(b_path.read_text())
    if a.get("judge_settings") != b.get("judge_settings") or a["report_sha256"] != b["report_sha256"]:
        rows.append({"run_id": d.name, "comparable": False})
        continue
    la = {x["id"]: x["label"] for x in a["comp"]["labels"]}
    lb = {x["id"]: x["label"] for x in b["comp"]["labels"]}
    qa = {c["report_quote"] for c in a["fact_claims"]["claims"]}
    qb = {c["report_quote"] for c in b["fact_claims"]["claims"]}
    rows.append({
        "run_id": d.name, "comparable": True,
        "fmt": [a["fmt"]["score"], b["fmt"]["score"]],
        "comp": [a["comp"]["score"], b["comp"]["score"]],
        "comp_labels_agree": sum(la[k] == lb.get(k) for k in la), "comp_labels_n": len(la),
        "comp_label_changes": {k: [la[k], lb.get(k)] for k in la if la[k] != lb.get(k)},
        "fact_b": [a["fact_claims"]["score"], b["fact_claims"]["score"]],
        "fact_b_counts": [f"{a['fact_claims']['supported']}/{a['fact_claims']['claims_checked']}",
                          f"{b['fact_claims']['supported']}/{b['fact_claims']['claims_checked']}"],
        "checked_claims_in_common": len(qa & qb), "checked_claims": [len(qa), len(qb)],
    })
    print(rows[-1])
(ROOT / "analysis" / "judge_retest.json").write_text(json.dumps(rows, indent=1))

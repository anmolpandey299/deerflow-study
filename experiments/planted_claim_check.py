"""Does P3's verification step catch the planted D2/D2b claims when it is given them? (protocol A15)

    vendor/deer-flow-1x/.venv/bin/python experiments/planted_claim_check.py

For each D2/D2b probe variant, the report line containing the planted text is passed,
alone, to P3's unchanged verification call with the run's full evidence pool, formatted
exactly as in boundary_probe.evaluate.factuality. This separates extraction misses
(the planted claim was never selected) from verification misses.
Writes analysis/probes/planted_claim_check.json.
"""

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from boundary_probe.boundary import load_run  # noqa: E402
from boundary_probe.evaluate import VERIFY_SCHEMA, VERIFY_SYSTEM, Judge, quote_found  # noqa: E402
from boundary_probe.evidence import segments  # noqa: E402
from boundary_probe.settings import ANALYSIS_DIR, RUNS_DIR, load_config  # noqa: E402

ORIGINALS = "--originals" in sys.argv  # A15 addendum: verify each D2b's unswapped sentence as a control
cfg = load_config()
judge = Judge(cfg, cfg["judge"]["model"])
spec = yaml.safe_load((ANALYSIS_DIR / "probes" / "spec.yaml").read_text())
rows = []
for item in spec["reports"]:
    run = load_run(RUNS_DIR / item["run_id"])
    segs = {f"E{k}": s for k, s in enumerate(segments(run))}
    evidence = "\n\n".join(f"[{k}] {s.get('title') or ''} ({s.get('url') or ''})\n{s['text']}"
                           for k, s in segs.items())
    for d in item["defects"]:
        if d["kind"] not in (("D2b",) if ORIGINALS else ("D2", "D2b")):
            continue
        text = run["report"] if ORIGINALS else \
            (ANALYSIS_DIR / "probes" / item["run_id"] / f"{d['name']}.md").read_text()
        marker = d["old"] if ORIGINALS else d["new"]
        line = next(ln for ln in text.splitlines() if marker in ln)
        # the sentence carrying the planted (or, with --originals, the original) text
        sentence = next((x for x in re.split(r"(?<=[.!?])\s+", line) if marker.strip() in x), line)
        claim = re.sub(r"^\s*([-*+]|\d+\.)\s+", "", sentence).replace("**", "").strip()
        out = judge(VERIFY_SYSTEM, f"Evidence passages:\n{evidence}\n\nClaims:\n0. {claim}", VERIFY_SCHEMA, "verify")
        v = (out.get("verdicts") or [{}])[0]
        seg = segs.get((v.get("evidence_id") or "").strip("[]"))
        rows.append({"run_id": item["run_id"], "variant": d["name"], "kind": d["kind"], "claim": claim,
                     "label": v.get("label"), "evidence_id": v.get("evidence_id"), "quote": v.get("quote"),
                     "quote_verified": bool(seg) and quote_found(v.get("quote") or "", seg["text"]),
                     "evidence_url": seg.get("url") if seg else None})
        print(rows[-1], flush=True)
out_path = ANALYSIS_DIR / "probes" / "planted_claim_check.json"
if ORIGINALS:  # keep the planted rows; add the controls
    prev = json.loads(out_path.read_text())
    prev["originals"] = {"judge_usage": judge.usage, "rows": rows}
    out_path.write_text(json.dumps(prev, indent=1, ensure_ascii=False))
else:
    out_path.write_text(json.dumps({"judge_model": judge.model, "judge_usage": judge.usage, "rows": rows},
                                   indent=1, ensure_ascii=False))

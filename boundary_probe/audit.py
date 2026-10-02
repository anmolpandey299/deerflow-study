"""Blinded claim-audit packets.

    python -m boundary_probe.audit build <spec.yaml>     # writes analysis/audit/packets/*.md + key
    python -m boundary_probe.audit export <dir>          # one isolated directory per auditor
    python -m boundary_probe.audit score                 # joins returned labels with the key and P3

Each packet holds one report under a random id, the query, and the exact recorded
passages for every source the report cites (by URL). Nothing in a packet names
the run, case, condition or seed; the key lives in analysis/audit/key.json and is
not given to the auditor. The auditor is an AI assistant, not a human annotator.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import yaml

from .boundary import load_run
from .evidence import normalize_url, segments, urls_in
from .settings import ANALYSIS_DIR, RUNS_DIR, load_queries

AUDIT_DIR = ANALYSIS_DIR / "audit"
INSTRUCTIONS = """# Audit instructions (read first)

For each packet: read the report, then list its 5 most central factual claims (prefer
numbers, comparisons and attributions). For each claim give:
  label: SUPPORTED (a listed passage explicitly states it, including numbers and the
         attribution), UNSUPPORTED (no listed passage states it), CONTRADICTED (a passage
         states something incompatible), MISATTRIBUTED (a passage states it, but the report
         attributes it to a different source)
  passage_id: the passage you relied on (or none)
Use only the passages in the packet, never outside knowledge. Return JSON:
{"<packet_id>": {"claims": [{"claim": "...", "label": "...", "passage_id": "..."}],
                 "target_fact": "STATED_CORRECTLY | STATED_INCORRECTLY | NOT_STATED | n/a"}}
"""


def _packet(report: str, run: dict, query_text: str, target_fact: str | None) -> str:
    cited = {normalize_url(u) for u in urls_in(report)}
    segs = [s for s in segments(run) if s.get("url") and normalize_url(s["url"]) in cited]
    passages = "\n\n".join(f"[P{i}] {s.get('title') or ''} — {s['url']}\n{s['text']}" for i, s in enumerate(segs))
    tf = f"\n## Target fact to check\n\n{target_fact}\n" if target_fact else ""
    return (f"## Query\n\n{query_text}\n{tf}\n## Report\n\n{report}\n\n"
            f"## Passages retrieved by the system for the sources this report cites\n\n"
            f"{passages or '(the report cites no retrieved source)'}\n")


def build(spec_path: str) -> None:
    spec = yaml.safe_load(Path(spec_path).read_text())
    queries = load_queries()
    rng = random.Random(spec.get("seed", 20260930))
    items = []
    for it in spec["items"]:
        run = load_run(RUNS_DIR / it["run_id"])
        if it.get("replay"):
            rec = json.loads((RUNS_DIR / it["run_id"] / "replays" / it["replay"]).read_text())
            report = rec["content"]
        else:
            report = run["report"]
        items.append((it, run, report))
    rng.shuffle(items)
    (AUDIT_DIR / "packets").mkdir(parents=True, exist_ok=True)
    (AUDIT_DIR / "packets" / "INSTRUCTIONS.md").write_text(INSTRUCTIONS)
    key = {}
    for it, run, report in items:
        pid = f"P{rng.randrange(16**6):06x}"
        q = queries[run["manifest"]["query_id"]]["text"]
        (AUDIT_DIR / "packets" / f"{pid}.md").write_text(_packet(report, run, q, it.get("target_fact")))
        key[pid] = it
    (AUDIT_DIR / "key.json").write_text(json.dumps(key, indent=1))
    print(f"{len(key)} packets written; key kept separately")


def export(dest: str, overlap: int = 3) -> None:
    """Copy packets (never the key) into one isolated directory per auditor.

    Two auditors; `overlap` packets are given to both, to measure agreement between auditors.
    """
    import shutil
    pids = sorted(p.stem for p in (AUDIT_DIR / "packets").glob("P*.md"))
    half = (len(pids) + overlap) // 2
    assignment = {"auditor1": pids[:half], "auditor2": pids[len(pids) - half:]}
    for name, ids in assignment.items():
        d = Path(dest) / name
        d.mkdir(parents=True, exist_ok=True)
        shutil.copy(AUDIT_DIR / "packets" / "INSTRUCTIONS.md", d / "INSTRUCTIONS.md")
        for pid in ids:
            shutil.copy(AUDIT_DIR / "packets" / f"{pid}.md", d / f"{pid}.md")
        print(f"{name}: {len(ids)} packets -> {d}")
    (AUDIT_DIR / "assignment.json").write_text(json.dumps(assignment, indent=1))


def _p3(item: dict) -> dict:
    """P3 claim-support labels for the same report, if the judge phase has scored it."""
    base = ANALYSIS_DIR / "evals" / item["run_id"]
    path = base / item["replay"] if item.get("replay") else base / "baseline.json"
    fc = json.loads(path.read_text()).get("fact_claims") if path.exists() else None
    if not fc:
        return {}
    return {"p3_fact_b": fc["score"], "p3_checked": fc["claims_checked"],
            "p3_supported": fc["supported"], "p3_contradicted": fc["contradicted"]}


def _uses_restored_fact(item: dict) -> bool | None:
    from .replay_analysis import uses_fact
    if not (item.get("replay") or "").startswith("c"):
        return None
    case = yaml.safe_load((ANALYSIS_DIR / "cases" / f"{item['replay'].split('/')[0]}.yaml").read_text())
    rep = json.loads((RUNS_DIR / item["run_id"] / "replays" / item["replay"]).read_text())
    rule = case["repair"]["usage_detect"]
    return uses_fact(rep["content"], rule["anchor"], rule["any_of"])


def _spearman(x: list[float], y: list[float]) -> float | None:
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2
            i = j + 1
        return r
    if len(x) < 3:
        return None
    rx, ry = ranks(x), ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den if den else None


def score() -> None:
    from collections import Counter
    key = json.loads((AUDIT_DIR / "key.json").read_text())
    rows = []
    for f in sorted(AUDIT_DIR.glob("labels*.json")):  # one file per auditor
        for pid, lab in json.loads(f.read_text()).items():
            claims = lab.get("claims", [])
            counts = Counter(c["label"] for c in claims)
            rows.append({"packet": pid, "auditor": f.stem, **key[pid], "n_claims": len(claims),
                         "counts": dict(counts),
                         "audit_supported_share": counts.get("SUPPORTED", 0) / len(claims) if claims else None,
                         "target_fact": lab.get("target_fact"),
                         "target_fact_evidence": lab.get("target_fact_evidence"),
                         "detector_uses_restored_fact": _uses_restored_fact(key[pid]), **_p3(key[pid])})
    by_pid: dict[str, list[dict]] = {}
    for r in rows:
        by_pid.setdefault(r["packet"], []).append(r)
    overlap = {pid: [(r["auditor"], r["target_fact"], r["counts"]) for r in rs]
               for pid, rs in by_pid.items() if len(rs) > 1}
    paired = [r for r in rows if r.get("p3_fact_b") is not None and r["audit_supported_share"] is not None]
    h1 = [r for r in rows if r["detector_uses_restored_fact"] is not None]
    summary = {
        "packets_labelled": len(by_pid), "labels": len(rows),
        "claim_label_totals": dict(sum((Counter(r["counts"]) for r in rows), Counter())),
        "auditor_overlap": overlap,
        "audit_vs_p3": {"n": len(paired),
                        "spearman_supported_share_vs_p3_fact_b": _spearman(
                            [r["audit_supported_share"] for r in paired], [r["p3_fact_b"] for r in paired]),
                        "mean_audit_supported_share": (sum(r["audit_supported_share"] for r in paired) / len(paired))
                        if paired else None,
                        "mean_p3_fact_b": (sum(r["p3_fact_b"] for r in paired) / len(paired)) if paired else None},
        "target_fact_vs_detector": [{"packet": r["packet"], "auditor": r["auditor"], "replay": r.get("replay"),
                                     "audit": r["target_fact"], "detector": r["detector_uses_restored_fact"]}
                                    for r in h1],
    }
    (AUDIT_DIR / "unblinded.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    {"build": lambda: build(sys.argv[2]), "score": score,
     "export": lambda: export(sys.argv[2])}[sys.argv[1]]()

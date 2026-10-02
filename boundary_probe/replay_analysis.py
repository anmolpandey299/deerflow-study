"""Per-case replay analysis with the pre-registered decision rules applied mechanically.

    python -m boundary_probe.replay_analysis      # -> analysis/replays.json, analysis/replays.md

H1 cases (protocol §5): u_X = share of samples in condition X whose body text uses the
restored fact (citation-list lines excluded). Evidence-specific effect iff
u_B >= 2/3 and max(u_A, u_C) <= 1/3; reporter insensitivity iff u_B <= 1/3.

Probe E cases (amendments A7/A8, EXPLORATORY): counts of ungrounded report items unique
to the target observation, and of reporter-originated ungrounded items, per condition.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from statistics import mean
from typing import Any

import yaml

from .boundary import load_run
from .evaluate import format_checks
from .evidence import checkable_items, evidence_pool_text, item_present, segments, url_provenance
from .settings import ANALYSIS_DIR, RUNS_DIR, load_config
from .tables import rating_cells

CITATION_LINE = re.compile(r"^\s*([-*+]|\d+\.)?\s*(\[\[?\d+\]?\]\(#[^)]*\)\s*)?\*{0,2}\[[^\]]+\]\(https?://[^)]+\)\*{0,2}\s*$")


def body_sentences(report: str) -> list[str]:
    lines = [ln for ln in report.splitlines() if not CITATION_LINE.match(ln)]
    return [s for s in re.split(r"(?<=[.!?])\s+|\n+", "\n".join(lines)) if s.strip()]


def uses_fact(report: str, anchor: str, any_of: list[str]) -> bool:
    return any(anchor.lower() in s.lower() and any(a.lower() in s.lower() for a in any_of)
               for s in body_sentences(report))


def _samples(case_id: str, run_id: str) -> dict[str, list[dict[str, Any]]]:
    by: dict[str, list[dict[str, Any]]] = {}
    for f in sorted((RUNS_DIR / run_id / "replays" / case_id).glob("*-s*.json")):
        rec = json.loads(f.read_text())
        ev = ANALYSIS_DIR / "evals" / run_id / case_id / f.name
        rec["eval"] = json.loads(ev.read_text()) if ev.exists() else None
        by.setdefault(rec["condition"], []).append(rec)
    return by


def _judge_cols(rec: dict[str, Any]) -> dict[str, Any]:
    ev = rec.get("eval") or {}
    if "comp" not in ev:
        return {}
    return {"COMP": ev["comp"]["score"], "FACTb": ev["fact_claims"]["score"],
            "unsupported": ev["fact_claims"]["unsupported"],
            "req_labels": {x["id"]: x["label"] for x in ev["comp"]["labels"]}}


def analyse_h1(case: dict[str, Any]) -> dict[str, Any]:
    run = load_run(RUNS_DIR / case["run_id"])
    rule = case["repair"]["usage_detect"]
    rows = {}
    for cond, recs in _samples(case["case_id"], case["run_id"]).items():
        rows[cond] = [{"seed": r["seed"], "chars": len(r["content"]),
                       "uses_restored_fact": uses_fact(r["content"], rule["anchor"], rule["any_of"]),
                       "fmt": format_checks(r["content"])["score"],
                       "unretrieved_urls": len(url_provenance(r["content"], run)["fabricated_urls"]),
                       "reproduces_original": r.get("reproduces_original_report"),
                       "wall_s": r["wall_s"], "completion_tokens": (r.get("usage") or {}).get("completion_tokens"),
                       **_judge_cols(r)} for r in recs]
    seeds = lambda c: [x for x in rows.get(c, []) if x["reproduces_original"] is None]  # noqa: E731
    u = {c: (mean(x["uses_restored_fact"] for x in seeds(c)) if seeds(c) else None) for c in rows}
    n_seeds = len(load_config()["replay"]["seeds"])
    verdict = "incomplete (fewer than all seeds per condition)"
    if all(len(seeds(c)) == n_seeds for c in "ABC"):
        if u["B"] >= 2 / 3 and max(u["A"], u["C"]) <= 1 / 3:
            verdict = "evidence-specific effect"
        elif u["B"] <= 1 / 3:
            verdict = "reporter insensitivity"
        else:
            verdict = "inconclusive under the pre-registered rule"
    baseline_uses = uses_fact(run["report"], rule["anchor"], rule["any_of"])
    return {"case_id": case["case_id"], "kind": "H1", "run_id": case["run_id"], "usage_rate": u,
            "verdict": verdict, "baseline_report_uses_fact": baseline_uses, "samples": rows}


def analyse_e(case: dict[str, Any]) -> dict[str, Any]:
    run = load_run(RUNS_DIR / case["run_id"])
    obs = run["final_state"]["observations"]
    pool = evidence_pool_text(run)
    t = case["target_step"]
    unique = [i for i in checkable_items(obs[t])
              if not item_present(i, pool) and not any(item_present(i, o) for k, o in enumerate(obs) if k != t)]

    def reporter_originated(text: str) -> list[str]:
        return [i for i in checkable_items(text) if not item_present(i, pool)
                and not any(item_present(i, o) for o in obs)]

    rows = {}
    for cond, recs in _samples(case["case_id"], case["run_id"]).items():
        rows[cond] = [{"seed": r["seed"], "chars": len(r["content"]),
                       "target_unique_items_in_report": sum(item_present(i, r["content"]) for i in unique),
                       "reporter_originated_items": len(reporter_originated(r["content"])),
                       "rating_cells": rating_cells(r["content"]),
                       "unretrieved_urls": len(url_provenance(r["content"], run)["fabricated_urls"]),
                       "fmt": format_checks(r["content"])["score"], "wall_s": r["wall_s"],
                       **_judge_cols(r)} for r in recs]
    metric = case["primary_metric"]
    key = "rating_cells" if metric == "rating_cells" else "target_unique_items_in_report"
    m = {c: mean(x[key] for x in v) for c, v in rows.items() if v}
    ro = {c: mean(x["reporter_originated_items"] for x in v) for c, v in rows.items() if v}
    n_seeds = len(load_config()["replay"]["seeds"])
    complete = all(len(rows.get(c, [])) == n_seeds for c in "ADG")
    verdict = None if complete else "incomplete (fewer than all seeds per condition)"
    if complete and m["A"] > 0:
        upstream = m["D"] <= 0.2 * m["A"] and m["G"] >= 0.8 * m["A"]
        confab = (ro["D"] - ro["A"] >= 3) if key != "rating_cells" else (m["D"] >= 0.5 * m["A"])
        verdict = {"upstream_attribution": upstream, "compensatory_confabulation": confab}
    return {"case_id": case["case_id"], "kind": "E (exploratory)", "run_id": case["run_id"],
            "primary_metric": key, "target_unique_items": unique, "mean_primary": m,
            "mean_reporter_originated": ro, "verdict": verdict, "samples": rows,
            "baseline": {"target_unique_items_in_report": sum(item_present(i, run["report"]) for i in unique),
                         "rating_cells": rating_cells(run["report"]),
                         "reporter_originated_items": len(reporter_originated(run["report"]))}}


def _m(rows: list[dict[str, Any]], k: str) -> str:
    v = [x[k] for x in rows if x.get(k) is not None and x.get("reproduces_original") is None]
    return f"{mean(v):.1f}" if v else "-"


def to_markdown(results: list[dict[str, Any]]) -> str:
    out = ["# Replay summary (generated by boundary_probe.replay_analysis)\n",
           "Per condition: mean over seeds 101-103 (the byte-reproduction sample is excluded).\n"]
    for r in results:
        conds = sorted(r["samples"])
        head = (f"## {r['case_id']} ({r['kind']}, run {r['run_id']})\n\n**Verdict:** {r['verdict']}")
        if r["kind"] == "H1":
            head += f" | usage rate {r['usage_rate']} | baseline uses fact: {r['baseline_report_uses_fact']}"
        else:
            head += (f" | primary metric `{r['primary_metric']}` means {r['mean_primary']} | "
                     f"reporter-originated means {r['mean_reporter_originated']} | baseline {r['baseline']}")
        cols = ["chars", "unretrieved_urls", "fmt"] + (["uses_restored_fact"] if r["kind"] == "H1" else
                                                         ["target_unique_items_in_report", "reporter_originated_items", "rating_cells"])
        table = "| condition | n | " + " | ".join(cols) + " |\n|" + "---|" * (len(cols) + 2) + "\n"
        for c in conds:
            rows = r["samples"][c]
            n = sum(1 for x in rows if x.get("reproduces_original") is None)
            table += f"| {c} | {n} | " + " | ".join(_m(rows, k) for k in cols) + " |\n"
        repro = [x["reproduces_original"] for x in r["samples"].get("A", []) if x.get("reproduces_original") is not None]
        out.append(head + "\n\n" + table + (f"\nByte-reproduction of the original report: {repro}\n" if repro else ""))
    return "\n".join(out)


def main() -> None:
    results = []
    for cf in sorted((ANALYSIS_DIR / "cases").glob("*.yaml")):
        case = yaml.safe_load(cf.read_text())
        if not (RUNS_DIR / case["run_id"] / "replays" / case["case_id"]).exists():
            continue
        results.append(analyse_h1(case) if case.get("kind", "H1") == "H1" else analyse_e(case))
    (ANALYSIS_DIR / "replays.json").write_text(json.dumps(results, indent=1, default=str))
    (ANALYSIS_DIR / "replays.md").write_text(to_markdown(results))
    for r in results:
        head = {k: v for k, v in r.items() if k not in ("samples",)}
        print(json.dumps(head, default=str))


if __name__ == "__main__":
    main()

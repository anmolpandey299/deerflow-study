"""Deliberate defects (SYNTHETIC, clearly labelled) to test whether the proxy judge
moves in the expected direction. They are applied to real baseline reports.

  D1  facet removal      delete every line / table column matching a facet pattern
  D2  irrelevant passage replace one sourced sentence's content with a sentence from an
                         irrelevant recorded passage, keeping its source mention
  D2b attribution swap   attribute a sourced claim to a different retrieved source
  D3  structure removal  strip headings, bullets and tables to plain paragraphs

    python -m boundary_probe.probes analysis/probes/spec.yaml --judge-model gpt-oss:20b

The spec (written before any probe is scored) names the exact edits per report.
Each variant is scored by P3-proxy v1 and by DeerFlow's in-repo evidence-blind
LLMJudge (src/eval/llm_judge.py) using the same judge model.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml


def remove_facet(report: str, pattern: str, strict: bool = False) -> str:
    """Delete one facet: matching lines, and table columns whose header matches.

    Default (the registered D1): a table that lost a column keeps its remaining rows even
    if other cells still mention the facet, and headings are kept. strict=True (A17)
    also blanks every remaining table cell that mentions the facet and drops matching
    headings, except the report's title line.
    """
    rx = re.compile(pattern, re.I)
    out, drop_cols = [], None
    for n, line in enumerate(report.splitlines()):
        if line.lstrip().startswith("|"):
            cells = line.strip().strip("|").split("|")
            if drop_cols is None:  # header row of a new table
                drop_cols = {i for i, c in enumerate(cells) if rx.search(c)}
            kept = [c for i, c in enumerate(cells) if i not in drop_cols]
            if strict:
                kept = [" — " if rx.search(c) else c for c in kept]
            if kept and not (len(kept) == 1 and not kept[0].strip()):
                row = "|" + "|".join(kept) + "|"
                if drop_cols or strict or not rx.search(row):
                    out.append(row)
            continue
        drop_cols = None
        heading = re.match(r"^\s*#", line)
        is_title = heading and line.lstrip().startswith("# ") and not any(x.strip() for x in report.splitlines()[:n])
        if rx.search(line) and (not heading or (strict and not is_title)):
            continue
        out.append(line)
    return "\n".join(out)


def replace_once(report: str, old: str, new: str) -> str:
    if report.count(old) != 1:
        raise ValueError(f"target must occur exactly once, found {report.count(old)}: {old[:60]!r}")
    return report.replace(old, new)


def strip_structure(report: str) -> str:
    out = []
    for line in report.splitlines():
        s = line.strip()
        if re.match(r"^\|?\s*:?-{3,}", s) or re.fullmatch(r"-{3,}", s):
            continue
        s = re.sub(r"^#{1,6}\s+", "", s)
        s = re.sub(r"^([-*+]|\d+\.)\s+", "", s)
        s = s.replace("**", "")
        if s.startswith("|"):
            s = "; ".join(c.strip() for c in s.strip("|").split("|") if c.strip())
        s = s.lstrip("> ")
        out.append(s)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out))


def apply(report: str, defect: dict[str, Any]) -> str:
    kind = defect["kind"]
    if kind == "D1":
        return remove_facet(report, defect["pattern"], strict=defect.get("strict", False))
    if kind in ("D2", "D2b"):
        return replace_once(report, defect["old"], defect["new"])
    if kind == "D3":
        return strip_structure(report)
    raise ValueError(kind)


def deerflow_judge(report: str, query: str, cfg: dict[str, Any], model: str) -> dict[str, Any]:
    """DeerFlow's own LLMJudge: evidence-blind, truncates at 15,000 chars (llm_judge.py:22)."""
    from langchain_openai import ChatOpenAI
    from src.eval.llm_judge import LLMJudge

    llm = ChatOpenAI(model=model, base_url=cfg["model"]["base_url"], api_key="ollama",
                     temperature=cfg["judge"]["temperature"], seed=cfg["judge"]["seed"])
    res = LLMJudge(llm=llm).evaluate_sync(report, query)
    return {**res.to_dict(), "parse_failed": "Unable to parse evaluation" in res.strengths}


def main() -> None:
    from . import deerflow_env
    from .boundary import load_run
    from .evaluate import EVALUATOR, Judge, evaluate
    from .settings import ANALYSIS_DIR, RUNS_DIR, load_config, load_queries

    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--judge-model", required=True)
    ap.add_argument("--in-repo-judge-model", default=None,
                    help="model tag for DeerFlow's LLMJudge (OpenAI-compatible endpoint; A12: a tag "
                         "with num_ctx pinned, since that endpoint cannot set it); default --judge-model")
    args = ap.parse_args()
    in_repo_model = args.in_repo_judge_model or args.judge_model
    cfg, queries = load_config(), load_queries()
    spec = yaml.safe_load(Path(args.spec).read_text())  # read before prepare() changes the working directory
    deerflow_env.prepare(cfg)
    out = ANALYSIS_DIR / "probes"
    out.mkdir(parents=True, exist_ok=True)
    for item in spec["reports"]:
        run = load_run(RUNS_DIR / item["run_id"])
        q = queries[run["manifest"]["query_id"]]
        variants = {"original": run["report"]}
        for d in item["defects"]:
            variants[d["name"]] = apply(run["report"], d)
        for name, text in variants.items():
            path = out / item["run_id"] / f"{name}.json"
            if path.exists():
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            (path.parent / f"{name}.md").write_text(text)
            diff = "".join(difflib.unified_diff(run["report"].splitlines(True), text.splitlines(True), n=0))
            res = {"label": "SYNTHETIC PROBE" if name != "original" else "real baseline report",
                   "run_id": item["run_id"], "variant": name, "evaluator": EVALUATOR,
                   "p3": evaluate(text, run, q, cfg, Judge(cfg, args.judge_model)),
                   "deerflow_llm_judge": deerflow_judge(text, q["text"], cfg, in_repo_model),
                   "deerflow_llm_judge_model": in_repo_model,
                   "diff_lines": diff.count("\n")}
            path.write_text(json.dumps(res, indent=1, ensure_ascii=False))
            (path.parent / f"{name}.diff").write_text(diff)
            p3 = res["p3"]
            print(item["run_id"], name, f"FMT={p3['fmt']['score']:.2f} COMP={p3['comp']['score']:.2f} "
                  f"FACTb={p3['fact_claims']['score']} DF-judge={res['deerflow_llm_judge']['scores']}",
                  flush=True)


EXPECTED = {"D1": ("comp", "COMP falls"), "D2": ("fact_b", "FACT-b falls (registered; may not, see spec)"),
            "D2b": ("fact_b", "FACT-b falls if attribution is checked"), "D3": ("fmt", "FMT falls")}


def _row(res: dict[str, Any]) -> dict[str, Any]:
    p3, dj = res["p3"], res["deerflow_llm_judge"]
    fc = p3.get("fact_claims") or {}
    return {"fmt": p3["fmt"]["score"], "comp": p3["comp"]["score"], "comp_lenient": p3["comp"]["score_lenient"],
            "fact_b": fc.get("score"), "fact_b_n": f"{fc.get('supported')}/{fc.get('claims_checked')}",
            "contradicted": fc.get("contradicted"), "url_prov": p3["fact_url"]["provenance_rate"],
            "nums_not_in_evidence": len(p3["numeric_items_not_in_evidence"]),
            "dj_weighted": dj.get("weighted_score"), "dj_factual": (dj.get("scores") or {}).get("factual_accuracy"),
            "dj_complete": (dj.get("scores") or {}).get("completeness"),
            "dj_parse_failed": dj.get("parse_failed"),
            "dj_failed": any("Evaluation failed" in w for w in dj.get("weaknesses") or [])}


def _detection(kind: str, defect: dict[str, Any], orig: dict[str, Any], var: dict[str, Any]) -> str:
    """Did P3 detect *this* defect (not merely move an axis)?

    D1: labels of the requirements the removed facet covers, original -> variant.
    D2/D2b: the planted sentence among the extracted claims, and its label.
    D3: the format score, original -> variant.
    """
    if kind == "D1":
        lab = lambda r: {x["id"]: x["label"] for x in r["p3"]["comp"]["labels"]}  # noqa: E731
        o, v = lab(orig), lab(var)
        return "; ".join(f"{rid} {o.get(rid)}->{v.get(rid)}" for rid in defect.get("affects", []))
    if kind in ("D2", "D2b"):
        planted = re.sub(r"\W+", " ", defect["new"]).lower().split()
        key = " ".join(planted[:6])
        hits = [c for c in (var["p3"].get("fact_claims") or {}).get("claims", [])
                if key in " ".join(re.sub(r"\W+", " ", c["report_quote"]).lower().split())]
        return ("planted claim not extracted" if not hits else
                "; ".join(f"extracted, labelled {c['label']}" + ("" if c["quote_verified"] else " (quote unverified)")
                          for c in hits))
    if kind == "D3":
        return f"FMT {orig['p3']['fmt']['score']:.2f}->{var['p3']['fmt']['score']:.2f}"
    return "-"


def summarize() -> None:
    """Probe table with per-defect detection -> analysis/probes/summary.{json,md}."""
    from .settings import ANALYSIS_DIR
    out = ANALYSIS_DIR / "probes"
    spec = yaml.safe_load((out / "spec.yaml").read_text())
    if (out / "spec_a17.yaml").exists():  # corrected D1 variants, reported alongside the registered ones
        extra = {it["run_id"]: it["defects"] for it in yaml.safe_load((out / "spec_a17.yaml").read_text())["reports"]}
        for it in spec["reports"]:
            it["defects"] = it["defects"] + extra.get(it["run_id"], [])
    rows, md = [], ["| report | variant | expected | FMT | COMP strict (lenient) | FACT-b (supported/checked) | "
                    "DeerFlow judge: weighted / factual / completeness | did P3 detect this defect? |",
                    "|---|---|---|---|---|---|---|---|"]
    for item in spec["reports"]:
        d = out / item["run_id"]
        if not (d / "original.json").exists():
            continue
        orig = json.loads((d / "original.json").read_text())
        defects = {x["name"]: x for x in item["defects"]}
        for name in ["original"] + list(defects):
            f = d / f"{name}.json"
            if not f.exists():
                continue
            res = json.loads(f.read_text())
            r = _row(res)
            kind = defects[name]["kind"] if name in defects else None
            expect = EXPECTED.get(kind, (None, "-"))[1]
            det = _detection(kind, defects[name], orig, res) if kind else "-"
            rows.append({"run_id": item["run_id"], "variant": name, "kind": kind, "expected": expect, **r,
                         "detection": det})
            dj = ("parse failed (all 5s)" if r["dj_parse_failed"] else "call failed (all 0s)" if r["dj_failed"]
                  else f"{r['dj_weighted']} / {r['dj_factual']} / {r['dj_complete']}")
            fb = "-" if r["fact_b"] is None else round(r["fact_b"], 2)
            md.append(f"| {item['run_id'][:7]} | {name} | {expect} | {r['fmt']:.2f} | {r['comp']:.2f} "
                      f"({r['comp_lenient']:.2f}) | {fb} ({r['fact_b_n']}) | {dj} | {det} |")
    (out / "summary.json").write_text(json.dumps(rows, indent=1))
    (out / "summary.md").write_text("# Evaluator probes (SYNTHETIC defects on real reports)\n\n" + "\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    if sys.argv[1:2] == ["summary"]:
        summarize()
    else:
        main()

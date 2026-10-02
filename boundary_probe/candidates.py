"""Automatic half of the omission-selection rule (protocol §6) and the S1 funnel.

    python -m boundary_probe.candidates runs/<run_id> [runs/<run_id> ...]

Writes analysis/candidates/<run_id>.json. Relevance to a pre-registered
requirement and the final choice are made by hand and recorded in
analysis/cases/<case_id>.yaml, never here.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from .boundary import load_run, reporter_call
from .evidence import checkable_items, evidence_pool_text, item_present, normalize_url, segments, urls_in
from .settings import ANALYSIS_DIR


def reporter_input_text(run: dict[str, Any]) -> str:
    msgs = reporter_call(run)["request"]["messages"]
    return "\n".join(m["content"] for m in msgs if isinstance(m.get("content"), str))


def funnel(run: dict[str, Any]) -> dict[str, Any]:
    segs = [s for s in segments(run) if s["role"] == "researcher"]
    obs = run["final_state"].get("observations") or []
    obs_text, rin, rep = "\n".join(obs), reporter_input_text(run), run["report"]
    items = {i for s in segs for i in checkable_items(s["text"])}
    seg_urls = {normalize_url(s["url"]) for s in segs if s.get("url")}
    norm = lambda text: {normalize_url(u) for u in urls_in(text)}  # noqa: E731
    pool_text = evidence_pool_text(run)
    report_items = checkable_items(rep)
    shown = {c["url"]: c for c in run["crawl_fulltext"]}
    l1_lost = sorted({i for c in shown.values() for i in checkable_items(c["full_markdown"])
                      if not item_present(i, c["full_markdown"][:c["shown_chars"]])})
    return {
        "researcher_segments": len(segs),
        "items": {"in_tool_outputs": len(items),
                  "in_observations": sum(item_present(i, obs_text) for i in items),
                  "in_reporter_input": sum(item_present(i, rin) for i in items),
                  "in_report": sum(item_present(i, rep) for i in items)},
        "urls": {"in_tool_outputs": len(seg_urls),
                 "in_observations": len(seg_urls & norm(obs_text)),
                 "in_reporter_input": len(seg_urls & norm(rin)),
                 "in_report": len(seg_urls & norm(rep))},
        "report_items_total": len(report_items),
        "report_items_not_in_any_tool_output": [i for i in report_items if not item_present(i, pool_text)],
        "crawl_items_cut_by_1000_char_truncation": l1_lost,
    }


def candidates(run: dict[str, Any]) -> list[dict[str, Any]]:
    obs = run["final_state"].get("observations") or []
    out = []
    for s in segments(run):
        if s["role"] != "researcher" or s["step"] is None or s["step"] >= len(obs):
            continue
        items = checkable_items(s["text"])
        missing = [i for i in items if not item_present(i, obs[s["step"]])]
        if not missing:
            continue
        out.append({**s, "items": items, "missing_from_step_observation": missing,
                    "missing_items_in_report": [i for i in missing if item_present(i, run["report"])],
                    "url_in_step_observation": bool(s.get("url")) and
                    normalize_url(s["url"]) in {normalize_url(u) for u in urls_in(obs[s["step"]])}})
    return out


_STOP = set("the a an and or of to in on for with by from at as is are was were be been this that these those "
             "it its their our we can may more most than into over under between such via using used also".split())


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9][a-z0-9\-\.%]+", text.lower()) if w not in _STOP and len(w) > 2}


def review_sheet(run: dict[str, Any]) -> str:
    """Reading aid for the manual half of the rule: each retrieved sentence with the share
    of its content words that reappear in the step's observation (low = possibly lost)."""
    obs = run["final_state"].get("observations") or []
    lines = [f"# Review sheet: {run['run_id']} (aid only; decisions go in analysis/cases)"]
    for s in segments(run):
        if s["role"] != "researcher" or s["step"] is None or s["step"] >= len(obs):
            continue
        ow = _words(obs[s["step"]])
        lines.append(f"\n## seg {s['seg_id']} (step {s['step']}, {s['tool']}) {s.get('title')}\n{s.get('url')}")
        for sent in re.split(r"(?<=[.!?])\s+|\n+", s["text"]):
            w = _words(sent)
            if len(w) >= 6:
                cov = len(w & ow) / len(w)
                lines.append(f"- [{cov:.2f}] {sent.strip()[:400]}")
    return "\n".join(lines) + "\n"


def main(paths: list[str]) -> None:
    outdir = ANALYSIS_DIR / "candidates"
    outdir.mkdir(parents=True, exist_ok=True)
    for p in paths:
        run = load_run(Path(p))
        data = {"run_id": run["run_id"], "funnel": funnel(run), "candidates": candidates(run)}
        (outdir / f"{run['run_id']}.json").write_text(json.dumps(data, indent=1, ensure_ascii=False))
        (outdir / f"{run['run_id']}.review.md").write_text(review_sheet(run))
        print(run["run_id"], json.dumps(data["funnel"]["items"]), json.dumps(data["funnel"]["urls"]),
              f"candidates={len(data['candidates'])}")


if __name__ == "__main__":
    main(sys.argv[1:])

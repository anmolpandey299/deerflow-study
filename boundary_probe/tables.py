"""Derived analysis tables from raw runs (raw files are only read).

    python -m boundary_probe.tables            # -> analysis/tables/*.csv and analysis/tables.md

Tables: per-run cost; evidence funnel; origin of report numbers that appear in no
tool output (which step type first introduced them); crawl truncation (L1); reporter
relay (post hoc: how often a number written in an observation reaches the report, split
by whether any retrieved text contains it and by DeerFlow's no-search warning).
Judge costs: per P3 call type, from every stored evaluation made with the A9 settings.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

from .boundary import load_run
from .candidates import funnel
from .evidence import checkable_items, evidence_pool_text, item_present, normalize_url, segments, url_provenance, urls_in
from .settings import ANALYSIS_DIR, RUNS_DIR

RATING_RE = re.compile(r"^\s*(very\s+)?(high|medium|moderate|low)(\s+to\s+(very\s+)?(high|medium|moderate|low))?\b", re.I)


def step_kinds(run: dict[str, Any]) -> list[str]:
    """Type of each observation, in step order."""
    kinds = []
    plan = run["final_state"].get("current_plan") or {}
    steps = plan.get("steps", []) if isinstance(plan, dict) else []
    for i, obs in enumerate(run["final_state"].get("observations") or []):
        stype = steps[i]["step_type"] if i < len(steps) else "?"
        if obs.startswith("[ERROR]"):
            kinds.append("error")
        elif obs.lstrip().startswith("<tool_call>"):
            kinds.append("researcher, summary = unparsed tool call")
        elif stype == "analysis":
            kinds.append("analyst (no tools)")
        elif "VALIDATION WARNING" in obs:
            kinds.append("researcher, no search")
        else:
            kinds.append("researcher, searched")
    return kinds


def rating_cells(report: str) -> int:
    """Qualitative rating cells (High / Medium / Low ...) inside markdown tables."""
    n = 0
    for line in report.splitlines():
        if line.strip().startswith("|") and not re.match(r"^\s*\|?\s*:?-{3,}", line.strip()):
            n += sum(1 for c in line.strip().strip("|").split("|") if RATING_RE.match(c.strip().strip("*")))
    return n


def origins(run: dict[str, Any]) -> dict[str, Any]:
    pool = evidence_pool_text(run)
    obs = run["final_state"].get("observations") or []
    kinds = step_kinds(run)
    out: dict[str, list[str]] = {}
    items = checkable_items(run["report"])
    for it in items:
        if item_present(it, pool):
            continue
        k = next((kinds[i] for i, o in enumerate(obs) if item_present(it, o)), "reporter (in no observation)")
        out.setdefault(k, []).append(it)
    return {"report_numbers": len(items),
            "numbers_in_no_tool_output": sum(len(v) for v in out.values()),
            "by_first_origin": {k: len(v) for k, v in out.items()}, "examples": out}


def url_origins(run: dict[str, Any]) -> dict[str, Any]:
    """Report URLs never retrieved, by the step type that first contains them."""
    prov = url_provenance(run["report"], run)
    obs = run["final_state"].get("observations") or []
    kinds = step_kinds(run)
    by: dict[str, int] = {}
    for u in prov["fabricated_urls"]:
        k = next((kinds[i] for i, o in enumerate(obs) if u in {normalize_url(x) for x in urls_in(o)}),
                 "reporter (in no observation)")
        by[k] = by.get(k, 0) + 1
    return {"report_urls": prov["report_urls"], "unretrieved_urls": len(prov["fabricated_urls"]), "by_origin": by}


def researcher_steps(run: dict[str, Any]) -> list[dict[str, Any]]:
    """Per researcher step: did its first model call use a tool, and did it ever search?"""
    by_ns: dict[str, list[dict[str, Any]]] = {}
    for c in run["llm_calls"]:
        if c.get("role") == "researcher" and c.get("ns"):
            by_ns.setdefault(c["ns"].split("|")[0], []).append(c)
    searches = {(t.get("ns") or "").split("|")[0] for t in run["tool_calls"] if t["tool"] == "web_search"}
    rows = []
    for k, (ns, cs) in enumerate(by_ns.items()):
        first = (cs[0].get("response") or {}).get("tool_calls") or []
        rows.append({"run_id": run["run_id"], "step": k, "model_calls": len(cs),
                     "first_call_used_tool": bool(first), "searched": ns in searches,
                     "input_had_prior_findings": "Completed Research Steps" in json.dumps(cs[0]["request"]["messages"])})
    return rows


def cost_row(run: dict[str, Any]) -> dict[str, Any]:
    m = run["manifest"]
    s = m["summary"]
    roles = s["llm_by_role"]
    tools = s["tools_by_name"]
    return {
        "run_id": run["run_id"], "query": m["query_id"], "status": m["status"], "wall_s": round(m["wall_s"], 1),
        "llm_calls": s["llm_calls"],
        **{f"calls_{r}": int(roles.get(r, {}).get("calls", 0)) for r in ("planner", "researcher", "analyst", "reporter")},
        "prompt_tokens": s["prompt_tokens"], "completion_tokens": s["completion_tokens"],
        "reporter_completion_tokens": int(roles.get("reporter", {}).get("completion_tokens", 0)),
        "peak_context": s["peak_context_tokens"],
        "search_calls": int(tools.get("web_search", {}).get("calls", 0)),
        "crawl_calls": int(tools.get("crawl_tool", {}).get("calls", 0)),
        "tool_errors": int(sum(v.get("errors", 0) for v in tools.values())),
        "step_kinds": "; ".join(step_kinds(run)),
        "report_chars": len(run["report"]),
    }


def crawl_row(run: dict[str, Any]) -> dict[str, Any]:
    c = run["crawl_fulltext"]
    full = sum(x["full_chars"] for x in c)
    shown = sum(x["shown_chars"] for x in c)
    return {"run_id": run["run_id"], "crawls_logged": len(c), "full_chars": full, "shown_chars": shown,
            "fraction_shown": round(shown / full, 3) if full else None}


WARNING = "[VALIDATION WARNING] Researcher did not use the web_search tool"


def relay_row(run: dict[str, Any]) -> dict[str, Any]:
    """Per run: distinct numbers written in observations, and how many reach the report."""
    pool, rep = evidence_pool_text(run), run["report"]
    obs = run["final_state"].get("observations") or []
    row = {"run_id": run["run_id"]}
    for kind in ("grounded", "ungrounded_in_warned_step", "ungrounded_other"):
        row[f"{kind}_in_observations"] = row[f"{kind}_in_report"] = 0
    for i in {i for o in obs for i in checkable_items(o)}:
        if item_present(i, pool):
            kind = "grounded"
        elif any(WARNING in o and item_present(i, o) for o in obs):
            kind = "ungrounded_in_warned_step"
        else:
            kind = "ungrounded_other"
        row[f"{kind}_in_observations"] += 1
        row[f"{kind}_in_report"] += item_present(i, rep)
    row["warned_observations"] = sum(WARNING in o for o in obs)
    return row


def judge_cost_rows() -> list[dict[str, Any]]:
    """Per P3 judge call type: count, mean wall time and tokens, from every stored evaluation."""
    calls: dict[str, list[dict[str, Any]]] = {}
    files = list((ANALYSIS_DIR / "evals").rglob("*.json")) + list((ANALYSIS_DIR / "probes").glob("*/*.json"))
    for f in files:
        ev = json.loads(f.read_text())
        ev = ev.get("p3", ev)  # probe files nest the P3 result
        if not ev.get("judge_settings") or ev["judge_settings"].get("think") is None:
            continue  # deterministic-only, or made before A9
        for u in ev.get("judge_usage") or []:
            calls.setdefault(u["call"], []).append(u)
    rows = []
    for name, us in sorted(calls.items()):
        mean = lambda k: round(sum(u.get(k) or 0 for u in us) / len(us), 1)  # noqa: E731
        rows.append({"call": name, "n": len(us), "mean_wall_s": mean("wall_s"),
                     "max_wall_s": round(max(u.get("wall_s") or 0 for u in us), 1),
                     "mean_prompt_tokens": mean("prompt_tokens"), "max_prompt_tokens": max(u.get("prompt_tokens") or 0 for u in us),
                     "mean_completion_tokens": mean("completion_tokens"), "mean_thinking_chars": mean("thinking_chars")})
    return rows


def baseline_score_row(run: dict[str, Any]) -> dict[str, Any] | None:
    """P3 scores of a run's baseline report next to the deterministic grounding measures."""
    f = ANALYSIS_DIR / "evals" / run["run_id"] / "baseline.json"
    ev = json.loads(f.read_text()) if f.exists() else {}
    if "comp" not in ev:
        return None
    o, u = origins(run), url_origins(run)
    fc = ev["fact_claims"]
    return {"run_id": run["run_id"], "fmt": ev["fmt"]["score"], "comp_strict": round(ev["comp"]["score"], 3),
            "comp_lenient": round(ev["comp"]["score_lenient"], 3), "fact_b": fc["score"],
            "fact_b_supported": fc["supported"], "fact_b_checked": fc["claims_checked"],
            "url_provenance": ev["fact_url"]["provenance_rate"],
            "report_numbers": o["report_numbers"], "numbers_in_no_tool_output": o["numbers_in_no_tool_output"],
            "report_urls": u["report_urls"], "unretrieved_urls": u["unretrieved_urls"]}


def main() -> None:
    out = ANALYSIS_DIR / "tables"
    out.mkdir(parents=True, exist_ok=True)
    runs = []
    for d in sorted(RUNS_DIR.iterdir()):
        if not (d / "raw" / "manifest.json").exists():
            continue
        run = load_run(d)
        run["excluded"] = (d / "EXCLUDED.txt").exists()
        run["outage_flag"] = (d / "FLAG_OUTAGE_AFFECTED.txt").exists()
        runs.append(run)
    completed = [r for r in runs if r["manifest"]["status"] == "completed" and not r["excluded"]]
    tables = {
        "costs": [cost_row(r) | {"excluded": r["excluded"], "outage_flag": r["outage_flag"]} for r in runs],
        "funnel": [{"run_id": r["run_id"], **{f"items_{k}": v for k, v in funnel(r)["items"].items()},
                    **{f"urls_{k}": v for k, v in funnel(r)["urls"].items()}} for r in completed],
        "origins": [{"run_id": r["run_id"], "report_numbers": (o := origins(r))["report_numbers"],
                     "numbers_in_no_tool_output": o["numbers_in_no_tool_output"],
                     **{f"origin: {k}": v for k, v in o["by_first_origin"].items()},
                     "rating_cells": rating_cells(r["report"]),
                     "report_urls": (u := url_origins(r))["report_urls"], "unretrieved_urls": u["unretrieved_urls"],
                     **{f"unretrieved url origin: {k}": v for k, v in u["by_origin"].items()}} for r in completed],
        "crawl_truncation": [crawl_row(r) for r in completed],
        "researcher_steps": [row for r in completed for row in researcher_steps(r)],
        "relay": [relay_row(r) for r in completed],
        "judge_costs": judge_cost_rows(),
        "baseline_scores": [row for r in completed if (row := baseline_score_row(r))],
    }
    md = []
    for name, rows in tables.items():
        cols = list(dict.fromkeys(k for row in rows for k in row))
        with open(out / f"{name}.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
        md.append(f"## {name}\n\n| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n" +
                  "\n".join("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |" for r in rows) + "\n")
    (ANALYSIS_DIR / "tables.md").write_text("# Derived tables (generated by boundary_probe.tables)\n\n" + "\n".join(md))
    print((ANALYSIS_DIR / "tables.md").read_text()[:6000])


if __name__ == "__main__":
    main()

"""Run one development query through the unmodified DeerFlow 1.x graph, capturing
every model call, tool call and state transition.

    python -m boundary_probe.run_query q01 --tag r01

Writes runs/<run_id>/raw/{manifest.json, llm_calls.jsonl, tool_calls.jsonl,
crawl_fulltext.jsonl, state_snapshots.jsonl, final_state.json, report.md,
deerflow.log}. Raw files are never edited after the run.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import logging
import time
import traceback
from collections import defaultdict
from pathlib import Path
from typing import Any

from . import deerflow_env, manifest
from .cassette import Cassette
from .recording import CallLog
from .settings import RUNS_DIR, code_fingerprint, load_config, load_queries, sha256_file


def graph_config(cfg: dict[str, Any], thread_id: str) -> dict[str, Any]:
    g = cfg["graph"]
    return {
        "configurable": {
            "thread_id": thread_id,
            "max_plan_iterations": g["max_plan_iterations"],
            "max_step_num": g["max_step_num"],
            "max_search_results": g["max_search_results"],
            "report_style": g["report_style"],
        },
        "recursion_limit": g["outer_recursion_limit"],
    }


def initial_state(cfg: dict[str, Any], query: str) -> dict[str, Any]:
    # Mirrors src/workflow.py:run_agent_workflow_async for a fresh query.
    g = cfg["graph"]
    return {
        "messages": [{"role": "user", "content": query}],
        "auto_accepted_plan": g["auto_accepted_plan"],
        "enable_background_investigation": g["enable_background_investigation"],
        "research_topic": query,
        "clarified_research_topic": query,
        "enable_clarification": g["enable_clarification"],
        "locale": g["locale"],
    }


def _plan_dict(plan: Any) -> Any:
    return plan.model_dump() if hasattr(plan, "model_dump") else plan


def snapshot(state: dict[str, Any]) -> dict[str, Any]:
    plan = _plan_dict(state.get("current_plan"))
    steps = None
    if isinstance(plan, dict):
        steps = [{"title": s.get("title"), "step_type": s.get("step_type"),
                  "execution_res_chars": len(s.get("execution_res") or "")}
                 for s in plan.get("steps", [])]
    return {
        "t": time.time(),
        "n_messages": len(state.get("messages", [])),
        "plan_iterations": state.get("plan_iterations"),
        "has_enough_context": plan.get("has_enough_context") if isinstance(plan, dict) else None,
        "plan_steps": steps,
        "n_observations": len(state.get("observations", []) or []),
        "n_citations": len(state.get("citations", []) or []),
        "final_report_chars": len(state.get("final_report") or ""),
    }


def serialize_state(state: dict[str, Any]) -> dict[str, Any]:
    from langchain_core.messages import BaseMessage, messages_to_dict

    out: dict[str, Any] = {}
    for k, v in state.items():
        if k == "messages":
            out[k] = messages_to_dict([m for m in v if isinstance(m, BaseMessage)])
        else:
            out[k] = _plan_dict(v)
    return out


def summarize(calls: list[dict[str, Any]], tools: list[dict[str, Any]], num_ctx: int) -> dict[str, Any]:
    by_role: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for c in calls:
        r = by_role[c.get("role") or "unknown"]
        r["calls"] += 1
        r["prompt_tokens"] += c.get("prompt_tokens") or 0
        r["completion_tokens"] += c.get("completion_tokens") or 0
        r["model_wall_s"] += c.get("wall_s") or 0.0
        r["errors"] += 1 if c.get("error") else 0
        r["finish_length"] += 1 if c.get("finish_reason") == "length" else 0
        r["max_prompt_tokens"] = max(r["max_prompt_tokens"], c.get("prompt_tokens") or 0)
    by_tool: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for t in tools:
        b = by_tool[t["tool"]]
        b["calls"] += 1
        b["errors"] += 1 if t.get("error") else 0
        b["wall_s"] += t.get("wall_s") or 0.0
    peak = max(((c.get("prompt_tokens") or 0) + (c.get("completion_tokens") or 0) for c in calls), default=0)
    return {
        "llm_by_role": {k: dict(v) for k, v in by_role.items()},
        "tools_by_name": {k: dict(v) for k, v in by_tool.items()},
        "llm_calls": len(calls),
        "tool_calls": len(tools),
        "prompt_tokens": sum(c.get("prompt_tokens") or 0 for c in calls),
        "completion_tokens": sum(c.get("completion_tokens") or 0 for c in calls),
        "peak_context_tokens": peak,
        "near_ctx_limit": peak > 0.95 * num_ctx,  # would indicate serving-layer truncation risk
    }


async def run(query_id: str, tag: str) -> Path:
    fingerprint = code_fingerprint()  # the code actually loaded for this run
    cfg = load_config()
    query = load_queries()[query_id]
    conf_yaml = deerflow_env.prepare(cfg)
    from src.graph.builder import build_graph  # noqa: E402  (after prepare)

    run_id = f"{query_id}-{tag}-{dt.datetime.now().strftime('%Y%m%dT%H%M%S')}"
    raw = RUNS_DIR / run_id / "raw"
    raw.mkdir(parents=True, exist_ok=False)

    handler = logging.FileHandler(raw / "deerflow.log")
    handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)

    frozen = dt.datetime.now().replace(microsecond=0)
    deerflow_env.freeze_prompt_time(frozen)
    call_log = CallLog()
    deerflow_env.inject_model(deerflow_env.recording_model(cfg, call_log))
    cassette = Cassette("record")
    crawl_log: list[dict[str, Any]] = []
    deerflow_env.install_tools(cassette, crawl_log)

    graph = build_graph()
    snapshots, final_state, status, error = [], {}, "completed", None
    started = dt.datetime.now(dt.timezone.utc)
    t0 = time.time()
    try:
        async for s in graph.astream(initial_state(cfg, query["text"]),
                                     graph_config(cfg, run_id), stream_mode="values"):
            snapshots.append(snapshot(s))
            final_state = s
    except Exception as exc:
        status, error = "error", "".join(traceback.format_exception(exc))
    wall = time.time() - t0
    if status == "completed" and not final_state.get("final_report"):
        status = "no_report"

    call_log.dump(raw / "llm_calls.jsonl")
    cassette.dump(raw / "tool_calls.jsonl")
    with open(raw / "crawl_fulltext.jsonl", "w") as f:
        for rec in crawl_log:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    with open(raw / "state_snapshots.jsonl", "w") as f:
        for snap in snapshots:
            f.write(json.dumps(snap, ensure_ascii=False, default=str) + "\n")
    (raw / "final_state.json").write_text(
        json.dumps(serialize_state(final_state), ensure_ascii=False, indent=1, default=str))
    (raw / "report.md").write_text(final_state.get("final_report") or "")
    logging.getLogger().removeHandler(handler)
    handler.close()

    files = sorted(p for p in raw.iterdir() if p.name != "manifest.json")
    man = manifest.build(
        cfg, conf_yaml=conf_yaml, probe_code_sha256=fingerprint,
        run_id=run_id, query_id=query_id, query_text=query["text"],
        status=status, error=error,
        started_utc=started.isoformat(), wall_s=wall,
        frozen_prompt_time=frozen.strftime("%a %b %d %Y %H:%M:%S %z"),
        retrieval_snapshot_id=sha256_file(raw / "tool_calls.jsonl"),
        search_provider=cfg["tools"]["search_api"], crawler=cfg["tools"]["crawler"],
        summary=summarize(call_log.records, cassette.records, cfg["model"]["num_ctx"]),
        files_sha256={p.name: sha256_file(p) for p in files},
    )
    (raw / "manifest.json").write_text(json.dumps(man, indent=1, ensure_ascii=False, default=str))
    return raw.parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("query_id")
    ap.add_argument("--tag", default="r01")
    args = ap.parse_args()
    out = asyncio.run(run(args.query_id, args.tag))
    man = json.loads((out / "raw" / "manifest.json").read_text())
    print(json.dumps({"run_dir": str(out), "status": man["status"], "wall_s": round(man["wall_s"], 1),
                      **{k: man["summary"][k] for k in ("llm_calls", "tool_calls", "prompt_tokens",
                                                        "completion_tokens", "peak_context_tokens")}}))


if __name__ == "__main__":
    main()

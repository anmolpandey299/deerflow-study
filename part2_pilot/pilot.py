"""Part 2 pilot: a ledger-form handoff versus Part 1's raw append (docs/part2_protocol.md).

    vendor/deer-flow-1x/.venv/bin/python -m part2_pilot.pilot            # run, honouring the caps
    vendor/deer-flow-1x/.venv/bin/python -m part2_pilot.pilot --dry-run  # build and guard every variant, send nothing

Reads Part 1's recorded reporter requests and case files; never writes them. Every request
is the recorded one with exactly two declared appended blocks (arms L, LC) or none (A-repro),
plus the seed; `expected_diff` must report nothing else before the request is sent.
"""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import time
from pathlib import Path
from typing import Any

import httpx
import yaml

from boundary_probe.boundary import (build_variant, expected_diff, insertion_block, load_run, observation_indices,
                                     reporter_call)
from boundary_probe.recording import request_hash
from boundary_probe.replay_reporter import check_provenance
from boundary_probe.settings import ANALYSIS_DIR, ROOT, RUNS_DIR, load_config, load_queries

OUT = ROOT / "part2_pilot" / "outputs"
SERVED_TAG = "dfprobe-qwen3-4b-ctx40k"

# protocol §2.1, verbatim
SCAFFOLD = """

## User query

{query}

## Requirement checklist

The report should address each requirement below, or state plainly that the retrieved evidence does not cover it.

{requirements}

## How to use evidence-ledger entries

Some observations below contain evidence-ledger entries. Each entry names the requirement(s) it addresses, gives its source a label such as [S1], and quotes text that has been checked word for word against what the research tools returned.
- Use each ledger entry in the part of the report that addresses its requirement(s), unless its quote does not actually address them, and cite it with its source label, e.g. [S1].
- A quote shows what its source says, not that the claim is true. Attribute it ("According to [S1], ..."), and do not add numbers or details that the quote does not contain.
"""

ENTRY = """

### Evidence-ledger entry [E1]

- Addresses: {entry_requirements}
- Source [S1]: {title} ({url})
- Retrieved by: {tool}
- Verified quote:

{quoted_passage}
"""

# protocol §5: most decision-relevant first
ORDER = [("c03", "A", 101),
         ("c03", "L", 101), ("c05", "L", 101), ("c01", "L", 101),
         ("c05", "LC", 101), ("c01", "LC", 101),
         ("c03", "L", 102), ("c05", "L", 102), ("c01", "L", 102),
         ("c03", "L", 103), ("c05", "L", 103), ("c01", "L", 103)]
# amendment A1: the reproduction gate failed, so the pre-registered fallback runs in-session arms for c03 and c05
FALLBACK_ORDER = [("c03", "B", 101), ("c05", "B", 101), ("c03", "L", 101), ("c05", "L", 101), ("c05", "LC", 101),
                  ("c03", "L", 102), ("c05", "L", 102), ("c03", "L", 103), ("c05", "L", 103),
                  ("c03", "B", 102), ("c05", "B", 102)]
MAX_GENERATIONS, NO_START_AFTER_S, TIMEOUT_S = 12, 41 * 60, 600
PART1_MODULES = ("boundary_probe.run_query", "boundary_probe.replay_reporter",
                 "boundary_probe.evaluate", "boundary_probe.probes")


def quote(passage: str) -> str:
    """Part 1's B template quoting (boundary.insertion_block)."""
    return "\n".join("> " + ln if ln.strip() else ">" for ln in passage.strip().splitlines())


def build_case(case_id: str) -> dict[str, Any]:
    case = yaml.safe_load((ANALYSIS_DIR / "cases" / f"{case_id}.yaml").read_text())
    run = load_run(RUNS_DIR / case["run_id"])
    for which in ("repair", "control"):
        check_provenance(run, case[which])  # verbatim in the recorded segment, same URL
    q = load_queries()[case["query_id"]]
    reqs = {r["id"]: r for r in q["requirements"]}
    tags = case["repair"]["requirement_ids"]
    scaffold = SCAFFOLD.format(query=q["text"].strip(),
                               requirements="\n".join(f"- {r['id']} ({r['kind']}): {r['text']}"
                                                      for r in q["requirements"]))
    entry_reqs = "; ".join(f"{t} ({reqs[t]['text']})" for t in tags)
    entries = {arm: ENTRY.format(entry_requirements=entry_reqs, title=case[which]["title"],
                                 url=case[which]["url"], tool=case[which]["tool"],
                                 quoted_passage=quote(case[which]["passage"]))
               for arm, which in (("L", "repair"), ("LC", "control"))}
    base = reporter_call(run)["request"]
    return {"case": case, "run": run, "base": base, "obs_index": observation_indices(base)[case["step"]],
            "scaffold": scaffold, "entries": entries}


def variant(bc: dict[str, Any], arm: str, seed: int) -> tuple[dict[str, Any], dict[int, str]]:
    """(request, declared changes {message index: exact new content})."""
    base, i = bc["base"], bc["obs_index"]
    v = copy.deepcopy(base)
    v["seed"] = seed
    expected: dict[int, str] = {}
    if arm in ("L", "LC"):
        expected = {1: base["messages"][1]["content"] + bc["scaffold"],
                    i: base["messages"][i]["content"] + bc["entries"][arm]}
        for k, content in expected.items():
            v["messages"][k]["content"] = content
    elif arm == "B":  # Part 1's own construction (boundary.insertion_block + build_variant)
        rep = bc["case"]["repair"]
        block = insertion_block(rep["passage"], rep["title"], rep["url"])
        v = build_variant(base, i, block, seed)
        expected = {i: base["messages"][i]["content"] + block}
    elif arm != "A":
        raise ValueError(arm)
    problems = expected_diff(base, v, expected)
    if problems:
        raise RuntimeError(f"undeclared difference in {arm}-s{seed}: {problems}")
    return v, expected


def concurrency_problem() -> str | None:
    ps = subprocess.run(["ollama", "ps"], capture_output=True, text=True, timeout=30).stdout
    loaded = [ln.split()[0] for ln in ps.splitlines()[1:] if ln.strip()]
    if any(not name.startswith(SERVED_TAG) for name in loaded):
        return f"another model is loaded: {loaded}"
    procs = subprocess.run(["ps", "-axo", "command"], capture_output=True, text=True).stdout
    busy = [m for m in PART1_MODULES if m in procs]
    return f"Part 1 module running: {busy}" if busy else None


def post(payload: dict[str, Any], base_url: str) -> dict[str, Any]:
    t0 = time.time()
    r = httpx.post(f"{base_url}/chat/completions", json=payload, timeout=TIMEOUT_S)
    r.raise_for_status()
    data = r.json()
    choice = data["choices"][0]
    return {"t_start": t0, "wall_s": time.time() - t0, "content": choice["message"].get("content") or "",
            "finish_reason": choice.get("finish_reason"), "usage": data.get("usage"),
            "response_id": data.get("id")}


def run(dry: bool = False) -> None:
    cfg = load_config()
    gate = OUT / "c03" / "A-s101.json"
    failed = gate.exists() and json.loads(gate.read_text()).get("reproduces_part1_sample") is not True
    order = FALLBACK_ORDER if failed else ORDER
    cases = {c: build_case(c) for c in sorted({c for c, _, _ in order})}
    log = OUT / "run_log.jsonl"
    OUT.mkdir(parents=True, exist_ok=True)
    # caps hold across restarts: count existing outputs, time from the first request ever sent
    existing = [json.loads(p.read_text()) for p in OUT.glob("c0*/*-s*.json")]
    done = len(existing)
    t0 = min((r["t_start"] for r in existing if "t_start" in r), default=time.time())
    for case_id, arm, seed in order:
        bc = cases[case_id]
        req, expected = variant(bc, arm, seed)
        path = OUT / case_id / f"{arm}-s{seed}.json"
        if dry:
            print(case_id, arm, seed, "guard ok", request_hash(req)[:12],
                  {k: len(v) - len(bc["base"]["messages"][k]["content"]) for k, v in expected.items()})
            continue
        if path.exists():
            continue
        elapsed = time.time() - t0
        stop = ("generation cap" if done >= MAX_GENERATIONS else
                "time cap" if elapsed > NO_START_AFTER_S else concurrency_problem())
        if stop:
            log.open("a").write(json.dumps({"event": "stop", "reason": stop, "next": [case_id, arm, seed],
                                            "elapsed_s": elapsed}) + "\n")
            print("STOP:", stop)
            return
        rec = {"case_id": case_id, "run_id": bc["case"]["run_id"], "arm": arm, "seed": seed,
               "base_request_hash": request_hash(bc["base"]), "request_hash": request_hash(req),
               "declared_changes": {str(k): v[len(bc["base"]["messages"][k]["content"]):]
                                    for k, v in expected.items()},
               "guard_problems": [], "request": req}
        sent = time.time()
        try:
            rec.update(post(req, cfg["model"]["base_url"]))
        except Exception as exc:  # recorded, not retried (protocol §5)
            rec.update({"error": repr(exc), "t_start": sent, "wall_s": time.time() - sent})
        done += 1
        if arm == "A" and "content" in rec:
            part1 = json.loads((RUNS_DIR / bc["case"]["run_id"] / "replays" / case_id / f"A-s{seed}.json").read_text())
            rec["reproduces_part1_sample"] = rec["content"] == part1["content"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
        summary = {k: rec.get(k) for k in ("case_id", "arm", "seed", "wall_s", "finish_reason", "usage",
                                            "error", "reproduces_part1_sample")}
        summary["chars"] = len(rec.get("content", ""))
        summary["elapsed_s"] = time.time() - t0
        log.open("a").write(json.dumps(summary) + "\n")
        print(json.dumps(summary), flush=True)
        if arm == "A" and rec.get("reproduces_part1_sample") is not True:
            log.open("a").write(json.dumps({"event": "stop", "reason": "A-repro failed or not byte-identical; re-plan per §5"}) + "\n")
            print("STOP: A-repro did not reproduce Part 1; re-plan per protocol §5 before any further generation")
            return


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    run(dry=ap.parse_args().dry_run)


if __name__ == "__main__":
    main()

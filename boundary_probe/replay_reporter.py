"""Replay the reporter from the recorded boundary.

    python -m boundary_probe.replay_reporter analysis/cases/<case_id>.yaml [--reproduce]

H1 cases: A (original), B (repair passage appended to one observation), C (control
passage appended). Probe E cases: A, D (target observation replaced by a stub),
G (a grounded observation replaced by the same stub).

For every (condition, seed) the recorded reporter request is copied, the declared
change is applied and the seed set; `expected_diff` must report nothing else before
the payload is POSTed unchanged to the same OpenAI-compatible endpoint. The reporter
has no tools bound, so a replay cannot issue a tool call. Raw responses go to
runs/<run_id>/replays/<case_id>/.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import httpx
import yaml

from .boundary import (OBS_PREFIX, build_replacement, build_variant, expected_diff, insertion_block,
                       load_run, observation_indices, reporter_call)
from .evidence import segments
from .recording import request_hash
from .settings import RUNS_DIR, code_fingerprint, load_config


class ProvenanceError(ValueError):
    pass


def check_provenance(run: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    """The inserted passage must be verbatim from the recorded tool output it cites."""
    seg = next((s for s in segments(run) if s["seg_id"] == spec["seg_id"]), None)
    if seg is None:
        raise ProvenanceError(f"segment {spec['seg_id']} not in run {run['run_id']}")
    if spec["passage"] not in seg["text"]:
        raise ProvenanceError(f"passage is not a verbatim substring of segment {spec['seg_id']}")
    if spec["url"] != seg["url"]:
        raise ProvenanceError(f"url {spec['url']} != recorded {seg['url']}")
    return seg


def load_case(path: Path) -> dict[str, Any]:
    return yaml.safe_load(Path(path).read_text())


STUB = "[No source-backed findings were produced for this step.]"  # probe E (amendment A7)


def plan_conditions(case: dict[str, Any], run: dict[str, Any]) -> tuple[dict, dict]:
    """condition -> (expected message changes {index: exact new content}, builder(seed))."""
    base = reporter_call(run)["request"]
    obs = observation_indices(base)
    conds = {"A": ({}, lambda seed: build_variant(base, None, "", seed))}
    if case.get("kind", "H1") == "H1":
        i = obs[case["step"]]
        check_provenance(run, case["repair"])
        check_provenance(run, case["control"])
        for c, spec in (("B", case["repair"]), ("C", case["control"])):
            block = insertion_block(spec["passage"], spec["title"], spec["url"])
            conds[c] = ({i: base["messages"][i]["content"] + block},
                        lambda seed, block=block: build_variant(base, i, block, seed))
    else:  # "E"
        for c, step in (("D", case["target_step"]), ("G", case["control_step"])):
            j = obs[step]
            conds[c] = ({j: OBS_PREFIX + STUB}, lambda seed, j=j: build_replacement(base, j, STUB, seed))
    return base, conds


def post(payload: dict[str, Any], base_url: str) -> dict[str, Any]:
    t0 = time.time()
    r = httpx.post(f"{base_url}/chat/completions", json=payload, timeout=3600)
    r.raise_for_status()
    data = r.json()
    choice = data["choices"][0]
    return {"t_start": t0, "wall_s": time.time() - t0, "content": choice["message"].get("content") or "",
            "finish_reason": choice.get("finish_reason"), "usage": data.get("usage"), "response_id": data.get("id")}


def run_case(case_path: Path, reproduce: bool = False) -> Path:
    cfg = load_config()
    case = load_case(case_path)
    run = load_run(RUNS_DIR / case["run_id"])
    base, conds = plan_conditions(case, run)
    out = RUNS_DIR / case["run_id"] / "replays" / case["case_id"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "replay_manifest.json").write_text(json.dumps({
        "case_file": str(case_path), "case": case, "base_request_hash": request_hash(base),
        "declared_changes": {c: {str(k): v[-400:] for k, v in exp.items()} for c, (exp, _) in conds.items()},
        "model": cfg["model"], "probe_code_sha256": code_fingerprint(),
    }, indent=1, ensure_ascii=False))

    jobs = [(c, s) for s in cfg["replay"]["seeds"] for c in conds]  # conditions interleaved per seed
    if reproduce:
        jobs.insert(0, ("A", base["seed"]))  # the original request, byte-for-byte
    for cond, seed in jobs:
        path = out / f"{cond}-s{seed}.json"
        if path.exists():
            continue
        expected, make = conds[cond]
        variant = make(seed)
        problems = expected_diff(base, variant, expected)
        if problems:  # the guard: nothing but the declared change and the seed may differ
            raise RuntimeError(f"undeclared difference in {cond}-s{seed}: {problems}")
        result = post(variant, cfg["model"]["base_url"])
        rec = {"case_id": case["case_id"], "run_id": case["run_id"], "kind": case.get("kind", "H1"),
               "condition": cond, "seed": seed, "request_hash": request_hash(variant),
               "declared_diff": problems, **result}
        if cond == "A" and seed == base["seed"]:
            original = reporter_call(run)["response"]["content"]
            rec["reproduces_original_report"] = rec["content"] == original
        path.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
        print(f"{case['case_id']} {cond}-s{seed}: {len(rec['content'])} chars, "
              f"{rec['usage']}, {rec['wall_s']:.0f}s", flush=True)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("case_files", nargs="+")
    ap.add_argument("--reproduce", action="store_true",
                    help="also resend the original request with its original seed")
    args = ap.parse_args()
    for cf in args.case_files:
        run_case(Path(cf), reproduce=args.reproduce)


if __name__ == "__main__":
    main()

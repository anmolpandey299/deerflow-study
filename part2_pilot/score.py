"""Scoring for the Part 2 pilot (docs/part2_protocol.md §3-§4).

    python -m part2_pilot.score table                # deterministic measures, every arm -> outputs/scores.json
    python -m part2_pilot.score export <dir>         # blinded audit packets, one sub-directory per auditor
    python -m part2_pilot.score unblind <labels...>  # auditor labels -> per-case u_X and verdicts

Part 1's A/B/C samples are read from runs/ (read-only); new L/LC samples from part2_pilot/outputs/.
"""

from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path
from statistics import mean
from typing import Any

import yaml

from boundary_probe.boundary import load_run
from boundary_probe.evaluate import format_checks
from boundary_probe.evidence import (checkable_items, evidence_pool_text, item_present, normalize_url, url_provenance,
                                     urls_in)
from boundary_probe.replay_analysis import body_sentences
from boundary_probe.settings import ANALYSIS_DIR, RUNS_DIR

from .pilot import OUT

CASES = ("c03", "c05")  # amendment A1: c01 dropped with the fallback plan
SEEDS = (101, 102, 103)

# protocol §3 (2): D±1 detector terms; anchors use word boundaries so "declarative" is not "LaRA"
DETECT = {
    "c01": {"anchor": [r"\blara\b"], "fact": [r"inconclusive", r"2,?326", r"benchmark limitation"]},
    "c03": {"anchor": [r"\bint8\b", r"8-bit integer"],
            "fact": [r"doubl", r"(?<![\d.])2\s?[x×]", r"\btwice\b", r"two-?fold"],
            "also": [r"\bfp16\b", r"16[- ]bit"]},
    "c05": {"anchor": [r"turboquant"],
            "fact": [r"(?<![\d.])3[\s-]?bits?\b", r"three bits", r"16\s?(?:or|–|-|/|to)\s?32"]},
}
# protocol §3 (6): control passage stated (LC parroting)
PARROT = {"c01": [r"wikipedia", r"incorporate new information"],
          "c05": [r"awesome[- ]llm", r"huangowen"]}
SIX_X = re.compile(r"(?<![\d.])6\s?[x×]")  # c05 planner-thought claim, descriptive (§3 (7))

# fixed with the audit task, before any label exists: what counts as the target fact
CORE = {
    "c01": ["LaRA's authors say existing RAG-versus-long-context comparisons are often inconclusive because of "
            "benchmark limitations", "LaRA is a benchmark with 2,326 test cases (four QA tasks, three long-context types)"],
    "c03": ["INT8 (8-bit integer) arithmetic can nearly double matrix-multiplication throughput compared with "
            "FP16 (16-bit floating point)"],
    "c05": ["TurboQuant compresses KV caches to 3 bits per value, whereas standard inference uses 16 or 32 bits"],
}


def window_hit(report: str, spec: dict[str, list[str]]) -> bool:
    low = [s.lower() for s in body_sentences(report)]
    has = lambda pats, text: any(re.search(p, text) for p in pats)  # noqa: E731
    for i, s in enumerate(low):
        if has(spec["anchor"], s):
            win = " ".join(low[max(0, i - 1):i + 2])
            if has(spec["fact"], win) and ("also" not in spec or has(spec["also"], win)):
                return True
    return False


def samples(case_id: str) -> list[dict[str, Any]]:
    case = yaml.safe_load((ANALYSIS_DIR / "cases" / f"{case_id}.yaml").read_text())
    out = []
    for arm in "ABC":
        for s in SEEDS:
            r = json.loads((RUNS_DIR / case["run_id"] / "replays" / case_id / f"{arm}-s{s}.json").read_text())
            out.append({"case_id": case_id, "arm": arm, "seed": s, "source": "part1", **_rec(r)})
    for p in sorted((OUT / case_id).glob("*-s*.json")):  # every in-session sample: A-repro, B, L, LC
        r = json.loads(p.read_text())
        if "content" in r:
            out.append({"case_id": case_id, "arm": r["arm"], "seed": r["seed"], "source": "part2", **_rec(r)})
    return out


def _rec(r: dict[str, Any]) -> dict[str, Any]:
    u = r.get("usage") or {}
    return {"content": r["content"], "wall_s": r["wall_s"], "prompt_tokens": u.get("prompt_tokens"),
            "completion_tokens": u.get("completion_tokens"), "finish_reason": r.get("finish_reason")}


def deterministic(case_id: str) -> list[dict[str, Any]]:
    case = yaml.safe_load((ANALYSIS_DIR / "cases" / f"{case_id}.yaml").read_text())
    run = load_run(RUNS_DIR / case["run_id"])
    pool = evidence_pool_text(run)
    obs = run["final_state"]["observations"]
    src = normalize_url(case["repair"]["url"])
    rows = []
    for s in samples(case_id):
        text = s["content"]
        body = " ".join(body_sentences(text)).lower()
        nums = checkable_items(text)
        rows.append({k: s[k] for k in ("case_id", "arm", "seed", "source", "wall_s", "prompt_tokens",
                                       "completion_tokens", "finish_reason")} | {
            "chars": len(text),
            "detector_pm1": window_hit(text, DETECT[case_id]),
            "restored_url_cited": src in {normalize_url(u) for u in urls_in(text)},
            "s1_markers": text.count("[S1]"),
            "numbers_not_in_tool_output": sum(not item_present(i, pool) for i in nums),
            "numbers_in_no_observation_or_tool_output": sum(
                not item_present(i, pool) and not any(item_present(i, o) for o in obs) for i in nums),
            "never_retrieved_urls": len(url_provenance(text, run)["fabricated_urls"]),
            "fmt": format_checks(text)["score"],
            "parrots_control": (any(re.search(p, body) for p in PARROT[case_id]) if case_id in PARROT else None),
            "six_x_claim": bool(SIX_X.search(body)) if case_id == "c05" else None,
        })
    return rows


def table() -> None:
    rows = [r for c in CASES for r in deterministic(c)]
    (OUT / "scores.json").write_text(json.dumps(rows, indent=1))
    keys = ["chars", "prompt_tokens", "completion_tokens", "wall_s", "detector_pm1", "restored_url_cited",
            "s1_markers", "numbers_not_in_tool_output", "numbers_in_no_observation_or_tool_output",
            "never_retrieved_urls", "fmt"]
    for c in CASES:
        for src in ("part1", "part2"):
            for arm in ("A", "B", "C", "L", "LC"):
                rs = [r for r in rows if r["case_id"] == c and r["arm"] == arm and r["source"] == src]
                if rs:
                    agg = {k: round(mean(float(r[k]) for r in rs), 2) for k in keys}
                    print(c, src, arm, len(rs), json.dumps(agg))


TASK = """# Audit task (Part 2 pilot; written before any label exists)

You are checking whether research reports state one specific fact. You are an AI assistant acting as a blinded
auditor; nobody expects you to know where the reports came from. Read only the packet files listed for you, in the
directory given. Do not open any other file or directory, and do not use web search or outside knowledge.

Each packet has a "Target fact" section (a source's title and URL, the verbatim passage, and the core statement(s)
that count as the fact) and a "Report" section. Reports are long: search each one for every mention of the target's
source, subject and key terms, and read the surrounding paragraphs. A bare title or link in a reference list does not
count as stating anything.

For each packet give:

1. `target_fact`, exactly one of:
   - STATED_CORRECTLY: the report's body text states at least one core statement, consistent with the passage
     (paraphrase is fine; extra claims elsewhere do not change this label).
   - STATED_INCORRECTLY: the report states the fact's subject with a wrong number, meaning or source.
   - SOURCE_ONLY: the report mentions the target's source or subject, but does not state the fact.
   - NOT_STATED: none of the above.
2. `attribution` (only if STATED_CORRECTLY, otherwise "n/a"), exactly one of:
   - ATTRIBUTED: the stating sentence or its neighbour names the source (by name, title or system name), links its
     URL, or cites a marker that resolves to that source in the report's reference list.
   - UNATTRIBUTED: no source is given for it.
   - MISATTRIBUTED: it is credited to a different source.
3. `evidence`: the report sentence(s) you relied on, verbatim (empty if NOT_STATED).

Be strict and literal. Write one JSON object to the output file you are given:

{"<packet_id>": {"target_fact": "...", "attribution": "...", "evidence": "..."}}

When you finish, reply only with the path you wrote and the number of packets labelled.
"""


def export(dest: Path, seed: int = 20261001) -> None:
    rng = random.Random(seed)
    items = []
    for c in CASES:
        case = yaml.safe_load((ANALYSIS_DIR / "cases" / f"{c}.yaml").read_text())
        for s in samples(c):
            items.append((c, s["arm"], s["seed"], s["content"], case["repair"], s["source"]))
    rng.shuffle(items)
    ids = [f"P{rng.getrandbits(24):06x}" for _ in items]
    key = {pid: {"case_id": c, "arm": a, "seed": s, "source": src} for pid, (c, a, s, _, _, src) in zip(ids, items)}
    half = len(items) // 2
    groups = {"auditor1": ids[:half] + ids[half:half + 3], "auditor2": ids[half:] + ids[:3]}  # 6 shared
    for name, pids in groups.items():
        d = dest / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "INSTRUCTIONS.md").write_text(TASK)
        for pid in pids:
            c, _, _, text, rep, _ = items[ids.index(pid)]
            quoted = "\n".join("> " + ln for ln in rep["passage"].strip().splitlines())
            core = "\n".join(f"- {x}" for x in CORE[c])
            (d / f"{pid}.md").write_text(
                f"# Packet {pid}\n\n## Target fact\n\nSource: {rep['title']} ({rep['url']})\n\nPassage (verbatim):\n\n"
                f"{quoted}\n\nCore statement(s) that count as the fact:\n\n{core}\n\n## Report\n\n{text}\n")
    audit = OUT / "audit"
    audit.mkdir(parents=True, exist_ok=True)
    (audit / "key.json").write_text(json.dumps(key, indent=1))
    (audit / "assignment.json").write_text(json.dumps(groups, indent=1))
    (audit / "auditor_task.md").write_text(TASK)
    print(f"{len(items)} packets; auditor1 {len(groups['auditor1'])}, auditor2 {len(groups['auditor2'])}; shared 6")


def unblind(label_files: list[str]) -> None:
    key = json.loads((OUT / "audit" / "key.json").read_text())
    labels: dict[str, dict[str, Any]] = {}
    for f in label_files:
        for pid, lab in json.loads(Path(f).read_text()).items():
            labels.setdefault(pid, {})[Path(f).stem] = lab
    rows = [{"packet": pid, **key[pid], "labels": labels.get(pid, {})} for pid in key]
    (OUT / "audit" / "unblinded.json").write_text(json.dumps(rows, indent=1))
    disagree = [r for r in rows if len({v["target_fact"] for v in r["labels"].values()}) > 1]
    print("unlabelled:", [r["packet"] for r in rows if not r["labels"]])
    print("shared-packet disagreements:", [(r["packet"], r["case_id"], r["arm"], r["seed"],
                                            {k: v["target_fact"] for k, v in r["labels"].items()}) for r in disagree])
    for c in CASES:
        for src in ("part1", "part2"):
            for arm in ("A", "B", "C", "L", "LC"):
                rs = sorted((r for r in rows if r["case_id"] == c and r["arm"] == arm and r["source"] == src),
                            key=lambda r: r["seed"])
                if rs:
                    print(c, src, arm, [(r["seed"], {k: (v["target_fact"], v.get("attribution")) for k, v in
                                                     r["labels"].items()}) for r in rs])


def summary() -> None:
    """Markdown tables for docs/part2_results.md, from scores.json and audit/unblinded.json."""
    rows = json.loads((OUT / "scores.json").read_text())
    audit = {(r["case_id"], r["arm"], r["seed"], r["source"]): r["labels"]
             for r in json.loads((OUT / "audit" / "unblinded.json").read_text())}
    print("| case | session | arm | seed | audit: target fact (attribution) | D±1 | chars | prompt tok | gen tok | wall s "
          "| nums not in tools | never-retrieved URLs | fmt | [S1] | restored URL cited | parrots control | '6x' claim |")
    print("|" + "---|" * 17)
    for r in sorted(rows, key=lambda r: (r["case_id"], r["source"], r["arm"], r["seed"])):
        labs = audit.get((r["case_id"], r["arm"], r["seed"], r["source"]), {})
        lab = "; ".join(f"{k[-1]}: {v['target_fact']}" + (f" ({v['attribution']})" if v.get("attribution") not in
                                                          (None, "n/a") else "") for k, v in sorted(labs.items()))
        print(f"| {r['case_id']} | {'P1' if r['source'] == 'part1' else 'P2'} | {r['arm']} | {r['seed']} | {lab} | "
              f"{int(r['detector_pm1'])} | {r['chars']} | {r['prompt_tokens']} | {r['completion_tokens']} | "
              f"{r['wall_s']:.0f} | {r['numbers_not_in_tool_output']} | {r['never_retrieved_urls']} | {r['fmt']:.3f} | "
              f"{r['s1_markers']} | {int(r['restored_url_cited'])} | "
              f"{'' if r['parrots_control'] is None else int(r['parrots_control'])} | "
              f"{'' if r['six_x_claim'] is None else int(r['six_x_claim'])} |")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "table":
        table()
    elif cmd == "export":
        export(Path(sys.argv[2]))
    elif cmd == "unblind":
        unblind(sys.argv[2:])
    elif cmd == "summary":
        summary()

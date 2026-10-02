"""The researcher -> reporter boundary.

A replay condition is the reporter's exact recorded request payload with (at most)
one declared block appended to one observation message, plus a replay seed.
`declared_diff` is the guard: it lists every way a variant differs from the base
payload other than that block and the seed; an intervention is valid only if the
list is empty.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

# reporter_node wraps each researcher summary like this (src/graph/nodes.py:917)
OBS_PREFIX = "Below are some observations for the research task:\n\n"
INSERT_HEADER = "\n\n### Additional retrieved passage\n\n"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def load_run(run_dir: Path) -> dict[str, Any]:
    raw = Path(run_dir) / "raw"
    return {
        "dir": Path(run_dir),
        "run_id": Path(run_dir).name,
        "manifest": json.loads((raw / "manifest.json").read_text()),
        "llm_calls": load_jsonl(raw / "llm_calls.jsonl"),
        "tool_calls": load_jsonl(raw / "tool_calls.jsonl"),
        "crawl_fulltext": load_jsonl(raw / "crawl_fulltext.jsonl"),
        "final_state": json.loads((raw / "final_state.json").read_text()),
        "report": (raw / "report.md").read_text(),
    }


def reporter_call(run: dict[str, Any]) -> dict[str, Any]:
    calls = [c for c in run["llm_calls"] if c["role"] == "reporter"]
    if len(calls) != 1:
        raise ValueError(f"expected exactly one reporter call, found {len(calls)}")
    return calls[0]


def observation_indices(payload: dict[str, Any]) -> list[int]:
    return [i for i, m in enumerate(payload["messages"])
            if m.get("role") == "user" and isinstance(m.get("content"), str)
            and m["content"].startswith(OBS_PREFIX)]


def insertion_block(passage: str, title: str, url: str) -> str:
    """Same template for the repair (B) and the control (C)."""
    quoted = "\n".join("> " + line if line.strip() else ">" for line in passage.strip().splitlines())
    return f"{INSERT_HEADER}{quoted}\n\n- [{title}]({url})\n"


def build_variant(base: dict[str, Any], obs_msg_index: int | None, block: str,
                  seed: int) -> dict[str, Any]:
    variant = copy.deepcopy(base)
    if block:
        msg = variant["messages"][obs_msg_index]
        if not (msg.get("role") == "user" and msg["content"].startswith(OBS_PREFIX)):
            raise ValueError(f"message {obs_msg_index} is not a researcher observation")
        msg["content"] = msg["content"] + block
    variant["seed"] = seed
    return variant


def build_replacement(base: dict[str, Any], obs_msg_index: int, body: str, seed: int) -> dict[str, Any]:
    """Probe E: replace one observation's text (after the fixed prefix) with `body`."""
    variant = copy.deepcopy(base)
    msg = variant["messages"][obs_msg_index]
    if not (msg.get("role") == "user" and msg["content"].startswith(OBS_PREFIX)):
        raise ValueError(f"message {obs_msg_index} is not a researcher observation")
    msg["content"] = OBS_PREFIX + body
    variant["seed"] = seed
    return variant


def expected_diff(base: dict[str, Any], variant: dict[str, Any], expected: dict[int, str]) -> list[str]:
    """Every difference between payloads other than the seed and the declared
    message contents in `expected` (index -> exact new content). [] means clean."""
    problems = []
    for key in sorted((set(base) | set(variant)) - {"messages", "seed"}):
        if base.get(key) != variant.get(key):
            problems.append(f"payload field {key!r} changed")
    bm, vm = base.get("messages", []), variant.get("messages", [])
    if len(bm) != len(vm):
        return problems + [f"message count {len(bm)} -> {len(vm)}"]
    for i, (a, b) in enumerate(zip(bm, vm)):
        if i in expected:
            if {k: v for k, v in a.items() if k != "content"} != {k: v for k, v in b.items() if k != "content"}:
                problems.append(f"message {i} metadata changed")
            if b.get("content") != expected[i]:
                problems.append(f"message {i} is not the declared new content")
        elif a != b:
            problems.append(f"message {i} changed")
    return problems


def declared_diff(base: dict[str, Any], variant: dict[str, Any],
                  obs_msg_index: int | None, block: str) -> list[str]:
    """Append form (conditions A/B/C)."""
    expected = {obs_msg_index: base["messages"][obs_msg_index]["content"] + block} if block else {}
    problems = expected_diff(base, variant, expected)
    return [p.replace("is not the declared new content",
                      "is not the base content plus exactly the declared block") for p in problems]

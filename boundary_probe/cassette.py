"""Strict record/replay for tool calls.

Invariant: in replay mode a call is answered only by a recording of the *same*
tool with the *same* canonical arguments, and the n-th occurrence of that call
gets the n-th recorded response. Anything else raises ToolCacheMiss. There is
no fallback to a "similar" response and no silent live call.
"""

from __future__ import annotations

import importlib
import json
import threading
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

from langchain_core.tools import BaseTool

from .settings import canonical_json


class ToolCacheMiss(RuntimeError):
    """A tool call was made in replay mode that has no matching recording."""


class RecordedToolError(RuntimeError):
    """Replays a recorded tool exception whose original class cannot be rebuilt."""


def tool_key(tool: str, args: dict[str, Any]) -> str:
    return canonical_json({"tool": tool, "args": args})


class Cassette:
    def __init__(self, mode: str, records: list[dict[str, Any]] | None = None):
        if mode not in ("record", "replay"):
            raise ValueError(f"unknown cassette mode {mode!r}")
        self.mode = mode
        self.records: list[dict[str, Any]] = []   # calls made in this session, in order
        # DeerFlow's researcher node converts any exception into an "[ERROR]"
        # observation, so a raised miss can be swallowed; callers must also
        # check that this list is empty.
        self.misses: list[str] = []
        self._occurrence: Counter[str] = Counter()
        # LangGraph runs a message's parallel tool calls concurrently; seq and
        # occurrence must be reserved atomically at call start.
        self._lock = threading.Lock()
        self._next_seq = 0
        self._recorded: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for rec in sorted(records or [], key=lambda r: (r["key"], r["occurrence"])):
            self._recorded[rec["key"]].append(rec)

    # -- persistence ---------------------------------------------------------
    @classmethod
    def load(cls, path: Path) -> "Cassette":
        recs = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
        return cls("replay", recs)

    def dump(self, path: Path) -> None:
        with open(path, "w") as f:
            for rec in sorted(self.records, key=lambda r: r["seq"]):
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # -- the one entry point used by CassetteTool ---------------------------
    def call(
        self,
        tool: str,
        args: dict[str, Any],
        live: Callable[[], tuple[Any, Any]],
        context: dict[str, Any] | None = None,
    ) -> tuple[Any, Any]:
        key = tool_key(tool, args)
        with self._lock:
            n = self._occurrence[key]
            self._occurrence[key] += 1
            seq = self._next_seq
            self._next_seq += 1
        base = {"seq": seq, "tool": tool, "args": args, "key": key,
                "occurrence": n, **(context or {})}

        if self.mode == "record":
            t0 = time.time()
            try:
                content, artifact = live()
            except Exception as exc:  # recorded, then re-raised unchanged
                with self._lock:
                    self.records.append({**base, "content": None, "artifact": None,
                                         "error": _describe(exc), "t_start": t0,
                                         "wall_s": time.time() - t0})
                raise
            with self._lock:
                self.records.append({**base, "content": content, "artifact": artifact,
                                     "error": None, "t_start": t0, "wall_s": time.time() - t0})
            return content, artifact

        recorded = self._recorded.get(key, [])
        if n >= len(recorded):
            msg = (f"unrecorded tool call: {tool} args={canonical_json(args)} "
                   f"occurrence={n} (recorded occurrences: {len(recorded)})")
            self.misses.append(msg)
            raise ToolCacheMiss(msg)
        rec = recorded[n]
        with self._lock:
            self.records.append({**base, "replayed_from_seq": rec["seq"]})
        if rec.get("error"):
            raise _rebuild(rec["error"])
        return rec["content"], rec["artifact"]


def _describe(exc: BaseException) -> dict[str, str]:
    return {"module": type(exc).__module__, "type": type(exc).__name__, "message": str(exc)}


def _rebuild(err: dict[str, str]) -> BaseException:
    try:
        cls = getattr(importlib.import_module(err["module"]), err["type"])
        return cls(err["message"])
    except Exception:
        return RecordedToolError(f"{err['type']}: {err['message']}")


class CassetteTool(BaseTool):
    """Proxy exposing exactly the inner tool's name, description and schema.

    The model therefore receives an identical tool definition; only the
    execution path (live-and-record versus replay) differs.
    """

    inner: BaseTool
    cassette: Any

    def __init__(self, inner: BaseTool, cassette: Cassette):
        super().__init__(
            name=inner.name,
            description=inner.description,
            args_schema=inner.args_schema,
            response_format=inner.response_format,
            inner=inner,
            cassette=cassette,
        )

    def _run(self, *args, run_manager=None, **kwargs):
        # A plain-string input (e.g. background_investigation_node's .invoke(query))
        # arrives positionally; key it by the schema's field names like a tool call.
        kwargs = {**dict(zip(self.inner.args.keys(), args)), **kwargs}

        def live():
            msg = self.inner.invoke(
                {"type": "tool_call", "name": self.inner.name, "args": kwargs, "id": "live"}
            )
            return msg.content, getattr(msg, "artifact", None)

        content, artifact = self.cassette.call(self.name, kwargs, live, {"ns": _namespace(run_manager)})
        if self.response_format == "content_and_artifact":
            return content, artifact
        return content


def _namespace(run_manager) -> str | None:
    meta = getattr(run_manager, "metadata", None) or {}
    return meta.get("langgraph_checkpoint_ns")

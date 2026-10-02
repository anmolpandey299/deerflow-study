"""Capture of every model call (RecordingChatOpenAI) and strict model replay.

The recorder subclasses DeerFlow's own client class (langchain_openai.ChatOpenAI)
and is injected into DeerFlow's LLM cache, so every role's call goes through it
with an unchanged request payload. The replay model computes the payload with
the same code path and answers only from a recording of a byte-identical
request (same hash, same occurrence index); otherwise it raises LLMCacheMiss.
"""

from __future__ import annotations

import json
import threading
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_openai import ChatOpenAI

from .settings import sha256_text


class LLMCacheMiss(RuntimeError):
    """A model request in replay mode has no byte-identical recording."""


# First words of each DeerFlow role prompt (src/prompts/*.md). Used only as a
# cross-check when LangGraph metadata does not name the calling node.
ROLE_MARKERS = {
    "coordinator": "You are DeerFlow, a friendly AI assistant",
    "planner": "You are a professional Deep Researcher",
    "researcher": "You are `researcher` agent",
    "analyst": "You are `analyst` agent",
    "coder": "You are `coder` agent",
    "reporter": "You are a distinguished academic researcher",
}


def request_hash(payload: dict[str, Any]) -> str:
    return sha256_text(json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str))


def role_from_prompt(payload: dict[str, Any]) -> str | None:
    for m in payload.get("messages", []):
        if m.get("role") in ("system", "developer") and isinstance(m.get("content"), str):
            for role, marker in ROLE_MARKERS.items():
                if marker in m["content"]:
                    return role
    return None


def role_from_run_manager(run_manager) -> tuple[str | None, str | None]:
    meta = getattr(run_manager, "metadata", None) or {}
    ns = meta.get("langgraph_checkpoint_ns") or None
    top = ns.split("|")[0].split(":")[0] if ns else meta.get("langgraph_node")
    return top, ns


class CallLog:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def add(self, rec: dict[str, Any]) -> None:
        with self._lock:
            rec["seq"] = len(self.records)
            self.records.append(rec)

    def dump(self, path: Path) -> None:
        with open(path, "w") as f:
            for rec in self.records:
                f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")


def _result_to_dict(result: ChatResult) -> dict[str, Any]:
    # Captured before BaseChatModel merges generation_info into response_metadata,
    # so finish_reason lives in generation_info and token counts in usage_metadata.
    gen = result.generations[0]
    msg = gen.message
    return {
        "content": msg.content,
        "tool_calls": list(getattr(msg, "tool_calls", []) or []),
        "invalid_tool_calls": list(getattr(msg, "invalid_tool_calls", []) or []),
        "id": msg.id,
        "additional_kwargs": msg.additional_kwargs,
        "response_metadata": msg.response_metadata,
        "usage_metadata": getattr(msg, "usage_metadata", None),
        "generation_info": gen.generation_info,
        "llm_output": result.llm_output,
    }


def _dict_to_result(d: dict[str, Any]) -> ChatResult:
    msg = AIMessage(
        content=d["content"],
        tool_calls=d.get("tool_calls") or [],
        invalid_tool_calls=d.get("invalid_tool_calls") or [],
        id=d.get("id"),
        additional_kwargs=d.get("additional_kwargs") or {},
        response_metadata=d.get("response_metadata") or {},
        usage_metadata=d.get("usage_metadata"),
    )
    return ChatResult(generations=[ChatGeneration(message=msg, generation_info=d.get("generation_info"))],
                      llm_output=d.get("llm_output"))


class RecordingChatOpenAI(ChatOpenAI):
    call_log: Any = None

    def _log(self, payload, run_manager, t0, t1, result=None, error=None, extra=None):
        role_meta, ns = role_from_run_manager(run_manager)
        role_prompt = role_from_prompt(payload)
        resp = _result_to_dict(result) if result is not None else None
        usage = (resp or {}).get("usage_metadata") or {}
        self.call_log.add({
            "role": role_meta or role_prompt,
            "role_from_metadata": role_meta,
            "role_from_prompt": role_prompt,
            "ns": ns,
            "request_hash": request_hash(payload),
            "request": payload,
            "response": resp,
            "prompt_tokens": usage.get("input_tokens"),
            "completion_tokens": usage.get("output_tokens"),
            "finish_reason": ((resp or {}).get("generation_info") or {}).get("finish_reason"),
            "error": None if error is None else f"{type(error).__name__}: {error}",
            "t_start": t0,
            "wall_s": t1 - t0,
            **(extra or {}),
        })

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        payload = self._get_request_payload(messages, stop=stop, **kwargs)
        t0 = time.time()
        try:
            result = super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
        except Exception as exc:
            self._log(payload, run_manager, t0, time.time(), error=exc)
            raise
        self._log(payload, run_manager, t0, time.time(), result=result)
        return result

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        payload = self._get_request_payload(messages, stop=stop, **kwargs)
        t0 = time.time()
        try:
            result = await super()._agenerate(messages, stop=stop, run_manager=run_manager, **kwargs)
        except Exception as exc:
            self._log(payload, run_manager, t0, time.time(), error=exc)
            raise
        self._log(payload, run_manager, t0, time.time(), result=result)
        return result


class ReplayChatOpenAI(RecordingChatOpenAI):
    """Answers from recordings only; never contacts a server."""

    recorded: Any = None     # request_hash -> [records in occurrence order]
    occurrence: Any = None   # Counter
    misses: Any = None       # see Cassette.misses: DeerFlow may swallow the exception

    @classmethod
    def from_records(cls, records: list[dict[str, Any]], call_log: CallLog, **model_kwargs):
        by_hash: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for rec in sorted(records, key=lambda r: r["seq"]):
            if rec.get("response") is not None:
                by_hash[rec["request_hash"]].append(rec)
        return cls(recorded=dict(by_hash), occurrence=Counter(), misses=[],
                   call_log=call_log, **model_kwargs)

    def _answer(self, messages, stop, run_manager, kwargs):
        payload = self._get_request_payload(messages, stop=stop, **kwargs)
        h = request_hash(payload)
        n = self.occurrence[h]
        self.occurrence[h] += 1
        recs = self.recorded.get(h, [])
        if n >= len(recs):
            msg = (f"no recording for request {h[:12]} (occurrence {n}; role guess "
                   f"{role_from_prompt(payload)})")
            self.misses.append(msg)
            raise LLMCacheMiss(msg)
        result = _dict_to_result(recs[n]["response"])
        t = time.time()
        self._log(payload, run_manager, t, t, result=result,
                  extra={"replayed_from_seq": recs[n]["seq"]})
        return result

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        return self._answer(messages, stop, run_manager, kwargs)

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        return self._answer(messages, stop, run_manager, kwargs)

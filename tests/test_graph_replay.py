"""Record a run through the real DeerFlow graph, then replay it strictly.

The model is scripted and the tools are offline fakes, so this test needs no
network or model server, but every node, prompt template, router, context
manager and message conversion is DeerFlow's own code at the pinned commit.
"""

import asyncio
import datetime as dt
import json
import re

import pytest
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel

from boundary_probe import deerflow_env
from boundary_probe.boundary import OBS_PREFIX
from boundary_probe.cassette import Cassette
from boundary_probe.recording import (CallLog, LLMCacheMiss, RecordingChatOpenAI,
                                      ReplayChatOpenAI, role_from_prompt)
from boundary_probe.run_query import graph_config, initial_state

QUERY = "Compare two toy retrieval methods on accuracy and cost."
PLAN = {"locale": "en-US", "has_enough_context": False, "thought": "Compare methods.",
        "title": "Toy comparison", "steps": [
            {"need_search": True, "title": "Method A results", "description": "Find A.", "step_type": "research"},
            {"need_search": True, "title": "Method B results", "description": "Find B.", "step_type": "research"}]}
LIVE = {"search": 0, "crawl": 0}


class _Query(BaseModel):
    query: str


class FakeSearch(BaseTool):
    name: str = "web_search"
    description: str = "offline search"
    args_schema: type = _Query
    response_format: str = "content_and_artifact"

    def _run(self, query: str, run_manager=None):
        LIVE["search"] += 1
        slug = re.sub(r"\W+", "-", query.lower()).strip("-")
        hit = {"snippet": f"{query}: accuracy 71.2% at cost $0.4", "title": f"T {query}",
               "link": f"https://example.org/{slug}"}
        return f"snippet: {hit['snippet']}, title: {hit['title']}, link: {hit['link']}", [hit]


def _crawl(url: str) -> str:
    LIVE["crawl"] += 1
    return json.dumps({"url": url, "crawled_content": f"# Page\n\nDetails from {url}"})


FAKE_CRAWL = StructuredTool.from_function(func=_crawl, name="crawl_tool", description="offline crawl")


class Scripted(RecordingChatOpenAI):
    """Deterministic stand-in for the LLM that still goes through the recorder."""

    def _reply(self, payload):
        role, msgs = role_from_prompt(payload), payload["messages"]
        if role == "coordinator":
            return AIMessage(content="", tool_calls=[{"name": "handoff_to_planner", "id": "c0",
                             "args": {"research_topic": QUERY, "locale": "en-US"}}])
        if role == "planner":
            return AIMessage(content=json.dumps(PLAN))
        if role == "researcher":
            title = re.search(r"## Title\n\n(.+)\n", msgs[0]["content"] if msgs[0]["role"] != "system"
                              else next(m["content"] for m in msgs if m["role"] == "user")).group(1)
            tools = [m for m in msgs if m["role"] == "tool"]
            if not tools:
                return AIMessage(content="", tool_calls=[{"name": "web_search", "id": f"s-{title}",
                                                          "args": {"query": title}}])
            if len(tools) == 1:
                return AIMessage(content="", tool_calls=[{"name": "crawl_tool", "id": f"c-{title}",
                                 "args": {"url": f"https://example.org/{title[-1]}"}}])
            return AIMessage(content=f"## Findings: {title}\n\n{tools[0]['content'][:60]}")
        if role == "reporter":
            obs = [m["content"][len(OBS_PREFIX):] for m in msgs
                   if m["role"] == "user" and m["content"].startswith(OBS_PREFIX)]
            return AIMessage(content="# Report\n\n" + "\n".join(obs))
        raise AssertionError(f"unexpected role {role}")

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        payload = self._get_request_payload(messages, stop=stop, **kwargs)
        msg = self._reply(payload)
        msg.usage_metadata = {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2}
        result = ChatResult(generations=[ChatGeneration(message=msg, generation_info={"finish_reason": "stop"})])
        self._log(payload, run_manager, 0.0, 0.0, result=result)
        return result

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        return self._generate(messages, stop=stop, run_manager=run_manager, **kwargs)


FROZEN = dt.datetime(2026, 9, 30, 12, 0, 0)


def _run(cfg, model, cassette):
    from src.graph.builder import build_graph

    deerflow_env.freeze_prompt_time(FROZEN)
    deerflow_env.inject_model(model)
    deerflow_env.install_tools(cassette, search_factory=lambda n: FakeSearch(), crawl_inner=FAKE_CRAWL)
    return asyncio.run(build_graph().ainvoke(initial_state(cfg, QUERY), graph_config(cfg, "test")))


def _reporter_request(log):
    (call,) = [c for c in log.records if c["role"] == "reporter"]
    return call["request"]


@pytest.fixture(scope="module")
def recorded(cfg):
    log, cas = CallLog(), Cassette("record")
    state = _run(cfg, Scripted(call_log=log, **deerflow_env.model_kwargs(cfg)), cas)
    assert state["final_report"].startswith("# Report")
    return log, cas, state


def test_replay_reproduces_every_role_handoff_without_live_tools(cfg, recorded):
    log, cas, state = recorded
    before = dict(LIVE)
    rlog = CallLog()
    model = ReplayChatOpenAI.from_records(log.records, rlog, **deerflow_env.model_kwargs(cfg))
    rcas = Cassette("replay", cas.records)
    replayed = _run(cfg, model, rcas)

    assert model.misses == [] and rcas.misses == []
    assert LIVE == before, "replay must not call live tools"
    assert replayed["current_plan"].model_dump() == state["current_plan"].model_dump()
    assert replayed["observations"] == state["observations"]
    assert _reporter_request(rlog) == _reporter_request(log)  # the boundary, byte-for-byte
    assert replayed["final_report"] == state["final_report"]
    assert [c["request_hash"] for c in rlog.records] == [c["request_hash"] for c in log.records]


def test_tampered_tool_response_is_detected_even_though_deerflow_swallows_it(cfg, recorded):
    log, cas, _ = recorded
    records = json.loads(json.dumps(cas.records))
    first_researcher_search = next(r for r in records
                                   if r["tool"] == "web_search" and (r.get("ns") or "").startswith("researcher"))
    first_researcher_search["content"] = first_researcher_search["content"].replace("71.2%", "91.2%")
    model = ReplayChatOpenAI.from_records(log.records, CallLog(), **deerflow_env.model_kwargs(cfg))

    with pytest.raises(LLMCacheMiss):  # finally surfaces at the reporter
        _run(cfg, model, Cassette("replay", records))
    # The first miss happened inside the researcher, where DeerFlow's
    # _execute_agent_step turns exceptions into an "[ERROR]" observation.
    assert len(model.misses) >= 2

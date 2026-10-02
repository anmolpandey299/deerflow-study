"""Strict tool record/replay: the properties the replay experiment relies on."""

import json

import pytest

from boundary_probe.cassette import Cassette, CassetteTool, ToolCacheMiss


def _record(calls):
    cas = Cassette("record")
    for tool, args, response in calls:
        cas.call(tool, args, lambda r=response: (r, None))
    return cas


def test_replay_returns_nth_recording_for_nth_identical_call():
    rec = _record([("web_search", {"query": "a"}, "first"),
                   ("web_search", {"query": "a"}, "second")])
    rep = Cassette("replay", rec.records)
    live_calls = []
    live = lambda: live_calls.append(1) or ("LIVE", None)  # noqa: E731
    assert rep.call("web_search", {"query": "a"}, live)[0] == "first"
    assert rep.call("web_search", {"query": "a"}, live)[0] == "second"
    assert live_calls == []  # replay never touches the live tool


@pytest.mark.parametrize("tool,args", [
    ("web_search", {"query": "b"}),          # new arguments
    ("crawl_tool", {"query": "a"}),          # same arguments, different tool
    ("web_search", {"query": "a "}),         # near-duplicate query is still a miss
])
def test_strict_replay_rejects_unrecorded_call(tool, args):
    rep = Cassette("replay", _record([("web_search", {"query": "a"}, "r")]).records)
    with pytest.raises(ToolCacheMiss):
        rep.call(tool, args, lambda: ("LIVE", None))
    assert len(rep.misses) == 1  # recorded even if a caller swallows the exception


def test_extra_occurrence_of_recorded_call_is_a_miss():
    rep = Cassette("replay", _record([("web_search", {"query": "a"}, "r")]).records)
    rep.call("web_search", {"query": "a"}, lambda: ("LIVE", None))
    with pytest.raises(ToolCacheMiss):
        rep.call("web_search", {"query": "a"}, lambda: ("LIVE", None))


def test_recorded_tool_error_is_replayed_as_the_same_exception_type():
    rec = Cassette("record")

    def boom():
        raise TimeoutError("upstream timed out")

    with pytest.raises(TimeoutError):
        rec.call("crawl_tool", {"url": "https://x.org"}, boom)
    rep = Cassette("replay", rec.records)
    with pytest.raises(TimeoutError, match="upstream timed out"):
        rep.call("crawl_tool", {"url": "https://x.org"}, lambda: ("LIVE", None))


def test_cassette_round_trips_through_disk(tmp_path):
    rec = _record([("web_search", {"query": "a"}, "r1")])
    rec.dump(tmp_path / "t.jsonl")
    rep = Cassette.load(tmp_path / "t.jsonl")
    assert rep.call("web_search", {"query": "a"}, lambda: ("LIVE", None))[0] == "r1"


def test_proxy_exposes_identical_tool_definitions_to_the_model(cfg):
    """The model must see byte-identical tool schemas with or without the proxy."""
    from langchain_core.utils.function_calling import convert_to_openai_tool
    from src.tools.crawl import crawl_tool
    from src.tools.search import get_web_search_tool

    for inner in (get_web_search_tool(3), crawl_tool):
        proxied = CassetteTool(inner, Cassette("record"))
        assert json.dumps(convert_to_openai_tool(proxied), sort_keys=True) == \
            json.dumps(convert_to_openai_tool(inner), sort_keys=True)
        assert proxied.response_format == inner.response_format


def test_concurrent_calls_get_unique_sequence_numbers():
    """Regression (amendment A4): parallel tool calls in one model turn run concurrently."""
    import threading
    import time

    cas = Cassette("record")
    barrier = threading.Barrier(6)

    def call(i):
        barrier.wait()
        cas.call("crawl_tool", {"url": f"https://x.org/{i}"}, lambda: (time.sleep(0.01) or f"page {i}", None))

    threads = [threading.Thread(target=call, args=(i,)) for i in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(r["seq"] for r in cas.records) == list(range(6))

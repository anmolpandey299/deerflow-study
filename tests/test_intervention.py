"""An intervention may change only its declared input."""

import copy
import json

import pytest

from boundary_probe.boundary import (OBS_PREFIX, build_replacement, build_variant, declared_diff,
                                     expected_diff, insertion_block,
                                     load_run, observation_indices, reporter_call)
from conftest import completed_runs

BASE = {
    "model": "m", "temperature": 0.7, "top_p": 0.8, "seed": 7, "stream": False,
    "messages": [
        {"role": "system", "content": "reporter prompt"},
        {"role": "user", "content": "# Research Requirements ..."},
        {"role": "user", "name": "observation", "content": OBS_PREFIX + "step 1 summary"},
        {"role": "user", "name": "observation", "content": OBS_PREFIX + "step 2 summary"},
        {"role": "user", "name": "system", "content": "## Available Source References ..."},
    ],
}
BLOCK = insertion_block("LongRAG reaches 62.7% EM on NQ.", "LongRAG", "https://arxiv.org/abs/2406.15319")


def test_repair_variant_differs_only_by_declared_block_and_seed():
    v = build_variant(BASE, 3, BLOCK, seed=101)
    assert declared_diff(BASE, v, 3, BLOCK) == []
    assert v["messages"][3]["content"].endswith(BLOCK) and v["seed"] == 101
    assert BASE["messages"][3]["content"] == OBS_PREFIX + "step 2 summary"  # base untouched


def test_condition_a_changes_only_the_seed():
    v = build_variant(BASE, None, "", seed=102)
    assert declared_diff(BASE, v, None, "") == []
    assert {k: v[k] for k in v if k != "seed"} == {k: BASE[k] for k in BASE if k != "seed"}


@pytest.mark.parametrize("tamper,expected", [
    (lambda v: v.__setitem__("temperature", 0.0), "payload field 'temperature' changed"),
    (lambda v: v["messages"][0].__setitem__("content", "other prompt"), "message 0 changed"),
    (lambda v: v["messages"][2].__setitem__("content", v["messages"][2]["content"] + " x"), "message 2 changed"),
    (lambda v: v["messages"][3].__setitem__("content", BLOCK + BASE["messages"][3]["content"]),
     "message 3 is not the base content plus exactly the declared block"),
    (lambda v: v["messages"].pop(), "message count 5 -> 4"),
])
def test_undeclared_changes_are_detected(tamper, expected):
    v = build_variant(BASE, 3, BLOCK, seed=101)
    tamper(v)
    assert expected in declared_diff(BASE, v, 3, BLOCK)


def test_block_can_only_target_an_observation_message():
    with pytest.raises(ValueError):
        build_variant(BASE, 1, BLOCK, seed=101)


@pytest.mark.parametrize("run_dir", completed_runs() or [pytest.param(None, marks=pytest.mark.skip("no recorded run"))])
def test_recorded_reporter_input_contains_each_researcher_handoff_verbatim(run_dir):
    """On real runs: the boundary we intervene on is exactly what DeerFlow handed over."""
    run = load_run(run_dir)
    req = reporter_call(run)["request"]
    idx = observation_indices(req)
    observations = run["final_state"]["observations"]
    assert len(idx) == len(observations)
    for i, obs in zip(idx, observations):
        assert req["messages"][i]["content"] == OBS_PREFIX + obs
    # and the raw response recorded for that request is the report DeerFlow returned
    assert reporter_call(run)["response"]["content"].strip() == run["report"].strip()
    json.dumps(copy.deepcopy(req))  # the payload is plain JSON, so replay posts it unchanged


def test_probe_e_replacement_changes_only_the_declared_observation():
    stub = "[No source-backed findings were produced for this step.]"
    v = build_replacement(BASE, 2, stub, seed=103)
    assert expected_diff(BASE, v, {2: OBS_PREFIX + stub}) == []
    assert v["messages"][3] == BASE["messages"][3]  # the other observation untouched
    v["messages"][3]["content"] += " x"
    assert "message 3 changed" in expected_diff(BASE, v, {2: OBS_PREFIX + stub})


def test_restored_fact_usage_ignores_bare_citation_lines():
    """u_B must not be inflated by the reporter merely listing the restored source."""
    from boundary_probe.replay_analysis import uses_fact
    cited_only = "## Key Citations\n- [LaRA: inconclusive RAG vs LC comparisons](https://x.org/lara)\n"
    used = cited_only + "\n## Analysis\nLaRA (2326 test cases) finds RAG-vs-LC comparisons inconclusive.\n"
    assert not uses_fact(cited_only, "LaRA", ["inconclusive", "2326"])
    assert uses_fact(used, "LaRA", ["inconclusive", "2326"])

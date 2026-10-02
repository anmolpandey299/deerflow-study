"""Fragile invariants of the Part 2 pilot (docs/part2_protocol.md §7). Offline."""

import copy
import json

import pytest

from boundary_probe.boundary import expected_diff
from boundary_probe.replay_reporter import ProvenanceError, check_provenance
from boundary_probe.settings import RUNS_DIR
from part2_pilot.pilot import build_case, variant
from part2_pilot.score import DETECT, window_hit


@pytest.mark.parametrize("case_id", ["c01", "c03", "c05"])
@pytest.mark.parametrize("arm", ["L", "LC"])
def test_variant_differs_only_by_declared_blocks(case_id, arm):
    bc = build_case(case_id)
    v, expected = variant(bc, arm, 101)
    assert set(expected) == {1, bc["obs_index"]}
    assert expected_diff(bc["base"], v, expected) == []
    # the original texts are untouched prefixes; only appended text differs
    for k, content in expected.items():
        assert content.startswith(bc["base"]["messages"][k]["content"])
    # a smuggled change anywhere else is caught
    bad = copy.deepcopy(v)
    bad["messages"][0]["content"] += " "
    assert expected_diff(bc["base"], bad, expected)


def test_entry_holds_passage_and_arms_share_the_template():
    bc = build_case("c05")
    case = bc["case"]
    assert "3 bits per value" in bc["entries"]["L"] and "3 bits" not in bc["entries"]["LC"]
    strip = lambda e, w: e.replace(case[w]["title"], "T").replace(case[w]["url"], "U")  # noqa: E731
    lines = lambda e: [ln for ln in e.splitlines() if not ln.startswith(">")]  # noqa: E731
    assert lines(strip(bc["entries"]["L"], "repair")) == lines(strip(bc["entries"]["LC"], "control"))


def test_provenance_rejects_an_edited_passage():
    bc = build_case("c03")
    spec = dict(bc["case"]["repair"], passage=bc["case"]["repair"]["passage"].replace("double", "triple"))
    with pytest.raises(ProvenanceError):
        check_provenance(bc["run"], spec)


def _part1(case_id, run_id, name):
    return json.loads((RUNS_DIR / run_id / "replays" / case_id / f"{name}.json").read_text())["content"]


def test_detector_window_on_known_part1_samples():
    c05 = "q03-r02-20260930T212748"
    # B-s102 states "3 bits" one sentence before naming TurboQuant (replay_notes c05)
    assert window_hit(_part1("c05", c05, "B-s102"), DETECT["c05"])
    # a sentence pairing TurboQuant with "6x" alone is not the restored fact
    assert not window_hit("Google's TurboQuant claims 6x memory reduction with zero accuracy loss.", DETECT["c05"])
    # c01 B-s103 names LaRA but misstates it (replay_notes c01)
    assert not window_hit(_part1("c01", "q01-r03-20260930T204051", "B-s103"), DETECT["c01"])
    assert not window_hit("Declarative pipelines are inconclusive.", DETECT["c01"])  # word-boundary anchor

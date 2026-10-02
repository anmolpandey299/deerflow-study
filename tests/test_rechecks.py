import pytest

from boundary_probe import rechecks


def test_clean_removes_dates_codes_and_versions_but_keeps_claims():
    text = ("Current Date: Wed Sep 30 2026 21:27:48. Connection refused (os error 61); Jina returned status 403. "
            "Licensed under Apache 2.0 or CC-BY-4.0. Medusa reaches a 2.3× speedup at 48% acceptance.")
    from boundary_probe.evidence import checkable_items
    assert checkable_items(rechecks.clean(text)) == ["2.3×", "48%"]


def test_specific_items():
    assert rechecks.specific("15%") and rechecks.specific("0.45") and rechecks.specific("512") and rechecks.specific("7B")
    assert not rechecks.specific("48") and not rechecks.specific("12")


def test_probabilities():
    assert rechecks.chance(0.5)["original_rule"] == pytest.approx(0.25)
    assert rechecks.chance(0.5)["a1_rule"] == pytest.approx(0.375)
    assert rechecks.h1b_fails(0.5) == pytest.approx(0.5)
    assert rechecks.fisher_one_sided(2, 13, 0, 30) == pytest.approx(105 / 990)
    assert rechecks.fisher_one_sided(2, 1, 1, 2) == pytest.approx(0.5)


@pytest.fixture(scope="module")
def runs():
    rs = rechecks.completed_runs()
    if len(rs) != 10:
        pytest.skip("needs the 10 completed runs under runs/")
    return rs


def test_variant_0_is_the_published_relay_table(runs):
    t = rechecks.relay(runs)["variant_0"]["totals"]
    assert (t["grounded_rep"], t["grounded_obs"]) == (33, 42)
    assert (t["warned_rep"], t["warned_obs"]) == (50, 56)


def test_report_numbers_variant_0_is_the_published_origin_table(runs):
    x = rechecks.report_numbers(runs)["variant_0"]
    assert (x["totals"]["unmatched"], x["totals"]["report_numbers"]) == (93, 132)
    assert (x["without_outage_run"]["unmatched"], x["without_outage_run"]["report_numbers"]) == (77, 116)


def test_crawl_and_citation_rechecks(runs):
    c = rechecks.crawl(runs)
    assert (c["crawls"], c["real_pages"], c["cut"]) == (28, 16, 16)
    assert rechecks.citations(runs)["from_crawls"] == rechecks.citations(runs)["citations"] == 27


def test_c03_insertions_follow_the_references_list():
    rows = {(x["case"], x["arm"]): x for x in rechecks.insertion_positions()}
    assert rows[("c03", "B")]["after_references_list"] and rows[("c03", "L")]["after_references_list"]
    assert not rows[("c05", "L")]["after_references_list"]

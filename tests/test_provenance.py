"""Source-to-citation links: passages, URLs and judge quotes must trace to raw records."""

import pytest

from boundary_probe.evaluate import quote_found
from boundary_probe.evidence import normalize_url, segments, url_provenance
from boundary_probe.replay_reporter import ProvenanceError, check_provenance

DDG = ("snippet: LongRAG reaches 62.7% EM on NQ, title: LongRAG paper, link: https://arxiv.org/abs/2406.15319, "
       "snippet: Self-Route cuts cost by 65%, title: Self-Route, link: https://example.org/self-route/")
RUN = {"run_id": "r", "llm_calls": [{"role": "researcher", "ns": "researcher:abc|model:1"}],
       "tool_calls": [
           {"seq": 0, "tool": "web_search", "args": {"query": "q"}, "ns": "researcher:abc|tools:9",
            "content": DDG, "artifact": None, "error": None},
           {"seq": 1, "tool": "crawl_tool", "args": {"url": "https://a.org/x"}, "ns": "researcher:abc|tools:9",
            "content": '{"url": "https://a.org/x", "crawled_content": "# Title X\\n\\nBody with 3x speedup."}',
            "artifact": None, "error": None}]}


def test_search_hits_become_individually_linked_segments():
    segs = segments(RUN)
    assert [(s["seg_id"], s["url"], s["step"]) for s in segs] == [
        ("0.0", "https://arxiv.org/abs/2406.15319", 0), ("0.1", "https://example.org/self-route/", 0),
        ("1.0", "https://a.org/x", 0)]
    assert segs[2]["title"] == "Title X"


def test_inserted_passage_must_be_verbatim_from_its_cited_segment():
    ok = {"seg_id": "0.0", "url": "https://arxiv.org/abs/2406.15319", "passage": "LongRAG reaches 62.7% EM"}
    assert check_provenance(RUN, ok)["tool_seq"] == 0
    with pytest.raises(ProvenanceError):  # paraphrase
        check_provenance(RUN, {**ok, "passage": "LongRAG gets 62.7% exact match"})
    with pytest.raises(ProvenanceError):  # right text, wrong source
        check_provenance(RUN, {**ok, "url": "https://example.org/self-route/"})
    with pytest.raises(ProvenanceError):  # text from a different segment
        check_provenance(RUN, {**ok, "passage": "Self-Route cuts cost by 65%"})


def test_report_urls_are_checked_against_retrieved_evidence():
    report = ("See [1](https://arxiv.org/abs/2406.15319). and https://www.example.org/self-route#sec, "
              "plus [made up](https://arxiv.org/abs/9999.99999).")
    prov = url_provenance(report, RUN)
    assert prov["report_urls"] == 3
    assert prov["fabricated_urls"] == [normalize_url("https://arxiv.org/abs/9999.99999")]


def test_judge_quotes_count_only_if_found_in_the_source():
    src = "**LongRAG** reaches 62.7% EM on NQ,\nwhile | Self-Route | cuts cost."
    assert quote_found("LongRAG reaches 62.7% EM on NQ", src)
    assert quote_found("LongRAG reaches ... cuts cost", src)
    assert not quote_found("LongRAG reaches 72.7% EM on NQ", src)
    assert not quote_found("EM", src)  # too short to be evidence


def test_numbers_match_by_value_and_identifiers_are_not_claims():
    from boundary_probe.evidence import checkable_items, item_present
    assert item_present("25k", "evaluated on 25,000 QA pairs")
    assert item_present("62.7%", "reaches 62.7 on NQ")
    assert item_present("62.7%", "reaches 62.71")  # a faithful rounding (A10)
    assert not item_present("62.7%", "reaches 62.76") and not item_present("62.7%", "reaches 62.8")
    assert checkable_items("see https://arxiv.org/abs/2406.15319 and doi 10.1145/3580305 in 2025: 3.5x faster") == ["3.5x"]


def test_quote_matching_tolerates_judge_unicode_but_not_changed_numbers():
    src = "Hybrid BM25 + dense retrieval is long-context friendly and reaches 62.7% EM on the NQ benchmark."
    assert quote_found("Hybrid\u202fBM25 + dense retrieval is long\u2011context friendly", src)
    # Tolerance is deliberate (A9): the quote only has to show the cited text exists; numbers must match.
    assert not quote_found("Hybrid BM25 + dense retrieval is long-context friendly and reaches 72.7% EM on NQ", src)


def test_judge_json_extraction_takes_the_final_object():
    from boundary_probe.evaluate import extract_json
    assert extract_json('reasoning {"x": 1} ... final:\n```json\n{"labels": [{"id": "R1"}]}\n```') == {"labels": [{"id": "R1"}]}


def test_judge_json_with_unescaped_inner_quotes_is_repaired():
    from boundary_probe.evaluate import extract_json
    bad = '{"labels": [{"id": "R1", "label": "FULL", "quote": "fall short of the ideal "Oracle Context.""}]}'
    out = extract_json(bad)
    assert out["labels"][0]["id"] == "R1" and out["labels"][0]["label"] == "FULL"


def test_judge_json_with_stray_quotes_between_array_items_is_recovered():
    """Literal pattern returned by gpt-oss in the A9 check."""
    from boundary_probe.evaluate import extract_json
    raw = ('{"labels":[{"id":"R1","label":"FULL","quote":"a"},{"id":"R2","label":"PARTIAL","quote":"b"},'
           '"{"id":"R3","label":"PARTIAL","quote":"c"}","{"id":"R4","label":"FULL","quote":"d"}]}')
    out = extract_json(raw)
    assert [x["id"] for x in out["labels"]] == ["R1", "R2", "R3", "R4"]


def test_tolerant_quote_match_accepts_paraphrase_but_not_changed_numbers():
    src = ("The absence of direct, side-by-side performance data across architectures was explicitly noted, "
           "with 62.7% accuracy reported only for one method.")
    assert quote_found("The lack of direct, side-by-side performance data across architectures was explicitly noted", src)
    assert not quote_found("with 72.7% accuracy reported only for one method and direct side-by-side data", src)
    assert not quote_found("Completely different sentence about vector databases and their operational cost profiles", src)


def test_number_matching_fixes_found_in_spot_check():
    """A10: false positives found by hand in q03-r02, q04, q05, q07."""
    from boundary_probe.evidence import checkable_items, item_present
    assert item_present("745B", "GLM-5: 745 billion parameters")            # number words
    assert item_present("47B", "Mixtral 8x7B has ~46.7B total parameters")   # rounding
    assert not item_present("46.7B", "Mixtral has ~47B parameters")          # the reverse is not rounding
    assert not item_present("1.3", "reported 1.8 ms per token")
    assert item_present("120B", "Download gpt-oss-120b and gpt-oss-20b")   # lower-case model sizes
    assert checkable_items("- [Qwen 3.8-27B on Hugging Face](https://hf.co/x) and [Mixtral 8x7B](https://y.org)") == []

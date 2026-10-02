"""The synthetic defects must remove exactly what they claim to remove."""

import pytest

from boundary_probe.probes import remove_facet, replace_once, strip_structure

REPORT = """# Title

## Key Points

- Method A has lower latency than B.
- Method B costs $2 per 1k queries.

| Method | Accuracy | Latency | Cost |
|---|---|---|---|
| A | 71% | 120 ms | $1 |
| B | 75% | 300 ms | $2 |
"""


def test_facet_removal_drops_matching_lines_and_table_columns_only():
    out = remove_facet(REPORT, r"cost|\$")
    assert "costs" not in out and "$" not in out and "| Cost" not in out
    assert "## Key Points" in out and "lower latency" in out
    assert "| A | 71% | 120 ms |" in out and "| Method | Accuracy | Latency |" in out


def test_structure_removal_keeps_content_but_no_markup():
    out = strip_structure(REPORT)
    assert "#" not in out and "|" not in out and "- " not in out
    assert "Method A has lower latency than B." in out and "B; 75%; 300 ms; $2" in out


def test_replacement_must_target_a_unique_span():
    assert "C has" in replace_once(REPORT, "Method A has", "C has")
    with pytest.raises(ValueError):
        replace_once(REPORT, "Method", "X")  # ambiguous target


def test_probes_main_reads_relative_spec_before_chdir(tmp_path, monkeypatch):
    """Regression: deerflow_env.prepare() changes the working directory; a relative spec path must still work."""
    import os
    import sys

    import yaml

    from boundary_probe import deerflow_env, evaluate, probes, settings
    from tests.conftest import completed_runs

    run_id = completed_runs()[0].name
    (tmp_path / "probes").mkdir()
    (tmp_path / "probes" / "spec.yaml").write_text(yaml.safe_dump(
        {"reports": [{"run_id": run_id, "defects": [{"name": "D3_strip_structure", "kind": "D3"}]}]}))
    (tmp_path / "elsewhere").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "ANALYSIS_DIR", tmp_path / "out")
    monkeypatch.setattr(deerflow_env, "prepare", lambda cfg: os.chdir(tmp_path / "elsewhere"))
    monkeypatch.setattr(evaluate, "Judge", lambda cfg, model: None)
    monkeypatch.setattr(evaluate, "evaluate", lambda text, run, q, cfg, judge: {
        "fmt": {"score": 1.0}, "comp": {"score": 0.5}, "fact_claims": {"score": 0.5}})
    monkeypatch.setattr(probes, "deerflow_judge", lambda text, query, cfg, model: {"scores": {}})
    monkeypatch.setattr(sys, "argv", ["probes", "probes/spec.yaml", "--judge-model", "stub"])
    probes.main()
    assert (tmp_path / "out" / "probes" / run_id / "D3_strip_structure.json").exists()


LEAKY = """# Latency and cost of methods

## Latency results

| Method | Accuracy | Latency | Limitations |
|---|---|---|---|
| A | 71% | 120 ms | not designed for low-latency use |
| B | 75% | 300 ms | memory heavy |
"""


def test_facet_removal_default_keeps_cells_strict_blanks_them():
    loose = remove_facet(LEAKY, r"latenc")
    assert "| Latency" not in loose and "low-latency" in loose  # the registered D1's leak (A17)
    strict = remove_facet(LEAKY, r"latenc", strict=True)
    assert "latenc" not in strict.lower().split("\n", 1)[1]  # nothing left below the title
    assert strict.startswith("# Latency and cost of methods")  # the title is kept
    assert "memory heavy" in strict and "| A | 71% |" in strict

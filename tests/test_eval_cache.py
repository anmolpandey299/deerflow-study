"""A stored evaluation is reused only if report, evaluator, judge model and judge settings all match."""

import json

from boundary_probe import evaluate as ev


def test_eval_cache_requires_same_judge_settings(tmp_path, cfg, monkeypatch):
    calls = []

    def fake_evaluate(report, run, query, cfg, judge):
        calls.append(1)
        return {"evaluator": ev.EVALUATOR, "report_sha256": ev.sha256_text(report),
                "judge_model": judge.model, "judge_settings": ev.judge_settings(judge)}

    monkeypatch.setattr(ev, "evaluate", fake_evaluate)
    out = tmp_path / "baseline.json"
    ev._eval_one("a report", {}, {}, cfg, "gpt-oss:20b", out, {})
    ev._eval_one("a report", {}, {}, cfg, "gpt-oss:20b", out, {})
    assert len(calls) == 1  # identical inputs and settings: reused

    stale = json.loads(out.read_text())
    stale["judge_settings"]["think"] = "low"  # e.g. a result made before amendment A9
    out.write_text(json.dumps(stale))
    ev._eval_one("a report", {}, {}, cfg, "gpt-oss:20b", out, {})
    assert len(calls) == 2  # different settings: recomputed

    ev._eval_one("another report", {}, {}, cfg, "gpt-oss:20b", out, {})
    assert len(calls) == 3  # different report: recomputed

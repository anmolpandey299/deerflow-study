# Commands executed (chronological; working directory `/Users/anmol/imperial/t1`)

`PY=vendor/deer-flow-1x/.venv/bin/python`. Times are local (UTC+1) on 2026-09-30.

## Environment and audit
```bash
git clone --branch main-1.x --single-branch https://github.com/bytedance/deer-flow.git vendor/deer-flow-1x   # HEAD 2ab2876
git clone --depth 1 --branch v2.1.0 https://github.com/bytedance/deer-flow.git vendor/deer-flow-2x           # audit only
python3 -m venv .venv && .venv/bin/pip install --upgrade pip uv
(cd vendor/deer-flow-1x && UV_HTTP_TIMEOUT=120 ../../.venv/bin/uv sync --frozen --python 3.13 --extra test)
ollama pull qwen3:4b-instruct-2507-q4_K_M
ollama create dfprobe-qwen3-4b-ctx40k -f experiments/ollama/Modelfile.dfprobe-qwen3-4b-ctx40k   # re-created once, adding num_predict (A2)
ollama pull gpt-oss:20b                                                                          # interrupted by the outage, resumed
```
The following were run as inline Python and curl commands; the output is summarised in the protocol and results:
- smoke tests of tool calling, long-context needle recovery, log-probs, prefill and decode speed;
- a flash-attention benchmark on a temporary server on port 11435, which was stopped afterwards;
- checks that DuckDuckGo, arXiv and Jina work without keys.

## Agent runs
```bash
$PY -m boundary_probe.run_query q01 --tag r01   # 20:13, harness error, excluded (A1)
$PY -m boundary_probe.run_query q01 --tag r02   # 20:16, pilot, completed
# batch.sh: q02 r01, q03 r01, q04..q08 r01, q01 r03 (20:28-20:50); q04..q08 r01 failed in the outage (A5)
# batch4.sh: q04 r02, q05 r02, q06 r02, q07 r02, q08 r02, q03 r02 (20:52-)
```

## Tests and analysis
```bash
$PY -m pytest tests/ -q -p no:cacheprovider
$PY -m boundary_probe.candidates runs/<run_id> ...        # for each completed run
$PY -m boundary_probe.tables
$PY -m boundary_probe.evaluate runs/q01-r02-20260930T201622                       # deterministic checks
$PY -m boundary_probe.evaluate runs/q01-r02-20260930T201622 --judge-model gpt-oss:20b   # judge smoke test (found A9 issues)
```

## Main batch, checks and replays (continued)
```bash
# batch4.sh (sequential; connectivity check before each run):
$PY -m boundary_probe.run_query q04 --tag r02   # likewise q05, q06, q07, q08, then q03, all with tag r02
$PY experiments/ollama_truncation_check.py      # default-context truncation (21:38)
$PY experiments/judge_config_check.py           # three judge settings; re-run after the JSON fixes (A9)
# replays.sh:
$PY -m boundary_probe.replay_reporter analysis/cases/c0{1..5}.yaml --reproduce   # H1, one case at a time
$PY -m boundary_probe.replay_reporter analysis/cases/e0{1..4}.yaml               # probe E
$PY -m boundary_probe.candidates runs/<each completed run>
$PY -m boundary_probe.tables
```

## Judge phase, audit and analysis (from 2026-10-01 00:00 local; times below are UTC)
```bash
ollama create dfprobe-gptoss-20b-ctx32k -f experiments/ollama/Modelfile.dfprobe-gptoss-20b-ctx32k   # in-repo judge tag (A12), 22:59 UTC
$PY -m pytest tests/ -q                                            # 48 passed (adds test_eval_cache.py, test_audit.py)
$PY -m boundary_probe.replay_analysis                              # re-run after each replay case
$PY -m boundary_probe.audit build analysis/audit/spec.yaml         # 21 packets, 23:01 UTC
$PY -m boundary_probe.audit export <scratchpad>/audit_packets      # 2 auditor directories, 12 packets each, 3 shared (A13)
# two blinded general-purpose AI sub-agents, prompt = analysis/audit/auditor_task.md + directory, packet list, output path
# judge_phase.sh, started automatically once replays.sh finished (after_replays.sh; run under `caffeinate -is`), 23:44Z:
$PY experiments/judge_truncation_check.py
# ...its probes step crashed (working-directory bug, A14); the phase was stopped and restarted as judge_phase2.sh (23:46Z), probes first:
$PY -m boundary_probe.probes analysis/probes/spec.yaml --judge-model gpt-oss:20b --in-repo-judge-model dfprobe-gptoss-20b-ctx32k
$PY -m boundary_probe.evaluate runs/q01-r03-* runs/q04-r02-* runs/q05-r02-* runs/q06-r02-* runs/q03-r02-* --replays --seeds 101 --cases c01 c02 c03 c04 c05 --judge-model gpt-oss:20b
$PY -m boundary_probe.evaluate runs/q01-r02-* runs/q02-r01-* runs/q04-r02-* runs/q05-r02-* --replays --seeds 101 --cases e01 e02 e03 e04 --judge-model gpt-oss:20b
$PY -m boundary_probe.evaluate <the 10 completed runs> --judge-model gpt-oss:20b     # baselines
$PY -m boundary_probe.audit score
```

## After the judge phase (UTC)
```bash
# judge_phase2.sh baselines step: the q07-r02 Completeness call did not finish; client stopped at 03:08Z (A18)
# post_judge.sh (03:08Z):
$PY experiments/planted_claim_check.py                                   # A15
$PY -m boundary_probe.probes analysis/probes/spec_a17.yaml --judge-model gpt-oss:20b --in-repo-judge-model dfprobe-gptoss-20b-ctx32k   # A17
$PY -m boundary_probe.probes summary
$PY experiments/judge_retest.py
$PY -m boundary_probe.audit score
$PY -m boundary_probe.tables
$PY -m boundary_probe.replay_analysis
# last_baselines.sh (03:19Z), with a watchdog stopping any q07 call that runs past 15 min (A18):
$PY -m boundary_probe.evaluate runs/q08-r02-* --judge-model gpt-oss:20b
$PY -m boundary_probe.evaluate runs/q07-r02-* --judge-model gpt-oss:20b   # one retry
$PY experiments/planted_claim_check.py --originals                       # A15 addendum (D2b control)
$PY -m pytest tests/ -q                                                  # final: see results / completion report
```

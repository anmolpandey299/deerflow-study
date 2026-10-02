# Evidence index for `submission/part1.md`

This index maps every evidence ID in `part1.md` and in the final report (supplied separately) to its exact records. Each ID has an anchor, so `evidence-index.md#e11` links to E11. It also holds two sections moved out of `part1.md`: the claim-to-evidence checklist and the differences from the internal documents.

- **Records.** Paths are relative to the repository root. The records are under `runs/` and `analysis/`, and `RECORDS.sha256` at the repository root lists their hashes, together with those of the pilot's outputs. The Part 1 review archive, `t1-part1-review.tar.gz` (SHA-256 `b8faa7a60aa9d849fb1630c44dfd2bbaf685755244549ea360aafee240e9032e`), is distributed separately; its folder `t1-part1-review/` holds the original versions of the same paths.
- **Corrections.** Rows changed by the integrity review of 2026-10-01 or the reconciliation with the final report of 2026-10-02 say so; the full study archive's `docs/corrections.md` lists every change, and `analysis/rechecks.md` holds the recomputations.
- **Omitted notes.** Paths under `docs/` below, such as the protocols, results and analysis notes and reference checks, name files in the full study archive, which this repository release omits.
- **`<run>`** stands for any of the 10 completed runs:
  - `q01-r02-20260930T201622`;
  - `q01-r03-20260930T204051`;
  - `q02-r01-20260930T202824`;
  - `q03-r01-20260930T203551` (degraded by the outage);
  - `q03-r02-20260930T212748`;
  - `q04-r02-20260930T205216`;
  - `q05-r02-20260930T205952`;
  - `q06-r02-20260930T210856`;
  - `q07-r02-20260930T211445`;
  - `q08-r02-20260930T212058`.
- **Replay cases and their runs:**
  - c01 → q01-r03, c02 → q04-r02, c03 → q05-r02, c04 → q06-r02, c05 → q03-r02;
  - e01 → q01-r02, e02 → q02-r01, e03 → q04-r02, e04 → q05-r02.
- **Judges.** The brief's benchmark judge was unavailable, so no benchmark score exists. Two local judges were tested, both on `gpt-oss:20b`:
  - **the proxy evaluator**, `boundary_probe/evaluate.py`. It has deterministic format checks, and LLM calls for completeness and claim support. Claim support checks at most `max_claims` = 10 claims per report (`experiments/config.yaml`).
  - **DeerFlow's in-repo `LLMJudge`** (K4), run through the Ollama tag `dfprobe-gptoss-20b-ctx32k`. Its Modelfile, `experiments/ollama/Modelfile.dfprobe-gptoss-20b-ctx32k`, reads `FROM gpt-oss:20b` with `num_ctx 32768`.

## Empirical claims (E)

| ID | Claim | Exact record(s) | How to check / caveat |
|---|---|---|---|
| <a id="e1"></a>E1 | No run had a second planning round. | `runs/<run>/raw/final_state.json`: `current_plan.has_enough_context`, `plan_iterations` | Both are false and 1, respectively, in all 10 runs. |
| <a id="e2"></a>E2 | 10 of 16 attempts completed. The outage crashed 5 (plus 1 harness error), and degraded 1 completed run whose 7 URLs were never retrieved. | `runs/*/raw/manifest.json` (`status`); `EXCLUDED.txt` in `runs/q01-r01-*` and `runs/q0[4-8]-r01-*`; `runs/q03-r01-20260930T203551/FLAG_OUTAGE_AFFECTED.txt`; `analysis/tables/origins.csv` (q03-r01: `report_urls` 7, `unretrieved_urls` 7) | The outage's timing is recorded in protocol A5 and its erratum. |
| <a id="e3"></a>E3 | Per trajectory: 435 s (254–573), 12.7 model calls, 61,805 prompt + 8,316 generated tokens, 8.1 tool calls. | `analysis/tables/costs.csv`, rows with `status` = completed | Tool calls = `search_calls` + `crawl_calls`. Tokens per trajectory: 61,805 + 8,316 = 70,121, of which 88% are prompt. The §7 figure "about 4.9k prompt tokens per call" is 61,805 / 12.7. |
| <a id="e4"></a>E4 | Shares of generated tokens: reporter 41%, researcher 34%, analyst 17%, planner 7.5%, coordinator 0.7%. | `runs/<run>/raw/llm_calls.jsonl`: `role`, `completion_tokens` | Mean of per-run shares. Not archived as a table; recomputed for this submission, and it matches `docs/part1_analysis.md` §3.6. |
| <a id="e5"></a>E5 | About three-quarters of the characters in researcher prompts are re-appended system prompts: mean 77%, range 67–87% by run. | `runs/<run>/raw/llm_calls.jsonl`: researcher `request.messages` with role `system`; `analysis/rechecks.md` | **A character share** (corrected 2026-10-01 from "prompt tokens"). Token counts per message were not recorded, and the original 75% (66–85%) estimate cannot be reproduced. |
| <a id="e6"></a>E6 | 93 of 132 report numbers are unmatched: 47 first appear in steps that never searched, 21 in the analyst, 8 in searched steps, 17 in the report. 26 of 80 URLs were never retrieved. | `analysis/tables/origins.csv` (column sums); method in `boundary_probe/evidence.py` and `boundary_probe/tables.py`; `analysis/rechecks.md` | **A provenance metric, not an error rate.** Rechecked 2026-10-01 under E10's stricter item definitions: 73–78% unmatched (74 of 101 at the strictest). Without the outage-degraded run q03-r01: 77 of 116 numbers and 19 of 73 URLs. The A10 spot check (14 of 15 flags correct) is recorded only in protocol A10; the sampled items are not archived. |
| <a id="e7"></a>E7 | Later research steps skipped search in 8 of 14 cases. A later step that skipped search used a median of 1 model call, 2,894 prompt tokens and 49 s of model time; one that searched used 4.5 calls, 24,286 prompt tokens and 108 s. | `analysis/tables/researcher_steps.csv`: rows with `step` > 0, column `searched`; `runs/<run>/raw/llm_calls.jsonl` (researcher calls grouped by step); `analysis/rechecks.md` | `searched` is False in 8 of the 14 rows (and True in all 10 first steps). The step costs are post hoc, added 2026-10-01. |
| <a id="e8"></a>E8 | The recursion-limit fallback fired in 4 runs; 3 passed on a tool-call string. | `runs/{q03-r02,q04-r02,q06-r02,q08-r02}-*/raw/deerflow.log` ("Recursion limit reached for researcher agent"); `analysis/tables/costs.csv` `step_kinds` ("unparsed tool call") | |
| <a id="e9"></a>E9 | The model saw 4.8% of crawled text (19,930 of 419,236 characters, 28 crawls). 16 of the 28 crawls returned page content, and every one of those 16 pages was cut; the median one was 7.9% visible (0.8%–60%). Over all 28 crawls the median share shown is 51.5%. 4 of the 10 completed runs had no crawl that returned content. | `analysis/tables/crawl_truncation.csv`; `runs/<run>/raw/crawl_fulltext.jsonl` (`full_chars`, `shown_chars`); `analysis/rechecks.md` | The pooled share is dominated by five long pages holding 78% of the characters. The other 12 crawls were error, CAPTCHA, 404 or empty pages, shown in full. Page-level figures added 2026-10-01. The all-crawl median and the per-run count were added 2026-10-02 (post hoc): the runs without content are q01-r03 and q07-r02 (no crawls), q03-r02 (three arXiv blocks) and q06-r02 (an empty page and a CAPTCHA). |
| <a id="e10"></a>E10 | Relay to the report, rechecked: 45 of 51 numbers (88%) from steps DeerFlow flagged as never having searched, and 23 of 26 (88%) numbers that retrieved text supports. No contrast between them is supported. | `analysis/tables/relay.csv` (column sums; `warned_observations`); `analysis/rechecks.md` | Post hoc. A rate conditional on presence in a summary; not isolated from other routes (E24). **Recheck, 2026-10-01:** the items first published, 50/56 (89%) and 33/42 (79%), included dates and clock times, an error code, licence versions and same-value duplicates; those figures are withdrawn. Without them, and without unitless integers below 100, the two rates are equal. 44 of the 51 flagged-step numbers come from q02-r01 and q04-r02. |
| <a id="e11"></a>E11 | H1a: in 6 of 9 eligible runs, requirement-relevant text that a researcher received was missing from its step summary. The summary dropped it in 3 runs; in 3 the fallback replaced the summary with a tool call written as text. Five of the six passages were search snippets (c01–c05); one, in q08-r02, was text from a crawled page. | `analysis/cases/review_log.md`; `analysis/candidates/*.json`; `analysis/cases/c0*.yaml` (`repair.tool` is `web_search` in all five); `runs/<run>/raw/crawl_fulltext.jsonl`; `runs/q08-r02-20260930T212058/raw/llm_calls.jsonl` (reporter request) | Pre-registered rule: protocol §6. **Added 2026-10-02 (post hoc):** the pages of c01, c03, c04 and c05 were never crawled, and c02's crawl returned no content (56 characters). The q08-r02 passage starts 218 characters into a crawled page, inside the 1,000 characters the researcher saw; only the page's first 150 characters reached the reporter, through the citation list, and they end before it. Whether that passage could meet a requirement's acceptance criterion was not assessed, so 6 of 9 is not a count of lost admissible evidence. |
| <a id="e12"></a>E12 | H1b rules and outcome. The fixed detector classified 4 cases as insensitive and 1 (c05) as an effect, so H1b failed by its pre-registered rule. A later, unblinded model-based reading (post hoc) found the c05 verdict to be a false positive, leaving all 5 insensitive. Byte reproduction 5/5. | `analysis/replays.json` (`usage_rate`, `verdict`, `reproduces_original`); `runs/<run>/replays/c0*/{A,B,C}-s10[1-3].json`, `A-s7.json`, `replay_manifest.json`; detectors in `analysis/cases/c0*.yaml` (`usage_detect`); `analysis/cases/replay_notes.md` (sections "c05" and "H1b across the five cases") | Rules: protocol §5, "Decision rules, fixed in advance". The c05 keyword list, including "6x", was fixed before any replay (replay_notes.md, c05, "Detector design caveat"). `replays.json` keeps the computed verdict, "evidence-specific effect". It was a post-hoc, unblinded model-based reading, not a person's (wording corrected 2026-10-02 from "manual reading"). |
| <a id="e13"></a>E13 | Correct statements in 2 of 15 B samples (c04 B-s103; c05 B-s102, missed by the detector) and 0 of 30 A/C samples. B appended the passage at the end of the step's observation: after the References list in c01–c03, and as the whole observation in c04–c05, where both correct statements occurred. The audit found 0 of 5 B reports correct. Salience: c04's true title appears in 3/3 B samples vs 0/6 A/C, and c05's source is discussed in 3/3 vs 0/6. An invented title sits on a real paper's URL. | `analysis/cases/replay_notes.md` (sections c04, c05, "H1b across the five cases", and Corrections 1–2); `analysis/audit/unblinded.json` (`summary.target_fact_vs_detector`); `runs/q06-r02-20260930T210856/raw/llm_calls.jsonl` (reporter call, step-1 References); `runs/q06-r02-20260930T210856/replays/c04/*.json` | The model-based reading is qualitative (wording corrected 2026-10-02 from "hand reading"). |
| <a id="e14"></a>E14 | Probe E: unmatched numbers vanish with their step (3/3, e.g. 16 → 0); a ratings table was rebuilt (2/3). | `analysis/replays.json` (e01–e04: `samples` A/D/G, `mean_primary`, `verdict`); `runs/<run>/replays/e0*/{A,D,G}-s10[1-3].json`; `analysis/cases/e0*.yaml` | Exploratory (protocol A7, A8). D stubs the target step; G stubs a control step. |
| <a id="e15"></a>E15 | Variance on an unchanged input: format 1.0/0.25/1.0; rating cells 6/20/7; self-invented numbers 2/7/1. | `analysis/replays.json`: c03 condition A `fmt`; e02 A `rating_cells`; e03 A `reporter_originated_items` (seeds 101–103) | |
| <a id="e16"></a>E16 | Proxy probes. Format 3/3; clean facet removal 3/4 (registered edit 1/4). **Six factuality probes**: D2, three irrelevant but evidence-supported sentences; D2b, three attribution swaps. Of these, 1 was selected for checking, and that case was uninformative. Given directly, the D2 sentences were SUPPORTED 3/3 and the D2b swaps NOT_FOUND 3/3, with only one informative control. COMP moved ±0.25 under irrelevant edits. | `analysis/probes/summary.md` and `.json` (`detection`, `comp`); `analysis/probes/<run>/*.{json,md,diff}`; `analysis/probes/planted_claim_check.json` (`rows`; `originals.rows`); `analysis/probes/spec.yaml` (`kind` D2/D2b; each D2 `note` names its source segment), `spec_a17.yaml`; scoring in `boundary_probe/evaluate.py:225–251` (`factuality`) | The selected probe is q02-r01's D2b ("extracted, labelled NOT_FOUND"). It is uninformative because that report's unedited original had 10 of 10 claims NOT_FOUND (`analysis/probes/q02-r01-20260930T202824/original.json`). The originals of the three D2b swaps were SUPPORTED only for q01-r02. FACT-b is the share of checked claims labelled SUPPORTED with a verified quote. |
| <a id="e17"></a>E17 | In-repo judge: weighted 6.8–8.35 over the 15 registered variants, and 5.8 on the corrected facet removal; 8/10 factual accuracy for the pilot. | `analysis/probes/summary.json` (`dj_weighted`); `analysis/probes/q01-r02-20260930T201622/original.json` (`deerflow_llm_judge.scores`; `deerflow_llm_judge_model` = `dfprobe-gptoss-20b-ctx32k`) | |
| <a id="e18"></a>E18 | Default Ollama context: 4,096 tokens kept and the needle lost. With a pinned context: 7,501 (agent) and 6,831 (judge path), needle recovered. | `analysis/ollama_truncation_check.json`; `analysis/judge_truncation_check.json` | |
| <a id="e19"></a>E19 | Judge repeatable within a session (3 reports identical) but not across sessions (R8 label changed). | `analysis/judge_retest.json`; `analysis/judge_config_check.json` (free+think_medium, q01-r02) vs `analysis/probes/q01-r02-20260930T201622/original.json` | |
| <a id="e20"></a>E20 | Removing invented numbers lowered COMP in 3 of 3 cases and never raised FACT-b. | `analysis/evals/{q02-r01…/e02,q04-r02…/e03,q05-r02…/e04}/{A,D,G}-s101.json` (`comp.score`, `fact_claims.score`) | Single samples (seed 101). |
| <a id="e21"></a>E21 | Audit: 23 of 120 claim labels supported (19%), 13 misattributed; ρ = 0.49 against the proxy; the c04 DOI finding. | `analysis/audit/labels_auditor1.json`, `labels_auditor2.json`, `key.json`, `assignment.json`, `unblinded.json`, `packets/*.md` | Blinded model-based labels from language-model sub-agents, not human ones. 120 labels = 24 auditor–packet label sets × 5 claims; the 24 cover 21 reports, 3 of them labelled by both auditors. ρ is Spearman over those 24 pairs, against single-seed proxy scores. |
| <a id="e22"></a>E22 | Baseline proxy scores (COMP 0.50–0.75 strict; FACT-b 0 in 5 of 9); q03-r01 scored 0.50 strict / 0.79 lenient; q07-r02 unscored. | `analysis/tables/baseline_scores.csv`; `analysis/evals/<run>/baseline.json` (9 runs) | **No q07-r02 evaluation exists** (protocol A18; its logs were not archived). |
| <a id="e23"></a>E23 | Replay median 99 s (86 replays); judge calls average 69 s (162 calls). | `runs/<run>/replays/*/*-s*.json` (`wall_s`, `usage`); `analysis/tables/judge_costs.csv` | 86 = 5 cases × 10 (A ×4 including `A-s7`, B ×3, C ×3) + 4 cases × 9 (A, D, G ×3). The §7 judging time is 102,400 reports × (95.7 + 52.5 + 57.6) s ≈ 244 days. |
| <a id="e24"></a>E24 | Only the planner reads the background search (K13). In 3 of 10 runs, its thought passes a quantitative claim from that search to the reporter without a source. The "6x" claim appears in c05 B-s101 and B-s103, and in no A or C sample. | `runs/<run>/raw/final_state.json`: `current_plan.thought` and `background_investigation_results`, for q02-r01 ("2–3x faster"), q03-r02 ("Google's TurboQuant claiming 6x memory reduction with zero accuracy loss") and q04-r02 ("a cost per token between half and one quarter of a dense model's active size"); `analysis/cases/replay_notes.md` ("A structural finding from c05" and "c05") | **Post hoc; re-counted for this submission.** No thought contains a URL. q04-r02's thought restates its source ("between a dense model half its active size and one quarter its total size") inexactly. `replay_notes.md` counts thoughts with numerals instead: 4 of 10, namely q02-r01, q03-r02, q07-r02 and q08-r02. Of those, q07-r02's "10B" echoes the query and is absent from its background search, contrary to the notes' "all four"; q08-r02's "10M to 100M vectors" is a planning range, not a claim. |

## Source facts (K): DeerFlow `main-1.x` @ `2ab28765803d4d9582aaa8f2f3355137d154e273`

These files are not in the archive; check them against a clone at that commit.

| ID | Fact | Lines |
|---|---|---|
| <a id="k1"></a>K1 | After `max_plan_iterations`, the graph goes to the reporter. `has_enough_context` routes before research. The pinned value is 1, DeerFlow's default. With a higher value, the Planner, called again after research, would make the stop/continue decision. | `src/graph/nodes.py:317–321`, `377–386`; `src/config/configuration.py:48`; `src/graph/builder.py:23–47`; `experiments/config.yaml` |
| <a id="k2"></a>K2 | The reporter receives: the plan title and thought; one message per step summary; and a citation list giving title, URL, domain and the first 150 characters of each description. It does not receive the query verbatim or the step list; in all 10 runs the thought restated the query and its comparison axes. Only crawled pages become citations, because DuckDuckGo's plain-text output is not parsed (all 27 citations are crawls). | `src/graph/nodes.py:881–889`, `895–912`, `913–938`; `src/citations/extractor.py:86–96`, `312`; `analysis/rechecks.md` |
| <a id="k3"></a>K3 | Crawled pages are cut to 1,000 characters. | `src/tools/crawl.py:60` |
| <a id="k4"></a>K4 | The in-repo judge sees only the query and report, truncates at 15,000 characters, and returns 5s if parsing fails. | `src/eval/llm_judge.py:185–196`, `22`, `150–163` |
| <a id="k5"></a>K5 | The recursion-limit fallback re-calls the model without tools. | `src/graph/nodes.py:1007–1077` (tools stripped at 1055–1059) |
| <a id="k6"></a>K6 | The background search call is unguarded. | `src/graph/nodes.py:256–260` |
| <a id="k7"></a>K7 | Every role uses the same model. | `src/config/agents.py:10–21` |
| <a id="k8"></a>K8 | "Never invent or extrapolate data"; "Include detailed tables … statistical data". | `src/prompts/reporter.md:246`, `266` |
| <a id="k9"></a>K9 | "Even if you're 90% certain … choose to gather more". | `src/prompts/planner.md:44` |
| <a id="k10"></a>K10 | The system prompt is returned as a new message on every turn. | `src/agents/agents.py:32–43` |
| <a id="k11"></a>K11 | If the plan is not valid JSON in the first iteration, the run ends with no report. | `src/graph/nodes.py:340–371` |
| <a id="k12"></a>K12 | With clarification disabled (our setting), the coordinator ends the run unless it calls `handoff_to_planner`. | `src/graph/nodes.py:621–651`, `805–846`; `experiments/config.yaml` (`enable_clarification: false`) |
| <a id="k13"></a>K13 | Only the planner reads the background search. Citations are extracted only from research-step tool calls. | `src/graph/nodes.py:295–307`, `1332–1348` |

## Not archived, or never produced

- **q07-r02 baseline judge score:** never produced (E22).
- **Orchestration and Ollama logs:** excluded as scratch. They are the only first-hand records of the A14 and A18 timings and the replay slowdown note.
- **Auditor transcripts:** not kept; only the labels are.
- **A10 spot-check items:** not archived.
- **The original method behind the 75% estimate (E5):** not archived.
- **Benchmark-judge scores:** never produced; the judge was unavailable.

## Claim-to-evidence checklist (moved from `part1.md`)

Every ID below is cited in `part1.md`, and every ID cited there is defined above. "C1"–"C7" are the challenges in §5 of `part1.md`, not the final report's contrasts C1–C6 (its C1 is the fixed-retrieval handoff test) or Part 2's components C1–C8.

| ID | Claim | Cited in |
|---|---|---|
| E1 | No second round | §1, C3 |
| E2 | Attempts and outage | §6, C5 |
| E3 | Trajectory costs | §7 |
| E4 | Token shares | §2 |
| E5 | System-prompt share (estimate) | §7 |
| E6 | 93/132 unmatched numbers | C4 |
| E7 | Later steps skipping search (`searched`) | C1, C2 |
| E8 | Recursion-limit fallbacks | C1, C6 |
| E9 | Crawl cut | C5 |
| E10 | Relay rates | C1, C2, C4, §6 |
| E11 | H1a | §3, C1, §6 |
| E12 | H1b rules, detector false positive, byte reproduction | §0, §6 |
| E13 | 2/15; audit; salience; invented title | §0, §3, C1, C4, §6 |
| E14 | Probe E | C4, §6 |
| E15 | Reporter variance | §4 |
| E16 | Proxy probes; six factuality probes | §0, C2 |
| E17 | In-repo judge | C2 |
| E18 | Truncation | §7 |
| E19 | Repeatability | C2 |
| E20 | Completeness rewards invented numbers | C2, C4 |
| E21 | Audit | C4 |
| E22 | Baseline scores; q07-r02 unscored | C2, C5 |
| E23 | Replay and judge costs | §7 |
| E24 | Planner-thought route | §0, C1, §9 |
| K1 | No post-research decision | §0, §1, C3 |
| K2 | Reporter's view | §1, C1 |
| K3 | Crawl cut | C5 |
| K4 | In-repo judge inputs | §0, C2 |
| K5 | Recursion-limit fallback | C1 |
| K6 | Unguarded background search | C5 |
| K7 | One model for all roles | §1, C6 |
| K8 | Reporter prompt | C4 |
| K9 | Planner prompt | C3 |
| K10 | Re-appended system prompt | §2, §7 |
| K11 | Unparsed plan ends the run | §1, C6 |
| K12 | Coordinator without handoff ends the run | §1, C6 |
| K13 | Background search read only by the planner | C1 |

## Differences from the internal documents (moved from `part1.md`)

The internal documents are `docs/part1_analysis.md`, `docs/part1_results.md`, `docs/part1_protocol.md` and `analysis/cases/replay_notes.md`. Since 2026-10-01 they carry dated corrections (`docs/corrections.md`), which bring items 7 and 9 below into line with `part1.md`; their original text is in the Part 1 review archive. `part1.md` differs from their original text as follows.

1. **The stop/continue decision** is ranked third (C3), not seventh. Its absence from the pinned graph is presented as our limitation.
2. **Identical reports** get identical judged scores, but their rewards differ by $-\lambda\Delta c$.
3. **Variance** is re-derived over the full pre-reporter history and the completed trace, with cost.
4. **"Unbiased, high variance, no systematic miscredit"** replaces "wrong pushes average out".
5. **PPO's $\epsilon$** limits the incentive, not the step.
6. **Baselines are token-specific ($b_{t,k}$)**, stated with the independence case, and $P_{\text{env}}$ is conditioned on the prior history.
7. **Token share is not update weight.** "About 7.5% of the update's weight" (`part1_analysis.md:253`) is withdrawn.
8. **Factuality probes.** D2/D2b are six factuality probes, not six false claims: the D2 sentences are supported by the run's retrievals. One of the six was selected, and it was uninformative; the analysis said none was.
9. **H1b.**
   - The success rule failed for five selected minimal-repair cases; the submission does not claim H1b is "falsified for this system".
   - c05's computed verdict, "evidence-specific effect", is reported in `part1_results.md:272` "as computed, with this caveat". Here it is stated as a detector false positive, corrected by an unblinded model-based reading.
10. **93/132** is a provenance metric, not an error rate.
11. **Costs** are split into measured and hypothetical.
    - The FLOP estimate adds rollout generation (≈5.7e19) to the trainer compute in `part1_analysis.md:563` (≈1.7e20), for ≈2.3e20 in total.
    - The judging time is added.
12. **In-repo judge.** The range 6.8–8.35 holds only for its 15 registered variants; it gave 5.8 on the corrected facet removal.
13. **The $p_Rp_W$ coupling.**
    - It is restricted to the researcher-summary path, with $p_W$ defined conditionally on the reporter's other input. `part1_analysis.md:364–380` states it for any fact the researcher keeps.
    - The planner-thought route is added, with an independent-routes formula.
14. **Replays** are described as local causal interventions, not as COMA-style per-role credit (`part1_analysis.md:388`, `646`).
15. **Dilution.** "Checked with probability about $k/N$" (`part1_analysis.md:509`) becomes an expected count of checked false claims, $kF/N$. It now comes with the conditions under which dilution can and cannot occur; a precision score dilutes at any $k$.
16. **Cost units and a failure reward** are defined: $r_{\text{fail}}$ for trajectories without a report, and masking for environment or judge failures. The analysis notes no-report exits (`part1_analysis.md:448`, `479`) without assigning them a reward.
17. **M4** is a wrong stop only if another round has positive expected net value. `part1_analysis.md:279` labels it "Wrong stop decision" without that condition.
18. **The two-plan sample size** $n\approx8\sigma^2/\Delta^2$ (`part1_analysis.md:241`) is now derived, with an 80%-power version ($\approx15.7\,\sigma^2/\Delta^2$).
19. **The planner-thought count** is 3 of 10 runs carrying a quantitative claim (E24). `replay_notes.md:62–64` counts 4 of 10 thoughts containing numerals, and states that all four occur in the background search; q07-r02's does not.
20. **Bibliography and prerequisites.** A short reference list (entries checked in `docs/references.md`) and a prerequisites section (§8) are added.

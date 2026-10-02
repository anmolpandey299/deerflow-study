# Replay observations beyond the pre-registered metric

These notes are qualitative. The verdicts come only from `analysis/replays.json` (the pre-registered rules).

## c01 (q01-r03, restored passage: LaRA, "RAG vs long-context comparisons are often inconclusive due to benchmark limitations … 2326 test cases")

- **Pre-registered usage**
  - u_A = u_B = u_C = 0/3. Verdict: **reporter insensitivity**.
  - Checked for false negatives: no sample in any condition contains "inconclusive", "2326", "benchmark limitation" or "four QA tasks", attributed or not.
- **Salience moved, content did not**
  - B-s101: one bare body mention, "LaRA (benchmarking framework) for evaluation standards".
  - B-s102: no body mention.
  - B-s103: four body mentions, and they **mischaracterise** the passage: "Existing benchmarks (e.g., LaRA, RAGPerf) focus on one dimension at a time", listed as an example of the "Lack of holistic benchmarks". LaRA's own abstract says it was introduced because such comparisons are inconclusive.
- **Control passage.** The Wikipedia RAG definition is not reproduced verbatim in any C sample.
- **Byte reproduction.** A-s7 is identical to the original report.

## Infrastructure note: a throttling episode

- **What happened.** Between about 22:27 and 22:47 local time, replay throughput dropped roughly 7×. Sample c02 C-s101 took 1,200 s instead of the usual 120–215 s.
- **Diagnosis.**
  - The Ollama runner kept working throughout, so nothing had hung.
  - No thermal warning was recorded.
  - The laptop battery was at 7% and charging.
  - Throughput recovered by 22:49; A-s102 took 117 s.
- **Effect.** Outputs are unaffected: replays are deterministic given the seed and input, and the byte-reproduction checks confirm this. Only that sample's wall time is inflated, and it is excluded from any timing statement.

## c02 (q04-r02, restored passage: W&B report, "combining a dense transformer model allows good training efficiency, significantly reducing the communication overhead", 600M models)

- **Pre-registered usage**
  - u_A = u_B = u_C = 0/3. Verdict: **reporter insensitivity**.
  - Byte reproduction: identical.
- **False-negative check.** "Communication overhead" and "hybrid architectures" occur in all three conditions, but only in content the no-search steps had already made up, such as the TPU table ("reduced inter-TPU communication overhead"), or as generic future-work bullets ("investigate hybrid (dense + MoE) models"). No sample states the restored claim or its 600M-parameter context.
- **Fabricated links.** B-s101 invents an image link on the real W&B report's id (`…/assets/123456789`). Fabricated links derived from real ids persist in every condition: 5.7–6.7 unretrieved URLs per report.

## c03 (q05-r02, restored passage: "INT8 can nearly double the throughput of matrix multiplications compared to … FP16")

- **Pre-registered usage**
  - u_A = u_B = u_C = 0/3. Verdict: **reporter insensitivity**.
  - Byte reproduction: identical.
- **False-negative check.** No sample in any condition has a sentence pairing INT8 or 8-bit with a doubling, a 2× figure, or a comparison with FP16/16-bit.

## c04 (q06-r02, restored passage: Hyper-RAG, *Nature Communications* 2026, "effectiveness in enhancing LLM reliability and reducing hallucinations")

- **Pre-registered usage**
  - u_A = 0/3, **u_B = 1/3**, u_C = 0/3. Verdict: **reporter insensitivity** under the rule (u_B ≤ 1/3).
  - Byte reproduction: identical.
- **The one use (B-s103)** is broadly correct, with embellishment: "the *Hyper-RAG* paper (Nature, 2026), which introduces a hypergraph-based retrieval model to improve semantic consistency and reduce hallucinations". Calling it "the most influential theoretical work" and the "semantic consistency" claim are not in the passage.
- **Citation uptake without content uptake**
  - In **3/3** B samples, Hyper-RAG became the **first** entry in "Key Citations", with its title copied from the inserted source line.
  - ~~It is in no A or C sample's citation list.~~ **Corrected (see Corrections below):** the same Nature URL is the *first* Key Citation in every A and C sample too, under an invented title. What B changes is the title, not whether the source is cited.
  - The restored block therefore reliably changes *how the source is cited*. It changes *what is said* in 1 of 3 samples.
- **The reporter cites what it never saw.** The Nature URL appears in **every** condition, including A. The reporter received it twice:
  - as a bare URL in step 0's collapsed tool-call string;
  - in step 1's reference list, under the invented title "Retrieval Failure and Irrelevance in RAG Systems". Step 1 was a researcher step that never searched.

  The reporter cites a source whose content it never received.

## A structural finding from c05: the planner's `thought` carries source-stripped facts to the reporter

- **What the reporter receives.** Its "Research Requirements" message is the planner's plan title plus its `thought` (nodes.py:881–889). The planner writes the thought after reading the background search.
- **In q03-r02**, the thought contains "Google's TurboQuant claiming 6x memory reduction with zero accuracy loss", with no source. The reporter therefore had this claim in **every** condition (A, B and C).
- **How often.** 4 of 10 plan thoughts contain numbers. Some only echo the query (q07's "10B"). Others are background-search facts (q02's "3x" for EAGLE-3; q03-r02's "6x"; q08's "10M, 100M").
- **Consequence.** A third route by which specifics reach the report **without their source**, alongside tool-less steps and the reporter's own additions.
  - These numbers are not invented. All four thoughts' numbers occur in the background-search results.
  - But those results are read only by the planner (nodes.py:296–303), so the reporter receives the claim stripped of its URL.
  - q03-r02's "6x … zero accuracy loss" is the title of background result 0.2 (rits.shanghai.nyu.edu).

## c05 (q03-r02, restored passage: TurboQuant, "compresses KV caches down to 3 bits per value. Standard inference runs at 16 or 32 bits … closes it without touching the model")

- **Pre-registered usage.** u_A = 0/3, **u_B = 2/3**, u_C = 0/3. Verdict: **evidence-specific effect**. Byte reproduction: identical.
- **Manual reading (sensitivity check; does not replace the verdict).**

  | Sample | What it says | Detector |
  |---|---|---|
  | B-s101 | "claims of '6x memory reduction with zero accuracy loss' from Google's TurboQuant … not independently verified". This wording comes from the **planner's thought** (already in the input for every condition), not from the restored passage. | counted (TurboQuant + "6x") |
  | B-s102 | "TurboQuant claims to close this gap without modifying the model", which paraphrases the **restored passage** | **missed** (no keyword) |
  | B-s103 | calls "6× memory reduction with zero accuracy loss" "a misstatement or oversimplification", adding that TurboQuant "reduces the memory footprint of the KV cache" (consistent with the passage) | counted |
  | A, C (all six) | TurboQuant is **never** mentioned, although the planner's thought mentions it in all conditions | — |

- **Two readings of the same samples.**
  - As a **salience** effect, the insertion made TurboQuant appear: 3/3 in B against 0/6 in A and C.
  - As **fact uptake**, ~~no sample states the passage's specific figure~~ **corrected:** one sample (B-s102) states the figure and attributes it correctly: "The gap between standard inference (16–32 bits) and compressed representations (e.g., 3 bits) is where the bottleneck lies. Google's TurboQuant claims to close this gap …". The other two counted samples discuss a source-stripped claim from the plan. Specific-fact uptake is therefore 1/3.
- **Detector design caveat.** The case's keyword list included "6x"/"6×" because the source title reads "6x less memory". It was fixed before any replay, before it was known that the planner's thought also contained "6x".

## H1b across the five cases (pre-registered rule)

| Case | u_A | u_B | u_C | Verdict |
|---|---|---|---|---|
| c01 | 0 | 0 | 0 | reporter insensitivity |
| c02 | 0 | 0 | 0 | reporter insensitivity |
| c03 | 0 | 0 | 0 | reporter insensitivity |
| c04 | 0 | 1/3 | 0 | reporter insensitivity |
| c05 | 0 | 2/3 | 0 | evidence-specific effect (see caveat) |

**Outcome.** Reporter insensitivity holds in a **majority (4/5)** of cases. By the rule fixed in §5, **H1b is falsified for this system**: restoring one lost, relevant passage at the boundary did not usually make the reporter state it.

**What *did* change consistently was salience and citation:**
- the restored source's citation carried its true title instead of an invented one (c04: 3/3 in B against 0/6 in A and C; corrected from "was cited first", see Corrections);
- the topic was discussed in B only (c05: 3/3 against 0/6);
- the source was named without its finding, or with its finding distorted (c01).

## Corrections (appended 22:52 UTC, after re-checking every claim against the replay files)

1. **c04 citation list.** The earlier note said Hyper-RAG "is in no A or C sample's citation list". That is wrong at the level of URLs:
   - the Nature URL is the first Key Citation in all 10 samples of every condition;
   - A and C (and the original report) cite it under the title "Retrieval Failure and Irrelevance in RAG Systems", which step 1's no-search researcher invented;
   - B cites it under its true title.

   The corrected claim is that insertion changes the citation's title, not its presence.
2. **c05 B-s102.** The earlier note said no sample states the 3-bit vs 16/32-bit figure. B-s102 does, in the sentence before its TurboQuant sentence. The same-sentence detector misses it. With a ±1-sentence window:
   - no hit is added in c01–c04;
   - B-s102 is added in c05.

## e01 (probe E, exploratory; q01-r02; target: the analyst step 2, which has no tools; control: step 1)

- **Where the ratings are.** Of all the reporter's inputs, only the analyst's observation contains qualitative rating cells: 15, in one table. Steps 0 and 1 and the plan thought contain none.
- **Mechanical result (A7/A8 rule).** Rating cells, mean over seeds 101–103: A 15, D 11.3, G 15.
  - `upstream_attribution` = false (D is not ≤ 0.2·A).
  - `compensatory_confabulation` = true (D ≥ 0.5·A).
- **Per seed.**
  - A: 15, 15, 15. G: 15, 15, 15. The analyst's table is relayed intact.
  - D: **0, 18, 16**. With no rating anywhere in its input, the reporter built its own ratings table in 2 of 3 samples, with much the same rows (Hybrid BM25, MiA-RAG, hierarchical, memory-augmented; these approaches are named in steps 0 and 1).
- **New ungrounded numbers appear only in D.** Reporter-originated numbers per sample: A 0, 0, 0; G 0, 0, 0; D 1, 4, 5. Examples:
  - D-s102: "High (↑18% over BM25)", "High (↑12% on QA)", "$0.001";
  - D-s103: "$0.00001", "$0.0001".
- **Prompt context.** The reporter prompt asks for tables in several places (reporter.md:251, 253, 266 "Include detailed tables with comprehensive headers and statistical data", 389), right next to "Never invent or extrapolate data" (reporter.md:246).
- **Reading.** Removing unsupported upstream content did not remove unsupported content from the report. The reporter replaced it in 2 of 3 samples. A counterfactual credit that blames the analyst for the table would be right for A, but a policy that fixed only the analyst would still receive tables from the reporter.

## e02 (probe E, exploratory; q02-r01; target: step 1, a researcher step that never searched and carries DeerFlow's warning; control: step 0, which searched)

- **Target content.** 20 numbers appear only in the target observation, and in no other observation or tool output. They include the "quality" table's BLEU-4 scores (0.38–0.54) and accuracies (82–95%).
- **Mechanical result (A7/A8 rule).** Target-unique numbers in the report, mean over seeds: A 15.3, **D 0**, G 16.3.
  - `upstream_attribution` = **true**.
  - `compensatory_confabulation` = false. Reporter-originated numbers, mean: A 1.0, D 1.0, G 2.0.
- **Per seed.** A 16, 15, 15; D 0, 0, 0; G 17, 16, 16.
  - With the target present, the reporter relays 75–80% of its invented numbers. When it is removed, none appear, and the reporter does not invent replacements.
- **Qualitative ratings** (secondary measure): A 6, 20, 7; D 15, 17, 14; G 6, 16, 7.
  - Only step 0 contains ratings (5 cells). The spread between A seeds (6–20) is too large to read a D effect.
- **Contrast with e01.** Numbers unique to an upstream step disappear with that step here. A qualitative comparison table was rebuilt by the reporter in e01. Whether an upstream fix reaches the report depends on the kind of content.

## e03 (probe E, exploratory; q04-r02; target: step 1, a researcher step that never searched and carries the warning; control: step 0, which searched)

- **Target content.** 7 numbers are unique to the target: 1.3, 1.8, 0.8, 1.2, 60%, 25%, 0.9.
- **Mechanical result.** Mean target-unique numbers in the report: A 7.0, **D 0.33**, G 6.33.
  - `upstream_attribution` = **true**.
  - `compensatory_confabulation` = false. Reporter-originated numbers, mean: A 3.33, D 3.33, G 0.67.
- **Per seed.**
  - Target-unique numbers: A 7, 7, 7 (every one relayed, every time); D 0, 1, 0; G 7, 6, 6.
  - Reporter-originated numbers: A 2, 7, 1; D 3, 2, 5; G 0, 0, 2. The original report (seed 7) had none, so the reporter's own invention varies a lot with the seed alone.
- **Never-retrieved URLs** fall with the target: A 5, 6, 6; D 4, 4, 3; G 6, 5, 7. The case rationale attributes 3 fabricated URLs to the target.
- **Qualitative ratings** (secondary measure): A 1, 1, 1; **D 3, 6, 6**; G 0, 0, 7.
  - Every D sample has more rating cells than every A sample. If the six values were exchangeable, that ordering would have probability 1/20.
  - With n = 3 and G's spread (0–7), this is suggestive only. It points the same way as e01: without the numbers, the reporter adds qualitative ratings.

## e04 (probe E, exploratory; q05-r02; target: step 1, a researcher step that DID search, yet added numbers found in no source; control: step 2)

- **Target content.** Only 2 numbers are unique to the target: "10" and "15%". The metric is coarse by design (A8 note).
- **Mechanical result.** Target-unique numbers: A 2, 2, 2; **D 0, 0, 0**; G 2, 2, 2.
  - `upstream_attribution` = **true**.
  - `compensatory_confabulation` = false. Reporter-originated numbers, mean: A 1.0, D 1.0, G 3.0.
- **Qualitative ratings** (secondary measure; A7 fixed no rule for numeric cases): A 11, 10, 15; D 13, 17, 19; G 13, 9, 11.
- **Across the three numeric cases** (e02, e03, e04), mean rating cells are higher under D than under A: 15.3 vs. 11.0, 5.0 vs. 1.0, and 16.3 vs. 12.0. The per-seed ranges overlap in e02 and e04, and not in e03.
  - The direction is consistent: when an upstream step's numbers are removed, the reporter writes more qualitative ratings. This is a post-hoc reading of a secondary measure, with n = 3 per condition.

## Correction (appended 2026-10-01 ~18:55 UTC, integrity review)

The outcome line under "H1b across the five cases" says that H1b "is falsified for this system". The rule supports a narrower reading: H1b failed by its pre-registered rule for these five cases, with a raw passage appended at the end of the step's observation and a 4B reporter. In c01–c03 that position is after the summary's References list; the two correct B statements both came from c04 and c05, where the appended block was in effect the whole observation. No condition wrote the fact into the summary's own prose, so the result cannot separate reporter inattention from position, format or weak sources (protocol A19). The verdicts above are unchanged.

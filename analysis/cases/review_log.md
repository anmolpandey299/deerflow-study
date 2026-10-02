# H1 case-selection review log (protocol §6)

The rule is applied to every completed run that is not outage-affected:

1. **Automatic step.** List numeric candidates (`analysis/candidates/<run>.json`) and write a review sheet giving each retrieved sentence's lexical coverage in its step's summary (`<run>.review.md`).
2. **Manual step.** The experimenter confirms by hand that a candidate
   - contains a specific checkable item (a number, or a named method with a comparison);
   - addresses a pre-registered requirement;
   - is absent from, or distorted in, the summary of the step that received it.
3. **Choice.** Take the candidate whose requirement has the lowest baseline coverage; break ties by the earliest segment.

Every candidate considered is listed with its decision.

## q01-r02-20260930T201622 (pilot): no qualifying omission

| Candidate | Decision | Reason |
|---|---|---|
| seg 5.1/7.0 "25k QA pairs and over 51k documents" (EncouRAGe) | reject | A dataset size, not relevant to any q01 requirement. Also *distorted*: the step-1 summary gives these figures to RAGPerf (recorded as a misattribution observation). |
| seg 7.0 "Hybrid BM25 consistently achieves the best results …; RAG still underperforms … Oracle Context" | reject | Retained in the step-1 summary. |
| seg 3.0 contextual-normalisation finding (formatting shifts accuracy) | reject | Retained in the step-0 summary. |
| Remaining low-coverage sentences (background, component lists, author/e-mail lines) | reject | No checkable item relevant to a requirement. |

## q01-r03-20260930T204051: one qualifying omission, case c01

| Candidate | Decision | Reason |
|---|---|---|
| seg 1.2 LaRA: "Existing RAG vs. long-context (LC) LLM comparisons are often inconclusive due to benchmark limitations. We introduce LaRA … 2326 test cases …" | **accept, c01** | Named comparison (RAG vs. LC) plus a checkable item (2326). Addresses R7, and R1. The summary keeps only the bare link. The report cites LaRA only in its citation lists. Baseline R7 coverage: partial (one generic sentence). |
| seg 2.0 contextual retrieval vs. late chunking (better coherence, more compute) | reject | Retained almost verbatim in the step-0 summary. |
| seg 2.1/2.2 TreeRAG ("redundant information and noise results in higher inference costs") | reject | Not tied to a named method comparison or a number; a generic motivation. |
| Numeric listing: "28", "14", "18", "05", "23", "4.2" | reject | Dates and section numbers, not claims. |

## q02-r01-20260930T202824: no qualifying omission

| Candidate | Decision | Reason |
|---|---|---|
| "2–6x faster without changing a token of the output"; "EAGLE-3 … 3× throughput" | reject | Numbers retained in the step-0 summary. The "without changing a token" point was *not* retained and is contradicted by the report. That is a reporter/upstream factuality failure, recorded separately, not an omission of a missing fact. |
| seg 1.2 "(1−α^(K+1)) / ((1−α)(Kc+1)) throughput formula … the long-context failure mode" | reject | A table-of-contents snippet. The formula's variables are undefined in the passage and the failure mode is only named. Restoring it cannot supply a checkable fact without outside knowledge. |
| Numeric listing: "22", "20", "202634" | reject | Dates. |

## q03-r01-20260930T203551: excluded (outage-affected, amendment A6)

Candidate "98% memory reduction" (seg 2.0, R2) was lost when DeerFlow discarded the whole step after a tool exception (error-induced discard), not by a researcher summary.

## q04-r02-20260930T205216: one qualifying candidate, case c02

| Candidate | Decision | Reason |
|---|---|---|
| seg 2.2 "Mixtral 8x7B has ~46.7B total parameters, Llama 70B has ~70B"; "equal compute" ambiguity | reject | Retained in the step-0 summary ("about 47 billion", a faithful rounding). |
| seg 2.0 (wandb) "Train 600M MoE, Dense, Hybrid … combining a dense transformer model allows good training efficiency, significantly reducing the communication overhead" | **accept, c02** | Named comparison (hybrid vs. MoE, communication overhead) plus a number (600M). Addresses R2/R3. The summary keeps only the bare link, and the report says this source "returned no content". Weak: a small-scale blog report whose claim is vague. |
| seg 6.0 Jina 403 error text (arxiv.org anonymous access blocked) | reject | A tool error, not evidence (recorded as a tool-failure observation). |

Also observed: 5 of 8 report URLs were never retrieved, all introduced by steps 1–2 (researcher, no search).

## q05-r02-20260930T205952: one qualifying omission, case c03

| Candidate | Decision | Reason |
|---|---|---|
| seg 1.2 "using 8-bit integers (INT8) can nearly double the throughput of matrix multiplications compared to … (FP16)" | **accept, c03** | A speedup with its condition (R5), and relevant to the weight-activation distinction (R7). Absent from the step-0 summary and the report; the source is kept only as a reference. |
| seg 9.1 "Compiled FP8 or NVFP4 engines typically give the most tokens per GPU" | reject | Retained in paraphrase in the step-2 summary ("A100 and H100 support FP8 and NVFP4 engines … TensorRT-LLM or NVIDIA NIM"). |
| seg 3.2 SmoothQuant "training-free … W8A8" | reject | Retained in the step-0 summary. |
| seg 4.0 Jina 403 error text | reject | A tool error, not evidence. |
| Numeric listing: dates | reject | Not claims. |

All three research steps in this run searched. Even so, 10 of the report's 16 numbers appear in no tool output: 5 were introduced by searched-researcher summaries and 5 by the reporter.

## q06-r02-20260930T210856: whole step-0 summary lost, case c04

The step-0 summary handed to the reporter is only 122 characters: a raw `<tool_call>{"name": "crawl_tool", …}</tool_call>` string.
- The researcher's final turn emitted a tool call as text. The serving layer returned it as plain content (`finish=stop`, with no parsed or invalid tool call), and DeerFlow treated that content as the step's result.
- Every step-0 passage was therefore lost at the boundary.

| Candidate | Decision | Reason |
|---|---|---|
| seg 4.2 Hyper-RAG (*Nature Communications*, 2026): "confirm Hyper-RAG's effectiveness in enhancing LLM reliability and reducing hallucinations" | **accept, c04** | A named method with a comparative claim. Addresses R5 (the lowest-covered requirement by the experimenter's reading) and R1. |
| seg 4.0 SeaRAG (ACM, 2026): uncertainty probes as training-free hallucination-detection signals | reject (not chosen) | Relevant to R5, but a functional finding without a comparison. Criterion (ii) is weaker than for 4.2. |
| seg 4.1: 2×2 factorial user study, RAG-enhanced vs. non-RAG tools | reject (not chosen) | Relevant to R1, whose baseline coverage is higher (a fabricated "2026 benchmark study … 60%"). |
| seg 1.0/1.2: generic "RAG can lessen hallucinations" | reject | No specific checkable item. |
| seg 1.1: "Reduces hallucinations by 30–50% in controlled studies" | reject | The snippet leaves unclear which technique the figure belongs to. |

Also observed:
- 6 of the report's 8 URLs were never retrieved (5 from the no-search step 1), including an obviously invented `arxiv.org/abs/2603.12345`.
- One crawl returned a CAPTCHA page.

## q07-r02-20260930T211445: no qualifying omission

Only step 0 searched; steps 1 and 2 answered without any tool call. Step-0 retrieval was mostly off-target: golf's Open Championship, the Open University, and Chinese-language Hotmail login pages.

| Candidate | Decision | Reason |
|---|---|---|
| seg 4.0 DeepSeek "released its models under free and open-source software licenses" since January 2025 (R4) | reject | Retained in the step-0 summary. |
| seg 3.0 Small Language Model Leaderboard: "scores come from official model cards, technical reports, or verified third-party evaluations" (R6) | reject | Content retained. The summary attributes it to the *Open LLM Leaderboard* (seg 3.1), a misattribution that leaves the requirement-relevant content intact. This is the same standard applied to the q01-r02 misattribution. |
| seg 4.1 gpt-oss, seg 4.2 GLM-5 | reject | Retained, and correctly excluded as over 10B. |
| Numeric listing: "155" (golf), dates, citation markers | reject | Not claims. |

## q08-r02-20260930T212058: qualifying loss, but no admissible control, so not replayed

The step-0 summary is again a raw unparsed `<tool_call>` string: 138 characters, `finish=stop`, no parsed tool call. This is the same failure as q06, and all step-0 evidence was lost at the boundary.

| Candidate | Decision | Reason |
|---|---|---|
| seg 2.0 (crawl): "the two most-cited public benchmarks on this pairing disagree sharply on which engine 'wins' … Qdrant tends to win on tail latency; pgvector (with pgvectorscale) has posted an order-of-magnitude throughput lead in at least one independently published test" | **qualifies (counts for H1a)**, **not replayed** | A named comparison plus a benchmark caveat, addressing R5, R8, R2 and R4. The pre-registered control rule cannot be satisfied: no off-requirement segment falls within ±25% of the passage length, because all snippets and crawls are on-topic and the only off-topic segment is a 149-character 404 page. The C′ fallback, a redundant passage, does not exist either, because the step-0 summary is empty. Cutting a control span by hand would be an undeclared degree of freedom, so the case is not replayed. |
| seg 6.0 (crawl): "all four deliver high recall with HNSW indexing; they diverge on filtered search, write-heavy patterns …" | qualifies (H1a), not chosen | Also lost. |

Also observed: 14 of the report's 19 numbers appear in no tool output. 7 came from the analyst step and 7 were introduced by the reporter. Steps 1 and 2 were a researcher step without search and an analyst step.

## q03-r02-20260930T212748: step-1 summary lost, case c05

The step-1 summary handed to the reporter is only 104 characters: a raw unparsed `<tool_call>` string, the third occurrence of this failure, after q06 and q08. Several of that step's crawls also hit the Jina 403 block on arxiv.org. Step 0 kept its main findings, including the INT8 "4×" memory reduction and RocketKV.

| Candidate | Decision | Reason |
|---|---|---|
| seg 6.1 TurboQuant: "compresses KV caches down to 3 bits per value. Standard inference runs at 16 or 32 bits …" | **accept, c05** | A specific memory figure (R2), and the quantization family (R1). Lost with the step-1 summary; absent from the report. |
| seg 6.0 Kara; seg 7.2 PackKV / Keyformer | reject (not chosen) | Address R1, which the baseline already covers well from step 0. |
| seg 6.2 / 7.1 (generic bandwidth and cost statements); seg 7.0 (evaluation-metric statement) | reject | No specific checkable item. |
| Numeric listing: dates, error codes | reject | Not claims. |


## Correction (2026-09-30, about 20:55 UTC): mechanism of the collapsed summaries (q06, q08, q03-r02)

The three summaries that reached the reporter as raw `<tool_call>` strings all came from DeerFlow's **recursion-limit fallback**:
- The researcher used up its step budget (recursion limit 25, about 6 tool calls).
- `_handle_recursion_limit_fallback` (nodes.py:1007–1077) re-called the model **with no tools bound** (nodes.py:1055–1059), adding the prompt "You have reached the maximum number of reasoning steps…".
- The model replied with a tool call written as plain text, and DeerFlow logged "Graceful fallback succeeded" and used that text as the step's result.

The fallback was triggered 4 times in total; only q04's produced a real summary (5,950 characters). Earlier entries said the serving layer had not parsed the call. That was imprecise: with no tools bound, there was nothing to parse.

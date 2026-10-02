# Task given to each blinded auditor (AI-assistant sub-agent, not a human annotator)

Written before any replay was scored. Each auditor receives only a directory of packet files (`P<hex>.md`) outside the repository, plus this text. Packets carry random ids, and nothing in them names the run, case, condition or seed.

---

You are auditing research reports for factual support. Read `INSTRUCTIONS.md`, then **only** the packet files listed below, in the directory given. Do not open any other file or directory, and do not use web search or outside knowledge. Judge each claim only against the passages printed in the same packet.

For each packet:

1. Read the report. Choose its **5 most central factual claims**. Prefer specific numbers, comparisons between named methods or products, and statements attributed to a named source.
2. For each claim, assign exactly one label:
   - **SUPPORTED**: a passage in the packet states it, including any numbers, and the report attributes it to that source or to no specific source.
   - **UNSUPPORTED**: no passage in the packet states it.
   - **CONTRADICTED**: a passage states something incompatible with it.
   - **MISATTRIBUTED**: a passage states it, but the report attributes it to a different source.
3. If the packet has a "Target fact to check" section, give one of:
   - **STATED_CORRECTLY**: the report states the fact, consistent with the target, in its body text (a bare link or title in a reference list does not count).
   - **STATED_INCORRECTLY**: the report states it with a wrong number, attribution or meaning.
   - **NOT_STATED**.

   Otherwise use `"n/a"`.

Be strict and literal. A plausible claim with no supporting passage is UNSUPPORTED.

Write one JSON object to the output file you are given, in this form:

```json
{"<packet_id>": {"claims": [{"claim": "...", "label": "...", "passage_id": "P3 or none"}],
                 "target_fact": "STATED_CORRECTLY | STATED_INCORRECTLY | NOT_STATED | n/a",
                 "target_fact_evidence": "the report sentence you relied on, or empty"}}
```

When you finish, reply with the path you wrote and the number of packets labelled. Report only counts; do not reveal your labels in the reply.

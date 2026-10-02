# Audit task (Part 2 pilot; written before any label exists)

You are checking whether research reports state one specific fact. You are an AI assistant acting as a blinded
auditor; nobody expects you to know where the reports came from. Read only the packet files listed for you, in the
directory given. Do not open any other file or directory, and do not use web search or outside knowledge.

Each packet has a "Target fact" section (a source's title and URL, the verbatim passage, and the core statement(s)
that count as the fact) and a "Report" section. Reports are long: search each one for every mention of the target's
source, subject and key terms, and read the surrounding paragraphs. A bare title or link in a reference list does not
count as stating anything.

For each packet give:

1. `target_fact`, exactly one of:
   - STATED_CORRECTLY: the report's body text states at least one core statement, consistent with the passage
     (paraphrase is fine; extra claims elsewhere do not change this label).
   - STATED_INCORRECTLY: the report states the fact's subject with a wrong number, meaning or source.
   - SOURCE_ONLY: the report mentions the target's source or subject, but does not state the fact.
   - NOT_STATED: none of the above.
2. `attribution` (only if STATED_CORRECTLY, otherwise "n/a"), exactly one of:
   - ATTRIBUTED: the stating sentence or its neighbour names the source (by name, title or system name), links its
     URL, or cites a marker that resolves to that source in the report's reference list.
   - UNATTRIBUTED: no source is given for it.
   - MISATTRIBUTED: it is credited to a different source.
3. `evidence`: the report sentence(s) you relied on, verbatim (empty if NOT_STATED).

Be strict and literal. Write one JSON object to the output file you are given:

{"<packet_id>": {"target_fact": "...", "attribution": "...", "evidence": "..."}}

When you finish, reply only with the path you wrote and the number of packets labelled.

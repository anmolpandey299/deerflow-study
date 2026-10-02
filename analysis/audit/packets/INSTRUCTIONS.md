# Audit instructions (read first)

For each packet: read the report, then list its 5 most central factual claims (prefer
numbers, comparisons and attributions). For each claim give:
  label: SUPPORTED (a listed passage explicitly states it, including numbers and the
         attribution), UNSUPPORTED (no listed passage states it), CONTRADICTED (a passage
         states something incompatible), MISATTRIBUTED (a passage states it, but the report
         attributes it to a different source)
  passage_id: the passage you relied on (or none)
Use only the passages in the packet, never outside knowledge. Return JSON:
{"<packet_id>": {"claims": [{"claim": "...", "label": "...", "passage_id": "..."}],
                 "target_fact": "STATED_CORRECTLY | STATED_INCORRECTLY | NOT_STATED | n/a"}}

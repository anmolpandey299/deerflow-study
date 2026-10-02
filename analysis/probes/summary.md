# Evaluator probes (SYNTHETIC defects on real reports)

| report | variant | expected | FMT | COMP strict (lenient) | FACT-b (supported/checked) | DeerFlow judge: weighted / factual / completeness | did P3 detect this defect? |
|---|---|---|---|---|---|---|---|
| q01-r02 | original | - | 1.00 | 0.62 (0.62) | 0.33 (2/6) | 8.35 / 8 / 8 | - |
| q01-r02 | D1_remove_cost | COMP falls | 0.88 | 0.56 (0.56) | 0.38 (3/8) | 8.0 / 7 / 8 | R4 ABSENT->ABSENT; R5 FULL->FULL |
| q01-r02 | D2_irrelevant_passage | FACT-b falls (registered; may not, see spec) | 1.00 | 0.50 (0.50) | 0.0 (0/10) | 8.0 / 7 / 8 | planted claim not extracted |
| q01-r02 | D2b_attribution_swap | FACT-b falls if attribution is checked | 1.00 | 0.44 (0.56) | 0.0 (0/10) | 8.0 / 7 / 8 | planted claim not extracted |
| q01-r02 | D3_strip_structure | FMT falls | 0.12 | 0.38 (0.56) | 0.1 (1/10) | 7.5 / 7 / 8 | FMT 1.00->0.12 |
| q01-r02 | D1s_remove_cost | COMP falls | 0.88 | 0.56 (0.56) | 0.1 (1/10) | 7.8 / 7 / 8 | R4 ABSENT->ABSENT; R5 FULL->PARTIAL |
| q01-r03 | original | - | 1.00 | 0.69 (0.69) | 0.5 (5/10) | 7.9 / 7 / 8 | - |
| q01-r03 | D1_remove_latency | COMP falls | 0.88 | 0.56 (0.56) | 0.38 (3/8) | 7.8 / 7 / 8 | R3 PARTIAL->ABSENT; R5 FULL->FULL |
| q01-r03 | D2_irrelevant_passage | FACT-b falls (registered; may not, see spec) | 1.00 | 0.75 (0.75) | 0.0 (0/10) | 8.0 / 7 / 8 | planted claim not extracted |
| q01-r03 | D2b_attribution_swap | FACT-b falls if attribution is checked | 1.00 | 0.62 (0.62) | 0.4 (4/10) | 7.7 / 7 / 8 | planted claim not extracted |
| q01-r03 | D3_strip_structure | FMT falls | 0.12 | 0.69 (0.69) | 0.1 (1/10) | 7.8 / 7 / 8 | FMT 1.00->0.12 |
| q01-r03 | D1s_remove_latency | COMP falls | 0.88 | 0.50 (0.50) | 0.0 (0/10) | 7.8 / 7 / 8 | R3 PARTIAL->ABSENT; R5 FULL->FULL |
| q02-r01 | original | - | 1.00 | 0.75 (0.75) | 0.0 (0/10) | 6.8 / 5 / 7 | - |
| q02-r01 | D1_remove_deployment | COMP falls | 0.88 | 0.75 (0.75) | 0.1 (1/10) | 6.95 / 6 / 8 | R7 FULL->FULL |
| q02-r01 | D2_irrelevant_passage | FACT-b falls (registered; may not, see spec) | 1.00 | 0.81 (0.81) | 0.0 (0/10) | 6.8 / 5 / 7 | planted claim not extracted |
| q02-r01 | D2b_attribution_swap | FACT-b falls if attribution is checked | 1.00 | 0.81 (0.81) | 0.0 (0/9) | 6.8 / 5 / 7 | extracted, labelled NOT_FOUND |
| q02-r01 | D3_strip_structure | FMT falls | 0.12 | 1.00 (1.00) | 0.0 (0/10) | 7.35 / 6 / 8 | FMT 1.00->0.12 |
| q02-r01 | D1s_remove_deployment | COMP falls | 0.88 | 0.69 (0.69) | 0.2 (2/10) | 5.8 / 4 / 6 | R7 FULL->PARTIAL |

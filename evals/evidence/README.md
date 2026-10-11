# Recorded evaluation evidence

These are fixed snapshots of the fictional support-ticket demo on October 11, 2026. They are included for reviewers; current generated runs remain under ignored `evals/results/`. The case rubrics still require human approval and judge calibration. No customer responses were sent.

| Evidence | What it establishes |
|---|---|
| [Baseline score report](baseline-2026-10-11.md) | All 26 existing CSV answers evaluated: 7 provisional Ship recommendations, 19 Hold off, and all eight known-error answers held. |
| [Baseline JSON trace](baseline-2026-10-11.json) | Per-dimension scores, predicate probabilities, checks, source revisions, policy and decisions. Baseline evidence comes from case reference sections, not runtime retrieval. |
| [Baseline answers CSV](baseline-2026-10-11.csv) | The existing answers assessed in that baseline run. |
| [Marcus before repair](published-marcus-ui-evaluation.txt) | A generated answer scored 0.653 and was held without retry. |
| [Marcus after repair](published-marcus-fixed-ui-evaluation.txt) | The published RAG flow retrieved the transport supplement and scored 0.930, with every mandatory gate passing. |
| [Dataset-key regression](published-dataset-regression-ui-evaluation.txt) | Correct app/dataset credential scope scored 0.991 after the retrieval repair. |
| [Provider-setup hold](provider-setup-fixed-ui-evaluation.txt) | An incomplete generated answer scored 0.552 and was held without retry. |
| [Controlled retry test](controlled-live-retry.json) | A synthetic 0.75 scheduling trigger exercised exactly two real generations and judgments. Their unchanged real scores are recorded separately: 0.9305 and 0.967375. This is a scheduling test, excluded from benchmark totals. |
| [Executed correction prompt](correction-llm-process.json) | Dify's actual LLM process data contains the original ticket and the exact correction feedback from the controlled test. |

The JSON traces retain original execution metadata, including container artifact paths and run IDs. Those paths describe the recorded run; use the links above to open the bundled files. Scores are answer-quality assessments, not measured ticket-resolution probabilities. A naturally triggered live borderline retry has not been observed.

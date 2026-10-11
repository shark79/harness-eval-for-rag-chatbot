# Ticket response scoring and delivery policy

Selected 2026-10-11: [Harness Evals](https://github.com/harness/harness-evals), researched at commit `37eb2377068ef7664d7dcff1fc415b12362f2bd3` (upstream 0.25.4; installed published package pinned to 0.25.3). Its `Golden`, `EvalCase`, `BaseMetric`, `Score` and `evaluate` APIs are the evaluation substrate. Scores are normalized to 0–1; thresholds belong to this project. Use the core package and our OpenAI Decisions adapter, rather than the optional TypeSafe decision provider.

## Scores to assert

| Score | Weight | What a high score means | CSV-specific failure example |
|---|---:|---|---|
| Grounding | 30% | Every substantive claim follows from the actual approved evidence | TCK-1021 invents a 24-hour provider propagation delay |
| Factual correctness | 25% | Claims preserve documented conditions, limits and entity scope | TCK-1006/1009 promise Team SSO; TCK-1020 promises unlimited Enterprise quotas |
| Concern relevance | 20% | The answer solves the operation requested in the original ticket | TCK-1001 must explain an app key, not an OpenAI provider key |
| Completeness | 15% | All concerns are answered or explicitly routed/clarified when unsupported | TCK-1015 needs upload diagnosis and workspace billing/proration handling |
| Category accuracy | 5% | Primary category follows the concern, and secondary concerns survive | TCK-1016 combines API limits with plan information |
| Clarity and actionability | 5% | Steps are understandable, direct and usable without unsupported certainty | TCK-1023 needs a useful clarification, not a diagnostic/error dump |

`quality_score = sum(weight × dimension_score)`. For the initial ordinal judge, each semantic dimension has levels 0–4: wrong/absent; major defects; partially useful; mostly correct with a material omission; fully meets the rubric. Normalize the probability-weighted level index by dividing by four. Record the level distribution and confidence separately. This is an assessment, not the probability a customer will resolve their problem. Category can be checked deterministically against the adjudicated routing proposals. Do not score prose by exact word match against the noisy CSV answer.

## Ship, retry, hold

Evaluate the full-precision score; round only for display.

| Condition | Action |
|---|---|
| Any hard gate fails, judging is unavailable, or the score is invalid/missing | **hold off** |
| All hard gates pass and `quality_score >= 0.80` | **ship** eligibility |
| All hard gates pass and `0.70 <= quality_score < 0.80` | **one corrective attempt, then ship or hold off** |
| All hard gates pass and `quality_score < 0.70` | **hold off** |

Exactly 0.70 permits one corrective attempt; exactly 0.80 qualifies to ship. The final outcome is always `ship` or `hold_off`; retry is a recorded internal action. A displayed rounded 0.80 must not ship a raw 0.7999. Validate every score is finite, numeric (not a Boolean), and in [0,1]. No averaging over missing dimensions, no confidence substitution, and no automatic pass on a refusal, timeout, malformed answer or metric failure.

Hard gates cover the transport/output contract, approved source revision and excerpt membership, citations pointing to actual evidence, wrong key/entity scope, unsupported or contradictory substantive claims, relevance to the original concern, and an appropriate answer/clarification/escalation disposition. Predicate cutoffs are provisional calibration settings, not truth guarantees. A score of 0.92 with an invented entitlement still holds. Same-document support without ticket relevance still holds.

`ship` is a per-response classification. Production delivery additionally requires approved case/rubric review and judge calibration. The current cases are drafts, so reports must expose `delivery_approved=false` / release readiness rather than treating a provisional score as authorization to send an answer. This application previews answers; it has no ticketing-system writeback.

## Correction loop

Run an initial candidate and at most one corrective candidate, only when the initial valid score is in [0.70, 0.80) and the gates permit repair. Below 0.70, hold off immediately. Never retry just to obtain a more favorable judge score. For a retry-eligible result, give the generator the original ticket, failed dimensions, concise rubric-based feedback and approved evidence. Revisit missed concerns/category and retrieve missing relevant content when the evidence diagnosis calls for it; changing wording alone cannot fix an evidence gap. The Dify workflow must accept and use that feedback for a live correction.

Re-run the entire suite on every revision. Stop and hold off for no measurable improvement, a repeated unchanged response, a newly failed hard gate, an exhausted single corrective attempt, missing customer information or provider failure. Never force every failed answer into a loop. Preserve initial/final scores, all attempts, evidence and reasons. Count the ticket once. An improved candidate still below 0.80 holds off. A candidate can ship only after its own complete checks pass; improvement by itself is insufficient.

## CSV report and release assertions

Run both the existing 26 CSV answers (`baseline`) and the chatbot on those same ticket inputs (`chatbot`). Keep the originals unchanged and retain raw labels as metadata. Each report lists ticket ID, category, deterministic rule score, six dimension scores, quality score, hard gate failures, final ship/hold off action, generation and scoring retry flags, initial/final scores, ranking explanations, attempts, final disposition and review status. The three-column customer CSV remains `ticket_text,assistant_answer,category`; delivery policy is in the sidecar.

Without a judge key, deterministic scores are measurable but semantic dimensions and quality score are **null**, and all delivery actions **hold off**. Do not print zero as a fake semantic score or claim the remaining answers passed because no rule detected an error. The eight source-audited baseline problems are TCK-1005, 1006, 1009, 1012, 1015, 1020, 1021 and 1023. Offline detection is diagnostic and cannot certify all other claims.

Assert these before releasing a response: valid contract and approved evidence; no hard failures; every required dimension measured; quality score at least 0.80; calibrated judge and approved rubric. Before releasing a system version, also assert no critical false accepts in the approved regression suite, all eight baseline defects covered, and performance on a fresh reviewed holdout. Keep the 95% strict resolution target separate from a 0.80 response score. Correct escalation counts as safe handling, not direct resolution; report both all-ticket and independently answerable-ticket denominators.

Thresholds and weights are an initial policy requested for this build. Calibrate them against independent human judgments before making a production acceptance claim; increasing a threshold alone does not establish quality.

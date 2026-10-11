# Evaluation harness and acceptance plan

Design baseline: 2026-10-11. No ticket-generation benchmark, retrieval run or live model call has been executed. This document specifies the harness before implementation. The existing helper's software tests do not measure ticket-resolution quality.

## Product target and denominators

The aspiration is at least 95% direct, relevant ticket resolution, with ambiguity or insufficient information routed appropriately. Treat 95% as a measured product target, not an assumed model capability. Do not force clarification/escalation to exactly 5%; observed traffic and documentation scope determine the genuine rate.

A ticket counts as **strictly resolved** only if every requested issue is answered with a supported, relevant and actionable solution, no prohibited claim appears, citations are valid, and no necessary follow-up remains. A plausible diagnosis without telemetry is not a confirmed fix. A correct clarification, safe abstention, partial answer or specialist escalation can be correct handling but is not strict direct resolution.

Report these distinct measures, with counts and denominators:

| Measure | Definition and purpose |
|---|---|
| Strict resolution, all tickets | Strictly resolved / all received valid tickets; exposes real product scope and avoids excluding difficult tickets after seeing results. |
| Strict resolution, answerable tickets | Strictly resolved / tickets independently adjudicated answerable from approved corpus and supplied facts before execution; isolates system quality. |
| Correct handling | Correct direct answer, necessary clarification, appropriate partial escalation or escalation / all valid tickets; never relabel as resolution. |
| Unsupported-claim rate | Answers with at least one unsupported substantive claim / all generated answers; separately track high-impact wrong credential, entitlement and billing claims. |
| Concern coverage | Supported requested subissues answered / supported requested subissues; a multi-issue ticket fails strict resolution if one is omitted. |
| Retrieval evidence recall | Required supporting facts present in returned chunks / adjudicated required supporting facts; section presence alone is a coarse diagnostic. |
| Citation validity and entailment | Referenced evidence exists, belongs to approved scope/revision, and actually supports its associated claim. |
| Inappropriate abstention | Answerable tickets unnecessarily clarified/escalated / adjudicated answerable tickets. |
| Ambiguity/escalation recall | Genuine ambiguous/out-of-corpus tickets handled correctly / such adjudicated tickets. |
| Routing | Per-concern category precision/recall, primary-category confusion matrix, unknown handling; not exact agreement with noisy CSV labels. |
| Judge quality | False accepts, false rejects and agreement with independent human adjudication on calibrated examples. |
| Runtime reliability | Timeout/schema/provider failures / attempted tickets, final retry count, latency percentiles and total cost including judging. |

Count infrastructure failures separately and include them as unresolved in the operational all-ticket rate; do not silently remove them. Count partial issue resolution separately. Malformed transport payloads are API reliability cases, not valid support tickets, but track their rejected counts.

The supplied 26 tickets are development examples with known ambiguity and unsupported scope. At least TCK-1009 and TCK-1018 require specialist handling under this corpus, and TCK-1023 lacks an actionable problem description: even resolving every other ticket would yield only 23/26 = 88.46% strict all-ticket resolution. More cases require clarification or partial escalation in the draft rubric. This does not justify inventing answers to achieve 95%. A hypothetical 25/26 passes is 96.15% observed on one small sample; it is neither current evidence nor proof of production reliability. Report uncertainty intervals and collect a larger representative, independently reviewed holdout before making a population-level claim. The 95% goal may require broader approved documentation and account diagnostics, beyond better prompts.

## Cases and reference authority

[Source-based case drafts](../evals/cases/support-tickets.json) cover all 26 IDs. Each preserves exact ticket text, original category and original assistant answer; records required and prohibited semantic claims, expected sections/sources, acceptable dispositions and clarification targets; and has `draft_require_human_review` status. `reference_answer` is null deliberately. The fictional guide remains the authority for fixture key behavior, plan prices, limits and policies. The approved `api_transport_supplement` only supplies Bearer authentication transport for Marcus's example; it does not replace fixture UI labels or billing facts.

The raw CSV is noisy baseline evidence, not gold and not retrieval material. Required/prohibited claims need semantic judgment: an answer saying “Team does not provide SSO” contains the string “Team” and “SSO” but must not be rejected by a naive forbidden-token matcher. Category proposals follow the routing map; a justified alternative primary category is acceptable if every concern survives and all required evidence is retrieved.

Use this review sequence:

1. A documentation reviewer checks each required/prohibited claim against exact source spans, scope and revision, and decides answerability before seeing new system outputs.
2. A second reviewer checks multi-issue completeness and disposition. Resolve disagreements, record reviewer/date and promote only agreed cases to approved gold.
3. Optionally produce a concise reference/dummy response from the approved evidence and rubric, then review it. Generate independently of the candidate and exclude noisy CSV responses. A reference can be useful without defining the only acceptable wording.
4. Freeze development cases and create fresh reserved evaluation variants. [Challenge proposals](../evals/datasets/holdout-proposals.json) include 18 adversarial/paraphrase examples, but are visible to developers and therefore are not a sealed holdout. An independent reviewer must reserve unseen variants before tuning.
5. Store run outputs separately under `evals/results/` with case/source hashes and full versions. Do not add generated results to the knowledge base automatically.

## Independent response evaluator

Judge the original ticket, independently parsed concerns, approved rubric, actual candidate and exact retrieved evidence. Do not trust the generator's category, citations or self-reported confidence as correctness. The offline evaluator also sees approved required evidence to diagnose a retrieval miss; the runtime evaluator must not claim support from unavailable content.

Evaluate these gates separately: (1) valid output contract, (2) evidence sufficiency for each concern, (3) factual support and contradiction, (4) relevance to the requested operation, (5) completeness across concerns, (6) calibrated disposition/clarification, and (7) usable customer wording. Reject if any mandatory gate fails. A same-document answer about a provider key fails relevance when the ticket asks to authenticate calls to a published app, even if every quoted statement is faithful to the guide.

A reference comparison should explain missing/contradictory claims, not score word overlap. No BLEU, embedding similarity, judge average or two-model agreement overrides a hard failure. Two models can share the same misconception; independence of evidence review and human calibration matters more than merely using two agents. Do not ask for or store private chain-of-thought; store concise failure reasons and evidence references.

The user-selected [OpenAI Decisions API](https://developers.openai.com/api/docs/guides/decisions) offers `predicate`, `choice` and ordinal `score` questions. Propose separate predicates such as “Are all substantive claims supported by these evidence spans?” and “Does this answer address every supplied concern?” rather than a single vague good-answer probability. Its probabilities/confidence are model estimates requiring empirical calibration, not a guarantee that a ticket resolves. Decisions does not generate customer prose or arbitrary extraction schemas; use a structured textual judge through the Responses path for claim-to-evidence mapping and actionable failure reasons. Refusals, API errors and invalid/missing verdicts must not pass. Decisions availability/version is a dependency to verify before runtime implementation.

Expected internal judge record: `run_id`, `attempt`, gate booleans, supported/unsupported claim references, missing concern IDs, concise failure reasons, retry action, reviewer-required flag and grader version. Keep it in the trace sidecar; use the canonical project schema when implemented. Require deterministic source-ID verification outside the model and human review for contested policy/entitlement claims, contradictory evidence or judge disagreement.

## Bounded correction loop

Allow one initial candidate and at most two corrective attempts as an initial design budget, with an overall timeout/cost ceiling chosen during implementation. Record every attempt; never count retries as new tickets.

| Failure | Corrective action |
|---|---|
| Lost negation or wrong intent/category | Reparse original redacted ticket, preserve negation/operation/entity relations, reconsider candidate categories. |
| Missing or irrelevant evidence | Reformulate the concern query and retrieve alternate relevant sections; preserve cross-category fallback. |
| Supported source, irrelevant answer | Regenerate specifically for unmet concern using already validated evidence. |
| Unsupported/contradictory claim | Remove unsupported claim and regenerate; do not repeatedly search until something superficially agrees. |
| Multi-issue omission | Retrieve/regenerate only missing issue as needed, then reevaluate the complete answer. |
| Genuine missing facts/corpus scope | Ask one useful clarification or escalate immediately; further paraphrasing cannot create evidence. |
| Operational failure or evaluator failure | Return calibrated temporarily unavailable/review result, preserve sanitized trace; use bounded technical retry only for retryable failures. |

Pass each candidate through the full gates after correction. Stop early when no new evidence/interpretation is gained or when the same failure repeats. After the cap, route to review/clarification/escalation with the supported partial answer when appropriate; never automatically release a failed candidate. Retain the initial and final outcome to measure actual retry benefit and regression. A revision loop must not launder fabricated claims by changing a citation or disposition alone.

## Harness tool proposition

| Option | Problem it solves | Proposed role |
|---|---|---|
| [promptfoo](https://github.com/promptfoo/promptfoo) | Repeatable input/output runs, comparisons and regression assertions | First runner once implementation starts: a [custom provider](https://www.promptfoo.dev/docs/providers/custom-api/) can call the Dify endpoint and retain trace metadata; [assertions](https://www.promptfoo.dev/docs/configuration/expected-outputs/) cover JSON/schema checks, custom semantic rubrics and separate metrics. All hard gates remain conjunctive, not a weighted average. |
| [Ragas](https://github.com/vibrantlabsai/ragas) | RAG-specific diagnostic metrics | Optional later diagnostic adapter. [Faithfulness](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/) checks claims against retrieved context; [context recall](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_recall/) checks supporting coverage using a reference. These do not establish the whole ticket was resolved. |
| [DeepEval](https://github.com/confident-ai/deepeval) | Python-based semantic test organization and judge metrics | Alternative if implementation favors pytest. [Answer relevancy](https://deepeval.com/docs/metrics-answer-relevancy) and [faithfulness](https://deepeval.com/docs/metrics-faithfulness) are distinct diagnostics. Choose an explicit LLM judge path matching OpenAI; do not enable a Jev-dependent evaluation mode. |

Recommendation: start with one runner (promptfoo) and project-specific semantic rubrics, then add Ragas only if retrieval diagnostics materially help. Do not install three frameworks or move workflow orchestration out of Dify for evaluation convenience. Verify/pin selected framework versions and licenses at implementation; current docs were researched 2026-10-11. Context7 documentation resolution was attempted but unavailable during this research, so official docs/repositories were used. No dependencies have been added by this plan.

## Software tests versus AI evaluations

| Layer | Required checks before the first working slice is accepted |
|---|---|
| Input parsing/normalization | CSV quoted commas/newlines/Unicode round-trip; blank/null/over-limit request validation; signatures/quoted history removed only from retrieval text; original ticket preserved; negation, provider/app/dataset target and multiple concerns survive. |
| Routing/contracts | Schema, bounded enums, unknown/multiple topics, Decisions response/refusal/error validation; keyword conflicts; alternate primary-category evidence routing. Use stubs for provider calls. |
| Retrieval integration | Correct dataset/revision bindings, source permissions, section metadata, billing-table context, empty hit, index not ready, stale source, rerank/score handling and all required concerns' evidence. |
| Output/export | Canonical structured result, source ID allowlist, no fabricated citations, stable original order/row count, no secret/diagnostic spill; safely quoted CSV. |
| Orchestration | Bounded attempts/timeout/cost, repeated failures stop, judge failures cannot auto-pass, no retries for genuine missing facts, one final exported record per ticket. |
| Golden path | Marcus input → app-key route → §1 plus transport supplement → supported output → passing independent gates → expected three-column export and evidence sidecar. |
| Fault/adversarial | Provider timeout/refusal, malformed response, injection in ticket/retrieved text, fake citation, cross-workspace evidence, confidential secret input, wrong-but-faithful same-source answer. |
| AI quality | Adjudicated 26-case dev suite, eight previously flagged corrections, multi-issue cases, challenge variants, sealed holdout and human judge calibration. Repeat stochastic runs where used and report every run; no cherry-picking the best retry/model seed. |

The external export has exactly `ticket_text,assistant_answer,category`, preserving the full original ticket text/signature, safe CSV quoting and a single selected primary category. Category selection never discards secondary concerns. Keep `ticket_id`, all topics, citations, dispositions, evaluator verdicts and versions in an internal trace sidecar joined by immutable row identity/run ID; avoid conflating a review-required answer with an accepted answer in downstream automation. The consuming workflow must consult the internal disposition before delivery.

For the Marcus output, validate the answer gives app API Access/secret creation, shown-once `app-` storage, app scope, and Bearer transport with supplemental evidence. A greeting or congratulations is optional; exact phrasing is not the gate. Fail an OpenAI-provider-key substitution even if it resembles a plausible support answer.

## Exit gates and reporting

Before building, the design artifacts can pass structural consistency checks only; no claim of live resolution quality follows. Before accepting implementation: all approved regression cases have valid contracts; all eight flagged baseline errors are corrected; no critical credential/policy fabrication occurs; every required concern is handled; unsupported/vague cases have justified dispositions; independent grading is calibrated; a live golden path and operational failure path are verified; and measured answerability/resolution rates are reported with their denominators.

Proposed ≥95% target applies to independently adjudicated answerable holdout tickets first. All-ticket ≥95% remains the broader product objective and requires enough corpus/diagnostic coverage in actual traffic. Report failed cases, inappropriate abstentions, source gaps and uncertainty rather than conceal them under correct-handling percentages. No score, coverage percentage, reviewer approval or production readiness is asserted by this scaffold.

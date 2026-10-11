# Routing and tool research

Reviewed October 11, 2026. This is a technical proposition and compatibility checklist, not a live model benchmark. The user selected **OpenAI Decisions API** for bounded decisions. Dify owns the knowledge workflow; OpenAI Decisions supplies category and evidence judgments; a generative model extracts concerns and writes the answer. No deployment, installation or paid inference was performed for this research.

## Recommended division of work

| Component | Problem it solves | Recommended responsibility |
|---|---|---|
| Conservative text normalizer | Greetings, signatures, markup and quoted boilerplate distract retrieval | Preserve raw text; produce a searchable view; preserve negation, model/provider names, error codes, quantities and scope. Extract the customer's name separately. |
| Structured extraction | A bag of keywords cannot distinguish the credential's owner or separate two requests | Dify LLM node / OpenAI Responses Structured Outputs extracts concerns, object, action, symptoms, constraints, uncertainty and verbatim evidence spans. Schema validation checks shape; factual extraction still requires evaluation. |
| OpenAI Decisions category gate | Resolve app key versus provider key and bounded category overlap | For each extracted concern, use a `choice` across the five category IDs plus `unknown`. Retain secondary categories through separately named topic predicates or separate concern decisions. |
| Dify retrieval | Find the relevant procedure and its conditions | Search the approved corpus with original concern text plus a contextual query; use category/section hints to prioritize, then verify evidence. Keep cross-section expansion available. |
| OpenAI Decisions evidence gate | A passage may share words while answering a different question | Evaluate passage relevance to the concern and whether cited evidence supports each proposed claim. Use separate named predicates so relevance cannot hide unsupported claims. |
| Grounded response writer | Convert applicable documentation into a usable answer | Supply ticket concerns and verified excerpts to a generative LLM; cover all concerns, clarify missing facts, and separate documented possibilities from confirmed diagnoses. |
| Independent response reviewer and controller | A fluent draft can contain wrong scope, causal claims or missing steps | Judge coverage and claim support using ticket plus evidence; emit structured defects. Code/explicit workflow controls retry budget and routing. Reference wording is optional; matching another generated answer is not truth. |

The technical meaning behind the user's “sentiment around keywords” is mostly **contextual intent, object and relation**. Emotional sentiment controls politeness/urgency handling, while “not my OpenAI key,” “published chatbot,” and “from my backend” determine the kind of key. For Marcus, the useful query is “create Dify app-scoped API key for a published chatbot called from an external backend,” not simply “API key.” For TCK-1023, anger adds no missing billing facts: the topic may be billing, but the disposition remains clarification.

## OpenAI: Decisions and Responses serve different roles

OpenAI now documents a dedicated `POST /v1/decisions` endpoint with `predicate`, `choice` and `score` questions. At review time it is public beta and the guide lists `gpt-6-luna` as the supported model. The documented minimum SDK versions for examples are **OpenAI Python SDK 3.26.0** and **JavaScript SDK 7.30.0**; these are package versions, not Python/JavaScript language versions. Confirm target account access and installed SDK before implementation. [Decisions guide](https://developers.openai.com/api/docs/guides/decisions).

Every question needs a stable name. Inspect the returned answer type and validate allowed category values; handle per-question refusals and missing answers as unavailable decisions. `choice` selects a single supplied option and returns its distribution/confidence; `predicate` estimates a condition; `score` summarizes ordered levels. The API supports bounded decisions rather than arbitrary text extraction or response writing. [Decisions API reference](https://developers.openai.com/api/reference/resources/decisions/methods/create).

Use Responses Structured Outputs for custom ticket-analysis objects, concern arrays and answer/reviewer objects. Supported strict schemas constrain output form; they do not guarantee correct interpretation or grounding. Handle refusals and incomplete outputs explicitly, and validate the accepted schema. An OpenAI model can also be configured through Dify's provider plugin for generative LLM nodes, but provider support for Responses/strict schemas and support for the **separate Decisions endpoint** must be checked independently. [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses).

**Integration proposal:** keep an `OpenAIDecisionProvider` behind one small service/adapter, invoked by Dify through an HTTP Request node or a tool with a typed contract. Do not assume installing the ordinary OpenAI model plugin exposes Decisions. A direct authenticated HTTP call is also technically possible; the adapter is preferable when it centralizes validation, credential handling, logging and retry policy. This is a design choice; no adapter has been implemented or called. The existing local Dify API helper can later exercise the published Workflow independently of the Decisions adapter.

No measured speed, price or quality advantage is claimed here. Compare native Dify LLM classification with the selected Decisions implementation on the same reviewed cases, recording response validity, category/concern recall, review rate, latency and token cost. Thresholds are empirical operating points, not a guarantee that a reported 0.95 means 95% of the project's tickets are solved.

## Dify surfaces and boundaries

The native Question Classifier chooses the best class and branches the graph. Current docs distinguish the class description (`class_name`) from the canvas title (`class_label`); stable machine category IDs must be mapped explicitly rather than inferred from presentation labels. It remains useful as a comparison baseline or classifier after concern splitting, but one whole-ticket branch can lose a second issue. [Question Classifier](https://docs.dify.ai/en/self-host/use-dify/nodes/question-classifier).

The LLM node supports a JSON Schema with nested objects/arrays. Its docs caution that providers lacking native structured output receive schema instructions in prompts and may vary. Wire Knowledge Retrieval results into LLM context; do not assume attaching a dataset elsewhere exposes its content to the writer. Validate every intermediate payload. [LLM node](https://docs.dify.ai/en/self-host/use-dify/nodes/llm).

Knowledge Retrieval returns chunk content and metadata and supports multiple knowledge bases, reranking, top-k, score threshold and document metadata filters. Metadata is **document-level** in this documented surface. If the entire four-section guide is one Dify document, a `section_id` filter cannot safely be assumed to select individual chunks. Start with full approved-corpus retrieval; either preserve section IDs in chunk text/provenance or create reviewed per-section documents before testing metadata narrowing. [Knowledge Retrieval](https://docs.dify.ai/en/self-host/use-dify/nodes/knowledge-retrieval).

Do not apply a category-only hard filter before evidence verification. API usage caps are in billing §4, not the key-creation §1; member invitations need §§1 and 4; retrieval failures can need quota conditions. For this small corpus, full-corpus retrieval is a simple baseline. In a larger corpus, verify hinted retrieval, expand to approved cross sections on weak/missing evidence and record what the expansion recovered. Permission/access filters are mandatory even when topical filters expand.

The target Dify edition/version remains unselected. The existing [resource map](RESOURCE_MAP.md) records the prior 1.17.1 release and pinned `main` evidence; do not equate that with installed runtime behavior. Export a target-compatible Workflow before authoring DSL. Neither a locally valid JSON/YAML design nor current hosted docs proves importability, native Decisions support or execution.

## Category mapping

The canonical design config is [category-map.json](../shared/contracts/category-map.json). Existing CSV labels remain provenance; reviewed multi-label routing is the intended behavior.

| Category ID | Concern and boundary | Relevant guide sections |
|---|---|---|
| `api_keys` | Dify app/dataset keys, endpoint authentication, rotation and app API caps; excludes model-provider credential configuration | `workspace_api_keys`, `billing_plans` |
| `account_workspace` | Workspace roles, invitations and member access; Enterprise SSO/audit requests need coverage checks | `workspace_api_keys`, `billing_plans` |
| `model_providers` | Provider credentials, model selection, hosted credits versus direct provider usage, variable credit burn | `model_providers`, `billing_plans` |
| `rag_pipeline` | Ingestion/chunking/indexing, retrieval settings, missing chunks and upload troubleshooting | `rag_pipeline`, `billing_plans` |
| `billing_plans` | Workspace subscription, prices, quotas, payment and downgrade effects; actual account state/proration require more evidence | `billing_plans`; expand to provider/workspace/RAG sections as needed |
| `unknown` | Topic/object/intent cannot be identified or request is unrelated; known topics needing clarification do not become unknown automatically | No fixed section; clarify or inspect corpus coverage |

Use the first explicit actionable concern as primary and retain secondary categories for the output/harness. TCK-1006 spans API caps and SSO/membership; TCK-1015 spans upload troubleshooting and subscription changes; TCK-1021 spans provider setup and retrieval. TCK-1016 remains primary `api_keys`, secondary `billing_plans`, because it asks about app API usage. A category can be clear while the answer is unsupported: SSO configuration remains an account topic with escalation, not an invented Team procedure.

The fixture guide governs fictional policy and UI labels. The separately approved `api_transport_supplement` can support Bearer/Authorization transport for Marcus, but must not replace fixture prices, key scopes or UI conventions. Never ingest the noisy CSV's generated answers as retrieval knowledge.

## GitHub and optional library candidates

| Candidate | Problem solved | Decision and compatibility | License evidence |
|---|---|---|---|
| [langgenius/dify](https://github.com/langgenius/dify) | Workflow, document ingestion, retrieval, generation and traces in one platform | Selected platform. Use public app/knowledge APIs; a fork/custom plugin is unnecessary for initial design. Reuse existing project skills and agent briefs. | [Pinned Dify license](https://github.com/langgenius/dify/blob/5fe7f018764e94aefa06f098a23e28a55d6b4e18/LICENSE): Apache-based Dify license with additional conditions; see resource map. |
| [openai/openai-python](https://github.com/openai/openai-python) | Official typed API client, Responses parsing and dedicated Decisions calls when supported | Selected API family. Check Decisions minimum SDK version and account access; no package was installed. | [Apache-2.0](https://github.com/openai/openai-python/blob/main/LICENSE). SDK license does not license hosted model weights or waive service terms. |
| [pydantic/pydantic-ai](https://github.com/pydantic/pydantic-ai) | Typed agent output, model-independent validation and bounded corrective retries | Optional external Python harness; defer unless it materially simplifies the selected adapter/reviewer. Type validation cannot certify grounding. | [MIT](https://github.com/pydantic/pydantic-ai/blob/main/LICENSE). |
| [typesafe-ai/typesafe-sdk-python](https://github.com/typesafe-ai/typesafe-sdk-python) | Jev decision model client for finite category/relevance questions | User's suggestion is a real tool, verified through official docs. Deferred because the user selected OpenAI Decisions. It is a separate product from PydanticAI. | [MIT SDK license](https://github.com/typesafe-ai/typesafe-sdk-python/blob/main/LICENSE). Jev is a hosted model; SDK license is not a model license. |

PydanticAI's `output_type`, output validators and `ModelRetry` can encode shape/semantic checks and bounded output retries if a Python harness is adopted. Use evidence-bound validators and explicit stop conditions; do not confuse SDK transport retries with quality repair passes. [PydanticAI output validation](https://pydantic.dev/docs/ai/core-concepts/output/).

Jev accepts state plus Choice/Score/Noul questions and returns typed decisions; it does not write customer responses. Its official quickstart also links a coding-agent skill at `typesafe-ai/skills`. This research records the resource without installing or activating it. [Official TypeSafe quickstart](https://docs.typesafe.ai/introduction/quickstart), [official skill overview](https://docs.typesafe.ai/agent-skill). Its confidence guidance and model limitations are additional evaluation inputs if it is reconsidered later. [Confidence](https://docs.typesafe.ai/confidence), [known limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13).

Promptfoo, Ragas and DeepEval concern evaluation, not category ownership or retrieval authority. See the project's evaluation design for selection. Avoid introducing overlapping orchestrators before the Dify/OpenAI vertical slice is proven.

## Research quality and implementation gate

Official Dify/OpenAI/TypeSafe docs and official GitHub repositories support feature claims above. Context7 successfully returned Dify and TypeSafe primary documentation after initial availability failures; subsequent PydanticAI/OpenAI query calls failed in transport, so their official web docs were used. The source inventory and source-based category map were read locally. Searches returned several similarly named unofficial Jev sites; they were excluded. No GitHub issue report is presented as a confirmed runtime defect, and no exact untested dependency version is selected.

Before building: choose target Dify/version and approved generative models; verify Decisions access and SDK support; finalize contracts, per-concern category tests and evidence checks; decide the shared retry/cost budget; then implement one ticket through retrieval, generation, independent review and output. Keep mock adapters for offline golden-path tests, and label fixture-only results separately from live Dify/OpenAI runs.

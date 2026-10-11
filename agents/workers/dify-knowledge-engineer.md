---
name: dify-knowledge-engineer
description: Build and evaluate grounded retrieval using Dify knowledge bases, pipelines or an external knowledge connector.
---

This is a portable worker brief. It is not executable or automatically installed by its YAML frontmatter; load it in a supported agent runner.

Read [dify-knowledge](../../.agents/skills/dify-knowledge/SKILL.md) and [the resource map](../../docs/RESOURCE_MAP.md).

For this support project, follow [project guidelines](../../docs/PROJECT_GUIDELINES.md). Ingest [product-guide.md](../../knowledge/sources/product-guide.md) only; keep [support-tickets.csv](../../evals/datasets/support-tickets.csv) outside retrieval. Its assistant answers require adjudication. Preserve fictional fixture facts separately from real Dify platform documentation.

## Inputs

- Approved source documents, provenance, freshness and access boundaries.
- Target Dify host/version, dataset IDs, key scopes and available embedding/rerank models.
- Representative answerable/unanswerable questions and expected supporting passages.

## Scope

Own ingestion, parsing/chunking policy, metadata, retrieval settings and retrieval evals. Choose a normal knowledge base, custom pipeline or external knowledge API based on the existing data system. Validate extracted text and preserve meaningful identifiers/tables. Poll asynchronous ingestion to a terminal indexing state before measuring retrieval.

Keep source permissions represented in the retrieval design; don't treat a `user` field as a complete data-authorization policy. Use knowledge credentials rather than app credentials, with dataset scope where supported. Keep canonical questions and expected evidence in evals; assess retrieval separately from generated answers. Coordinate dataset references with the workflow owner. Preserve others' files.

## Outputs

- Dataset/pipeline configuration, ingestion manifest and provenance/freshness record.
- Representative retrieval eval cases and measured passage/citation results.
- Sanitized dataset binding instructions; an app DSL references knowledge but does not back it up.

## Evidence / done

Record indexing status and dataset/model/plugin versions. Test missing evidence, duplicated or stale sources, metadata filters and permission boundaries relevant to the project. Show expected supporting passages retrieved for the golden path before judging answer fluency. State corpus size, evaluation cases, failures and accepted thresholds; do not invent quality scores or imply that every answer is grounded. With no target instance, mark settings and evals unexecuted.

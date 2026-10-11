---
name: dify-knowledge
description: Configure and evaluate Dify knowledge bases, ingestion, and retrieval using version-aware public Knowledge APIs and retrieval evidence.
---

# Dify Knowledge

Start with the project's source documents, access rules, representative queries, and required citations. Identify target deployment/version and dataset IDs. A Dify DSL references a knowledge base but does not carry its documents. Plan data transfer and ID remapping separately.

When present, read [project guidelines](../../../docs/PROJECT_GUIDELINES.md). For this toolkit, `knowledge/sources/product-guide.md` is user-supplied fictional product knowledge. `evals/datasets/support-tickets.csv` contains noisy supplied RAG outputs, not authoritative answers: do not ingest them or score candidates by matching them blindly. Derive expected facts from the guide and mark cases the guide cannot answer. Fictional plan prices are fixture facts, not real Dify pricing.

## Ingest and retrieve

1. Inspect the existing dataset's index technique, embedding model, chunk configuration, metadata, and retrieval settings. Reuse it when appropriate; do not silently rebuild a populated index.
2. Choose chunks that preserve the source's meaning, such as headings and parent/child context where supported. Preserve source identifier, version/date, and citation location. Select the embedding/rerank models actually installed on the target.
3. For public API work, copy the Knowledge Service API endpoint and use a knowledge key with the needed scope. Current scoped keys can address permitted `dataset_id` paths but cannot list/create all datasets; a list request's 403 may be a scope restriction rather than invalid credentials. Verify that behavior for the deployed release.
4. Document creation runs asynchronously. Capture the returned document/batch IDs, poll indexing with a bounded deadline, and handle terminal errors. A successful upload is not proof that retrieval is ready. Do not blindly retry a timed-out create request and duplicate content.
5. Retrieve expected facts, ambiguous questions, and questions outside the corpus. Inspect returned chunks, scores, metadata, and source attribution before tuning top-k, thresholds, hybrid search, or reranking. Retrieval scores are model/config dependent and are not universal confidence percentages.
6. In a Workflow/Chatflow, wire the Knowledge Retrieval output into model context and provide explicit grounded-answer behavior when no relevant content is found. Test both retrieval and the final generated answer.

Keep software contract tests separate from answer-quality evaluations. Record corpus version, query/expected source, retrieval settings, model versions, and observed output in the project's `evals/` when present. Use a deterministic fixture corpus for local demos without mislabeling it as live Dify evidence.

## Toolkit helper and boundaries

Read `python3 scripts/dify_api.py --help` plus subcommand help from the toolkit root. Relevant commands are `knowledge-list`, `knowledge-get`, `knowledge-create-text`, `knowledge-index-status`, and `knowledge-retrieve`; place global `--dry-run` before the subcommand to inspect sanitized requests before authorized ingestion. The helper reads flags/environment variables, not `.env` files. It does not imply complete coverage of document updates, files, pipelines, or metadata APIs.

External knowledge connectors call an API implemented by your own retrieval service; their response schema is distinct from Dify's Knowledge API. Use the documented external knowledge contract when choosing that design. Keep credentials and private document contents out of public artifacts.

## Evidence

Reviewed 2026-10-11: [Knowledge API](https://docs.dify.ai/en/api-reference/guides/knowledge), [Create document by text](https://docs.dify.ai/en/api-reference/documents/create-document-by-text), [Indexing status](https://docs.dify.ai/en/api-reference/documents/get-document-indexing-status), [Test retrieval](https://docs.dify.ai/en/cloud/use-dify/knowledge/test-retrieval), [External Knowledge API](https://docs.dify.ai/en/self-host/use-dify/knowledge/external-knowledge-api). Check edition/release differences before applying live documentation.

Pinned implementation evidence: [Knowledge Service API controllers](https://github.com/langgenius/dify/tree/5fe7f018764e94aefa06f098a23e28a55d6b4e18/api/controllers/service_api/dataset), including `dataset.py`, `document.py`, and `hit_testing.py`, at Dify commit `5fe7f018764e94aefa06f098a23e28a55d6b4e18`.

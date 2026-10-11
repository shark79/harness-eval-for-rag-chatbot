# Connect the ticket workspace to Dify Cloud

The configured destination is `https://api.dify.ai/v1`. The local application is ready to call a published Workflow; a Cloud Workflow named talent-hunt-eval-harness exists but had no published version when inspected; its model and knowledge configuration have not been verified. The default `.env` uses local extractive retrieval and offline evaluation until credentials are available.

## Workflow contract

Create a Workflow in the intended Cloud workspace, with required text input `ticket_text` and optional text input `evaluation_feedback` (empty by default). Use the approved product guide and API transport supplement as knowledge documents; exclude the ticket CSV and generated answers. Inspect chunking and indexing before publishing. Preserve source and section identity using the [evidence manifest](../shared/contracts/evidence-sources.json); metadata identifiers must map back to the approved local revision.

The smallest useful graph is input → Knowledge Retrieval → grounded LLM answer → deterministic evidence/attribution mapping → output. Use `agents/prompts/answer-generator.md` and the project guidelines for answer behavior. Category hints must preserve app/dataset/provider key scope and secondary concerns. The feedback input is for one evidence-anchored corrective response, using unchanged policy and scoring rules. It must not instruct the model to optimize an evaluation score.

Return these named outputs:

| Output | Contract |
|---|---|
| `answer` | Nonempty customer response string |
| `category` | `api_keys`, `account_workspace`, `model_providers`, `rag_pipeline`, `billing_plans`, or `unknown` |
| `disposition` | `answered`, `needs_clarification`, `escalated`, `partial_escalation`, or `temporarily_unavailable` |
| `evidence` | Array of actual retrieved records: `evidence_id`, `source_id`, `section_id`, `source_revision`, exact `excerpt` |
| `citations` | Array referencing those records by `evidence_id`, `source_id`, `section_id`; optional excerpt must match |

JSON-encoded arrays are accepted when the Workflow output cannot expose native arrays. Source revisions use the manifest's SHA-256. `evidence_id` is a stable identifier assigned to returned evidence, not a model-invented citation. Map Dify retrieval records to these values deterministically using original content and document identity. Do not synthesize evidence from an answer after generation. The backend verifies excerpt membership, revision and citation relationships; unsupported content is rejected.

Publish the Workflow and obtain its app key from its API Access page. Follow that app's generated API documentation for its current configuration. The adapter uses blocking `POST /workflows/run`; Chatbot/Chatflow API keys with different execution endpoints are not interchangeable with a Workflow endpoint. See the [official workflow API](https://docs.dify.ai/en/api-reference/workflow-execution/execute-workflow) and [API authentication guide](https://docs.dify.ai/en/api-reference/guides/get-started).

## Local environment

Edit the ignored `.env` locally:

```dotenv
RAG_MODE=dify
DIFY_API_BASE_URL=https://api.dify.ai/v1
DIFY_INPUT_NAME=ticket_text
DIFY_APP_API_KEY=
EVAL_MODE=decisions
OPENAI_API_KEY=
```

Fill the blank values with the respective keys. The Dify app key executes generation; the OpenAI key calls the independent Decisions judge. A knowledge API key is only needed for separate management/retrieval CLI operations. Keep credentials server-side and out of source control and chat.

Recreate the container after changing its environment:

```sh
docker compose up -d --force-recreate
```

Try Marcus's question in the UI, inspect actual evidence from the app-key section and transport supplement, then run the fresh-chatbot suite. Decisions access is a dependency to verify with the configured account. Missing keys, provider failures and unrun judgments hold responses. No automatic fallback to extractive mode occurs if a configured Cloud call fails.

The first live result must be reviewed for source mapping, missing concerns and score calibration. A 0.80 score is a project policy threshold, not proof of correctness or production readiness. Current evaluation cases remain draft references requiring independent review.

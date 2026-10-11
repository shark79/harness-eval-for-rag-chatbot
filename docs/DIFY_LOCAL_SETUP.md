# Connect the ticket workspace to local Dify

The selected endpoint is `http://localhost/v1` for native commands and `http://host.docker.internal/v1` for the ticket container. These point to a separate self-hosted Dify deployment, not the ticket demo on port 8080. No local Dify service was running when inspected. The default `.env` retains extractive retrieval and offline evaluation until the local Workflow and credentials are ready.

## Local Dify deployment

The official 1.17.1 deployment checkout is available at `/Users/shark7901/Documents/Projects/dify-local`, commit `8387590ace4a094de812b7847fc6a4c3a27cd52b`. It uses sparse checkout for the Docker tree after full-clone transfer failures. All deployment files and Compose syntax were verified; Dify startup and account initialization remain pending. See [clone recovery and startup commands](../starter-kit/TROUBLESHOOTING.md#dify-clone-resets-or-reports-early-eof).

Use the [official Docker Compose guide](https://docs.dify.ai/en/self-host/deploy/quick-start/docker-compose) and the Compose files from an explicit released Dify tag. The toolkit Compose stack runs only the ticket demo; it does not install Dify. On macOS, the official guide recommends at least 2 virtual CPUs and 8 GiB of Docker VM memory.

After starting Dify, open `http://localhost/install` to initialize its local admin account, then `http://localhost` to create the Workflow. A Cloud workspace and its app keys are separate from this local instance. Publish the local Workflow, then create its app API key from its API Access page and store it only in `.env`.

If nginx publishes a different host port, include it in both endpoint variables. Compose maps `host.docker.internal` to the Docker host gateway; `localhost` inside the ticket container would address the ticket container itself. Do not use the internal Dify `/console/api` endpoint for Workflow execution.

## Workflow contract

Create a Workflow in the local workspace, with required text input `ticket_text` and optional text input `evaluation_feedback` (empty by default). Use the approved product guide and API transport supplement as knowledge documents; exclude the ticket CSV and generated answers. Inspect chunking and indexing before publishing. Preserve source and section identity using the [evidence manifest](../shared/contracts/evidence-sources.json); metadata identifiers must map back to the approved local revision.

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
DIFY_API_BASE_URL=http://localhost/v1
DIFY_DOCKER_API_BASE_URL=http://host.docker.internal/v1
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

Try Marcus's question in the UI, inspect actual evidence from the app-key section and transport supplement, then run the fresh-chatbot suite. Decisions access is a dependency to verify with the configured account. Missing keys, provider failures and unrun judgments hold responses. No automatic fallback to extractive mode occurs if a configured Dify call fails.

The first live result must be reviewed for source mapping, missing concerns and score calibration. A 0.80 score is a project policy threshold, not proof of correctness or production readiness. Current evaluation cases remain draft references requiring independent review.

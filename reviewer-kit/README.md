# Support answers you can inspect before sending

This demo pairs a documentation-based support assistant with an independent evaluator. It helps reviewers catch convincing answers that use the wrong API key, invent product policy, or miss the customer's concern.

The project uses a **fictional product guide and 26 fictional support tickets**. Existing CSV answers are examples to assess, not facts the chatbot should memorize. A separately approved supplement supports Bearer authorization and backend key handling.

## What a reviewer sees

1. Open **RAG bot**, select a sample ticket, and click **Draft answer**. The bot retrieves approved documentation and shows its answer with supporting passages.
2. Click **Evaluate this response**. The **Eval bot** tab shows a score, the reasons for it, ranked quality dimensions, source evidence, and a **Ship** or **Hold off** recommendation.
3. A borderline answer can receive **one correction**, with the original and final scores and retry flags retained. An unsupported answer stays held even if its overall score looks high.

“Ship” is a provisional recommendation in this demo. The application does not send customer messages. Human approval of the case rubrics and judge calibration are still required.

## Review the evidence without setup

The ZIP contains this README and the project under `project/`.

| Verified example | Outcome |
|---|---|
| Marcus asking for an app API key | **0.653 Hold** before the missing transport source was indexed; **0.930 Ship** after retrieval and prompt repair |
| All 26 existing CSV answers | **7 Ship / 19 Hold**; all eight source-audited known-error answers were held |
| A fresh provider-setup answer, TCK-1002 | **0.552 Hold** for missing required steps; no retry |
| Dataset API key regression, TCK-1011 | **0.991 Ship** after the retrieval repair; correct app/dataset scope and all gates passed |

Open the [26-ticket score report](project/evals/results/20261011T215139Z-fdc5ab46-baseline.md), [repaired Marcus dashboard](project/docs/screenshots/eval-marcus-fixed.png), and [project rulebook](project/docs/PROJECT_GUIDELINES.md).

A separate [controlled retry trace](project/evals/results/cloud-smoke/controlled-live-retry.json) used a **synthetic 0.75 scheduling score** to exercise exactly one correction. It made two real Dify generations and two real evaluator calls; their unmodified quality scores were **0.9305 → 0.967375**. It is excluded from the benchmark. The [LLM trace](project/docs/screenshots/correction-llm-trace.png) confirms that correction feedback reached the model. A naturally triggered live borderline retry remains unobserved. These results do not establish a 95% resolution rate.

## How scores become recommendations

Harness Evals executes the checks; our separate OpenAI Decisions judge rates six dimensions, normalizes them to 0–1, and calculates their weighted average. This is answer quality, separate from retrieval similarity:

| Dimension | Weight |
|---|---:|
| Grounding in evidence | 30% |
| Factual correctness | 25% |
| Relevance to the concern | 20% |
| Completeness | 15% |
| Category accuracy | 5% |
| Clarity | 5% |

**At least 0.80:** Ship only if every mandatory gate passes. **0.70 through below 0.80:** one corrective attempt when gates pass, then Ship or Hold. **Below 0.70:** Hold immediately. No improvement or an improved score still below 0.80 means Hold.

Source revisions, exact passages and citations must validate. Semantic gates check support, key/entity scope, concern coverage and appropriate disposition; each uses a provisional predicate probability cutoff of **0.90**. Missing judgments or failed gates mean Hold. Scores measure assessed answer quality, not the probability of solving a customer's problem.

## Run the two-tab demo

Install Python, Node.js/npm and Docker, then from the extracted folder:

```sh
cd project
make setup
```

For live use, import the [Dify Workflow export](project/agents/workflows/support-ticket-rag.yml) into your own Dify Cloud Studio. Configure OpenAI for generation/embedding and the Tongyi reranker, then create a knowledge base and upload the two files from `uploads/` with their supplied filenames. Use High Quality indexing; keep document chunks aligned to the paragraphs as described in the [rulebook](project/docs/PROJECT_GUIDELINES.md#transport-retrieval-repair--2026-10-11). In the imported Knowledge Retrieval node, replace the original workspace's knowledge reference with your new knowledge base. Publish the Workflow and create its app API key. The export contains the graph, not the knowledge index or provider credentials. Edit local `.env`:

```dotenv
RAG_MODE=dify
EVAL_MODE=decisions
DIFY_API_BASE_URL=https://api.dify.ai/v1
DIFY_DOCKER_API_BASE_URL=https://api.dify.ai/v1
DIFY_APP_API_KEY=your-published-workflow-key
OPENAI_API_KEY=your-local-evaluator-key
```

Keep keys local. The OpenAI provider credential saved inside Dify is separate from the evaluator credential above. Live calls consume provider credits.

```sh
docker compose up -d --build
```

Open **http://127.0.0.1:8080/** and follow the three review steps above. Without keys, leave the default `extractive` / `offline` modes: the UI quotes local approved passages and performs rule checks, but semantic scores remain unrun and responses held. Recorded live reports remain available to inspect.

The stack is Python's standard-library HTTP server, plain HTML/CSS/JavaScript, **Harness Evals 0.25.3**, Docker, Dify Cloud Workflow with `gpt-4.1-mini`, `text-embedding-3-small` and `qwen3-rerank`, and OpenAI Decisions with `gpt-6-luna`.

Developer checks: `make test PYTHON=.venv/bin/python` and `make check PYTHON=.venv/bin/python`. View logs with `make logs`; stop with `docker compose down`. See the [developer README](project/README.md) for details.

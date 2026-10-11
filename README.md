# Dify project toolkit

A ticket chatbot and separate Harness Evals dashboard for reviewing support answers against approved documentation.

The supplied fictional support dataset contains answers that invent or contradict product policy. The project uses approved product documentation for retrieval and the 26 tickets as a noisy baseline to review and evaluate. Start with [project guidelines](docs/PROJECT_GUIDELINES.md), which records source provenance, a ticket-by-ticket audit and proposed acceptance criteria.

## What is implemented

- Five project-local skills: Workflow/Chatflow design, Service API integration, Knowledge/RAG, plugins and self-hosting under `.agents/skills/`.
- Four portable worker briefs under `agents/workers/`; load them as role instructions rather than assuming automatic agent registration.
- [Dify resource map](docs/RESOURCE_MAP.md), covering upstream source, docs, SDKs, native agent capabilities, plugins, Marketplace, MCP, deployment and compatibility.
- `scripts/dify_api.py`, a dependency-free Python helper for app metadata, blocking generation and knowledge operations, with credential-free request previews.
- Byte-preserving copies of both supplied files, separated into knowledge sources and evaluation data.

The basic application serves a ticket form, real local document retrieval, source excerpts, CSV export and a separate evaluation dashboard. Self-hosted local Dify is selected for live generation; a published Workflow and app key must be configured. Local extractive mode quotes approved paragraphs and is explicitly labeled. It does not emulate a model.

[Harness Evals](https://github.com/harness/harness-evals) supplies real `Golden`, `EvalCase`, metric and `Score` execution. OpenAI Decisions supplies optional semantic judging. Every final recommendation is **ship** or **hold off**. Only scores in **[0.70, 0.80)** permit **one** corrective response attempt; at least **0.80** also requires every grounding/relevance gate to pass. No score or no improvement means hold off. See [scoring policy](docs/SCORING_POLICY.md). Current rubric drafts and judge calibration block production delivery.

## Architecture and stack

The application boundary is browser → Python HTTP backend → local approved retrieval or local Dify Workflow → separate Harness Evals service → OpenAI Decisions when configured. Keys stay server-side. The UI is static JavaScript; the backend uses the standard library and pinned Harness Evals core. Docker uses Python 3.12. Tests use unittest, real local HTTP requests, provider stubs and Node’s built-in test runner.

The inspected upstream research snapshot is `langgenius/dify` commit `5fe7f018764e94aefa06f098a23e28a55d6b4e18`. That is research provenance, not a deployment recommendation. Select a release and verify feature/API compatibility before adoption; see the resource map.

## Setup, run and verification

From this repository directory:

```sh
make setup
make build
make up
```

Open [Ticket desk](http://127.0.0.1:8080). In the RAG bot tab, select a CSV ticket and draft an answer. Inspect its sources, then click Evaluate this response to open the Eval bot tab. Review the recommendation, original/final scores, retry flags and citations. You can also run the 26-ticket suite against existing CSV answers or fresh chatbot answers. Offline evaluation displays actual rule checks and **unrun** semantic scores; responses remain held. Generated reports live under `evals/results/`.

```sh
make test PYTHON=.venv/bin/python
make check PYTHON=.venv/bin/python
.venv/bin/python scripts/run_evaluations.py --source baseline
.venv/bin/python scripts/run_evaluations.py --source chatbot
```

Use `.venv/bin/python -m backend.app.api.server` for local development without Docker. Manage the standing container with `docker compose logs --tail=100 ticket-assistant` and `docker compose down`. Rebuild after source changes. See [quickstart](starter-kit/QUICKSTART.md), [environment variables](starter-kit/ENVIRONMENT.md), and [local Dify setup](docs/DIFY_LOCAL_SETUP.md).

Tests verify software behavior and score boundaries using controlled judge fixtures. Offline CSV runs assess explicit regressions and source integrity. Neither proves semantic resolution quality or the 95% product target. Live Dify/OpenAI verification requires keys.

## Configuration and commands

The web application and evaluation CLI centrally load local `.env`; process environment values override it. The standalone Dify helper reads only process environment, not `.env` automatically. Use `.env.example` as a configuration template for the consuming project's centralized environment loader or export variables in your shell. `DIFY_API_BASE_URL` defaults to `http://localhost/v1`; Compose overrides it with `DIFY_DOCKER_API_BASE_URL` (default `http://host.docker.internal/v1`); `DIFY_TIMEOUT` defaults to 100 seconds. Live app commands require `DIFY_APP_API_KEY`; live knowledge commands require the separate `DIFY_KNOWLEDGE_API_KEY`. Live generation requires `DIFY_USER` or `--user`.

```sh
python3 scripts/dify_api.py --help
python3 scripts/dify_api.py info
python3 scripts/dify_api.py parameters
python3 scripts/dify_api.py --dry-run workflow-run --inputs '{"ticket_text":"Where do I get an app API key?"}' --user demo-user
python3 scripts/dify_api.py --dry-run knowledge-create-text 00000000-0000-0000-0000-000000000001 --name product-guide --text-file knowledge/sources/product-guide.md
```

The placeholder dataset UUID and dry-run commands are examples, not created resources. Use an actual dataset ID and the app's documented input names for live operations. Generation can consume provider credits; document creation changes a knowledge base. Review previews before live operations.

Available commands: `info`, `parameters`, `workflow-run`, `chat`, `completion`, `knowledge-list`, `knowledge-get`, `knowledge-create-text`, `knowledge-index-status`, `knowledge-retrieve`. Consult each command's `--help` for payload-file and query options. `knowledge-list` returns one page. Creating text does not wait for indexing; use the returned batch ID with `knowledge-index-status` before retrieval.

The helper accepts JSON object responses in blocking mode, rejects redirects, bounds file/response sizes and avoids automatic POST retries. Workflow generation with a failed status returns a failure exit code. Chat modes that require streaming, file uploads, console/workspace authoring and plugin management need dedicated integrations. Successful response JSON and dry-run payloads may contain customer data; handle output accordingly. Remote plain HTTP requires the explicit `--allow-insecure-http` option; prefer HTTPS.

## Use the skills and briefs

Open this repository as a Codex project for project-local skill discovery. Example request: “Use `$dify-workflow` to design the first support-ticket slice following `docs/PROJECT_GUIDELINES.md`.” For another project, copy only the needed whole skill folders into its `.agents/skills/` directory after inspecting existing entries. Global installation has not been performed.

See [adoption guidance](docs/ADOPTION.md) for integration steps. Native Dify agent skills, Codex skills and Dify plugins are different formats and execution surfaces; use the relevant skill to choose the appropriate one.

## Repository structure

```text
.agents/skills/          Codex skill entrypoints, references and UI metadata
agents/workers/          Portable role briefs
docs/                   Guidelines, resource map and adoption instructions
backend/app/            API, configuration, retrieval and Dify adapter
frontend/src/           Static ticket workspace and evaluation dashboard
knowledge/sources/      Approved guide and narrow transport supplement
shared/                 Canonical contracts, schemas and examples
agents/evals/           Harness Evals metrics, policy and runner
evals/                  Dataset, draft cases and generated results
starter-kit/            Exact setup, configuration and troubleshooting
scripts/                Service API helper
tests/                  Unit, local HTTP integration and CLI tests
```

## Known limitations and next steps

Configure a published local Dify Workflow and its app key locally; configure OpenAI access to measure semantic scores. Adjudicate the case drafts, calibrate the judge, then test a fresh holdout before approving delivery. The basic lexical router cannot establish semantic completeness for multi-issue tickets. The full structured concern-extraction/retrieval-repair design remains documented in `docs/HARNESS_DESIGN.md`; the current correction path passes evidence-anchoring feedback to the configured Workflow. No automatic ticket delivery is implemented.

# Dify project toolkit

Reusable Codex skills, agent briefs and API tooling for building a grounded Dify support assistant.

The supplied fictional support dataset contains answers that invent or contradict product policy. The project uses approved product documentation for retrieval and the 26 tickets as a noisy baseline to review and evaluate. Start with [project guidelines](docs/PROJECT_GUIDELINES.md), which records source provenance, a ticket-by-ticket audit and proposed acceptance criteria.

## What is implemented

- Five project-local skills: Workflow/Chatflow design, Service API integration, Knowledge/RAG, plugins and self-hosting under `.agents/skills/`.
- Four portable worker briefs under `agents/workers/`; load them as role instructions rather than assuming automatic agent registration.
- [Dify resource map](docs/RESOURCE_MAP.md), covering upstream source, docs, SDKs, native agent capabilities, plugins, Marketplace, MCP, deployment and compatibility.
- `scripts/dify_api.py`, a dependency-free Python helper for app metadata, blocking generation and knowledge operations, with credential-free request previews.
- Byte-preserving copies of both supplied files, separated into knowledge sources and evaluation data.

This is a toolkit and project baseline. A published support workflow, frontend/backend application, live Dify instance and model-quality benchmark remain to be implemented against the selected project.

## Architecture and stack

Use the consuming project's existing frontend and backend. The intended boundary is frontend → backend → published Dify Service API → retrieval/model/tools. Keep secret keys and deterministic business services on the backend. Dify manages the workflow and approved knowledge base. The CLI uses Python 3.11+ standard library; tests use `unittest` and a local HTTP stub.

The inspected upstream research snapshot is `langgenius/dify` commit `5fe7f018764e94aefa06f098a23e28a55d6b4e18`. That is research provenance, not a deployment recommendation. Select a release and verify feature/API compatibility before adoption; see the resource map.

## Setup and verification

From this repository directory:

```sh
make setup
make test
make check
make demo
```

`make demo` prints a proposed workflow request without credentials or network access. It verifies request construction; it does not run a live Dify workflow.

`make test` covers validation, successful/failed workflow responses, safe error handling, local HTTP integration and subprocess CLI behavior. A real Dify instance, plugin import and provider/model calls must be verified separately.

## Configuration and commands

The helper reads the process environment, not `.env` automatically. Use `.env.example` as a configuration template for the consuming project's centralized environment loader or export variables in your shell. `DIFY_API_BASE_URL` defaults to `https://api.dify.ai/v1`; `DIFY_TIMEOUT` defaults to 100 seconds. Live app commands require `DIFY_APP_API_KEY`; live knowledge commands require the separate `DIFY_KNOWLEDGE_API_KEY`. Live generation requires `DIFY_USER` or `--user`.

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
knowledge/sources/      Approved fictional knowledge document
evals/datasets/         Raw noisy support-answer dataset
scripts/                Service API helper
tests/                  Unit, local HTTP integration and CLI tests
```

## Next steps

Select the target project and Dify deployment, configure a model and knowledge base, adjudicate evaluation cases, build/import a version-compatible workflow, and verify one real project request. Preserve the guidelines as the maintained project reference. This toolkit has no runnable application service; use the selected Dify release's upstream Compose stack for self-hosting rather than inventing a reduced deployment.

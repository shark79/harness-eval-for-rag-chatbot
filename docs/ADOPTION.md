# Adopt Dify in an existing project

This toolkit is prepared independently because the target project and first workflow have not been specified. It contains project-local Codex skills, portable agent briefs and a Python command-line helper. It does not provision a Dify instance or register custom agents with an agent runtime.

## Choose the first vertical slice

Identify one real user input, the required data/tools and the expected result. Inspect the existing project first. Choose a Workflow for a defined task or Chatflow for a conversation. If autonomous agent execution is needed, confirm the installed Dify version supports the selected agent mode and its deployment dependencies.

The default integration boundary is existing frontend → existing backend → Dify Service API. Keep product authentication, business operations and secrets in the existing backend. Use a Dify workflow to coordinate model calls, retrieval and approved tools. Keep deterministic business rules in project services.

For a RAG slice, prepare a small approved corpus, index it, verify ingestion completion and retrieval, then connect the knowledge base to the app. For a tools slice, select an existing trusted plugin, a supported MCP connection or a narrow HTTP/OpenAPI adapter before writing a plugin.

## Make the skills discoverable

Open this toolkit as a Codex project to use its `.agents/skills/` entries. To use them in another project, copy the relevant whole skill folders into that project's `.agents/skills/` directory, preserving each skill's references and UI metadata. Inspect any existing folder with the same name first and merge intentionally. Do not replace the project's `AGENTS.md` or copy this toolkit over its application source.

The four files under `agents/workers/` are briefs that a coordinating agent can load. A Markdown brief does not automatically create or register a runnable agent. Select the actual agent runtime before adapting its registration format.

Optional global installation means copying selected whole skill folders to `~/.codex/skills/` after reviewing existing entries. The delivered toolkit has not modified that directory. The skills are authored for Codex; native Dify agent skills have their own packaging, runtime and support requirements. Use the native Dify documentation rather than uploading this entire toolkit as a plugin.

## Connect credentials and verify

Create the app and use its API Access documentation to confirm the app mode, base URL, inputs and response contract. Create separate app and knowledge API keys as needed. `.env.example` describes helper variables; the helper reads exported process environment values only.

Run `python3 scripts/dify_api.py --help` before choosing a command. Use `--dry-run` to review requests without credentials or network access. Then verify read-only app metadata against the actual instance, followed by an explicitly requested generation or ingestion operation. These can consume provider credits or modify knowledge bases.

Save a Dify-exported DSL with the project, record the Dify version and plugin identifiers, and re-import into a disposable app on the same target version. Check credentials and dataset bindings separately; do not assume exports are deployment manifests. Verify the final result and workflow status, not just HTTP 200.

## Self-hosting

Use the selected release's upstream `docker/` Compose configuration and environment templates. Do not duplicate Dify's services into a hand-written simplified stack. Follow the `dify-self-host` skill for preflight, persistence, startup, API verification and upgrades. Dify is an external platform here; this toolkit itself has no frontend or backend service and needs no container deployment.

## Completion evidence

Record the target project's path, Dify release, app mode/ID, dataset IDs, plugin versions and required environment names without secret values. Verify one end-to-end project request against the running Dify instance. Add deterministic fixtures for provider outages and a small separate evaluation set for answer quality, citations and retrieval. Keep source-control tests distinct from model-quality evaluations.

The current toolkit can validate its local helper and skills without a live instance. A live Dify call, imported DSL, installed plugin or running deployment must be verified separately before claiming that project integration works.

---
name: dify-api-integration
description: Integrate a published Dify app into a backend using its public Service API, with correct app mode, user identity, and response handling.
---

# Dify API Integration

Identify the actual deployment/version, Service API base URL, app mode, and published inputs. Use the target app's API documentation; current Cloud docs can describe endpoints absent from a pinned release. Public app keys are scoped to an app. Knowledge keys have a separate scope and cannot substitute for app keys.

## Contract and implementation

- Store keys in the backend environment; keep the adapter under the project's integrations/services boundary. Never put a Dify key into browser code, prompts, fixtures, or committed request logs.
- Get app information and parameters before guessing input names. The Cloud base URL is `https://api.dify.ai/v1`; use the copied Service API URL for self-host. Normalize a single `/v1` suffix.
- Workflow execution uses `POST /workflows/run`; Chatflow, Chatbot, and supported Agent modes use `POST /chat-messages`; Text Generator uses `POST /completion-messages`. Select the endpoint from the app mode and target's documentation rather than routing all apps through one call.
- Preserve a stable opaque `user` for the real end user. Keep conversation IDs associated with the same app and user; authorize that mapping in your backend rather than trusting a caller-supplied ID.
- Choose blocking only for supported short calls. Current Agent and Legacy Agent docs require streaming. Parse SSE frames incrementally, ignore pings, and dispatch documented events by app mode. An HTTP 200 stream can still contain an error or failed workflow status; do not report success before its terminal status.
- Set connect/read timeouts, propagate cancellation when supported, and retain task/run IDs for diagnostics. A dropped connection may leave the operation running; check status before resubmitting a workflow with side effects. Retry only within the task's bounded policy and never claim exactly-once execution without a verified mechanism.

## Toolkit helper

From the toolkit root, run `python3 scripts/dify_api.py --help` and the chosen command's `--help` before composing calls. The helper covers `info`, `parameters`, `workflow-run`, `chat`, and `completion`; place the global `--dry-run` flag before the subcommand to inspect sanitized requests before a live run. It reads explicit flags/environment variables and does not load `.env` automatically. Generation is blocking-only, so use another client for streaming-only Agent modes and flows requiring Human Input. Keep unsupported streaming/resume/upload behavior explicit instead of presenting a blocking helper as a complete SDK.

Verify the adapter with local mock responses covering valid output, authentication errors, invalid inputs, timeout, and any supported SSE failure path. A dry run verifies request construction; it does not verify a Dify deployment or provider response. Run live generation only within the requested integration/test scope because it can consume provider credits and invoke configured tools.

## Boundaries and evidence

The Service API runs published applications; do not invent public endpoints for app creation, DSL authoring/import, or console administration. Official `difyctl`, the plugin scaffolding CLI, and this toolkit's Python helper are different tools. Match the documented tool and release to the task.

Reviewed 2026-10-11: [API getting started](https://docs.dify.ai/en/api-reference/guides/get-started), [End user identity](https://docs.dify.ai/en/api-reference/guides/end-user-identity), [Streaming responses](https://docs.dify.ai/en/api-reference/guides/streaming), [Workflow API](https://docs.dify.ai/en/api-reference/guides/workflow), [Errors](https://docs.dify.ai/en/api-reference/guides/errors), [OpenAPI specification](https://docs.dify.ai/en/api-reference/openapi_service.json). These are live docs; verify behavior against the deployed version.

Pinned implementation evidence: [app Service API controllers](https://github.com/langgenius/dify/tree/5fe7f018764e94aefa06f098a23e28a55d6b4e18/api/controllers/service_api/app), including `workflow.py` and `completion.py`, at Dify commit `5fe7f018764e94aefa06f098a23e28a55d6b4e18`.

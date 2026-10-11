---
name: dify-plugin
description: Build or adapt a Dify plugin with the official plugin SDK and scaffolding tool, covering schemas, credentials, tests, and packaging.
---

# Dify Plugin

Identify target Dify release, plugin-daemon compatibility, SDK version, and required capability. Inspect available installed/official plugins before building one. An existing tool, custom OpenAPI tool, HTTP Request node, or MCP integration may satisfy the project with less code. Select a plugin when its runtime or reusable provider interface materially helps.

## Implement

- Use the official plugin scaffolding tool and inspect its version/help. Its `plugin init` / `plugin package` commands are separate from the app-management `difyctl` CLI. Preserve generated structure and pin the SDK/dependencies; current tool-plugin docs use Python 3.12, so check the selected SDK's requirement rather than assuming the app backend's runtime.
- Pick the matching type: tool, model provider, agent strategy, datasource, trigger, or endpoint. Availability differs across Dify releases. An agent strategy plugin is distinct from a native Agent skill package and from this Codex project skill.
- For a tool, make manifest/provider/tool YAML paths agree with actual files. Keep credential declarations, provider validation, input parameters, and structured outputs aligned with the SDK's schema. In tool parameters, `form` and `llm` have different meanings for agent inference and workflow configuration; confirm both entry points when supported.
- Implement external I/O behind a small adapter with explicit timeouts and useful, sanitized errors. Use runtime credentials, never hardcoded secrets. Ensure credential validation does not accidentally perform a costly or destructive operation.
- Request only the manifest permissions required by the capability. The broad permissions in an example are not requirements for every plugin.

## Verify and package

Test valid inputs, missing credentials, invalid authentication, malformed provider responses, timeouts, and the declared output contract with fixtures before integration. Run packaging using the installed CLI and record SDK, plugin version, target Dify release, and package hash. Packaging success does not prove installation or execution.

Remote debugging connects to a real workspace and makes the plugin visible there; use a test workspace and carry out that step only within the user's authorized testing scope. Use protected debug keys outside version control. Confirm the tool in the intended workflow/agent entry point before describing it as working.

Marketplace submission and GitHub release are distribution actions, separate from generating a local `.difypkg`. If publication is requested, read current submission, privacy, and signature requirements and produce a reviewable package first. Preserve signature verification; do not normalize disabling it to install arbitrary packages.

## Evidence

Reviewed 2026-10-11: [Tool plugin walkthrough](https://docs.dify.ai/en/develop-plugin/dev-guides-and-walkthroughs/tool-plugin), [General specifications](https://docs.dify.ai/en/develop-plugin/features-and-specs/plugin-types/general-specifications), [Plugin SDK repository](https://github.com/langgenius/dify-plugin-sdks), [Plugin daemon repository](https://github.com/langgenius/dify-plugin-daemon), [Distribution choices](https://docs.dify.ai/en/develop-plugin/publishing/marketplace-listing/release-overview). Read the matching release documentation when an interface differs.

Dify platform integration baseline: [api/core/plugin](https://github.com/langgenius/dify/tree/5fe7f018764e94aefa06f098a23e28a55d6b4e18/api/core/plugin) at commit `5fe7f018764e94aefa06f098a23e28a55d6b4e18`. The SDK and plugin daemon are separate repositories/releases; this platform commit does not pin their APIs.

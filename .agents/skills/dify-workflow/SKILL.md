---
name: dify-workflow
description: Design, review, and validate Dify Workflow or Chatflow applications, including version-aware DSL export and import.
---

# Dify Workflow

Use this Codex project skill to build an application on Dify. First identify the target deployment (Cloud or self-host), its release, app type, and the project's input/output contract. Features on upstream `main` and current Cloud docs may be unavailable on a deployed release.

When present, read [project guidelines](../../../docs/PROJECT_GUIDELINES.md). For this toolkit's support example, `knowledge/sources/product-guide.md` is fictional project source material, while `evals/datasets/support-tickets.csv` contains noisy supplied answers to evaluate. Do not treat those answers as knowledge or fictional prices as current Dify pricing.

Choose Workflow for a single execution with explicit outputs; choose Chatflow for conversation state and replies. Prefer the smallest graph that demonstrates the project's golden path. Keep deterministic rules in services, Code nodes, or explicit branches; use models for work that needs reasoning. Check the target's node names: current docs use User Input and Output where older exports may use Start and End.

## Build and verify

1. Write required inputs, output schema, failure behavior, and a representative example before constructing the graph.
2. Configure model/provider and tool dependencies from the target workspace. Resolve node IDs, variable selectors, and types against a real export or that release's source rather than guessing YAML fields.
3. Route retrieval results explicitly into model context. Configure bounded iteration, retries, and tool effects for the task; verify missing inputs and provider failures.
4. Test individual nodes and the whole graph in Dify's preview. Preserve traces and expected outputs without credentials or user data. Record separately whether the draft, imported app, and published app were tested.
5. Use the actual app API contract for backend integration. Read `$dify-api-integration` when wiring execution into application code.

## DSL changes

Read [DSL provenance and compatibility](references/dsl.md) when creating, modifying, sharing, or importing a DSL file. Prefer an export from the intended target or a known compatible upstream fixture. A locally parsed YAML document is not proof of successful import or execution.

## Skill surfaces

This directory teaches Codex how to work on the project. Upstream `.agents/skills/` teaches coding agents how to contribute to Dify itself; inspect upstream AGENTS.md when modifying its source. Native Dify Agent skill packages run inside the new Agent runtime and require a separate capability review. Do not upload this developer skill as a native agent capability by default.

Current new Agent docs describe `.zip` or `.skill` packages containing `SKILL.md`; importing an Agent DSL does not import its skills or files. Check availability in the target version before choosing that beta runtime.

## Evidence

Official docs reviewed 2026-10-11: [Workflow & Chatflow](https://docs.dify.ai/en/self-host/use-dify/build/workflow-chatflow), [Node reference index](https://docs.dify.ai/llms.txt), [Build an Agent](https://docs.dify.ai/en/cloud/use-dify/build/new-agent/build). Recheck these when the deployment version changes.

Source baseline: Dify commit `5fe7f018764e94aefa06f098a23e28a55d6b4e18`, [workflow engine](https://github.com/langgenius/dify/tree/5fe7f018764e94aefa06f098a23e28a55d6b4e18/api/core/workflow) and [Agent DSL service](https://github.com/langgenius/dify/blob/5fe7f018764e94aefa06f098a23e28a55d6b4e18/api/services/agent/dsl_service.py). This is research evidence, not a promise that the target runs these features.

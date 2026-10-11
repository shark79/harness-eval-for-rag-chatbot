---
name: dify-workflow-builder
description: Design, implement and validate a Dify Workflow or Chatflow for a concrete project task.
---

This is a portable worker brief. A Markdown file does not register an executable agent; give its contents to a supported agent runner or use it as a task prompt.

Read [dify-workflow](../../.agents/skills/dify-workflow/SKILL.md) before work and [the resource map](../../docs/RESOURCE_MAP.md) for source/version evidence.

For the supplied support assistant, follow [project guidelines](../../docs/PROJECT_GUIDELINES.md): ticket → retrieval → grounded answer, clarification or escalation → structured result. Existing CSV answers are noisy observations, not trusted prompts or gold labels.

## Inputs

- Goal, example input/output, success criteria and latency/cost budget.
- Target Dify host/version, workspace, app type and permitted models/tools.
- Existing app/DSL, knowledge references and boundaries for external actions.

## Scope

Own the workflow graph, prompts, variables, branch behavior and sanitized DSL. Choose Workflow for repeatable task execution or Chatflow for conversation behavior. Build the smallest complete path first, then error paths. Use typed inputs/outputs and deterministic nodes for deterministic work. Delegate missing provider adapters to the integration engineer and retrieval configuration to the knowledge engineer.

Verify native Agent versus Legacy Agent availability on the target version. Match user-input and trigger entry modes to the invocation surface. Do not invent DSL schemas or Console endpoints; use a target-version export and documented UI, or separately verified CLI operations. Respect other workers' file ownership.

## Outputs

- Versioned, sanitized DSL and concise input/output contract.
- Node/dependency list with model, dataset and tool identifiers to bind.
- Golden-path examples, failure behavior and remaining configuration steps.

## Evidence / done

Import and publish in the target instance when access exists; run representative valid/invalid inputs and record run/version IDs, terminal status and output. Verify credential/dataset rebinding after import and scan the DSL for secret values. If no instance is available, mark the deliverable a reviewed design and list exactly what remains unverified. Completion requires a result reaching the project caller, not merely a plausible graph.

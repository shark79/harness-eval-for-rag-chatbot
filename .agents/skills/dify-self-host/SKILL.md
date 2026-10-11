---
name: dify-self-host
description: Prepare, deploy, troubleshoot, or upgrade a self-hosted Dify release using its official Docker Compose and environment configuration.
---

# Dify Self-Host

Inspect existing deployment files, running services, data volumes, release, and customizations first. This toolkit is an integration companion, not a Dify deployment. Do not start infrastructure simply because this skill is selected; prepare a plan or execute according to the user's requested scope.

## Prepare the release

Select an explicit supported release/tag and record its commit. Upstream `main`, current documentation, and container images can describe different versions. Use the release's own `docker/` files, image tags, `.env.example`, and release notes together; do not replace an existing installation with files from `main` or promise beta Agent features on older images.

Check Docker availability/context and Compose version. Current official docs require Compose 2.24.0+ and baseline CPU/memory, with additional Docker VM memory guidance on macOS. Resource needs grow with datasets, models, and enabled services. Read the actual release documentation before quoting a service count.

Copy environment examples only if the local file does not exist. Configure required secrets, external URLs, ports, storage/database settings, and the chosen vector backend without printing credentials. Current docs can use optional templates under `docker/envs/`; older releases may have a different environment layout. Derive service names and environment precedence from the selected Compose/config files.

## Deploy and verify when requested

Use the official release Compose file rather than inventing a minimal stack that omits plugin, sandbox, worker, or proxy services. Validate its rendered configuration and perform image builds only where that release uses build contexts; official released images can be pulled directly.

Start the selected Compose project, inspect service health and relevant sanitized logs, and verify the install/login page through the configured public URL. A one-time initialization container can legitimately exit successfully. Avoid interpreting every exited container as a failure.

After workspace initialization and model configuration, verify one published app round trip through the actual Service API and check its output. A running container, responsive login page, and successful model execution are three different checks. Record which were completed; disclose missing credentials or unavailable providers.

## Upgrade or troubleshoot

Before a state-changing upgrade, inventory and back up the database, persistent storage, vector data, and deployment configuration with a restoration plan appropriate to the installation. Follow target release migration notes, compare environment examples, and reapply custom Compose changes to the new release's files. A DSL export alone is not a backup of documents, conversations, or credentials.

Investigate API/web URL mismatches, worker errors, provider connectivity, storage permissions, and plugin-daemon compatibility against logs and the pinned release. Do not delete volumes, reset databases, or disable proxy/sandbox/signature protections as a generic repair. Preserve the user's existing configuration.

## Evidence

Reviewed 2026-10-11: [Official Docker Compose guide](https://docs.dify.ai/en/self-host/deploy/quick-start/docker-compose), [Environment reference](https://docs.dify.ai/en/self-host/deploy/configuration/environments), [Releases and migration notes](https://github.com/langgenius/dify/releases), [Upstream deployment directory](https://github.com/langgenius/dify/tree/main/docker). These references must be checked against the chosen release.

Research baseline: [docker/docker-compose.yaml](https://github.com/langgenius/dify/blob/5fe7f018764e94aefa06f098a23e28a55d6b4e18/docker/docker-compose.yaml) at commit `5fe7f018764e94aefa06f098a23e28a55d6b4e18` pins API/web images to `1.17.1` while source is from `main`. Verify image features independently; checking out this commit does not build or run its source by default.

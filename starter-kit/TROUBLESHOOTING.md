# Troubleshooting

- **Docker daemon unavailable:** start the configured runtime, e.g. `colima start`, then retry `make build`.
- **Port 8080 occupied:** stop the other service; Compose publishes only local host port 8080.
- **Missing Harness module:** run `make setup`, then use `.venv/bin/python` for local commands. Docker installs the pinned core dependency.
- **Evaluation report permission denied:** set `.env` LOCAL_UID and LOCAL_GID to the output of `id -u` and `id -g`, then recreate the container.
- **Dify mode says unconfigured:** add the Workflow's app API key to local `.env`; a provider or dataset key does not replace it.
- **Dify evidence rejected:** inspect the Workflow outputs. Source IDs, section IDs, excerpts and revisions must match `shared/contracts/evidence-sources.json`; baseline ticket answers are never approved knowledge.
- **Scores say Not run and every response is held:** offline mode is deliberate. Configure `EVAL_MODE=decisions` and `OPENAI_API_KEY` for real semantic scoring. Thresholds require calibration before production release.
- **409 evaluation already running:** wait for the active evaluation; batch and interactive judging share a local execution lock.

- **Cannot connect to local Dify:** confirm the separate Dify Compose stack is running and publishes its nginx port. Use `http://localhost/v1` for native commands and `http://host.docker.internal/v1` inside the ticket container; update both URLs if the host port differs.
- **Local Dify rejects a Cloud key:** create a key in the published Workflow of the local workspace; Cloud app keys are not transferred.

## Dify clone resets or reports early EOF

The official 1.17.1 deployment checkout was recovered on 2026-10-11 at `/Users/shark7901/Documents/Projects/dify-local`, commit `8387590ace4a094de812b7847fc6a4c3a27cd52b`. All 82 tracked Docker deployment files were present and the official Compose configuration validated against the example environment in a temporary copy. Containers were not started during recovery.

For a fresh destination, download only the deployment tree:

```sh
cd /Users/shark7901/Documents/Projects
git -c http.version=HTTP/1.1 clone --filter=blob:none --sparse --depth 1 --branch 1.17.1 https://github.com/langgenius/dify.git dify-local
git -c http.version=HTTP/1.1 -C dify-local sparse-checkout set docker
```

These command-scoped HTTP settings do not change global Git configuration. The blob filter defers file content downloads; sparse checkout selects the official Docker deployment files. An existing destination must be inspected before retrying; do not delete a checkout or deployment data to fix a transfer error.

For the recovered checkout, proceed directly:

```sh
cd /Users/shark7901/Documents/Projects/dify-local/docker
test -f .env || cp .env.example .env
docker compose config -q
docker compose up -d
docker compose ps
```

Then open `http://localhost/install`. Release 1.17.1 auto-generates a persistent SECRET_KEY when the environment value is blank. Its example configuration publishes nginx ports 80/443 and plugin debugging port 5003 on all host interfaces; explicitly bind published ports to loopback for local-only use. Keep plugin debugging environment port values numeric because the API also consumes them.

See [Git clone options](https://git-scm.com/docs/git-clone), the [pinned Dify release](https://github.com/langgenius/dify/releases/tag/1.17.1) and [local Workflow setup](../docs/DIFY_LOCAL_SETUP.md).

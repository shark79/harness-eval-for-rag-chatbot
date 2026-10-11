# Troubleshooting

- **Docker daemon unavailable:** start the configured runtime, e.g. `colima start`, then retry `make build`.
- **Port 8080 occupied:** stop the other service; Compose publishes only local host port 8080.
- **Missing Harness module:** run `make setup`, then use `.venv/bin/python` for local commands. Docker installs the pinned core dependency.
- **Evaluation report permission denied:** set `.env` LOCAL_UID and LOCAL_GID to the output of `id -u` and `id -g`, then recreate the container.
- **Dify mode says unconfigured:** add the Workflow's app API key to local `.env`; a provider or dataset key does not replace it.
- **Dify evidence rejected:** inspect the Workflow outputs. Source IDs, section IDs, excerpts and revisions must match `shared/contracts/evidence-sources.json`; baseline ticket answers are never approved knowledge.
- **Scores say Not run and every response is held:** offline mode is deliberate. Configure `EVAL_MODE=decisions` and `OPENAI_API_KEY` for real semantic scoring. Thresholds require calibration before production release.
- **409 evaluation already running:** wait for the active evaluation; batch and interactive judging share a local execution lock.

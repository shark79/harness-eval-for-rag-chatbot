# Quickstart

From the repository root, run:

```sh
make setup
make build
make up
```

Open http://127.0.0.1:8080. In the first assistant tab, enter a ticket and generate a draft with source excerpts. In the second assistant tab, evaluate that actual draft and inspect its score and final ship/hold_off decision. The latest 64 generated drafts are held in memory; restarting the server clears them.

The default local retrieval mode returns exact documentation excerpts. Offline evaluation cannot measure semantic quality and holds delivery; it does not invent scores.

To develop without Docker:

```sh
.venv/bin/python -m backend.app.api.server
```

Verification:

```sh
make test PYTHON=.venv/bin/python
make check PYTHON=.venv/bin/python
.venv/bin/python scripts/run_evaluations.py --source chatbot
```

Container operations:

```sh
docker compose logs --tail=100 ticket-assistant
docker compose down
```

Add credentials only to your local ignored `.env`. See [environment configuration](ENVIRONMENT.md). After changing container environment configuration, run `docker compose up -d --force-recreate`; after source edits, run `docker compose build` then `docker compose up -d`.

For model-generated answers, first set up the separate local Dify instance and its published Workflow using [local Dify setup](../docs/DIFY_LOCAL_SETUP.md). The default extractive mode does not start Dify. Native commands use `http://localhost/v1`; the ticket container uses `http://host.docker.internal/v1`.

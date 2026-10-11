PYTHON ?= python3

.PHONY: setup test check demo dev build up down logs eval help
setup:
	$(PYTHON) -m venv .venv
	.venv/bin/python -m pip install -r requirements.txt
	$(PYTHON) -c "from pathlib import Path; import os; p=Path('.env'); p.exists() or p.write_text(Path('.env.example').read_text().replace('LOCAL_UID=10001', f'LOCAL_UID={os.getuid()}').replace('LOCAL_GID=10001', f'LOCAL_GID={os.getgid()}')); p.chmod(0o600)"

test:
	$(PYTHON) -m unittest discover -s tests -v
	npm --prefix frontend test

check:
	$(PYTHON) -m compileall -q backend agents scripts tests

dev:
	$(PYTHON) -m backend.app.api.server

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs --tail=100 ticket-assistant

eval:
	$(PYTHON) scripts/run_evaluations.py --source chatbot

demo:
	$(PYTHON) scripts/dify_api.py --dry-run workflow-run --inputs '{"ticket_text":"Where do I get an app API key?"}' --user demo-user

help:
	$(PYTHON) scripts/dify_api.py --help

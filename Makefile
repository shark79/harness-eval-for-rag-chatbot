PYTHON ?= python3

.PHONY: setup test check demo help
setup:
	$(PYTHON) --version
	$(PYTHON) scripts/dify_api.py --help

test:
	$(PYTHON) -m unittest discover -s tests -v

check:
	$(PYTHON) -m compileall -q scripts tests

demo:
	$(PYTHON) scripts/dify_api.py --dry-run workflow-run --inputs '{"ticket_text":"Where do I get an app API key?"}' --user demo-user

help:
	$(PYTHON) scripts/dify_api.py --help

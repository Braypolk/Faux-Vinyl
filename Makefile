PYTHON ?= python3

.PHONY: dev build test test-race test-tools test-ui secrets

dev build:
	$(MAKE) -C server $@

test:
	$(PYTHON) tests/run_go.py test
	$(PYTHON) tests/run_go.py vet

test-race:
	$(PYTHON) tests/run_go.py test -race

test-tools:
	$(PYTHON) -m pytest -q tests/artwork tests/tools

test-ui:
	node --test tests/ui/*.test.cjs

secrets:
	$(PYTHON) tools/check_secrets.py

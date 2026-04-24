PYTHON := ./.venv/bin/python3
MANAGE := $(PYTHON) manage.py

.PHONY: url-hygiene pre-release-gate

url-hygiene:
	$(MANAGE) url_hygiene_gate --strict --skip-check

pre-release-gate:
	$(MANAGE) url_hygiene_gate --strict

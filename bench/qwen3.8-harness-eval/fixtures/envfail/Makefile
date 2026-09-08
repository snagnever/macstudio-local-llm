.PHONY: venv check lint test

venv:
	python3 -m venv .venv
	.venv/bin/pip install -q -r requirements.txt

lint:
	.venv/bin/ruff check app tests

test:
	.venv/bin/python -m pytest -q

check: lint test

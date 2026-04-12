.PHONY: install format lint test run

UV = /opt/homebrew/bin/uv

install:
	$(UV) sync

format:
	$(UV) run ruff format .

lint:
	$(UV) run ruff check banktamer
	$(UV) run mypy banktamer tests

test:
	$(UV) run python -m unittest discover tests/unit

run:
	$(UV) run banktamer $(args)

build:
	$(UV) build

.PHONY: install format lint test test-integration test-e2e test-all run

UV = uv

install:
	$(UV) sync

format:
	$(UV) run ruff format .

lint:
	$(UV) run ruff check .
	$(UV) run ruff format --check .
	$(UV) run mypy banktamer tests

test:
	$(UV) run python -m unittest discover tests/unit

test-integration:
	$(UV) run python -m unittest discover tests/integration

test-e2e:
	$(UV) run python -m unittest tests/e2e/test_binary.py

test-all: test test-integration test-e2e

run:
	$(UV) run banktamer $(args)

build:
	$(UV) build

dist-exe:
	$(UV) run python -m nuitka --standalone --onefile --include-data-dir=banktamer/config=banktamer/config --output-dir=dist --output-filename=banktamer banktamer/cli.py

clean:
	rm -rf build dist banktamer.spec

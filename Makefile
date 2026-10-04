.PHONY: install format lint test test-integration test-all run tag

UV = uv

install:
	$(UV) sync
	$(UV) run playwright install chromium

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

test-all: test test-integration

run:
	$(UV) run banktamer $(args)

build:
	$(UV) build

# Create a git tag using the version in pyproject.toml and push it.
# This triggers the CI/CD pipeline to create a GitHub Release and publish to PyPI.
tag:
	@VERSION=$$(grep "^version =" pyproject.toml | sed 's/version = "\(.*\)"/\1/') && \
	echo "Tagging version v$$VERSION" && \
	git tag -a v$$VERSION -m "Release v$$VERSION" && \
	git push origin v$$VERSION

clean:
	rm -rf build dist


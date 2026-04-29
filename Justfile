default:
    @just --list

install:
    uv sync

test:
    uv run pytest -q

lint:
    uv run ruff check .

check: test lint

run:
    uv run todoist-mcp

.PHONY: install run lint format test test-unit test-integration docker-build up down

install:
	uv sync

run:
	uv run python -m src.raft

lint:
	uv run ruff check src tests
	uv run ruff format --check src tests

format:
	uv run ruff format src tests
	uv run ruff check --fix src tests

test:
	uv run pytest -v

test-unit:
	uv run pytest tests/unit -v

test-integration:
	uv run pytest tests/integration -v -s

docker-build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

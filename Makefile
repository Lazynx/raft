.PHONY: install run lint format test test-unit test-integration docker-build up down

install:
	uv sync --all-extras

run:
	uv run uvicorn src.raft.app:create_app --factory --host 0.0.0.0 --port 8000 --reload

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

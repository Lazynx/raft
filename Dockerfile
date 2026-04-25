FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

COPY src/ ./src/

ENV PYTHONUNBUFFERED=1

CMD ["uv", "run", "python", "-m", "src.raft"]

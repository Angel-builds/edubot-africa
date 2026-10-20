# Build the virtualenv in a throwaway stage. Doing this in the runtime image
# bakes uv's build cache (~150 MB) and the uv binary itself (~31 MB) into a
# layer that is never needed again.
FROM python:3.12-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1

COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv

WORKDIR /app

# Dependencies only, so this layer rebuilds only when the lockfile changes.
# `ingest` holds the PDF parser that builds the corpus; serving it never needs
# one, and leaving it out saves about 50 MB of pdfminer, pillow and pypdfium2.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-group ingest


FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

RUN useradd --create-home --uid 1000 edubot

WORKDIR /app

COPY --from=builder --chown=edubot:edubot /app/.venv /app/.venv

# The app imports core/ at startup and reads corpus/chunks.jsonl and
# web/index.html at runtime. An earlier version copied only api/ and the
# container crashed on its first import.
COPY --chown=edubot:edubot api/ ./api/
COPY --chown=edubot:edubot core/ ./core/
COPY --chown=edubot:edubot web/ ./web/
COPY --chown=edubot:edubot corpus/ ./corpus/

USER edubot

EXPOSE 8000

# Shell form so ${PORT} expands. Most platforms inject a port and expect the
# app to bind it -- Cloud Run sends 8080, Hugging Face Spaces expects 7860 --
# and a hardcoded port fails silently as a failed health check.
CMD ["sh", "-c", "exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

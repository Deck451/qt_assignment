FROM python:3.13-slim AS base

RUN apt update && apt install -y curl && rm -rf /var/lib/apt/lists/*

ENV POETRY_HOME="/opt/poetry"
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="$POETRY_HOME/bin:$PATH"

WORKDIR /app
COPY . /app
ENV PYTHONPATH=/app

RUN poetry install --no-root

FROM base AS app
EXPOSE 8000
CMD ["poetry", "run", "uvicorn", "app.main:application", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS worker
CMD ["poetry", "run", "celery", "-A", "worker.celery", "worker", "--beat", "--loglevel=info"]

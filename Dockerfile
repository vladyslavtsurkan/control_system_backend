ARG PYTHON_VERSION=3.14.3
FROM python:${PYTHON_VERSION}-slim AS base

RUN apt-get update && apt-get install -y postgresql-client netcat-openbsd

WORKDIR /app

ENV PYTHONPATH=.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev --no-install-project

COPY . .

RUN chmod +x ./scripts/app-start.sh ./scripts/worker-start.sh ./scripts/celery-worker-start.sh ./scripts/common.sh
CMD ["bash", "./scripts/app-start.sh"]

ARG PYTHON_VERSION=3.14.3
FROM python:${PYTHON_VERSION}-slim as base

RUN apt-get update && apt-get install -y postgresql-client netcat-openbsd

WORKDIR /app

ENV PYTHONPATH .

RUN pip install poetry

COPY poetry.lock pyproject.toml ./

RUN poetry config virtualenvs.create false \
    && poetry install --only main || echo "Poetry install failed"

COPY . .

RUN chmod +x ./scripts/app-start.sh ./scripts/worker-start.sh ./scripts/celery-worker-start.sh ./scripts/common.sh
CMD ["sh", "./scripts/app-start.sh"]

ARG PYTHON_VERSION=3.13.5
FROM python:${PYTHON_VERSION}-slim as base

RUN apt-get update && apt-get install -y postgresql-client

WORKDIR /app

ENV PYTHONPATH .

RUN pip install poetry

COPY poetry.lock pyproject.toml ./

RUN poetry config virtualenvs.create false \
    && poetry install --only main || echo "Poetry install failed"

COPY . .

RUN chmod +x ./scripts/app-start.sh
CMD ["sh", "./scripts/app-start.sh"]

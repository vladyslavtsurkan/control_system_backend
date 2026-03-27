# Control System Backend

This project now uses `uv` for dependency management and locking.

## Prerequisites

- Python 3.14
- `uv` installed (`uv --version`)

## Local setup

```bash
uv sync --no-install-project
```

Run the API:

```bash
uv run python -m app.main
```

Run worker:

```bash
uv run faststream run app.worker.main:app --workers 1
```

Run celery worker:

```bash
uv run celery -A app.infra.celery.app:celery_app worker --loglevel=info --concurrency=4 -Q celery
```

Apply migrations:

```bash
uv run alembic upgrade head
```

## Lockfile policy

- `uv.lock` is the canonical lockfile.
- Update locks with:

```bash
uv lock
```

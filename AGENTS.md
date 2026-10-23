# Repository guide

## Project map

- `app/main.py` creates and runs the FastAPI application. HTTP routers and dependencies live in `app/api/`;
  WebSocket connections and consumers live in `app/api/ws/`.
- `app/services/` contains business logic, authorization checks, and orchestration.
- `app/repositories/` contains database access and RabbitMQ repositories. `app/uow/` manages SQL, Redis,
  and RabbitMQ resource lifecycles; the SQL unit of work handles transaction commit and rollback.
- `app/models/` defines SQLAlchemy models; `app/schemas/` defines Pydantic API payloads.
- `app/worker/` implements the FastStream telemetry worker, sensor/rule caches, and alert processing.
- `app/infra/` contains database, Redis, RabbitMQ, and Celery integration; Celery tasks live in
  `app/infra/celery/tasks.py`. Alembic revisions live in `app/infra/database/alembic/versions/`.
- `contracts/telemetry.proto` defines the Protobuf contract. `scripts/` contains startup and generation helpers;
  `docker-compose.yaml` describes the API, workers, TimescaleDB/PostgreSQL, Redis, and RabbitMQ services.

## Setup and commands

Use Python 3.14 and `uv`. Run commands from the repository root.

```bash
uv sync --no-install-project
```

Use `.env.sample` as the reference for local configuration. Pydantic settings in `app/core/config/` load `.env`.
Configure the required database, Redis, RabbitMQ, and other settings before starting the relevant processes.
Compose uses an external network and external volumes; inspect its declarations before using it.

| Task | Command |
| --- | --- |
| Run the API | `uv run python -m app.main` |
| Run the telemetry worker | `uv run faststream run app.worker.main:app --workers 1` |
| Run the Celery worker | `uv run celery -A app.infra.celery.app:celery_app worker --loglevel=info --concurrency=4 -Q celery` |
| Apply migrations | `uv run alembic upgrade head` |
| Update the dependency lock | `uv lock` |
| Run configured hooks | `uv run pre-commit run --all-files` |
| Regenerate Protobuf code | `uv run bash scripts/compile_proto.sh` |

`uv.lock` is the canonical lockfile. Change dependencies in `pyproject.toml` and update the lockfile together.
The pre-commit hooks can modify files, including through Ruff fixes and formatting; review their changes.

## Implementation conventions

- Follow existing asynchronous router/service/repository boundaries. Keep business rules in services and
  persistence queries in repositories; use the existing units of work for resource and transaction handling.
- Preserve tenant validation and PostgreSQL row-level security context. Follow the existing tenant-scoped
  dependencies and authorization checks; keep RLS bypass limited to the established privileged operations.
- Preserve `deleted_at` filtering for active resources, including related parent resources where applicable.
  Follow existing audit logging patterns when changing audited operations.
- Follow Ruff settings in `pyproject.toml`: 120-character lines, four-space indentation, and double quotes.
  Reuse existing schemas, domain exceptions, and helpers where appropriate.
- Add Alembic revisions for schema changes and review generated migration operations, including tenant/RLS
  implications. Run migrations only against the intended configured database.
- Preserve RabbitMQ exchange types, routing keys, delivery behavior, and payload contracts unless the task
  explicitly changes them. Check affected publishers and consumers together.
- Change `contracts/telemetry.proto` and regenerate the Python output with the command above. Do not manually
  edit generated Protobuf code in `app/worker/generated/`; include regenerated output with contract changes.

## Validation and sensitive files

- No test sources are currently tracked, and no test dependencies are declared in `pyproject.toml`.
  Cached files under `tests/` are not a runnable test suite. Do not claim a test suite passed without running one.
- Choose checks appropriate to the change. Run the configured hooks for code changes and relevant tests when
  available; report missing coverage, unavailable services, and checks that could not run.
- For documentation-only changes, verify commands and paths, inspect Markdown, and run `git diff --check`.
- Keep credentials, `.env`, and private certificates out of commits, logs, and task output. Use configuration
  names and placeholders when documenting settings.
- Keep changes focused on the requested task and preserve unrelated working-tree changes. Report what changed,
  how it was checked, and any remaining verification gaps.

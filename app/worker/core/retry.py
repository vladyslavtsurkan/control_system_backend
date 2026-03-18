import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from loguru import logger
from sqlalchemy.exc import DBAPIError

from app.core.constants import WORKER_MAX_DB_RETRIES, WORKER_RETRY_BASE_DELAY_SECONDS
from app.worker.common.helpers import is_retryable_postgres_error, postgres_sqlstate

__all__ = ["run_with_db_retries"]

T = TypeVar("T")


async def run_with_db_retries(operation_name: str, operation: Callable[[], Awaitable[T]]) -> T:
    """Run DB operation with bounded retries for transient PostgreSQL errors."""
    for attempt in range(1, WORKER_MAX_DB_RETRIES + 1):
        try:
            return await operation()
        except DBAPIError as exc:
            if not is_retryable_postgres_error(exc) or attempt >= WORKER_MAX_DB_RETRIES:
                raise

            delay_seconds = WORKER_RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1))
            logger.warning(
                "Retrying {operation} after transient DB error: sqlstate={sqlstate}, attempt={attempt}/{max_attempts}",
                operation=operation_name,
                sqlstate=postgres_sqlstate(exc),
                attempt=attempt,
                max_attempts=WORKER_MAX_DB_RETRIES,
            )
            await asyncio.sleep(delay_seconds)

    raise RuntimeError(f"Unreachable retry state for operation: {operation_name}")

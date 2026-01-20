import asyncio
from functools import wraps
from typing import Any
from collections.abc import Awaitable, Callable

from loguru import logger


def retry(
    max_retries: int = 3,
    delay: int | float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple[type[Exception], ...] | None = None,
    reraise_last: bool = True,
) -> Callable:
    """
    Retry decorator for asynchronous functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff_factor: Multiplier for delay after each failed attempt
        exceptions: Tuple of exception types to catch (None means catch all)
        reraise_last: Whether to reraise the last exception if all retries fail
    """
    if exceptions is None:
        exceptions = (Exception,)

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    logger.warning(f"Function {func.__name__} failed on attempt {attempt + 1}/{max_retries + 1}: {e}")

                    if attempt < max_retries:
                        sleep_time = delay * (backoff_factor**attempt)
                        logger.info(f"Retrying in {sleep_time:.2f} seconds...")
                        await asyncio.sleep(sleep_time)
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}")

            if reraise_last and last_exception:
                raise last_exception

            return None

        return wrapper

    return decorator

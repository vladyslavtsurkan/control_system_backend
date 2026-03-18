import asyncio

from loguru import logger

from app.core.config import settings
from app.worker.services.no_data_checker import run_no_data_check

__all__ = ["run_no_data_loop"]


async def run_no_data_loop() -> None:
    interval = settings.rabbitmq.NO_DATA_CHECK_INTERVAL_SECONDS

    while True:
        await asyncio.sleep(interval)
        try:
            count = await run_no_data_check()
            if count:
                logger.info("NO_DATA check: {count} alerts triggered", count=count)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Error in NO_DATA background loop")

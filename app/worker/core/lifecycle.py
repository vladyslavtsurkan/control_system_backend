import asyncio

from loguru import logger

from app.worker.cache.rule_cache import rule_cache
from app.worker.services.no_data_loop import run_no_data_loop

__all__ = ["WorkerLifecycle"]


class WorkerLifecycle:
    def __init__(self) -> None:
        self._no_data_task: asyncio.Task | None = None

    async def on_startup(self) -> None:
        logger.info("Worker starting - loading rule cache ...")
        await rule_cache.load()

        self._no_data_task = asyncio.create_task(run_no_data_loop())
        logger.info("NO_DATA background checker started")

    async def on_shutdown(self) -> None:
        if self._no_data_task is not None:
            self._no_data_task.cancel()
            try:
                await self._no_data_task
            except asyncio.CancelledError:
                pass
        logger.info("Worker shut down gracefully")

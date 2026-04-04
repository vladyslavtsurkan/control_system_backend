from pydantic import Field

from app.core.config.base import BaseConfig


class WorkerConfig(BaseConfig):
    """
    Configuration for the worker process.
    """

    AMOUNT: int = Field(..., alias="WORKER_AMOUNT")
    CONCURRENCY: int = Field(..., alias="WORKER_CONCURRENCY")

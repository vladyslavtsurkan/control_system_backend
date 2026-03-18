from faststream import FastStream

from app.worker.core.lifecycle import WorkerLifecycle
from app.worker.core.subscribers import register_subscribers
from app.worker.core.topology import (
    broker,
    control_exchange,
    control_queue,
    telemetry_exchange,
    telemetry_queue,
)

__all__ = ["create_app"]


def create_app() -> FastStream:
    app = FastStream(broker)
    lifecycle = WorkerLifecycle()

    @app.on_startup
    async def _on_startup() -> None:
        await lifecycle.on_startup()

    @app.on_shutdown
    async def _on_shutdown() -> None:
        await lifecycle.on_shutdown()

    register_subscribers(
        broker=broker,
        telemetry_queue=telemetry_queue,
        telemetry_exchange=telemetry_exchange,
        control_queue=control_queue,
        control_exchange=control_exchange,
    )

    return app

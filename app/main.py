import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from app.api.routers import main_router, swagger
from app.api.routers.ws import router as ws_router
from app.core import exc
from app.core import settings
from app.core.exc import handlers
from app.api.ws import ConnectionManager, start_ws_consumer


@asynccontextmanager
async def lifespan(app: FastAPI):
    manager = ConnectionManager()
    app.state.ws_manager = manager

    consumer_task = asyncio.create_task(start_ws_consumer(manager))

    yield

    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass


def _include_router(app: FastAPI) -> None:
    app.include_router(main_router.router)
    app.include_router(swagger.router, prefix=main_router.router.prefix)
    # WebSocket router lives outside /api/v1 — top-level /ws prefix
    app.include_router(ws_router)


def _add_middleware(app: FastAPI) -> None:
    if not settings.IS_PRODUCTION:
        from app.core.middlewares import ProcessTimeMiddleware

        app.add_middleware(ProcessTimeMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.FRONTEND_URL if settings.FRONTEND_URL else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _add_handlers(app: FastAPI) -> None:
    app.add_exception_handler(exc.GoneException, handlers.handle_gone_exception)
    app.add_exception_handler(exc.NotAuthorizedException, handlers.handle_not_authorized_exception)
    app.add_exception_handler(exc.ObjectAlreadyExistsException, handlers.handle_object_already_exists)
    app.add_exception_handler(exc.ObjectNotFoundException, handlers.handle_object_not_found)
    app.add_exception_handler(exc.ForbiddenException, handlers.handle_forbidden_exception)
    app.add_exception_handler(exc.BadRequestException, handlers.handle_bad_request_exception)
    app.add_exception_handler(ValidationError, handlers.handle_validation_error)


def create_app() -> FastAPI:
    app = FastAPI(
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    _include_router(app)
    _add_middleware(app)
    _add_handlers(app)

    return app


if __name__ == "__main__":
    uvicorn.run(
        "app.main:create_app",
        factory=True,
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.RELOAD,
    )

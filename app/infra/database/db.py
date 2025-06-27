import functools

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.core import settings

__all__ = ["get_session_maker", "engine"]


@functools.lru_cache
def create_engine() -> AsyncEngine:
    return create_async_engine(
        settings.db.url,
        pool_size=settings.db.POOL_SIZE,
        max_overflow=settings.db.MAX_OVERFLOW,
        pool_recycle=settings.db.POOL_RECYCLE,
    )


@functools.lru_cache
def create_sessionmaker(engine_instance: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(bind=engine_instance, autoflush=False)


@functools.lru_cache
def get_session_maker() -> async_sessionmaker:
    engine_instance = create_engine()
    return create_sessionmaker(engine_instance)


engine = create_engine()

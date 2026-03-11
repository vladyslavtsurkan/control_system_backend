from typing import Self
from abc import ABC, abstractmethod
from uuid import UUID


class ABCUnitOfWork(ABC):
    @abstractmethod
    def __init__(self, tenant_id: UUID | str | None = None, bypass_rls: bool = False) -> None:
        raise NotImplementedError

    @abstractmethod
    async def __aenter__(self) -> Self:
        raise NotImplementedError

    @abstractmethod
    async def __aexit__(self, *args: any) -> None:
        raise NotImplementedError

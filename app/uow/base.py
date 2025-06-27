from abc import ABC, abstractmethod


class ABCUnitOfWork(ABC):
    @abstractmethod
    def __init__(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def __aenter__(self) -> "ABCUnitOfWork":
        raise NotImplementedError

    @abstractmethod
    async def __aexit__(self, *args: any) -> None:
        raise NotImplementedError

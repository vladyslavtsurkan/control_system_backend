from enum import StrEnum

__all__ = ["BaseStrEnum"]


class BaseStrEnum(StrEnum):
    @classmethod
    def list(cls) -> list[str]:
        return list(cls.__members__.values())

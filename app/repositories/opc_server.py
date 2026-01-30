from app.models import OpcServer
from app.repositories.base import BaseRepository

__all__ = ["OpcServerRepository"]


class OpcServerRepository(BaseRepository[OpcServer]):
    model = OpcServer

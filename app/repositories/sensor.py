from app.models import Sensor, Reading, Alert
from app.repositories.base import BaseRepository

__all__ = ["SensorRepository", "ReadingRepository", "AlertRepository"]


class SensorRepository(BaseRepository[Sensor]):
    model = Sensor


class ReadingRepository(BaseRepository[Reading]):
    model = Reading


class AlertRepository(BaseRepository[Alert]):
    model = Alert

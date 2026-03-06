from app.models import Sensor, Reading, AlertRule, Alert
from app.repositories.base import BaseRepository

__all__ = ["SensorRepository", "ReadingRepository", "AlertRuleRepository", "AlertRepository"]


class SensorRepository(BaseRepository[Sensor]):
    model = Sensor


class ReadingRepository(BaseRepository[Reading]):
    model = Reading


class AlertRuleRepository(BaseRepository[AlertRule]):
    model = AlertRule


class AlertRepository(BaseRepository[Alert]):
    model = Alert

import datetime
import uuid

from sqlalchemy import ForeignKey, String, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, CreatedAtMixin, UpdatedAtMixin

__all__ = ["CollectorApiKey"]


class CollectorApiKey(Base, UUIDMixin, CreatedAtMixin, UpdatedAtMixin):
    __tablename__ = "collector_api_keys"

    opc_server_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opc_servers.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    hashed_key: Mapped[str] = mapped_column(String(255), nullable=False)
    last_used_at: Mapped[datetime.datetime | None] = mapped_column(nullable=True)

    opc_server = relationship("OpcServer", back_populates="api_key", lazy="subquery")

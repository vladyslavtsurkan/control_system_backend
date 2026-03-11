from uuid import UUID, uuid7

from app.core.constants import WS_TICKET_TTL
from app.repositories.redis.base import BaseRedisRepository

__all__ = ["WsTicketRepository"]

WS_TICKET_KEY = "ws_ticket:{ticket}"


class WsTicketRepository(BaseRedisRepository):
    """Single-use, short-lived WebSocket auth tickets.

    Stored as Redis hashes via the inherited ``set`` / ``get`` / ``delete``
    methods.  TTL is enforced by ``set``; consumption is a ``get`` followed
    by ``delete`` — safe given the 30-second lifetime.
    """

    DEFAULT_TTL_SECONDS = WS_TICKET_TTL

    async def create(self, user_id: UUID, org_id: UUID) -> str:
        """Persist a new ticket and return its hex string."""
        ticket = uuid7().hex
        await self.set(
            key=WS_TICKET_KEY.format(ticket=ticket),
            value={"user_id": str(user_id), "org_id": str(org_id)},
        )
        return ticket

    async def consume(self, ticket: str) -> dict | None:
        """Retrieve and immediately delete a ticket.  Returns ``None`` if missing or expired."""
        key = WS_TICKET_KEY.format(ticket=ticket)
        payload = await self.get(key)
        if payload is None:
            return None
        await self.delete(key)
        return payload

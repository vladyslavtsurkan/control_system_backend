import asyncio
from uuid import UUID

import orjson
from fastapi import WebSocket
from fastapi.websockets import WebSocketState
from loguru import logger

from app.schemas.ws import WsBroadcastEvent

__all__ = ["ConnectionManager"]


class ConnectionManager:
    """Multi-tenant WebSocket connection registry.

    Connections are keyed by ``organization_id`` so broadcast events are only
    delivered to sockets belonging to the correct tenant.  All mutations are
    protected by an :class:`asyncio.Lock` to prevent concurrency issues.
    """

    def __init__(self) -> None:
        self._connections: dict[UUID, list[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, org_id: UUID, websocket: WebSocket) -> None:
        """Register *websocket* under *org_id*."""
        async with self._lock:
            self._connections.setdefault(org_id, []).append(websocket)
        logger.debug("WS connected: org={org} total={n}", org=org_id, n=len(self._connections[org_id]))

    async def disconnect(self, org_id: UUID, websocket: WebSocket) -> None:
        """Remove *websocket* from *org_id*, pruning the org entry when empty."""
        async with self._lock:
            sockets = self._connections.get(org_id, [])
            try:
                sockets.remove(websocket)
            except ValueError:
                pass
            if not sockets:
                self._connections.pop(org_id, None)
        logger.debug("WS disconnected: org={org}", org=org_id)

    async def broadcast_to_org(self, org_id: UUID, event: WsBroadcastEvent) -> None:
        """Send *event* as a JSON text frame to every socket registered under *org_id*.

        Stale or closed sockets are silently collected and removed after the sweep.
        """
        async with self._lock:
            sockets = list(self._connections.get(org_id, []))

        if not sockets:
            return

        payload = orjson.dumps(event.model_dump(mode="json")).decode()
        dead: list[WebSocket] = []

        for ws in sockets:
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_text(payload)
                else:
                    dead.append(ws)
            except Exception:
                logger.debug("WS send failed, dropping socket: org={org}", org=org_id)
                dead.append(ws)

        if dead:
            async with self._lock:
                live = self._connections.get(org_id, [])
                for ws in dead:
                    try:
                        live.remove(ws)
                    except ValueError:
                        pass
                if not live:
                    self._connections.pop(org_id, None)

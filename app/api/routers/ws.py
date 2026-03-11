import asyncio

from fastapi import APIRouter, WebSocket, status
from fastapi.websockets import WebSocketDisconnect
from loguru import logger

from app.api.dependencies import (
    ConnectionManagerDep,
    TenantIdDep,
    current_user,
    ws_authenticate_dep,
    ws_auth_service,
)
from app.core.constants import WS_PING_INTERVAL
from app.schemas.ws import WsTicketResponse

__all__ = ["router"]

router = APIRouter(prefix="/ws", tags=["WebSocket"])


@router.post("/ticket", response_model=WsTicketResponse, status_code=status.HTTP_201_CREATED)
async def issue_ws_ticket(
    user: current_user,
    tenant_id: TenantIdDep,
    service: ws_auth_service,
) -> WsTicketResponse:
    """Exchange a valid session for a short-lived single-use WebSocket ticket.

    The ticket is valid for 30 seconds and deleted on first use.
    Pass it as ``?ticket=<hex>`` when opening the WebSocket connection.
    """
    return await service.issue_ticket(user, tenant_id)


@router.websocket("/stream")
async def ws_stream(
    websocket: WebSocket,
    manager: ConnectionManagerDep,
    auth: ws_authenticate_dep,
) -> None:
    """Real-time telemetry & alert stream for a single tenant.

    Connect: ``ws://host/ws/stream?ticket=<hex>``

    Obtain a ticket first via ``POST /ws/ticket`` (authenticated with Bearer token).
    Pushes :class:`~app.schemas.ws.WsBroadcastEvent` JSON frames whenever the
    worker processes telemetry or fires an alert for the subscribed org.
    Sends a keepalive ping every ``WS_PING_INTERVAL`` seconds.
    Closes with code ``1008`` if the ticket is invalid or expired.
    """
    user, org_id = auth
    await websocket.accept()
    await manager.connect(org_id, websocket)

    logger.info("WS stream opened: user={user} org={org}", user=user.email, org=org_id)

    async def _ping_loop() -> None:
        while True:
            await asyncio.sleep(WS_PING_INTERVAL)
            try:
                await websocket.send_bytes(b"")
            except Exception:
                break

    ping_task = asyncio.create_task(_ping_loop())

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("WS stream closed: user={user} org={org}", user=user.email, org=org_id)
    except Exception:
        logger.exception("WS stream error: user={user} org={org}", user=user.email, org=org_id)
    finally:
        ping_task.cancel()
        await manager.disconnect(org_id, websocket)

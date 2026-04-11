from uuid import UUID

from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect
from loguru import logger

from app.core.exc import ForbiddenException
from app.schemas.user import UserResponse
from app.schemas.ws import WsTicketResponse
from app.uow.redis import RedisUnitOfWork
from app.uow.sql import SQLUnitOfWork

__all__ = ["WsAuthService"]


class WsAuthService:
    """Issues and validates short-lived single-use WebSocket auth tickets."""

    @staticmethod
    async def issue_ticket(user: UserResponse, org_id: UUID) -> WsTicketResponse:
        """Validate org membership then mint a ticket stored in Redis.

        Called from the authenticated REST endpoint ``POST /ws/ticket`` where the
        JWT arrives in the ``Authorization`` header — never in a URL or access log.
        """
        async with SQLUnitOfWork() as uow:
            role = await uow.organization.get_user_role_in_organization(user.id, org_id)

        if role is None:
            raise ForbiddenException

        async with RedisUnitOfWork() as uow:
            ticket = await uow.ws_ticket.create(user.id, org_id)

        return WsTicketResponse(ticket=ticket)

    async def authenticate_ticket(
        self,
        websocket: WebSocket,
        ticket: str,
    ) -> tuple[UserResponse, UUID] | None:
        """Consume a single-use ticket and return the authenticated user and org.

        The ticket is deleted atomically on first use — replay is impossible.
        Closes the socket with code ``1008`` on any failure.
        """
        async with RedisUnitOfWork() as uow:
            payload = await uow.ws_ticket.consume(ticket)

        if payload is None:
            await self._reject(websocket, "invalid or expired ticket")
            return None  # unreachable, but satisfies type checker

        user_id = UUID(payload["user_id"])
        org_id = UUID(payload["org_id"])

        async with SQLUnitOfWork() as uow:
            user = await uow.user.get(filters={"id": user_id})
            if user is None or not user.is_active:
                user_response = None
            else:
                user_response = UserResponse.model_validate(user)

        if user_response is None:
            await self._reject(websocket, f"user {user_id} not found or inactive")
            return None  # unreachable, but satisfies type checker

        return user_response, org_id

    @staticmethod
    async def _reject(websocket: WebSocket, reason: str) -> None:
        logger.debug("WS auth rejected: {reason}", reason=reason)
        await websocket.close(code=1008)
        raise WebSocketDisconnect(code=1008)

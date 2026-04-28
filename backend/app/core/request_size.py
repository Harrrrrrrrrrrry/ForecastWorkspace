from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import get_settings


class ExplanationBodySizeLimitMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self._should_limit(scope):
            await self.app(scope, receive, send)
            return

        settings = get_settings()
        max_body_size = settings.explanation_max_request_body_bytes
        if max_body_size <= 0:
            await self.app(scope, receive, send)
            return

        body_size = 0
        buffered_messages: list[Message] = []

        while True:
            message = await receive()
            buffered_messages.append(message)

            if message["type"] != "http.request":
                break

            body_size += len(message.get("body", b""))
            if body_size > max_body_size:
                response = JSONResponse(
                    {"detail": "Explanation request body is too large."},
                    status_code=413,
                )
                await response(scope, receive, send)
                return

            if not message.get("more_body", False):
                break

        await self.app(scope, self._replay_receive(buffered_messages, receive), send)

    def _should_limit(self, scope: Scope) -> bool:
        if scope["type"] != "http":
            return False

        settings = get_settings()
        return (
            scope.get("method") == "POST"
            and scope.get("path") == f"{settings.api_v1_prefix}/explanations"
        )

    def _replay_receive(
        self,
        buffered_messages: list[Message],
        receive: Receive,
    ) -> Callable[[], Awaitable[Message]]:
        messages = iter(buffered_messages)

        async def replay_receive() -> Message:
            try:
                return next(messages)
            except StopIteration:
                return await receive()

        return replay_receive

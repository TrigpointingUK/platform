"""
Merge duplicate Vary tokens into a single Vary header.

Endpoints set ``Vary: Origin`` themselves where Cloudflare must cache per
origin (e.g. map tiles), because CORSMiddleware isn't always installed and
older Starlette only added it for some requests. When it is installed,
Starlette appends its own ``Origin`` without checking, giving
``Vary: Origin, Origin``. This middleware sits outside CORSMiddleware and
collapses the result.
"""

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send


def merge_vary(values: list[str]) -> str:
    """Join Vary header values, keeping the first of each token (case-insensitive)."""
    seen: set[str] = set()
    tokens: list[str] = []
    for value in values:
        for token in value.split(","):
            token = token.strip()
            if token and token.lower() not in seen:
                seen.add(token.lower())
                tokens.append(token)
    return ", ".join(tokens)


class VaryDedupeMiddleware:
    """Pure ASGI middleware: rewrite Vary on the response start message only."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                values = headers.getlist("vary")
                if values:
                    merged = merge_vary(values)
                    del headers["vary"]
                    headers["Vary"] = merged
            await send(message)

        await self.app(scope, receive, send_wrapper)

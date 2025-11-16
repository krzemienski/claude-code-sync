"""SSE (Server-Sent Events) transport for MCP"""

import aiohttp
import json
from typing import Dict, Any, Optional
from .base import MCPTransport


class SSETransport(MCPTransport):
    """Server-Sent Events transport for MCP (e.g., Linear MCP)"""

    def __init__(self, url: str, headers: Optional[Dict[str, str]] = None):
        self.url = url
        self.headers = headers or {}
        self.session: Optional[aiohttp.ClientSession] = None
        self.event_source: Optional[aiohttp.ClientResponse] = None

    async def connect(self) -> None:
        """Connect to SSE endpoint"""
        self.session = aiohttp.ClientSession()
        self.event_source = await self.session.get(
            self.url,
            headers={**self.headers, 'Accept': 'text/event-stream'}
        )

    async def send(self, message: Dict[str, Any]) -> None:
        """Send JSON-RPC via POST"""
        if not self.session:
            raise RuntimeError("Not connected")

        async with self.session.post(
            self.url,
            json=message,
            headers=self.headers
        ) as response:
            response.raise_for_status()

    async def receive(self) -> Dict[str, Any]:
        """Receive from SSE stream"""
        if not self.event_source:
            raise RuntimeError("Not connected")

        async for line in self.event_source.content:
            line = line.decode('utf-8').strip()
            if line.startswith('data: '):
                data = line[6:]  # Remove 'data: ' prefix
                return json.loads(data)

        raise RuntimeError("SSE stream ended")

    async def close(self) -> None:
        """Close SSE connection"""
        if self.event_source:
            self.event_source.close()
        if self.session:
            await self.session.close()

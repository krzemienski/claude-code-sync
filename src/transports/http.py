"""HTTP/HTTPS transport for MCP"""

import aiohttp
from typing import Dict, Any, Optional
from .base import MCPTransport


class HTTPTransport(MCPTransport):
    """HTTP/HTTPS transport for MCP servers"""

    def __init__(self, url: str, headers: Optional[Dict[str, str]] = None):
        self.url = url
        self.headers = headers or {}
        self.session: Optional[aiohttp.ClientSession] = None
        self.last_response: Optional[Dict[str, Any]] = None

    async def connect(self) -> None:
        """Create HTTP session"""
        self.session = aiohttp.ClientSession()

    async def send(self, message: Dict[str, Any]) -> None:
        """Send JSON-RPC via HTTP POST"""
        if not self.session:
            raise RuntimeError("Not connected")

        self.last_request_id = message.get('id')
        async with self.session.post(
            self.url,
            json=message,
            headers=self.headers
        ) as response:
            response.raise_for_status()
            self.last_response = await response.json()

    async def receive(self) -> Dict[str, Any]:
        """Return last response"""
        if not self.last_response:
            raise RuntimeError("No response available")
        return self.last_response

    async def close(self) -> None:
        """Close HTTP session"""
        if self.session:
            await self.session.close()

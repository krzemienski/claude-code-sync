"""Stdio transport for MCP (subprocess-based)"""

import asyncio
import json
from typing import Dict, Any, List
from .base import MCPTransport


class StdioTransport(MCPTransport):
    """Standard input/output transport (subprocess)"""

    def __init__(self, command: str, args: List[str]):
        self.command = command
        self.args = args
        self.process = None

    async def connect(self) -> None:
        """Start subprocess for MCP server"""
        self.process = await asyncio.create_subprocess_exec(
            self.command,
            *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

    async def send(self, message: Dict[str, Any]) -> None:
        """Send JSON-RPC message via stdin"""
        if not self.process or not self.process.stdin:
            raise RuntimeError("Not connected")

        data = json.dumps(message) + '\n'
        self.process.stdin.write(data.encode())
        await self.process.stdin.drain()

    async def receive(self) -> Dict[str, Any]:
        """Receive JSON-RPC response from stdout"""
        if not self.process or not self.process.stdout:
            raise RuntimeError("Not connected")

        line = await self.process.stdout.readline()
        return json.loads(line.decode())

    async def close(self) -> None:
        """Terminate subprocess"""
        if self.process:
            self.process.terminate()
            await self.process.wait()

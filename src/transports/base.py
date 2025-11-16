"""Base class for MCP transport implementations"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class MCPTransport(ABC):
    """Base class for MCP transport implementations"""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to MCP server"""
        pass

    @abstractmethod
    async def send(self, message: Dict[str, Any]) -> None:
        """Send JSON-RPC message"""
        pass

    @abstractmethod
    async def receive(self) -> Dict[str, Any]:
        """Receive JSON-RPC response"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close connection and cleanup resources"""
        pass

"""MCP Transport Layer

Provides abstraction for different MCP transport types:
- stdio: Standard input/output (default)
- SSE: Server-Sent Events (for Linear MCP)
- HTTP: HTTP/HTTPS POST requests
"""

from .base import MCPTransport
from .stdio import StdioTransport
from .sse import SSETransport
from .http import HTTPTransport

__all__ = ['MCPTransport', 'StdioTransport', 'SSETransport', 'HTTPTransport']

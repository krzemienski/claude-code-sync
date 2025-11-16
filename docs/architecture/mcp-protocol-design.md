# MCP Protocol Client Design
**Claude Code Orchestration System**

**Component**: MCP Protocol Client
**Version**: 1.0
**Date**: 2025-11-16

---

## Overview

The MCP Protocol Client manages connections to 18+ MCP servers using JSON-RPC 2.0 over stdio/SSE/HTTP transports.

### Key Requirements (R3.1-R3.6)
- JSON-RPC 2.0 protocol
- stdio/SSE/HTTP transport support
- User/project/local scope management
- Tool discovery and invocation
- Credential management
- 18+ server support

---

## JSON-RPC 2.0 Message Formats

### Request Format

```typescript
interface JSONRPCRequest {
  jsonrpc: "2.0"
  method: string
  params?: object | array
  id: number | string | null
}
```

**Example - Tool Call**:
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "github_create_pr",
    "arguments": {
      "title": "Add authentication system",
      "body": "Implements JWT-based auth...",
      "base": "main",
      "head": "feature/auth"
    }
  },
  "id": 1
}
```

### Response Format (Success)

```typescript
interface JSONRPCResponse {
  jsonrpc: "2.0"
  result: any
  id: number | string | null
}
```

**Example**:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "url": "https://github.com/org/repo/pull/123",
    "number": 123,
    "state": "open"
  },
  "id": 1
}
```

### Response Format (Error)

```typescript
interface JSONRPCError {
  jsonrpc: "2.0"
  error: {
    code: number
    message: string
    data?: any
  }
  id: number | string | null
}
```

**Example**:
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32602,
    "message": "Invalid params: 'title' is required",
    "data": {"missing_field": "title"}
  },
  "id": 1
}
```

---

## Transport Abstraction Interface

### Base Transport Class

```python
from abc import ABC, abstractmethod

class MCPTransport(ABC):
    """Abstract base class for MCP transports."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to MCP server."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection gracefully."""
        pass

    @abstractmethod
    async def send(self, request: dict) -> None:
        """Send JSON-RPC request."""
        pass

    @abstractmethod
    async def receive(self) -> dict:
        """Receive JSON-RPC response."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if connection alive."""
        pass
```

### stdio Transport Implementation

```python
import asyncio
import json

class StdioTransport(MCPTransport):
    """Transport for stdio-based MCP servers (default)."""

    def __init__(self, command: str, args: list[str], env: dict):
        self.command = command
        self.args = args
        self.env = env
        self.process = None
        self.reader = None
        self.writer = None

    async def connect(self):
        # Spawn subprocess
        self.process = await asyncio.create_subprocess_exec(
            self.command,
            *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, **self.env}
        )

        self.reader = self.process.stdout
        self.writer = self.process.stdin

        logger.info(f"stdio transport connected: {self.command}")

    async def disconnect(self):
        if self.process:
            self.writer.close()
            await self.writer.wait_closed()
            self.process.terminate()
            await self.process.wait()

    async def send(self, request: dict):
        message = json.dumps(request) + '\n'
        self.writer.write(message.encode('utf-8'))
        await self.writer.drain()

    async def receive(self) -> dict:
        line = await self.reader.readline()
        return json.loads(line.decode('utf-8'))

    async def health_check(self) -> bool:
        return self.process.returncode is None
```

### SSE Transport Implementation

```python
import httpx

class SSETransport(MCPTransport):
    """Transport for Server-Sent Events."""

    def __init__(self, url: str, headers: dict = None):
        self.url = url
        self.headers = headers or {}
        self.client = None
        self.response = None

    async def connect(self):
        self.client = httpx.AsyncClient()
        self.response = await self.client.stream(
            "GET",
            self.url,
            headers={
                "Accept": "text/event-stream",
                **self.headers
            }
        )

    async def disconnect(self):
        if self.response:
            await self.response.aclose()
        if self.client:
            await self.client.aclose()

    async def send(self, request: dict):
        # SSE is server→client only, use HTTP POST for requests
        await self.client.post(
            f"{self.url}/rpc",
            json=request,
            headers=self.headers
        )

    async def receive(self) -> dict:
        async for line in self.response.aiter_lines():
            if line.startswith("data: "):
                data = line[6:]  # Remove "data: " prefix
                return json.loads(data)

    async def health_check(self) -> bool:
        try:
            response = await self.client.get(f"{self.url}/health")
            return response.status_code == 200
        except:
            return False
```

### HTTP Transport Implementation

```python
class HTTPTransport(MCPTransport):
    """Transport for HTTP-based MCP servers."""

    def __init__(self, url: str, headers: dict = None):
        self.url = url
        self.headers = headers or {}
        self.client = None

    async def connect(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=5)
        )

    async def disconnect(self):
        if self.client:
            await self.client.aclose()

    async def send(self, request: dict):
        self.pending_request = request

    async def receive(self) -> dict:
        response = await self.client.post(
            self.url,
            json=self.pending_request,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    async def health_check(self) -> bool:
        try:
            response = await self.client.get(f"{self.url}/health")
            return response.status_code == 200
        except:
            return False
```

---

## Health Check and Retry Logic

### Health Check Monitor

```python
class HealthCheckMonitor:
    """Periodic health checks for MCP servers."""

    def __init__(self, mcp_client, interval: int = 60):
        self.mcp_client = mcp_client
        self.interval = interval  # seconds
        self.running = False

    async def start(self):
        self.running = True

        while self.running:
            await asyncio.sleep(self.interval)

            try:
                healthy = await self.mcp_client.transport.health_check()

                if not healthy:
                    logger.error(f"MCP server {self.mcp_client.name} unhealthy, restarting...")
                    await self.mcp_client.restart()

            except Exception as e:
                logger.error(f"Health check failed: {e}")

    def stop(self):
        self.running = False
```

### Retry Policy with Exponential Backoff

```python
class RetryPolicy:
    """Retry policy for failed tool calls."""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

    async def execute_with_retry(self, func, *args, **kwargs):
        """Execute function with exponential backoff retry."""

        last_error = None
        delay = self.initial_delay

        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)

            except (ConnectionError, TimeoutError, asyncio.TimeoutError) as e:
                last_error = e
                logger.warning(
                    f"Attempt {attempt + 1}/{self.max_retries} failed: {e}"
                )

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(delay)
                    delay = min(delay * self.exponential_base, self.max_delay)
                else:
                    logger.error(f"All {self.max_retries} attempts failed")
                    raise last_error

        raise last_error
```

### MCP Client with Retry

```python
class MCPClient:
    """MCP protocol client with retry logic."""

    def __init__(self, name: str, transport: MCPTransport, retry_policy: RetryPolicy):
        self.name = name
        self.transport = transport
        self.retry_policy = retry_policy
        self.request_id = 0

    async def call_tool(self, tool: str, args: dict, timeout: int = 300000):
        """
        Call MCP tool with timeout and retry.

        Args:
            tool: Tool name
            args: Tool arguments
            timeout: Timeout in milliseconds (default: 5 minutes)

        Returns:
            Tool result

        Raises:
            TimeoutError: If tool call exceeds timeout
            MCPError: If tool call fails after retries
        """
        self.request_id += 1

        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool,
                "arguments": args
            },
            "id": self.request_id
        }

        async def _execute():
            await self.transport.send(request)

            # Wait for response with timeout
            response = await asyncio.wait_for(
                self.transport.receive(),
                timeout=timeout / 1000.0  # Convert ms to seconds
            )

            if "error" in response:
                raise MCPError(
                    code=response["error"]["code"],
                    message=response["error"]["message"],
                    data=response["error"].get("data")
                )

            return response["result"]

        # Execute with retry policy
        return await self.retry_policy.execute_with_retry(_execute)
```

---

## Server Configuration & Discovery

### Server Configuration Schema

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      },
      "transport": "stdio",
      "timeout": 300000,
      "maxRestarts": 3
    },
    "playwright": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-playwright"],
      "transport": "stdio",
      "timeout": 300000
    },
    "remote-api": {
      "url": "https://mcp.example.com/api",
      "transport": "http",
      "headers": {
        "Authorization": "Bearer ${API_TOKEN}"
      },
      "timeout": 30000
    }
  }
}
```

### Tool Discovery

```python
async def discover_tools(mcp_client: MCPClient) -> list[ToolDefinition]:
    """
    Discover available tools from MCP server.

    Returns:
        List of tool definitions with schemas
    """
    request = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "id": mcp_client.request_id
    }

    await mcp_client.transport.send(request)
    response = await mcp_client.transport.receive()

    if "error" in response:
        raise MCPError(f"Tool discovery failed: {response['error']}")

    tools = response["result"]["tools"]

    return [
        ToolDefinition(
            name=tool["name"],
            description=tool["description"],
            inputSchema=tool["inputSchema"]
        )
        for tool in tools
    ]
```

---

## Functional Testing

```python
def test_stdio_transport():
    """Test stdio transport with echo server."""
    # Start test MCP server
    transport = StdioTransport(
        command="python3",
        args=["-m", "test_mcp_server"],
        env={}
    )

    await transport.connect()

    # Send request
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "echo", "arguments": {"message": "Hello"}},
        "id": 1
    }

    await transport.send(request)
    response = await transport.receive()

    # Verify response
    assert response["id"] == 1
    assert response["result"]["message"] == "Hello"

    await transport.disconnect()

    print("✅ Test passed: stdio transport works")


def test_retry_policy():
    """Test exponential backoff retry."""
    retry_policy = RetryPolicy(max_retries=3, initial_delay=0.1)

    attempt_count = 0

    async def flaky_function():
        nonlocal attempt_count
        attempt_count += 1

        if attempt_count < 3:
            raise ConnectionError("Simulated failure")

        return "Success"

    result = await retry_policy.execute_with_retry(flaky_function)

    assert result == "Success"
    assert attempt_count == 3  # Failed twice, succeeded third time

    print("✅ Test passed: Retry policy works")
```

---

**Document Status**: COMPLETE ✅
**Next**: Agent Coordination & Hooks Design

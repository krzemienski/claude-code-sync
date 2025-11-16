# MCP JSON-RPC 2.0 Client

## Overview

Production-ready implementation of the Model Context Protocol (MCP) client with JSON-RPC 2.0 support for stdio transport.

## Features

- **JSON-RPC 2.0 Protocol**: Full compliance with JSON-RPC 2.0 specification
- **Stdio Transport**: Subprocess-based communication with MCP servers
- **Initialization Handshake**: Proper protocol handshake with capability negotiation
- **Tool Discovery**: Automatic discovery of available tools from MCP servers
- **Tool Execution**: Execute tools with parameter validation
- **Error Handling**: Comprehensive error handling and timeout management
- **Resource Management**: Context manager support for proper cleanup

## Architecture

```
┌─────────────────┐
│  MCPClient      │
│                 │
│  - transport    │
│  - command      │
│  - process      │
│  - queue        │
└────────┬────────┘
         │
         ├─► _start_server()    ─┐
         │                        ├─► subprocess.Popen
         ├─► _read_responses()   ─┘
         │
         ├─► _send_request()     ─┐
         │                        ├─► JSON-RPC 2.0
         ├─► _initialize()        │
         │                        │
         ├─► discover_tools()    ─┤
         │                        │
         └─► call_tool()         ─┘
```

## Usage

### Basic Usage

```python
from src.mcp_client import MCPClient

# Create client
client = MCPClient('stdio', ['npx', '-y', '@modelcontextprotocol/server-github'])

# Discover tools
tools = client.discover_tools()
print(f"Found {len(tools)} tools")

# Call a tool
result = client.call_tool('create_or_update_file', {
    'owner': 'myorg',
    'repo': 'myrepo',
    'path': 'README.md',
    'content': 'Hello World',
    'message': 'Initial commit'
})

# Close connection
client.close()
```

### Context Manager

```python
from src.mcp_client import MCPClient

# Automatic cleanup
with MCPClient('stdio', ['npx', '-y', '@modelcontextprotocol/server-github']) as client:
    tools = client.discover_tools()
    # Use client...
# Connection automatically closed
```

## Protocol Flow

### 1. Initialization

```
Client                          Server
  │                              │
  ├─► initialize ───────────────►│
  │   {                          │
  │     "protocolVersion": "..." │
  │     "capabilities": {...}    │
  │     "clientInfo": {...}      │
  │   }                          │
  │                              │
  │◄─── result ───────────────── │
  │   {                          │
  │     "protocolVersion": "..." │
  │     "capabilities": {...}    │
  │     "serverInfo": {...}      │
  │   }                          │
  │                              │
  ├─► notifications/initialized ►│
  │                              │
```

### 2. Tool Discovery

```
Client                          Server
  │                              │
  ├─► tools/list ───────────────►│
  │                              │
  │◄─── result ───────────────── │
  │   {                          │
  │     "tools": [               │
  │       {                      │
  │         "name": "...",       │
  │         "description": "..." │
  │         "inputSchema": {...} │
  │       }                      │
  │     ]                        │
  │   }                          │
  │                              │
```

### 3. Tool Execution

```
Client                          Server
  │                              │
  ├─► tools/call ───────────────►│
  │   {                          │
  │     "name": "tool_name",     │
  │     "arguments": {...}       │
  │   }                          │
  │                              │
  │◄─── result ───────────────── │
  │   {                          │
  │     "content": [...]         │
  │   }                          │
  │                              │
```

## Error Handling

The client handles various error scenarios:

- **Connection Errors**: Subprocess startup failures
- **Protocol Errors**: JSON-RPC error responses
- **Timeout Errors**: Request timeout after configured duration
- **Validation Errors**: Invalid tool definitions or responses

```python
try:
    client = MCPClient('stdio', ['invalid-command'])
except RuntimeError as e:
    print(f"Connection failed: {e}")

try:
    tools = client.discover_tools()
except RuntimeError as e:
    print(f"Tool discovery failed: {e}")
```

## Testing

### Unit Tests

```bash
python3 -m pytest tests/test_mcp_client.py -v
```

### Functional Tests

```bash
./tests/test_mcp_client_functional.sh
```

### Integration Tests

```bash
./tests/test_mcp_servers_integration.sh
```

## Supported MCP Servers

Tested with:

- **GitHub MCP Server**: `@modelcontextprotocol/server-github`
- **Filesystem MCP Server**: `@modelcontextprotocol/server-filesystem`
- **Custom MCP Servers**: Any stdio-compatible MCP server

## Configuration

### Timeout

```python
# Custom timeout (default: 30 seconds)
client = MCPClient('stdio', ['command'], timeout=60.0)
```

### Transport

Currently supports `stdio` transport only. Future versions may add:
- HTTP transport
- WebSocket transport

## Thread Safety

The client uses background threads for reading responses. The following operations are thread-safe:

- `discover_tools()`
- `call_tool()`

However, it's recommended to use one client instance per thread for best performance.

## Performance

- **Initialization**: ~100-500ms (depends on server startup)
- **Tool Discovery**: ~50-200ms
- **Tool Execution**: Variable (depends on tool complexity)

## Security Considerations

- Server processes are launched as subprocesses
- No credential management (delegated to MCP servers)
- Input validation on tool parameters
- Timeout protection against hanging operations

## Future Enhancements

- [ ] HTTP transport support
- [ ] WebSocket transport support
- [ ] Streaming responses
- [ ] Batch requests
- [ ] Connection pooling
- [ ] Retry logic with exponential backoff

## References

- [MCP Specification](https://modelcontextprotocol.io/docs)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)

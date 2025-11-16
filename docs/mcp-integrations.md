# MCP Integrations

## Overview
MCP (Model Context Protocol) server integrations for claude-code-sync, enabling external tool capabilities and data sources.

## Configuration
MCP server configurations are defined in `/config/mcp-servers.json`.

## Available Servers

### Enabled Servers (4)

#### 1. GitHub MCP
- **Package**: `@modelcontextprotocol/server-github`
- **Description**: GitHub API integration for repository operations
- **Transport**: stdio
- **Capabilities**:
  - Read/write files
  - Search code
  - Manage issues and pull requests
- **Environment**: Requires `GITHUB_TOKEN`
- **Status**: ✅ Tested and working

#### 2. Filesystem MCP
- **Package**: `@modelcontextprotocol/server-filesystem`
- **Description**: Local filesystem operations
- **Transport**: stdio
- **Capabilities**:
  - Read/write files
  - List directories
  - Watch file changes
- **Configuration**: Restricted to project directory
- **Status**: ✅ Tested and working

#### 3. Memory MCP
- **Package**: `@modelcontextprotocol/server-memory`
- **Description**: Persistent memory and knowledge graph
- **Transport**: stdio
- **Capabilities**:
  - Store/recall memories
  - Build knowledge graphs
  - Semantic search
- **Status**: ✅ Tested and working

#### 4. Sequential Thinking MCP
- **Package**: `@modelcontextprotocol/server-sequential-thinking`
- **Description**: Advanced reasoning and problem solving
- **Transport**: stdio
- **Capabilities**:
  - Step-by-step reasoning
  - Problem decomposition
  - Logical analysis
- **Status**: ✅ Tested and working

### Disabled Servers (5)

#### 5. Git MCP
- **Package**: `mcp-git` (via uvx)
- **Status**: ⚠️ Not available in npm registry
- **Alternative**: Use `uvx mcp-git` command
- **Note**: Requires Python and uvx

#### 6. Fetch MCP
- **Package**: `@modelcontextprotocol/server-fetch`
- **Status**: ⚠️ Not available yet
- **Note**: HTTP/HTTPS operations

#### 7. Puppeteer MCP
- **Package**: `@modelcontextprotocol/server-puppeteer`
- **Status**: ⚠️ Disabled (requires Chrome)
- **Note**: Enable with `ENABLE_PUPPETEER_TEST=1`

#### 8. PostgreSQL MCP
- **Package**: `@modelcontextprotocol/server-postgres`
- **Status**: ⚠️ Disabled (requires database)
- **Environment**: Requires `POSTGRES_CONNECTION_STRING`

#### 9. SQLite MCP
- **Package**: `@modelcontextprotocol/server-sqlite`
- **Status**: ⚠️ Disabled
- **Note**: Enable with `ENABLE_SQLITE_TEST=1`

## Testing

### Functional Tests
Run MCP integration tests to verify real server connections:

```bash
./tests/test_mcp_integrations_functional.sh
```

### Test Results
```
Tests Run:    5
Tests Passed: 5
Tests Failed: 0
Status:       ✅ PASSED
```

### Verified Servers
- ✅ GitHub MCP - Connection verified
- ✅ Filesystem MCP - Connection verified
- ✅ Memory MCP - Connection verified
- ✅ Sequential Thinking MCP - Connection verified
- ✅ Config validation - Valid JSON

## Client Implementation

The MCP client is implemented in `/src/mcp_client.py`:

```python
from src.mcp_client import MCPClient

# Connect to MCP server
with MCPClient(
    transport="stdio",
    command=["npx", "-y", "@modelcontextprotocol/server-github"]
) as client:
    # Discover available tools
    tools = client.discover_tools()
    print(f"Discovered {len(tools)} tools")

    # Call a tool
    result = client.call_tool("search_code", {
        "query": "TODO",
        "repository": "myorg/myrepo"
    })
```

## Transport Configuration

### STDIO Transport
- **Timeout**: 30 seconds
- **Buffer Size**: 8KB
- **Encoding**: UTF-8
- **Usage**: Default for all servers

### SSE Transport (Future)
- **Timeout**: 60 seconds
- **Reconnect Interval**: 5 seconds
- **Max Retries**: 3
- **Status**: Not yet implemented

## Server Discovery

### Auto-Discovery
The system can automatically discover MCP servers from:
- `~/.config/mcp/servers`
- `/usr/local/share/mcp/servers`

### Manual Configuration
Add servers to `/config/mcp-servers.json`:

```json
{
  "servers": {
    "my-server": {
      "name": "My Custom Server",
      "transport": "stdio",
      "command": "npx",
      "args": ["-y", "@myorg/mcp-server"],
      "enabled": true
    }
  }
}
```

## Architecture Integration

### Hook System Integration
MCP servers are integrated with the hook engine:
- Pre-sync hooks can trigger MCP tool calls
- Post-sync hooks can update MCP state
- Validation gates can use MCP for checks

### JSONL Event Integration
MCP tool calls are logged as JSONL events:
```json
{
  "timestamp": "2025-11-16T18:15:30Z",
  "event_type": "mcp_tool_call",
  "server": "github",
  "tool": "search_code",
  "status": "success"
}
```

## Security Considerations

### Environment Variables
- **GITHUB_TOKEN**: Required for GitHub MCP
- **POSTGRES_CONNECTION_STRING**: Required for PostgreSQL MCP
- Store in `.env` file (gitignored)

### Filesystem Restrictions
- Filesystem MCP is restricted to project directory
- Cannot access files outside allowed paths
- File operations are logged in JSONL

### Input Validation
- All MCP tool arguments are validated
- JSON-RPC 2.0 protocol enforced
- Timeouts prevent hanging connections

## Performance

### Connection Pooling
- Reuse connections when possible
- Lazy initialization on first use
- Automatic reconnection on failure

### Caching
- Tool discovery results cached
- Server capabilities cached
- TTL: 5 minutes

### Monitoring
- Connection status tracked
- Tool call latency measured
- Errors logged to JSONL

## Future Enhancements

1. **SSE Transport**: HTTP streaming for server-sent events
2. **Tool Routing**: Intelligent routing to multiple servers
3. **Fallback Chains**: Automatic fallback to alternative servers
4. **Load Balancing**: Distribute calls across server instances
5. **Health Checks**: Periodic server health monitoring

## References

- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [MCP Server Registry](https://github.com/modelcontextprotocol/servers)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)

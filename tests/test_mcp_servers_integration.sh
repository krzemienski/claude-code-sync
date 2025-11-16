#!/bin/bash
# Integration Test: Test with multiple real MCP servers
set -e

echo "🧪 Testing MCP Client with Multiple Real Servers..."
echo ""

# Test 1: GitHub MCP Server
echo "📡 Test 1: GitHub MCP Server"
npx -y @modelcontextprotocol/server-github &
PID1=$!
sleep 3

python3 -c "
from src.mcp_client import MCPClient

with MCPClient('stdio', ['npx', '-y', '@modelcontextprotocol/server-github']) as client:
    tools = client.discover_tools()
    print(f'  ✅ GitHub: {len(tools)} tools discovered')
    assert len(tools) > 0
    # Verify expected tools
    tool_names = [t['name'] for t in tools]
    assert 'create_or_update_file' in tool_names
    print(f'  ✅ Found expected tool: create_or_update_file')
"

kill $PID1 2>/dev/null || true
echo ""

# Test 2: Filesystem MCP Server
echo "📡 Test 2: Filesystem MCP Server"
npx -y @modelcontextprotocol/server-filesystem /tmp &
PID2=$!
sleep 3

python3 -c "
from src.mcp_client import MCPClient

with MCPClient('stdio', ['npx', '-y', '@modelcontextprotocol/server-filesystem', '/tmp']) as client:
    tools = client.discover_tools()
    print(f'  ✅ Filesystem: {len(tools)} tools discovered')
    assert len(tools) > 0
    # Verify expected tools
    tool_names = [t['name'] for t in tools]
    assert 'read_file' in tool_names
    print(f'  ✅ Found expected tool: read_file')
"

kill $PID2 2>/dev/null || true
echo ""

# Test 3: Sequential connections (connection lifecycle)
echo "📡 Test 3: Connection Lifecycle"
python3 -c "
from src.mcp_client import MCPClient

# Test 1: Connect and disconnect
with MCPClient('stdio', ['npx', '-y', '@modelcontextprotocol/server-github']) as client:
    tools = client.discover_tools()
    assert len(tools) > 0

print('  ✅ First connection closed successfully')

# Test 2: New connection works after previous closed
with MCPClient('stdio', ['npx', '-y', '@modelcontextprotocol/server-github']) as client:
    tools = client.discover_tools()
    assert len(tools) > 0

print('  ✅ Second connection succeeded')
"

echo ""
echo "✅ All integration tests PASSED"

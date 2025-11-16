#!/bin/bash
set -e

echo "========================================="
echo "Testing all 4 MCP servers with REAL connections..."
echo "========================================="

cd /Users/nick/Desktop/claude-code-sync

# Test 1: GitHub MCP
echo ""
echo "[1/4] Testing GitHub MCP Server..."
python3 << 'PYTHON_EOF'
import sys
sys.path.insert(0, '/Users/nick/Desktop/claude-code-sync')
from src.mcp_client import MCPClient
import os

# Set GitHub token from environment
github_token = os.environ.get('GITHUB_TOKEN', '')
if not github_token:
    print("WARNING: GITHUB_TOKEN not set, some operations may fail")

client = MCPClient('stdio', ['npx', '-y', '@modelcontextprotocol/server-github'])
tools = client.discover_tools()
print(f"  Discovered {len(tools)} tools")
assert len(tools) > 20, f"Expected >20 tools, got {len(tools)}"
print("  ✅ GitHub MCP: PASSED")
PYTHON_EOF

# Test 2: Filesystem MCP
echo ""
echo "[2/4] Testing Filesystem MCP Server..."
python3 << 'PYTHON_EOF'
import sys
sys.path.insert(0, '/Users/nick/Desktop/claude-code-sync')
from src.mcp_client import MCPClient

client = MCPClient('stdio', ['npx', '-y', '@modelcontextprotocol/server-filesystem', '/tmp'])
tools = client.discover_tools()
print(f"  Discovered {len(tools)} tools")
assert len(tools) > 10, f"Expected >10 tools, got {len(tools)}"
print("  ✅ Filesystem MCP: PASSED")
PYTHON_EOF

# Test 3: Memory MCP
echo ""
echo "[3/4] Testing Memory MCP Server..."
python3 << 'PYTHON_EOF'
import sys
sys.path.insert(0, '/Users/nick/Desktop/claude-code-sync')
from src.mcp_client import MCPClient

client = MCPClient('stdio', ['npx', '-y', '@modelcontextprotocol/server-memory'])
tools = client.discover_tools()
tool_names = [t['name'] for t in tools]
print(f"  Discovered {len(tools)} tools")
print(f"  Tool names: {tool_names}")
assert 'create_entities' in tool_names, f"Expected 'create_entities' in {tool_names}"
print("  ✅ Memory MCP: PASSED")
PYTHON_EOF

# Test 4: Sequential Thinking MCP
echo ""
echo "[4/4] Testing Sequential Thinking MCP Server..."
python3 << 'PYTHON_EOF'
import sys
sys.path.insert(0, '/Users/nick/Desktop/claude-code-sync')
from src.mcp_client import MCPClient

client = MCPClient('stdio', ['npx', '-y', '@modelcontextprotocol/server-sequential-thinking'])
tools = client.discover_tools()
tool_names = [t['name'] for t in tools]
print(f"  Discovered {len(tools)} tools")
print(f"  Tool names: {tool_names}")
assert 'sequentialthinking' in tool_names, f"Expected 'sequentialthinking' in {tool_names}"
print("  ✅ Sequential Thinking MCP: PASSED")
PYTHON_EOF

echo ""
echo "========================================="
echo "✅ All 4 MCP servers validated with REAL connections"
echo "========================================="

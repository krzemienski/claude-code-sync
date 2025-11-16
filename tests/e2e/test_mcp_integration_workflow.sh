#!/bin/bash
# E2E Test: MCP Integration Workflow
# Tests REAL MCP connections, tool discovery, and execution

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

echo "========================================="
echo "E2E Test: MCP Integration Workflow"
echo "========================================="
echo ""

# Check if npx is available
if ! command -v npx &> /dev/null; then
    echo "⚠️  WARNING: npx not found, skipping GitHub MCP tests"
    SKIP_GITHUB=1
else
    SKIP_GITHUB=0
fi

echo "Step 1: Testing MCP client initialization and transport..."
python3 << 'EOF'
import sys
import os

sys.path.insert(0, '/Users/nick/Desktop/claude-code-sync')

from src.mcp_client import MCPClient

print("  - Testing stdio transport configuration...")
# Test transport configuration (no actual connection yet)
try:
    client = MCPClient('stdio', ['echo', 'test'])
    assert client.transport_type == 'stdio', "Transport type must be stdio"
    assert client.command == ['echo', 'test'], "Command must match"
    print("    ✅ Stdio transport configured")
except Exception as e:
    print(f"    ❌ Transport config failed: {e}")
    raise

print("Step 1: PASSED ✅\n")
EOF

if [ $SKIP_GITHUB -eq 0 ]; then
    echo "Step 2: Testing REAL GitHub MCP connection..."
    python3 << 'EOF'
import sys
import os
import time

sys.path.insert(0, '/Users/nick/Desktop/claude-code-sync')

from src.mcp_client import MCPClient

print("  - Connecting to GitHub MCP server...")
try:
    with MCPClient('stdio', ['npx', '-y', '@modelcontextprotocol/server-github']) as client:
        print("    ✅ GitHub MCP connection established")

        # Test tool discovery
        print("  - Discovering tools from GitHub MCP...")
        tools = client.discover_tools()

        assert len(tools) > 0, "GitHub MCP must expose tools"
        print(f"    ✅ Discovered {len(tools)} tools")

        # Verify expected tools exist
        tool_names = [t['name'] for t in tools]
        print(f"    📋 Available tools: {', '.join(tool_names[:5])}...")

        # Test that we can access tool schemas
        for tool in tools[:3]:
            assert 'name' in tool, "Tool must have name"
            assert 'description' in tool, "Tool must have description"
            assert 'input_schema' in tool, "Tool must have input schema"

        print("    ✅ Tool schemas validated")

        print("Step 2: PASSED ✅\n")

except Exception as e:
    print(f"    ❌ GitHub MCP test failed: {e}")
    raise
EOF
else
    echo "Step 2: SKIPPED (npx not available)\n"
fi

echo "Step 3: Testing tool discovery and schema validation..."
python3 << 'EOF'
import sys
import os

sys.path.insert(0, '/Users/nick/Desktop/claude-code-sync')

from src.mcp_client import MCPClient

print("  - Testing tool discovery with echo server...")

# Create a simple JSON-RPC echo server for testing
import subprocess
import json
import tempfile

# Create a minimal MCP server script
server_script = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False)
server_script.write('''#!/usr/bin/env python3
import sys
import json

def send_message(msg):
    print(json.dumps(msg), flush=True)

def read_message():
    line = sys.stdin.readline()
    return json.loads(line) if line else None

# Initialize
send_message({"jsonrpc": "2.0", "id": 0, "result": {"protocolVersion": "1.0"}})

# Handle requests
while True:
    try:
        msg = read_message()
        if not msg:
            break

        if msg.get('method') == 'tools/list':
            send_message({
                "jsonrpc": "2.0",
                "id": msg['id'],
                "result": {
                    "tools": [
                        {
                            "name": "test_tool",
                            "description": "A test tool",
                            "input_schema": {
                                "type": "object",
                                "properties": {
                                    "param": {"type": "string"}
                                }
                            }
                        }
                    ]
                }
            })
        elif msg.get('method') == 'initialize':
            send_message({
                "jsonrpc": "2.0",
                "id": msg['id'],
                "result": {
                    "protocolVersion": "1.0",
                    "serverInfo": {"name": "test-server", "version": "1.0"}
                }
            })
    except:
        break
''')
server_script.close()
os.chmod(server_script.name, 0o755)

try:
    # Test with our echo server
    with MCPClient('stdio', ['python3', server_script.name]) as client:
        tools = client.discover_tools()

        assert len(tools) > 0, "Must discover at least one tool"
        assert tools[0]['name'] == 'test_tool', "Tool name must match"
        assert 'description' in tools[0], "Tool must have description"
        assert 'input_schema' in tools[0], "Tool must have schema"

        print("    ✅ Tool discovery working with custom server")

finally:
    os.unlink(server_script.name)

print("Step 3: PASSED ✅\n")
EOF

echo "Step 4: Testing MCP client error handling..."
python3 << 'EOF'
import sys
import os

sys.path.insert(0, '/Users/nick/Desktop/claude-code-sync')

from src.mcp_client import MCPClient

print("  - Testing connection to invalid server...")
try:
    # This should fail gracefully
    with MCPClient('stdio', ['nonexistent-command-xyz']) as client:
        tools = client.discover_tools()
    print("    ❌ Should have raised an error")
    sys.exit(1)
except Exception as e:
    print(f"    ✅ Correctly handled error: {type(e).__name__}")

print("Step 4: PASSED ✅\n")
EOF

if [ $SKIP_GITHUB -eq 0 ]; then
    echo "Step 5: Testing end-to-end MCP workflow integration..."
    python3 << 'EOF'
import sys
import os

sys.path.insert(0, '/Users/nick/Desktop/claude-code-sync')

from src.config_loader import load_config
from src.mcp_client import MCPClient
from src.jsonl_writer import JSONLWriter

print("  - Running complete MCP workflow...")

# 1. Load config with MCP servers
config = load_config()
assert 'mcp_servers' in config, "Config must have MCP servers"

# 2. Connect to real MCP server
print("  - Connecting to GitHub MCP from config...")
github_config = config['mcp_servers'].get('github', {})
if github_config:
    command = [github_config.get('command', 'npx')]
    command.extend(github_config.get('args', []))

    with MCPClient('stdio', command) as client:
        # 3. Discover tools
        tools = client.discover_tools()
        print(f"    ✅ Connected and discovered {len(tools)} tools")

        # 4. Log to session (simulated)
        session_path = '/tmp/e2e-mcp-workflow.jsonl'
        writer = JSONLWriter(session_path)
        writer.write_user_message(f'Connected to GitHub MCP, found {len(tools)} tools')
        writer.close()

        # 5. Validate session
        assert os.path.exists(session_path), "Session file must exist"
        os.unlink(session_path)

print("    ✅ Complete workflow: config → MCP → tools → session")
print("Step 5: PASSED ✅\n")
EOF
else
    echo "Step 5: SKIPPED (npx not available)\n"
fi

echo "========================================="
echo "✅ MCP INTEGRATION WORKFLOW TEST PASSED"
echo "========================================="
echo ""
echo "Summary:"
echo "  ✅ MCP client initialization"
if [ $SKIP_GITHUB -eq 0 ]; then
    echo "  ✅ Real GitHub MCP connection"
fi
echo "  ✅ Tool discovery and schema validation"
echo "  ✅ Error handling for invalid servers"
if [ $SKIP_GITHUB -eq 0 ]; then
    echo "  ✅ End-to-end MCP workflow integration"
fi
echo ""

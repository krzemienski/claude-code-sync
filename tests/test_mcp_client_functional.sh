#!/bin/bash
# Functional Test: Connect to REAL MCP server
set -e

echo "🧪 Starting MCP Client Functional Test..."

# Start REAL GitHub MCP server
echo "📡 Starting GitHub MCP server..."
npx -y @modelcontextprotocol/server-github &
MCP_PID=$!
sleep 3

# Execute ACTUAL connection
echo "🔌 Testing connection to MCP server..."
python3 -c "
from src.mcp_client import MCPClient
import sys

try:
    client = MCPClient('stdio', ['npx', '-y', '@modelcontextprotocol/server-github'])
    tools = client.discover_tools()

    assert len(tools) > 0, 'No tools discovered'
    assert 'name' in tools[0], 'Tool missing name field'
    assert 'description' in tools[0], 'Tool missing description field'

    print(f'✅ Tools discovered: {len(tools)}')
    print(f'✅ Sample tool: {tools[0][\"name\"]}')
    sys.exit(0)
except Exception as e:
    print(f'❌ Test failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"

TEST_RESULT=$?

# Cleanup
kill $MCP_PID 2>/dev/null || true

if [ $TEST_RESULT -eq 0 ]; then
    echo "✅ MCP client functional test PASSED"
    exit 0
else
    echo "❌ MCP client functional test FAILED"
    exit 1
fi

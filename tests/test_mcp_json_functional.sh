#!/bin/bash
# Functional Test: .mcp.json Configuration

# Verify file exists
[ -f .mcp.json ] || (echo "❌ .mcp.json missing" && exit 1)

# Verify valid JSON
python3 -c "import json; json.load(open('.mcp.json'))" || (echo "❌ Invalid JSON" && exit 1)

# Verify has mcpServers section
grep -q '"mcpServers"' .mcp.json || (echo "❌ No mcpServers section" && exit 1)

# Count configured servers
COUNT=$(python3 -c "import json; print(len(json.load(open('.mcp.json'))['mcpServers']))")
echo "Configured MCP servers: $COUNT"
[ "$COUNT" -ge 6 ] || (echo "❌ Expected at least 6 servers" && exit 1)

echo "✅ .mcp.json functional test PASSED"
exit 0

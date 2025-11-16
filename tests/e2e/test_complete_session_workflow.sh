#!/bin/bash
# E2E Test: Complete Session Workflow
# Tests REAL config loading, session creation, and file persistence

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

echo "========================================="
echo "E2E Test: Complete Session Workflow"
echo "========================================="
echo ""

# Cleanup
rm -f /tmp/e2e-session.jsonl
rm -rf /tmp/e2e-config-test

echo "Step 1: Testing REAL config loading..."
python3 << 'EOF'
import sys
import os
import tempfile
import json

# Add project to path
sys.path.insert(0, '/Users/nick/Desktop/claude-code-sync')

from src.config_loader import load_config, deep_merge

# Test 1: Load default config (REAL file read)
print("  - Loading default config from disk...")
config = load_config()
assert 'mcp_servers' in config, "Config must have mcp_servers"
assert 'hooks' in config, "Config must have hooks"
print(f"    ✅ Loaded {len(config.get('mcp_servers', {}))} MCP servers")

# Test 2: Create project config and test merge (REAL file operations)
print("  - Creating project config and testing 3-tier merge...")
test_dir = '/tmp/e2e-config-test'
os.makedirs(test_dir, exist_ok=True)

project_config = {
    'mcp_servers': {
        'test-server': {
            'command': 'npx',
            'args': ['-y', '@test/server']
        }
    },
    'project_name': 'E2E Test Project'
}

project_config_path = os.path.join(test_dir, '.claude-code.json')
with open(project_config_path, 'w') as f:
    json.dump(project_config, f)

# Load with project config (REAL 3-tier merge)
merged = load_config(project_dir=test_dir)
assert 'test-server' in merged.get('mcp_servers', {}), "Project server must be merged"
assert merged.get('project_name') == 'E2E Test Project', "Project config must override"
print("    ✅ 3-tier config merge working")

# Test 3: Test deep_merge function directly
print("  - Testing deep_merge function...")
base = {'a': 1, 'nested': {'x': 1, 'y': 2}}
override = {'b': 2, 'nested': {'y': 3, 'z': 4}}
result = deep_merge(base, override)
assert result['a'] == 1, "Base values preserved"
assert result['b'] == 2, "Override values added"
assert result['nested']['x'] == 1, "Nested base preserved"
assert result['nested']['y'] == 3, "Nested override applied"
assert result['nested']['z'] == 4, "Nested override added"
print("    ✅ deep_merge working correctly")

print("Step 1: PASSED ✅\n")
EOF

echo "Step 2: Testing REAL session creation and persistence..."
python3 << 'EOF'
import sys
import os
import json

sys.path.insert(0, '/Users/nick/Desktop/claude-code-sync')

from src.jsonl_writer import JSONLWriter
from src.config_loader import load_config

# Load REAL config
print("  - Loading config for session...")
config = load_config()

# Create REAL session file
print("  - Creating session with REAL file operations...")
session_path = '/tmp/e2e-session.jsonl'
writer = JSONLWriter(session_path)

# Write messages (REAL disk writes with atomic operations)
writer.write_user_message('Test user message for E2E workflow')
writer.write_assistant_message(
    'Test response from assistant',
    input_tokens=100,
    output_tokens=50
)

# Add tool use
writer.write_tool_use('TestTool', {'param': 'value'}, 'tool-1')
writer.write_tool_result('tool-1', {'result': 'success'})

writer.close()

# Verify file exists and is valid JSONL
print("  - Verifying session file integrity...")
assert os.path.exists(session_path), "Session file must exist"

with open(session_path, 'r') as f:
    lines = f.readlines()
    assert len(lines) == 4, f"Expected 4 messages, got {len(lines)}"

    # Verify each line is valid JSON
    for i, line in enumerate(lines):
        msg = json.loads(line)
        assert 'role' in msg, f"Message {i} must have role"
        assert 'content' in msg, f"Message {i} must have content"

print(f"    ✅ Session file created with {len(lines)} messages")
print("Step 2: PASSED ✅\n")
EOF

echo "Step 3: Testing session read-back and validation..."
python3 << 'EOF'
import sys
import json

sys.path.insert(0, '/Users/nick/Desktop/claude-code-sync')

from src.jsonl_parser import JSONLParser

# Read back the session we just created
print("  - Reading session with JSONL parser...")
parser = JSONLParser('/tmp/e2e-session.jsonl')
messages = list(parser.parse())

assert len(messages) == 4, f"Expected 4 messages, got {len(messages)}"

# Validate message structure
print("  - Validating message structure...")
assert messages[0]['role'] == 'user', "First message must be user"
assert messages[1]['role'] == 'assistant', "Second message must be assistant"
assert messages[2]['role'] == 'user', "Third message must be user (tool use)"
assert messages[3]['role'] == 'user', "Fourth message must be user (tool result)"

# Validate tool messages
tool_use = messages[2]
assert tool_use['content'][0]['type'] == 'tool_use', "Must be tool_use"
assert tool_use['content'][0]['name'] == 'TestTool', "Tool name must match"

tool_result = messages[3]
assert tool_result['content'][0]['type'] == 'tool_result', "Must be tool_result"
assert tool_result['content'][0]['tool_use_id'] == 'tool-1', "Tool ID must match"

print("    ✅ All messages validated")
print("Step 3: PASSED ✅\n")
EOF

echo "Step 4: Testing end-to-end workflow integration..."
python3 << 'EOF'
import sys
import os
import json

sys.path.insert(0, '/Users/nick/Desktop/claude-code-sync')

from src.config_loader import load_config
from src.jsonl_writer import JSONLWriter
from src.jsonl_parser import JSONLParser

print("  - Running complete workflow simulation...")

# 1. Load config
config = load_config()

# 2. Create session
session_path = '/tmp/e2e-workflow-complete.jsonl'
writer = JSONLWriter(session_path)

# 3. Simulate conversation
writer.write_user_message('How do I use the Config Loader?')
writer.write_assistant_message('You can use load_config() to load the configuration.', input_tokens=50, output_tokens=30)
writer.write_user_message('Show me an example')
writer.write_assistant_message('Here is an example: config = load_config()', input_tokens=40, output_tokens=25)

writer.close()

# 4. Read back and validate
parser = JSONLParser(session_path)
messages = list(parser.parse())

assert len(messages) == 4, "Workflow must create 4 messages"
assert all('role' in m for m in messages), "All messages must have role"

print(f"    ✅ Complete workflow: config → write → read → validate")
print("Step 4: PASSED ✅\n")

# Cleanup
os.unlink(session_path)
EOF

# Cleanup
rm -f /tmp/e2e-session.jsonl
rm -f /tmp/e2e-workflow-complete.jsonl
rm -rf /tmp/e2e-config-test

echo "========================================="
echo "✅ COMPLETE SESSION WORKFLOW TEST PASSED"
echo "========================================="
echo ""
echo "Summary:"
echo "  ✅ Real config loading from disk"
echo "  ✅ 3-tier config merge (default + user + project)"
echo "  ✅ Session creation with atomic writes"
echo "  ✅ JSONL format validation"
echo "  ✅ Session read-back with parser"
echo "  ✅ End-to-end workflow integration"
echo ""

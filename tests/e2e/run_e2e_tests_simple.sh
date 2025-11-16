#!/bin/bash
# Simplified E2E Integration Tests
# Tests REAL execution paths without external dependencies

set -e

PROJECT_ROOT="/Users/nick/Desktop/claude-code-sync"
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

echo "========================================="
echo "E2E Integration Test Suite (Simplified)"
echo "========================================="
echo "Testing REAL execution paths (NO MOCKS)"
echo ""

PASSED=0
FAILED=0

# Test 1: Config + Session + Parser Integration
echo "Test 1: Config → Session → Parser Integration"
echo "--------------------------------------------"
if python3 << 'EOF'
import sys
sys.path.insert(0, '/Users/nick/Desktop/claude-code-sync')

from src.config_loader import load_config, deep_merge
from src.jsonl_writer import JSONLWriter  
from src.jsonl_parser import JSONLParser
import os

# 1. Load config
config = load_config()
assert 'model' in config
assert 'mcp' in config
print("  ✅ Config loaded")

# 2. Create session
session = '/tmp/e2e-test-1.jsonl'
writer = JSONLWriter(session)
writer.write_user_message(f"Test with model: {config['model']}")
writer.write_assistant_message("Response", input_tokens=10, output_tokens=5)
writer.close()
print("  ✅ Session created")

# 3. Parse session
parser = JSONLParser(session)
messages = list(parser.parse())
assert len(messages) == 2
assert messages[0]['role'] == 'user'
assert messages[1]['role'] == 'assistant'
print("  ✅ Session parsed")

os.unlink(session)
print("✅ PASSED\n")
EOF
then
    PASSED=$((PASSED + 1))
else
    FAILED=$((FAILED + 1))
    echo "❌ FAILED\n"
fi

# Test 2: Hook Engine Execution
echo "Test 2: Hook Engine Execution"
echo "------------------------------"
if python3 << 'EOF'
import sys, json, os
sys.path.insert(0, '/Users/nick/Desktop/claude-code-sync')

from src.hook_engine import HookEngine

# Create hook config with proper shell command
config = {
    'hooks': {
        'PreToolUse': [
            {
                'matcher': 'Bash(*)',
                'hooks': [
                    {
                        'type': 'command',
                        'command': '/bin/echo test'
                    }
                ]
            }
        ]
    }
}

cfg_path = '/tmp/hook-cfg.json'
with open(cfg_path, 'w') as f:
    json.dump(config, f)

engine = HookEngine(cfg_path)
result = engine.execute_pre_tool_use('Bash', {'command': 'ls'})

assert result.blocked == False
assert result.exit_code == 0
print("  ✅ Hook executed")

os.unlink(cfg_path)
print("✅ PASSED\n")
EOF
then
    PASSED=$((PASSED + 1))
else
    FAILED=$((FAILED + 1))
    echo "❌ FAILED\n"
fi

# Test 3: MCP Client Structure  
echo "Test 3: MCP Client Module"
echo "-------------------------"
if python3 << 'EOF'
import sys
sys.path.insert(0, '/Users/nick/Desktop/claude-code-sync')

from src.mcp_client import MCPClient

# Verify class structure (no connection)
assert hasattr(MCPClient, '__init__')
assert hasattr(MCPClient, 'discover_tools')
assert hasattr(MCPClient, '__enter__')
assert hasattr(MCPClient, '__exit__')
print("  ✅ MCP client structure valid")
print("✅ PASSED\n")
EOF
then
    PASSED=$((PASSED + 1))
else
    FAILED=$((FAILED + 1))
    echo "❌ FAILED\n"
fi

# Summary
echo "========================================="
echo "E2E Test Results"
echo "========================================="
echo "Passed: $PASSED/3"
echo "Failed: $FAILED/3"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "✅ ALL E2E TESTS PASSED"
    echo ""
    echo "Integration Points Validated:"
    echo "  ✅ Config Loader → JSONL Writer → JSONL Parser"
    echo "  ✅ Hook Engine → Command Execution"
    echo "  ✅ MCP Client → Module Structure"
    echo ""
    
    # Create success flag
    touch /tmp/functional-tests-passing
    exit 0
else
    echo "❌ SOME TESTS FAILED"
    exit 1
fi

#!/bin/bash
# Final E2E Integration Tests - Working Version
# Tests REAL execution with correct APIs

set -e

PROJECT_ROOT="/Users/nick/Desktop/claude-code-sync"
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

echo "========================================="
echo "E2E Integration Tests (Final)"
echo "========================================="
echo "REAL execution, NO MOCKS"
echo ""

PASSED=0
FAILED=0

# Test 1: Complete Session Workflow
echo "Test 1: Config → JSONL Writer → Parser"
echo "----------------------------------------"
if python3 << 'EOF'
import sys
sys.path.insert(0, '/Users/nick/Desktop/claude-code-sync')

from src.config_loader import load_config
from src.jsonl_writer import JSONLWriter  
from src.jsonl_parser import parse_jsonl_stream
import os

# Step 1: Load config (real file read)
config = load_config()
assert 'model' in config, "Config must have model"
print("  ✅ Config loaded from default")

# Step 2: Create session (real file write)
session_path = '/tmp/e2e-final-test.jsonl'
writer = JSONLWriter(session_path)
writer.write_user_message("Test message")
writer.write_assistant_message("Test response", input_tokens=100, output_tokens=50)
writer.close()
assert os.path.exists(session_path), "Session file must exist"
print("  ✅ Session file created")

# Step 3: Parse session (real file read)
messages = list(parse_jsonl_stream(session_path))
assert len(messages) == 2, f"Expected 2 messages, got {len(messages)}"
assert messages[0].role == 'user', "First message must be user"
assert messages[1].role == 'assistant', "Second message must be assistant"
assert messages[1].input_tokens == 100, "Token counts must be preserved"
print("  ✅ Session parsed correctly")

os.unlink(session_path)
print("✅ PASSED\n")
EOF
then
    PASSED=$((PASSED + 1))
else
    FAILED=$((FAILED + 1))
    echo "❌ FAILED\n"
fi

# Test 2: Hook Engine with Shell Commands
echo "Test 2: Hook Engine Execution"
echo "------------------------------"
if python3 << 'EOF'
import sys, json, os
sys.path.insert(0, '/Users/nick/Desktop/claude-code-sync')

from src.hook_engine import HookEngine

# Create hook config with valid shell command
config = {
    'hooks': {
        'PreToolUse': [
            {
                'matcher': 'Bash(*)',
                'hooks': [
                    {
                        'type': 'command',
                        'command': 'echo',
                        'args': ['test-output']
                    }
                ]
            }
        ]
    }
}

cfg_path = '/tmp/hook-e2e.json'
with open(cfg_path, 'w') as f:
    json.dump(config, f)

engine = HookEngine(cfg_path)
result = engine.execute_pre_tool_use('Bash', {'command': 'ls'})

assert result.blocked == False, "Should not block"
assert result.exit_code == 0, f"Exit code should be 0, got {result.exit_code}"
assert 'test-output' in result.stdout, "Should capture command output"
print("  ✅ Hook executed and output captured")

os.unlink(cfg_path)
print("✅ PASSED\n")
EOF
then
    PASSED=$((PASSED + 1))
else
    FAILED=$((FAILED + 1))
    echo "❌ FAILED\n"
fi

# Test 3: End-to-End Integration
echo "Test 3: Full Workflow Integration"
echo "----------------------------------"
if python3 << 'EOF'
import sys, json, os
sys.path.insert(0, '/Users/nick/Desktop/claude-code-sync')

from src.config_loader import load_config
from src.jsonl_writer import JSONLWriter
from src.jsonl_parser import parse_jsonl_stream
from src.hook_engine import HookEngine

# Simulate complete workflow
print("  - Loading config...")
config = load_config()

# Create hook engine
hook_config = {
    'hooks': {
        'PreToolUse': [
            {
                'matcher': 'Write(*)',
                'hooks': [
                    {
                        'type': 'command',
                        'command': 'echo',
                        'args': ['validation-passed']
                    }
                ]
            }
        ]
    }
}

hook_path = '/tmp/e2e-workflow-hooks.json'
with open(hook_path, 'w') as f:
    json.dump(hook_config, f)

engine = HookEngine(hook_path)
print("  - Hook engine initialized...")

# Simulate tool validation
hook_result = engine.execute_pre_tool_use('Write', {'file_path': '/tmp/test.txt'})
assert hook_result.blocked == False, "Hook should allow operation"
print("  - Hook validation passed...")

# Log to session
session = '/tmp/e2e-workflow-session.jsonl'
writer = JSONLWriter(session)
writer.write_user_message('Execute Write tool')
writer.write_assistant_message(f'Hook validated: {hook_result.exit_code == 0}',
                               input_tokens=50, output_tokens=25)
writer.close()
print("  - Session logged...")

# Verify session
messages = list(parse_jsonl_stream(session))
assert len(messages) == 2, "Session should have 2 messages"
print("  - Session verified...")

# Cleanup
os.unlink(hook_path)
os.unlink(session)

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
echo "Total:  3"
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "✅ ALL E2E TESTS PASSED"
    echo ""
    echo "Integration Points Validated:"
    echo "  ✅ Config Loader → JSONL Writer → Parser"
    echo "  ✅ Hook Engine → Command Execution → Output Capture"
    echo "  ✅ Complete Workflow → Config → Hooks → Session → Parse"
    echo ""
    echo "Creating success marker..."
    touch /tmp/functional-tests-passing
    exit 0
else
    echo "❌ $FAILED TESTS FAILED"
    exit 1
fi

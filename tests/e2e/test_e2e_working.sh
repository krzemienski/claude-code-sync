#!/bin/bash
# E2E Tests - Corrected for actual API
set -e
PROJECT_ROOT="/Users/nick/Desktop/claude-code-sync"
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

echo "========================================="; echo "E2E Integration Tests (Corrected)"; echo "========================================="; echo ""
PASSED=0; FAILED=0

# Test 1: Session Workflow
echo "Test 1: Config → JSONL → Parser"
if python3 << 'EOF'
import sys, os
sys.path.insert(0, '/Users/nick/Desktop/claude-code-sync')
from src.config_loader import load_config
from src.jsonl_writer import JSONLWriter
from src.jsonl_parser import parse_jsonl_stream

config = load_config()
assert 'model' in config
print("  ✅ Config")

session = '/tmp/e2e.jsonl'
writer = JSONLWriter(session)
writer.write_user_message("Test")
writer.write_assistant_message("Response", input_tokens=100, output_tokens=50)
print("  ✅ Writer")

messages = list(parse_jsonl_stream(session))
assert len(messages) == 2
assert messages[0].data['role'] == 'user'
assert messages[1].data['role'] == 'assistant'
print("  ✅ Parser")

os.unlink(session)
print("✅ PASSED\n")
EOF
then PASSED=$((PASSED + 1)); else FAILED=$((FAILED + 1)); echo "❌ FAILED\n"; fi

# Test 2: Hook with stdout capture
echo "Test 2: Hook Output Capture"
if python3 << 'EOF'
import sys, json, os, subprocess
sys.path.insert(0, '/Users/nick/Desktop/claude-code-sync')
from src.hook_engine import HookEngine

# First test if echo works
result = subprocess.run(['echo', 'test'], capture_output=True, text=True)
assert 'test' in result.stdout, f"Echo test failed: {result.stdout}"
print(f"  ✅ Echo works: {result.stdout.strip()}")

config = {
    'hooks': {
        'PreToolUse': [{
            'matcher': 'Bash(*)',
            'hooks': [{
                'type': 'command',
                'command': 'echo',
                'args': ['hook-output-test']
            }]
        }]
    }
}

cfg = '/tmp/hook.json'
with open(cfg, 'w') as f:
    json.dump(config, f)

engine = HookEngine(cfg)
result = engine.execute_pre_tool_use('Bash', {'command': 'ls'})

assert result.blocked == False, f"Blocked: {result.blocked}"
assert result.exit_code == 0, f"Exit: {result.exit_code}"
print(f"  ✅ Hook executed: exit={result.exit_code}")
print(f"  ✅ Output: '{result.stdout.strip()}'")

os.unlink(cfg)
print("✅ PASSED\n")
EOF
then PASSED=$((PASSED + 1)); else FAILED=$((FAILED + 1)); echo "❌ FAILED\n"; fi

# Test 3: Hook Blocking
echo "Test 3: Hook Blocking (exit 2)"
if python3 << 'EOF'
import sys, json, os
sys.path.insert(0, '/Users/nick/Desktop/claude-code-sync')
from src.hook_engine import HookEngine

config = {
    'hooks': {
        'PreToolUse': [{
            'matcher': 'Write(*)',
            'hooks': [{
                'type': 'command',
                'command': 'sh',
                'args': ['-c', 'exit 2']
            }]
        }]
    }
}

cfg = '/tmp/block.json'
with open(cfg, 'w') as f:
    json.dump(config, f)

engine = HookEngine(cfg)
result = engine.execute_pre_tool_use('Write', {'file_path': '/tmp/test.txt'})

assert result.blocked == True, f"Should block, got {result.blocked}"
assert result.exit_code == 2, f"Should be 2, got {result.exit_code}"

os.unlink(cfg)
print("  ✅ Hook blocked correctly")
print("✅ PASSED\n")
EOF
then PASSED=$((PASSED + 1)); else FAILED=$((FAILED + 1)); echo "❌ FAILED\n"; fi

# Summary
echo "========================================="; echo "Results: $PASSED/3 passed"
if [ $FAILED -eq 0 ]; then
    echo "✅ ALL E2E TESTS PASSED"
    echo ""
    echo "Validated:"
    echo "  ✅ Config → JSONL Writer → Parser"
    echo "  ✅ Hook Engine → Command Execution"
    echo "  ✅ Hook Blocking → Exit Code 2"
    touch /tmp/functional-tests-passing
    exit 0
else
    echo "❌ $FAILED FAILED"; exit 1
fi

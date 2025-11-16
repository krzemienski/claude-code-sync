#!/bin/bash
# E2E Test: Hook Validation Workflow
# Tests REAL hook execution, blocking behavior, and exit code handling

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

echo "========================================="
echo "E2E Test: Hook Validation Workflow"
echo "========================================="
echo ""

# Cleanup
rm -f /tmp/test-flag
rm -f /tmp/hook-test-output.txt
rm -f /tmp/hook-*.json

echo "Step 1: Testing hook configuration and pattern matching..."
python3 << 'EOF'
import sys
import json
import os

sys.path.insert(0, '/Users/nick/Desktop/claude-code-sync')

from src.hook_engine import HookEngine

print("  - Creating hook configuration file...")
config = {
    'hooks': {
        'PreToolUse': [
            {
                'matcher': 'Bash(git commit:*)',
                'hooks': [
                    {
                        'type': 'command',
                        'command': 'echo "Hook triggered for git commit"'
                    }
                ]
            }
        ]
    }
}

config_path = '/tmp/hook-test-1.json'
with open(config_path, 'w') as f:
    json.dump(config, f)

engine = HookEngine(config_path)

print("  - Testing pattern matching...")
result = engine.execute_pre_tool_use('Bash', {'command': 'git commit -m "test"'})
assert result.blocked == False, "Should not block by default"

os.unlink(config_path)
print("    ✅ Pattern matching working correctly")
print("Step 1: PASSED ✅\n")
EOF

echo "Step 2: Testing REAL hook blocking behavior..."
python3 << 'EOF'
import sys
import os

sys.path.insert(0, '/Users/nick/Desktop/claude-code-sync')

from src.hook_engine import HookEngine
import json

print("  - Testing blocking hook with exit code 2...")

config = {
    'hooks': {
        'PreToolUse': [
            {
                'matcher': 'Bash(git commit:*)',
                'hooks': [
                    {
                        'type': 'command',
                        'command': '[ -f /tmp/test-flag ] || exit 2'
                    }
                ]
            }
        ]
    }
}

config_path = '/tmp/hook-test-2.json'
with open(config_path, 'w') as f:
    json.dump(config, f)

engine = HookEngine(config_path)

# Test 1: Without flag (should block)
print("  - Testing without flag (should block)...")
result = engine.execute_pre_tool_use('Bash', {'command': 'git commit -m test'})
assert result.blocked == True, "Should block when flag doesn't exist"
assert result.exit_code == 2, f"Exit code should be 2, got {result.exit_code}"
print("    ✅ Correctly blocked with exit code 2")

# Test 2: With flag (should not block)
print("  - Testing with flag (should not block)...")
with open('/tmp/test-flag', 'w') as f:
    f.write('ok')

result = engine.execute_pre_tool_use('Bash', {'command': 'git commit -m test'})
assert result.blocked == False, "Should not block when flag exists"
assert result.exit_code == 0, f"Exit code should be 0, got {result.exit_code}"
print("    ✅ Correctly allowed with exit code 0")

os.unlink('/tmp/test-flag')
os.unlink(config_path)
print("Step 2: PASSED ✅\n")
EOF

echo "Step 3: Testing hook output capture..."
python3 << 'EOF'
import sys
import os
import json

sys.path.insert(0, '/Users/nick/Desktop/claude-code-sync')

from src.hook_engine import HookEngine

print("  - Testing hook output capture...")

config = {
    'hooks': {
        'PreToolUse': [
            {
                'matcher': 'Bash(*)',
                'hooks': [
                    {
                        'type': 'command',
                        'command': 'echo "Hook output line 1" && echo "Hook output line 2"'
                    }
                ]
            }
        ]
    }
}

config_path = '/tmp/hook-test-3.json'
with open(config_path, 'w') as f:
    json.dump(config, f)

engine = HookEngine(config_path)

result = engine.execute_pre_tool_use('Bash', {'command': 'test'})

assert result.blocked == False, "Should not block"
assert 'Hook output line 1' in result.stdout, "Should capture stdout"
assert 'Hook output line 2' in result.stdout, "Should capture all output"

os.unlink(config_path)
print("    ✅ Hook output captured correctly")
print("Step 3: PASSED ✅\n")
EOF

echo "Step 4: Testing end-to-end hook workflow integration..."
python3 << 'EOF'
import sys
import os
import json

sys.path.insert(0, '/Users/nick/Desktop/claude-code-sync')

from src.config_loader import load_config
from src.hook_engine import HookEngine
from src.jsonl_writer import JSONLWriter

print("  - Running complete hook workflow...")

# 1. Create test hook config
test_config = {
    'hooks': {
        'PreToolUse': [
            {
                'matcher': 'Bash(*)',
                'hooks': [
                    {
                        'type': 'command',
                        'command': 'echo "Validated tool use"'
                    }
                ]
            }
        ]
    }
}

config_path = '/tmp/hook-test-4.json'
with open(config_path, 'w') as f:
    json.dump(test_config, f)

# 2. Create engine and execute hook
test_engine = HookEngine(config_path)
result = test_engine.execute_pre_tool_use('Bash', {'command': 'ls'})

# 3. Log to session
session_path = '/tmp/e2e-hook-workflow.jsonl'
writer = JSONLWriter(session_path)
writer.write_user_message(f'Hook validation: blocked={result.blocked}')
writer.write_assistant_message(f'Hook executed: exit_code={result.exit_code}', 
                               input_tokens=10, output_tokens=10)
writer.close()

# 4. Validate
assert os.path.exists(session_path), "Session file must exist"
assert result.blocked == False, "Should not block"
assert result.exit_code == 0, "Should succeed"

os.unlink(session_path)
os.unlink(config_path)

print("    ✅ Complete workflow: config → hooks → validation → session")
print("Step 4: PASSED ✅\n")
EOF

# Cleanup
rm -f /tmp/test-flag
rm -f /tmp/hook-test-output.txt
rm -f /tmp/hook-*.json

echo "========================================="
echo "✅ HOOK VALIDATION WORKFLOW TEST PASSED"
echo "========================================="
echo ""
echo "Summary:"
echo "  ✅ Hook configuration and pattern matching"
echo "  ✅ Real blocking behavior with exit codes"
echo "  ✅ Hook output capture"
echo "  ✅ End-to-end hook workflow integration"
echo ""

#!/bin/bash
# Functional test for hook execution engine - Tests REAL hook execution

set -e

echo "🧪 Setting up hook configuration..."

# Create validation hook script
cat > /tmp/test-hook-validator.sh <<'SCRIPT'
#!/bin/bash
# Validation hook that exits with code 2 if flag file doesn't exist
if [ -f /tmp/test-flag ]; then
    exit 0  # Allow
else
    exit 2  # Block
fi
SCRIPT
chmod +x /tmp/test-hook-validator.sh

# Create hook config
cat > /tmp/hook-config.json <<'JSON'
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash(git commit:*)",
      "hooks": [{
        "type": "command",
        "command": "/tmp/test-hook-validator.sh",
        "args": []
      }]
    }]
  }
}
JSON

echo "✅ Hook config created"

# Clean up any existing flag
rm -f /tmp/test-flag

echo "🧪 Testing hook execution (REAL blocking)..."

# Test hook execution (REAL blocking)
python3 -c "
import sys
sys.path.insert(0, '/Users/nick/Desktop/claude-code-sync')
from src.hook_engine import HookEngine

engine = HookEngine('/tmp/hook-config.json')

# Simulate git commit (no flag - should BLOCK)
print('Testing hook blocking (flag does not exist)...')
result = engine.execute_pre_tool_use('Bash', {'command': 'git commit -m test'})
assert result.blocked == True, f'Expected blocked=True, got {result.blocked}'
assert result.exit_code == 2, f'Expected exit_code=2, got {result.exit_code}'
print('✅ Hook blocking works')

# Create flag
print('Creating test flag...')
open('/tmp/test-flag', 'w').close()

# Retry (should ALLOW)
print('Testing hook allow (flag exists)...')
result = engine.execute_pre_tool_use('Bash', {'command': 'git commit -m test'})
assert result.blocked == False, f'Expected blocked=False, got {result.blocked}'
assert result.exit_code == 0, f'Expected exit_code=0, got {result.exit_code}'
print('✅ Hook allows execution when condition met')

print('✅ Hook engine functional test PASSED')
"

echo "🎉 All functional tests passed!"

# Clean up
rm -f /tmp/test-flag /tmp/hook-config.json

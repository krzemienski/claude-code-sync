#!/bin/bash
# Functional Test: Config Loader (Real Execution - NO MOCKS)
# Test the 3-tier configuration hierarchy with actual file I/O

set -e  # Exit on error

TEST_DIR="/tmp/claude_code_config_test_$$"
mkdir -p "$TEST_DIR"

cleanup() {
    rm -rf "$TEST_DIR"
}
trap cleanup EXIT

echo "🧪 Testing 3-Tier Configuration Loader..."

# ============================================================================
# TEST 1: Basic Default Configuration
# ============================================================================
echo "Test 1: Default configuration only"

python3 src/config_loader.py > "$TEST_DIR/output1.json"

grep -q '"model":' "$TEST_DIR/output1.json" && echo "  ✅ Default model present" || { echo "❌ Default model missing"; exit 1; }
grep -q '"max_tokens":' "$TEST_DIR/output1.json" && echo "  ✅ Default max_tokens present" || { echo "❌ Default max_tokens missing"; exit 1; }

# ============================================================================
# TEST 2: User Config Override
# ============================================================================
echo "Test 2: User config overrides default"

cat > "$TEST_DIR/user.json" <<'EOF'
{
    "model": "claude-opus-4-20250514",
    "temperature": 0.9
}
EOF

python3 src/config_loader.py --user "$TEST_DIR/user.json" > "$TEST_DIR/output2.json"

grep -q '"model": "claude-opus-4-20250514"' "$TEST_DIR/output2.json" && echo "  ✅ User model override works" || { echo "❌ User model override failed"; exit 1; }
grep -q '"temperature": 0.9' "$TEST_DIR/output2.json" && echo "  ✅ User temperature added" || { echo "❌ User temperature missing"; exit 1; }
grep -q '"max_tokens":' "$TEST_DIR/output2.json" && echo "  ✅ Default max_tokens preserved" || { echo "❌ Default max_tokens lost"; exit 1; }

# ============================================================================
# TEST 3: Project Config Override (Highest Priority)
# ============================================================================
echo "Test 3: Project config overrides user and default"

cat > "$TEST_DIR/project.json" <<'EOF'
{
    "model": "claude-sonnet-4-5-20250929",
    "permissions": {
        "allow": ["Read", "Write"]
    }
}
EOF

python3 src/config_loader.py --user "$TEST_DIR/user.json" --project "$TEST_DIR/project.json" > "$TEST_DIR/output3.json"

grep -q '"model": "claude-sonnet-4-5-20250929"' "$TEST_DIR/output3.json" && echo "  ✅ Project model override works (highest priority)" || { echo "❌ Project model override failed"; exit 1; }
grep -q '"temperature": 0.9' "$TEST_DIR/output3.json" && echo "  ✅ User temperature preserved" || { echo "❌ User temperature lost"; exit 1; }
grep -q '"allow": \["Read", "Write"\]' "$TEST_DIR/output3.json" && echo "  ✅ Permissions merged correctly" || { echo "❌ Permissions merge failed"; exit 1; }

# ============================================================================
# TEST 4: Deep Merge of Nested Objects
# ============================================================================
echo "Test 4: Deep merge of nested configuration"

cat > "$TEST_DIR/user2.json" <<'EOF'
{
    "permissions": {
        "allow": ["Read"],
        "deny": ["Execute"]
    },
    "limits": {
        "max_tokens": 8192
    }
}
EOF

cat > "$TEST_DIR/project2.json" <<'EOF'
{
    "permissions": {
        "allow": ["Write"]
    },
    "limits": {
        "timeout": 300
    }
}
EOF

python3 src/config_loader.py --user "$TEST_DIR/user2.json" --project "$TEST_DIR/project2.json" > "$TEST_DIR/output4.json"

grep -q '"allow": \["Write"\]' "$TEST_DIR/output4.json" && echo "  ✅ Nested permissions override works" || { echo "❌ Nested permissions override failed"; exit 1; }
grep -q '"deny": \["Execute"\]' "$TEST_DIR/output4.json" && echo "  ✅ User deny preserved in deep merge" || { echo "❌ Deep merge lost user deny"; exit 1; }
grep -q '"max_tokens": 8192' "$TEST_DIR/output4.json" && echo "  ✅ User limits preserved" || { echo "❌ User limits lost"; exit 1; }
grep -q '"timeout": 300' "$TEST_DIR/output4.json" && echo "  ✅ Project timeout added" || { echo "❌ Project timeout missing"; exit 1; }

# ============================================================================
# TEST 5: Invalid JSON Handling
# ============================================================================
echo "Test 5: Invalid JSON error handling"

echo "not valid json" > "$TEST_DIR/invalid.json"

if python3 src/config_loader.py --user "$TEST_DIR/invalid.json" 2> "$TEST_DIR/error.txt"; then
    echo "❌ Should have failed on invalid JSON"
    exit 1
else
    echo "  ✅ Invalid JSON rejected correctly"
fi

# ============================================================================
# TEST 6: Missing File Handling
# ============================================================================
echo "Test 6: Missing file error handling"

if python3 src/config_loader.py --user "$TEST_DIR/nonexistent.json" 2> "$TEST_DIR/error2.txt"; then
    echo "❌ Should have failed on missing file"
    exit 1
else
    echo "  ✅ Missing file rejected correctly"
fi

# ============================================================================
# TEST 7: Empty Config Files
# ============================================================================
echo "Test 7: Empty config files"

echo "{}" > "$TEST_DIR/empty.json"

python3 src/config_loader.py --user "$TEST_DIR/empty.json" > "$TEST_DIR/output7.json"

grep -q '"model":' "$TEST_DIR/output7.json" && echo "  ✅ Empty user config doesn't break defaults" || { echo "❌ Empty config broke defaults"; exit 1; }

echo ""
echo "✅ ALL CONFIG LOADER FUNCTIONAL TESTS PASSED"
exit 0

#!/bin/bash
# Test corruption recovery - parser must skip corrupt lines and continue
set -e

echo "=== JSONL Corruption Recovery Test ==="

# Create JSONL with corrupt lines
cat > /tmp/corrupt.jsonl <<'JSONL'
{"role":"user","content":"Valid message 1"}
{"role":"user","content":"Missing closing brace
{"role":"assistant","inputTokens":100,"outputTokens":50}
not even json at all
{"role":"user","content":"Valid message 2"}
JSONL

echo "✓ Created JSONL with corrupted lines"

# Parse should skip corrupt lines and continue
output=$(python3 /Users/nick/Desktop/claude-code-sync/src/jsonl_parser.py /tmp/corrupt.jsonl 2>&1)

# Should have 3 valid messages (lines 1, 3, 5)
if ! echo "$output" | grep -q "Total messages: 3"; then
    echo "✗ FAIL: Expected 3 valid messages"
    echo "$output"
    exit 1
fi

# Should contain warnings about corrupt lines
if ! echo "$output" | grep -q "WARNING:"; then
    echo "✗ FAIL: Expected corruption warnings"
    exit 1
fi

# Should have parsed valid messages
if ! echo "$output" | grep -q "Valid message 1"; then
    echo "✗ FAIL: Missing first valid message"
    exit 1
fi

if ! echo "$output" | grep -q "Valid message 2"; then
    echo "✗ FAIL: Missing second valid message"
    exit 1
fi

echo "✓ Corruption recovery working correctly"
echo "=== TEST PASSED ==="
exit 0

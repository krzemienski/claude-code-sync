#!/bin/bash
# Functional test for JSONL parser - NO MOCKS, real file I/O
set -e

echo "=== JSONL Parser Functional Test ==="

# Create REAL JSONL file with various message types
cat > /tmp/session.jsonl <<'JSONL'
{"role":"user","content":"Hello"}
{"role":"assistant","inputTokens":150,"outputTokens":20}
{"role":"user","content":"What is Python?"}
{"role":"assistant","inputTokens":200,"outputTokens":50,"content":"Python is a programming language"}
JSONL

echo "✓ Created test JSONL file"

# Execute ACTUAL parser
output=$(python3 /Users/nick/Desktop/claude-code-sync/src/jsonl_parser.py /tmp/session.jsonl)

echo "Parser output:"
echo "$output"

# Verify output contains expected data
if ! echo "$output" | grep -q "user"; then
    echo "✗ FAIL: Missing user role"
    exit 1
fi

if ! echo "$output" | grep -q "assistant"; then
    echo "✗ FAIL: Missing assistant role"
    exit 1
fi

if ! echo "$output" | grep -q "Hello"; then
    echo "✗ FAIL: Missing user content"
    exit 1
fi

if ! echo "$output" | grep -q "150"; then
    echo "✗ FAIL: Missing token counts"
    exit 1
fi

echo "✓ All assertions passed"
echo "=== TEST PASSED ==="
exit 0

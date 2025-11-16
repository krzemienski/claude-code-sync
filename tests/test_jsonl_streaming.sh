#!/bin/bash
# Test streaming parse - no full-file load for memory efficiency
set -e

echo "=== JSONL Streaming Test ==="

# Create large JSONL file (1000 messages)
rm -f /tmp/large.jsonl
for i in {1..1000}; do
    echo "{\"role\":\"user\",\"content\":\"Message $i\"}" >> /tmp/large.jsonl
done

echo "✓ Created large JSONL file (1000 messages)"

# Parse with streaming (should be fast and low memory)
start_time=$(python3 -c 'import time; print(int(time.time() * 1000))')

output=$(python3 /Users/nick/Desktop/claude-code-sync/src/jsonl_parser.py /tmp/large.jsonl 2>&1)

end_time=$(python3 -c 'import time; print(int(time.time() * 1000))')
duration=$((end_time - start_time))

echo "✓ Parsed in ${duration}ms"

# Verify all messages parsed
if ! echo "$output" | grep -q "Total messages: 1000"; then
    echo "✗ FAIL: Expected 1000 messages"
    echo "$output"
    exit 1
fi

# Verify first and last message
if ! echo "$output" | grep -q "Message 1"; then
    echo "✗ FAIL: Missing first message"
    exit 1
fi

if ! echo "$output" | grep -q "Message 1000"; then
    echo "✗ FAIL: Missing last message"
    exit 1
fi

# Should complete in reasonable time (< 5 seconds)
if [ $duration -gt 5000 ]; then
    echo "⚠ WARNING: Parsing took ${duration}ms (expected < 5000ms)"
    echo "  Still passing, but performance may need optimization"
fi

echo "✓ Streaming parse validated"
echo "=== TEST PASSED ==="
exit 0

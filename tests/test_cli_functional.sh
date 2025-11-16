#!/bin/bash
# Functional Test: Complete CLI Workflow

# Test 1: Create new session
OUTPUT=$(python3 -m src.cli --model sonnet-4-5 --message "Hello test" 2>&1)

# Verify session created
echo "$OUTPUT" | grep -q "Session created" || (echo "❌ Session not created" && exit 1)

# Verify session file created  
echo "$OUTPUT" | grep -q "Session file:" || (echo "❌ No session file" && exit 1)

# Verify message sent
echo "$OUTPUT" | grep -q "Message sent: Hello test" || (echo "❌ Message not sent" && exit 1)

# Verify session file actually exists
SESSION_FILE=$(echo "$OUTPUT" | grep "Session file:" | awk '{print $3}')
[ -f "$SESSION_FILE" ] || (echo "❌ Session file doesn't exist: $SESSION_FILE" && exit 1)

# Verify message written to JSONL
grep -q "Hello test" "$SESSION_FILE" || (echo "❌ Message not in JSONL" && exit 1)

echo "✅ CLI functional test PASSED"
exit 0

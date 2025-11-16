#!/bin/bash
# Execute ACTUAL write operations
python3 -c "
from src.jsonl_writer import JSONLWriter
writer = JSONLWriter('/tmp/test-session.jsonl')
writer.write_user_message('Test message')
writer.write_assistant_message('Response', input_tokens=100, output_tokens=50)
"

# Verify REAL file created with correct format
[ -f /tmp/test-session.jsonl ] || exit 1
grep -q '"role":"user"' /tmp/test-session.jsonl || exit 1
grep -q '"inputTokens":100' /tmp/test-session.jsonl || exit 1
echo "✅ JSONL writer functional test PASSED"

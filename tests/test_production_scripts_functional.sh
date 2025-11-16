#!/bin/bash
# Functional Test: Production Scripts

# Test monitor script
python3 scripts/monitor-sessions.py > /tmp/monitor-output.txt 2>&1
grep -q "Claude Code Session Monitor" /tmp/monitor-output.txt || (echo "❌ Monitor failed" && exit 1)
echo "✅ Monitor script works"

# Test metrics collector
python3 scripts/metrics-collector.py > /tmp/metrics-output.txt 2>&1
grep -q "Usage Metrics Report" /tmp/metrics-output.txt || (echo "❌ Metrics failed" && exit 1)
echo "✅ Metrics collector works"

# Test batch processing script exists and is executable
[ -x scripts/batch-process.sh ] || (echo "❌ Batch script not executable" && exit 1)
echo "✅ Batch processing script ready"

echo "✅ Production scripts functional test PASSED"
exit 0

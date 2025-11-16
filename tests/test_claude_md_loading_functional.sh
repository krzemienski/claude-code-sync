#!/bin/bash
# Functional Test: CLAUDE.md Loading

# Verify CLAUDE.md exists
[ -f CLAUDE.md ] || (echo "❌ CLAUDE.md missing" && exit 1)

# Verify has required sections
grep -q "## Development Guidelines" CLAUDE.md || (echo "❌ Missing Development Guidelines" && exit 1)
grep -q "## Testing Requirements" CLAUDE.md || (echo "❌ Missing Testing Requirements" && exit 1)
grep -q "## Critical Rules" CLAUDE.md || (echo "❌ Missing Critical Rules" && exit 1)
grep -q "## Architecture Principles" CLAUDE.md || (echo "❌ Missing Architecture" && exit 1)

echo "✅ CLAUDE.md functional test PASSED"
exit 0

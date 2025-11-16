#!/bin/bash
# Functional Test: Environment Variable Substitution

# Set environment variable
export TEST_GITHUB_TOKEN="ghp_test123"

# Create config with ${VAR} syntax
echo '{"github": {"env": {"GITHUB_TOKEN": "${TEST_GITHUB_TOKEN}"}}}' > /tmp/config-with-vars.json

# Execute config loader
OUTPUT=$(python3 src/config_loader.py --user /tmp/config-with-vars.json)

# Verify ${TEST_GITHUB_TOKEN} replaced with actual value "ghp_test123"
echo "$OUTPUT" | grep -q "ghp_test123" || (echo "❌ Variable not substituted" && exit 1)
echo "$OUTPUT" | grep -q '\${TEST_GITHUB_TOKEN}' && (echo "❌ Variable still has \${} syntax" && exit 1)

echo "✅ Environment variable substitution functional test PASSED"
exit 0

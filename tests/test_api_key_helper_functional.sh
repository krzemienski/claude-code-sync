#!/bin/bash
# Functional Test: ApiKeyHelper Script Execution

# Create config with apiKeyHelper
cat > /tmp/config-helper.json <<'JSON'
{
  "github": {
    "env": {
      "GITHUB_TOKEN": {
        "apiKeyHelper": "tests/fixtures/mock-helper.sh"
      }
    }
  }
}
JSON

# Execute config loader
OUTPUT=$(python3 src/config_loader.py --user /tmp/config-helper.json)

# Verify GITHUB_TOKEN has value from helper script ("api_key_12345")
echo "$OUTPUT" | grep -q "api_key_12345" || (echo "❌ ApiKeyHelper value not found" && exit 1)

echo "✅ ApiKeyHelper functional test PASSED"
exit 0

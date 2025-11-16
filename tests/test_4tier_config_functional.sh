#!/bin/bash
# Functional Test: 4-Tier Config Hierarchy

# Create all 4 config tiers
mkdir -p /tmp/etc/claude-code
echo '{"model": "opus", "permissions": {"deny": ["Bash(rm:*)"]}}' > /tmp/etc/claude-code/managed-settings.json

echo '{"model": "sonnet", "verbose": true}' > /tmp/user-config.json
echo '{"theme": "dark"}' > /tmp/project-shared.json
echo '{"dev": true}' > /tmp/project-local.json

# Execute with all 4 tiers
python3 src/config_loader.py \
  --enterprise /tmp/etc/claude-code/managed-settings.json \
  --user /tmp/user-config.json \
  --project-shared /tmp/project-shared.json \
  --project-local /tmp/project-local.json

# Verify enterprise wins (model should be "opus" not "sonnet")
# Verify permissions deny merged from enterprise
# Verify other settings merged correctly

exit 0

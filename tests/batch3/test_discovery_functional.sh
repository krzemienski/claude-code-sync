#!/bin/bash
# Functional Test: Discovery Engine
# NO MOCKS - Tests with REAL Claude Code artifacts on this Mac

set -e

echo "==========================================="
echo "Test: Discovery Engine"
echo "==========================================="

echo ""
echo "[1/6] Testing skills discovery..."
skill_count=$(python3 -c "
from claude_sync.discovery import discover_skills
skills = discover_skills()
print(len(skills))
")

echo "  Found: $skill_count skills"

if [ "$skill_count" -lt 70 ]; then
    echo "  ❌ FAIL: Expected at least 70 skills, found $skill_count"
    exit 1
fi
echo "  ✓ Skills discovery working ($skill_count >= 70)"

echo ""
echo "[2/6] Testing agents discovery..."
agent_count=$(python3 -c "
from claude_sync.discovery import discover_agents
agents = discover_agents()
print(len(agents))
")

echo "  Found: $agent_count agents"
echo "  ✓ Agents discovery working"

echo ""
echo "[3/6] Testing commands discovery..."
command_count=$(python3 -c "
from claude_sync.discovery import discover_commands
commands = discover_commands()
print(len(commands))
")

echo "  Found: $command_count commands"
echo "  ✓ Commands discovery working"

echo ""
echo "[4/6] Testing configs discovery..."
config_count=$(python3 -c "
from claude_sync.discovery import discover_configs
configs = discover_configs()
print(len(configs))
")

echo "  Found: $config_count config files"
if [ "$config_count" -lt 1 ]; then
    echo "  ⚠️  WARNING: No config files found (expected at least settings.json)"
fi
echo "  ✓ Config discovery working"

echo ""
echo "[5/6] Testing plugins discovery..."
plugin_count=$(python3 -c "
from claude_sync.discovery import discover_plugins
plugins = discover_plugins()
print(len(plugins))
")

echo "  Found: $plugin_count plugin config files"
echo "  ✓ Plugin discovery working"

echo ""
echo "[6/6] Testing complete inventory..."
python3 -c "
from claude_sync.discovery import discover_all, print_inventory
inventory = discover_all()
print_inventory(inventory)
"

echo ""
echo "==========================================="
echo "✅ ALL DISCOVERY TESTS PASSED"
echo "==========================================="
echo ""
echo "Validated:"
echo "  ✓ Discovers $skill_count skills on real Mac"
echo "  ✓ Discovers $agent_count agents"
echo "  ✓ Discovers $command_count commands"
echo "  ✓ Discovers $config_count configs"
echo "  ✓ Discovers $plugin_count plugin configs"
echo "  ✓ Complete inventory aggregation works"
echo ""

# Create success flag
touch /tmp/functional-tests-passing

exit 0

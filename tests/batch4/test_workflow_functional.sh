#!/bin/bash
# Functional Test: Complete init→add→commit Workflow
# NO MOCKS - Real Git operations on real filesystem

set -e

echo "==========================================="
echo "Test: Init→Add→Commit Workflow"
echo "==========================================="

# Clean any existing repo
rm -rf ~/.claude-sync
echo "✓ Cleaned existing repository"

echo ""
echo "[1/5] Testing claude-sync init..."
init_output=$(claude-sync init 2>&1)

if [[ ! "$init_output" =~ "Initialized claude-sync repository" ]]; then
    echo "  ❌ FAIL: Init didn't show success message"
    echo "  Output: $init_output"
    exit 1
fi

# Verify directory created
if [ ! -d ~/.claude-sync/repo/.git ]; then
    echo "  ❌ FAIL: Git repository not created"
    exit 1
fi

echo "  ✓ Repository initialized at ~/.claude-sync/"
echo "  ✓ Git repository created"

# Verify discovery ran
if [[ ! "$init_output" =~ "Discovered:" ]]; then
    echo "  ❌ FAIL: Discovery didn't run"
    exit 1
fi

echo "  ✓ Discovery ran successfully"

echo ""
echo "[2/5] Testing claude-sync add --all..."
add_output=$(claude-sync add --all 2>&1)

if [[ ! "$add_output" =~ "Staging complete" ]]; then
    echo "  ❌ FAIL: Add didn't complete"
    echo "  Output: $add_output"
    exit 1
fi

echo "  ✓ All artifacts staged"

# Verify skills were copied to repo
skill_count=$(find ~/.claude-sync/repo/skills -name 'SKILL.md' 2>/dev/null | wc -l | xargs)

if [ "$skill_count" -lt 70 ]; then
    echo "  ❌ FAIL: Expected 70+ skills in repo, found $skill_count"
    exit 1
fi

echo "  ✓ $skill_count skills copied to repository"

# Verify agents were copied
agent_count=$(find ~/.claude-sync/repo/agents -name '*.md' 2>/dev/null | wc -l | xargs)
echo "  ✓ $agent_count agents copied to repository"

echo ""
echo "[3/5] Testing Git status after add..."
cd ~/.claude-sync/repo
git_status=$(git status --short | wc -l | xargs)

if [ "$git_status" -eq 0 ]; then
    echo "  ❌ FAIL: No files staged in Git"
    exit 1
fi

echo "  ✓ Git index has staged files"

echo ""
echo "[4/5] Testing claude-sync commit..."
cd - >/dev/null
commit_output=$(claude-sync commit -m "Test commit" 2>&1)

if [[ ! "$commit_output" =~ "Committed:" ]]; then
    echo "  ❌ FAIL: Commit didn't succeed"
    echo "  Output: $commit_output"
    exit 1
fi

echo "  ✓ Commit created successfully"

# Verify commit exists in Git
cd ~/.claude-sync/repo
commit_count=$(git log --oneline | wc -l | xargs)

if [ "$commit_count" -lt 1 ]; then
    echo "  ❌ FAIL: No commits in Git log"
    exit 1
fi

echo "  ✓ Git log shows $commit_count commit(s)"

echo ""
echo "[5/5] Verifying repository structure..."
cd - >/dev/null

# Check all expected directories exist
dirs=("skills" "agents/user" "commands/user" "config" "plugins")
for dir in "${dirs[@]}"; do
    if [ ! -d ~/.claude-sync/repo/$dir ]; then
        echo "  ❌ FAIL: Directory $dir not created"
        exit 1
    fi
done

echo "  ✓ All required directories created"

echo ""
echo "==========================================="
echo "✅ ALL WORKFLOW TESTS PASSED"
echo "==========================================="
echo ""
echo "Validated:"
echo "  ✓ claude-sync init creates repository"
echo "  ✓ Discovery finds $skill_count skills"
echo "  ✓ claude-sync add stages all artifacts"
echo "  ✓ Git index updated correctly"
echo "  ✓ claude-sync commit creates Git snapshot"
echo "  ✓ Complete workflow: init→add→commit works"
echo ""

# Create success flag
touch /tmp/functional-tests-passing

exit 0

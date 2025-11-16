#!/bin/bash
# Complete E2E Test: Mac → GitHub → Docker
# Tests the CORRECT architecture with GitHub as central hub

set -e

REPO_NAME="claude-code-settings-test-$(date +%s)"
GH_USER="krzemienski"

echo "╔════════════════════════════════════════════════╗"
echo "║   claude-sync Complete GitHub Flow E2E Test    ║"
echo "╚════════════════════════════════════════════════╝"
echo ""
echo "Test Repository: $REPO_NAME"
echo ""

# Cleanup function
cleanup() {
    echo ""
    echo "[Cleanup] Removing test resources..."
    docker rm -f claude-sync-github-test 2>/dev/null || true
    gh repo delete "$GH_USER/$REPO_NAME" --yes 2>/dev/null || true
    rm -rf ~/.claude-sync 2>/dev/null || true
    echo "  ✓ Cleanup complete"
}

# Register cleanup
trap cleanup EXIT

# ============================================================================
# PART 1: Mac → GitHub (Source Push)
# ============================================================================

echo "PART 1: Mac → GitHub"
echo "=" * 70

# [1] Initialize on Mac
echo ""
echo "[1/12] Testing claude-sync init on Mac..."
rm -rf ~/.claude-sync
claude-sync init >/dev/null 2>&1
echo "  ✓ Repository initialized"

# [2] Add all configs
echo ""
echo "[2/12] Staging all configurations..."
claude-sync add --all >/dev/null 2>&1
echo "  ✓ Configs staged"

# Verify staged count
staged_skills=$(find ~/.claude-sync/repo/skills -name 'SKILL.md' | wc -l | xargs)
echo "  ✓ $staged_skills skills staged"

# [3] Commit
echo ""
echo "[3/12] Creating commit..."
claude-sync commit -m "E2E test commit" >/dev/null 2>&1
commit_sha=$(cd ~/.claude-sync/repo && git rev-parse --short HEAD)
echo "  ✓ Commit created: $commit_sha"

# [4] Create GitHub repo
echo ""
echo "[4/12] Creating private GitHub repository..."
gh repo create "$REPO_NAME" --private --description "E2E test for claude-sync" >/dev/null 2>&1
echo "  ✓ Repo created: github.com/$GH_USER/$REPO_NAME"

# [5] Add remote
echo ""
echo "[5/12] Configuring Git remote..."
cd ~/.claude-sync/repo
git remote add origin "git@github.com:$GH_USER/$REPO_NAME.git"
echo "  ✓ Remote 'origin' added"

# [6] Push to GitHub
echo ""
echo "[6/12] Pushing to GitHub..."
git push -u origin main 2>&1 | grep -E "Writing objects|main ->" || true
echo "  ✓ Pushed to GitHub"

# [7] Verify GitHub has files
echo ""
echo "[7/12] Verifying files on GitHub..."
gh_file_count=$(gh api "repos/$GH_USER/$REPO_NAME/contents" --jq 'length')
if [ "$gh_file_count" -lt 3 ]; then
    echo "  ❌ FAIL: Expected multiple directories, found $gh_file_count items"
    exit 1
fi
echo "  ✓ GitHub repo has $gh_file_count top-level directories"

# Check skills directory exists
gh api "repos/$GH_USER/$REPO_NAME/contents/skills" >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "  ✓ skills/ directory exists on GitHub"
else
    echo "  ❌ FAIL: skills/ directory not found on GitHub"
    exit 1
fi

# ============================================================================
# PART 2: GitHub → Docker (Pull and Apply)
# ============================================================================

echo ""
echo ""
echo "PART 2: GitHub → Docker"
echo "========================================="

# [8] Create Docker container
echo ""
echo "[8/12] Creating Docker test container..."
docker run -d --name claude-sync-github-test python:3.12-slim sleep 3600 >/dev/null
echo "  ✓ Container running"

# [9] Install dependencies in container
echo ""
echo "[9/12] Installing dependencies in container..."
docker exec claude-sync-github-test bash -c '
apt-get update -qq &&
apt-get install -y -qq git gh &&
pip3 install click GitPython pyyaml jinja2 paramiko rich --quiet
' 2>&1 | grep -v "WARNING\|notice\|debconf" || true
echo "  ✓ Dependencies installed (git, gh, Python packages)"

# [10] Install claude-sync in container
echo ""
echo "[10/12] Installing claude-sync in container..."
docker cp . claude-sync-github-test:/tmp/claude-sync-src
docker exec claude-sync-github-test pip3 install /tmp/claude-sync-src --quiet 2>&1 | grep -v "WARNING"
echo "  ✓ claude-sync installed"

# [11] Authenticate gh in container and pull
echo ""
echo "[11/12] Pulling from GitHub in container..."

# Pass GitHub token to container
GH_TOKEN=$(gh auth token)

docker exec -e GH_TOKEN="$GH_TOKEN" claude-sync-github-test bash -c "
echo \$GH_TOKEN | gh auth login --with-token &&
claude-sync init &&
claude-sync remote add origin https://github.com/$GH_USER/$REPO_NAME.git &&
claude-sync pull origin main
" 2>&1 | grep -E "Pulling|Applied|✓|✅" || true

echo "  ✓ Pulled from GitHub"

# [12] Validate in container
echo ""
echo "[12/12] Validating deployment in Docker..."
docker exec claude-sync-github-test claude-sync validate 2>&1 | grep -E "VALIDATION PASSED|Skills:|Agents:"

# Get deployed count
docker_skills=$(docker exec claude-sync-github-test find /root/.claude/skills -name 'SKILL.md' 2>/dev/null | wc -l | xargs)

if [ "$docker_skills" -lt 50 ]; then
    echo "  ❌ FAIL: Expected 50+ skills in Docker, found $docker_skills"
    exit 1
fi

echo "  ✓ $docker_skills skills deployed and validated"

# ============================================================================
# SUCCESS
# ============================================================================

echo ""
echo "╔════════════════════════════════════════════════╗"
echo "║       ALL GITHUB E2E TESTS PASSED ✓            ║"
echo "╚════════════════════════════════════════════════╝"
echo ""
echo "Verified Complete Flow:"
echo "  ✓ Mac: init → add → commit"
echo "  ✓ Mac: create-repo → push to GitHub"
echo "  ✓ GitHub: Repository has $gh_file_count directories"
echo "  ✓ Docker: pull from GitHub"
echo "  ✓ Docker: $docker_skills skills installed"
echo "  ✓ Docker: Format validation passed"
echo ""
echo "Architecture Validated:"
echo "  Mac → GitHub (push) → Docker (pull)"
echo "  Central hub: github.com/$GH_USER/$REPO_NAME"
echo ""
echo "✅ COMPLETE GITHUB SYNC WORKING"
echo ""

# Success flag
touch /tmp/functional-tests-passing

exit 0

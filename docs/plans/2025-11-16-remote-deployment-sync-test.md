# Remote Deployment and Cross-Machine Sync Test Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deploy claude-code-sync to remote Linux machine, sync configs/skills/MCPs from Mac, validate Claude can access everything

**Remote Machine**:
- Host: home.hack.ski
- Port: 22
- User: nick
- Password: Usmc12345!
- OS: Linux

**Source Machine**: macOS (current)

**Architecture:** SSH-based deployment with intelligent cross-platform sync (configs, skills, MCPs) and path validation

**Tech Stack:** SSH/scp, git, Python 3.11+, bash

**Estimated Duration:** 30-40 hours (including debugging iterations)

**Expectation**: Things WILL break. Plan includes debugging and retry steps.

---

## Phase 1: SSH Connection and Environment Validation (2-3 hours)

### Task 1.1: Test SSH Connection

**Step 1: Test basic SSH connectivity**

```bash
# Test SSH connection
sshpass -p 'Usmc12345!' ssh -p 22 -o StrictHostKeyChecking=no nick@home.hack.ski "echo 'SSH connection successful'"
```

**Expected**: "SSH connection successful"
**If fails**: Check network, firewall, credentials

**Step 2: Verify sshpass installed**

```bash
# Check if sshpass available on Mac
which sshpass || brew install hudochenkov/sshpass/sshpass
```

**Step 3: Test with actual command**

```bash
# Run command on remote
sshpass -p 'Usmc12345!' ssh -p 22 nick@home.hack.ski "uname -a; python3 --version"
```

**Expected Output**:
```
Linux ... (kernel version)
Python 3.x.x
```

**If Python missing**: Install Python 3.11+ on Linux first

**Step 4: Create SSH alias for convenience**

```bash
# Add to local script
cat > /tmp/ssh-remote.sh <<'EOF'
#!/bin/bash
sshpass -p 'Usmc12345!' ssh -p 22 -o StrictHostKeyChecking=no nick@home.hack.ski "$@"
EOF

chmod +x /tmp/ssh-remote.sh

# Test
/tmp/ssh-remote.sh "hostname"
```

**Expected**: home.hack.ski (or similar)

---

### Task 1.2: Validate Remote Environment

**Step 1: Check Python version**

```bash
/tmp/ssh-remote.sh "python3 --version"
```

**Expected**: Python 3.11+ (required for modern type hints)
**If <3.11**: Install Python 3.11 or adjust code for compatibility

**Step 2: Check pip availability**

```bash
/tmp/ssh-remote.sh "python3 -m pip --version"
```

**If missing**: Install pip

**Step 3: Check git availability**

```bash
/tmp/ssh-remote.sh "git --version"
```

**If missing**: `sudo apt install git` (on Linux)

**Step 4: Check disk space**

```bash
/tmp/ssh-remote.sh "df -h ~"
```

**Expected**: At least 100MB free for installation

**Step 5: Check home directory structure**

```bash
/tmp/ssh-remote.sh "ls -la ~ | head -20"
```

**Verify**: Can write to home directory

---

## Phase 2: Clone and Install on Remote Linux (1-2 hours)

### Task 2.1: Clone Repository on Remote

**Step 1: Clone from GitHub**

```bash
/tmp/ssh-remote.sh "cd ~ && git clone https://github.com/krzemienski/claude-code-sync.git"
```

**Expected**: Repository cloned successfully

**Step 2: Verify clone**

```bash
/tmp/ssh-remote.sh "ls -la ~/claude-code-sync/src/"
```

**Expected**: Should list Python modules (config_loader.py, cli.py, etc.)

**If fails**: Check git access, network connectivity

**Step 3: Check Python dependencies**

```bash
/tmp/ssh-remote.sh "cd ~/claude-code-sync && cat requirements.txt"
```

**Expected**: Should show aiohttp dependency

---

### Task 2.2: Install Dependencies on Remote

**Step 1: Install aiohttp**

```bash
/tmp/ssh-remote.sh "python3 -m pip install aiohttp --user"
```

**Expected**: Successfully installed

**Step 2: Verify installation**

```bash
/tmp/ssh-remote.sh "python3 -c 'import aiohttp; print(aiohttp.__version__)'"
```

**Expected**: Version number (e.g., 3.9.x)

**Step 3: Test basic import of our code**

```bash
/tmp/ssh-remote.sh "cd ~/claude-code-sync && python3 -c 'from src.config_loader import load_config; print(\"✅ Import works\")'"
```

**Expected**: "✅ Import works"
**If fails**: Check Python path, permissions

---

### Task 2.3: Test Basic CLI on Remote

**Step 1: Run CLI with simple command**

```bash
/tmp/ssh-remote.sh "cd ~/claude-code-sync && python3 -m src.cli --message 'Remote test' 2>&1"
```

**Expected**:
- Session created: <uuid>
- Session file: /home/nick/.config/claude/projects/<hash>/<date>.jsonl
- ✅ CLI execution complete

**If fails**: Debug output, check permissions, verify paths

**Step 2: Verify session file created on remote**

```bash
/tmp/ssh-remote.sh "ls -lh ~/.config/claude/projects/*/2025-11-16.jsonl"
```

**Expected**: File exists with size >0 bytes

**Step 3: Read session content on remote**

```bash
/tmp/ssh-remote.sh "cat ~/.config/claude/projects/*/2025-11-16.jsonl | head -5"
```

**Expected**: JSON lines with "Remote test" message

---

## Phase 3: Sync Configurations Mac → Linux (3-4 hours)

### Task 3.1: Create Sync Script for Configs

**Files:**
- Create: `scripts/sync-to-remote.sh`

**Step 1: Write sync script**

```bash
cat > scripts/sync-to-remote.sh <<'EOF'
#!/bin/bash
# Sync claude-code-sync configs from Mac to Linux

set -e

REMOTE_HOST="home.hack.ski"
REMOTE_PORT="22"
REMOTE_USER="nick"
REMOTE_PASS="Usmc12345!"

echo "================================================"
echo "Claude Code Sync: Mac → Linux"
echo "================================================"

# Helper function for SSH
remote_ssh() {
    sshpass -p "$REMOTE_PASS" ssh -p "$REMOTE_PORT" -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" "$@"
}

# Helper function for SCP
remote_scp() {
    sshpass -p "$REMOTE_PASS" scp -P "$REMOTE_PORT" -o StrictHostKeyChecking=no "$@"
}

echo "Step 1: Create remote .config/claude directory"
remote_ssh "mkdir -p ~/.config/claude"

echo "Step 2: Sync .claude project settings"
if [ -d ".claude" ]; then
    remote_scp -r .claude "$REMOTE_USER@$REMOTE_HOST:~/claude-code-sync/"
    echo "✅ .claude synced"
else
    echo "⚠️  No .claude directory to sync"
fi

echo "Step 3: Sync CLAUDE.md"
if [ -f "CLAUDE.md" ]; then
    remote_scp CLAUDE.md "$REMOTE_USER@$REMOTE_HOST:~/claude-code-sync/"
    echo "✅ CLAUDE.md synced"
fi

echo "Step 4: Sync .mcp.json"
if [ -f ".mcp.json" ]; then
    remote_scp .mcp.json "$REMOTE_USER@$REMOTE_HOST:~/claude-code-sync/"
    echo "✅ .mcp.json synced"
fi

echo "================================================"
echo "Config sync complete"
echo "================================================"
EOF

chmod +x scripts/sync-to-remote.sh
```

**Step 2: Run sync script**

```bash
cd /Users/nick/Desktop/claude-code-sync
./scripts/sync-to-remote.sh
```

**Expected**: All config files copied to remote

**Step 3: Verify configs on remote**

```bash
/tmp/ssh-remote.sh "ls -la ~/claude-code-sync/.claude/ ~/claude-code-sync/CLAUDE.md ~/claude-code-sync/.mcp.json"
```

**Expected**: All files present on remote

---

### Task 3.2: Sync Skills Directory

**Step 1: Count skills on Mac**

```bash
find ~/.claude/skills -name "SKILL.md" | wc -l
```

**Expected**: ~80 skills

**Step 2: Create skills sync script**

```bash
cat > scripts/sync-skills.sh <<'EOF'
#!/bin/bash
# Sync skills from Mac to Linux

set -e

REMOTE_HOST="home.hack.ski"
REMOTE_PORT="22"
REMOTE_USER="nick"
REMOTE_PASS="Usmc12345!"

echo "Syncing skills to remote..."

# Create remote skills directory
sshpass -p "$REMOTE_PASS" ssh -p "$REMOTE_PORT" -o StrictHostKeyChecking=no \
    "$REMOTE_USER@$REMOTE_HOST" "mkdir -p ~/.claude/skills"

# Sync entire skills directory
sshpass -p "$REMOTE_PASS" scp -P "$REMOTE_PORT" -r -o StrictHostKeyChecking=no \
    ~/.claude/skills/* "$REMOTE_USER@$REMOTE_HOST:~/.claude/skills/"

echo "✅ Skills synced"
EOF

chmod +x scripts/sync-skills.sh
```

**Step 3: Run skills sync**

```bash
./scripts/sync-skills.sh
```

**Step 4: Verify skills on remote**

```bash
/tmp/ssh-remote.sh "find ~/.claude/skills -name 'SKILL.md' | wc -l"
```

**Expected**: ~80 (same count as Mac)

**Step 5: Test specific skill exists**

```bash
/tmp/ssh-remote.sh "cat ~/.claude/skills/using-shannon/SKILL.md | head -20"
```

**Expected**: Should show skill content

---

### Task 3.3: Sync MCP Server Configurations

**Step 1: Check Mac's MCP config**

```bash
ls -la ~/.config/claude/settings.json ~/.claude.json 2>/dev/null || echo "No user-level MCP configs"
```

**Step 2: Create MCP sync script**

```bash
cat > scripts/sync-mcp-configs.sh <<'EOF'
#!/bin/bash
# Sync MCP configurations

REMOTE_HOST="home.hack.ski"
REMOTE_PORT="22"
REMOTE_USER="nick"
REMOTE_PASS="Usmc12345!"

remote_scp() {
    sshpass -p "$REMOTE_PASS" scp -P "$REMOTE_PORT" -o StrictHostKeyChecking=no "$@"
}

# Sync user-level Claude config (if exists)
if [ -f ~/.config/claude/settings.json ]; then
    remote_scp ~/.config/claude/settings.json "$REMOTE_USER@$REMOTE_HOST:~/.config/claude/"
    echo "✅ User settings.json synced"
fi

# Sync legacy .claude.json (if exists)
if [ -f ~/.claude.json ]; then
    remote_scp ~/.claude.json "$REMOTE_USER@$REMOTE_HOST:~/"
    echo "✅ .claude.json synced"
fi

echo "✅ MCP configs synced"
EOF

chmod +x scripts/sync-mcp-configs.sh
```

**Step 3: Run MCP sync**

```bash
./scripts/sync-mcp-configs.sh
```

**Step 4: Verify on remote**

```bash
/tmp/ssh-remote.sh "cat ~/.config/claude/settings.json 2>/dev/null | python3 -c 'import sys, json; print(\"MCP servers:\", len(json.load(sys.stdin).get(\"mcpServers\", {})))'"
```

---

## Phase 4: Project Path Validation and Intelligent Sync (4-5 hours)

### Task 4.1: Discover Projects on Mac

**Step 1: Find Serena project list**

```bash
# From Serena memory (if available)
python3 -c "
# Serena project list from earlier:
projects = ['ClaudeCodeUI-iOS', 'RepoNexus-iOS', 'capture-analyzer', 'ccflare',
            'claude-code-monorepo', 'claude-mobile-expo', 'happy', 'happy-server',
            'ios', 'opcode-mobile', 'playback-cut', 'repo-nexus', 'reponexus-vc',
            'shannon', 'shannon-cli', 'shannon-framework', 'shannon-ios', 'shortsplit',
            'yt-transition-shorts-detector']

print('\\n'.join(projects))
" > /tmp/mac-projects.txt

cat /tmp/mac-projects.txt
```

**Step 2: Find actual project paths on Mac**

```bash
# Try to locate projects
cat > scripts/find-project-paths.sh <<'EOF'
#!/bin/bash
# Find actual paths for Serena projects on Mac

while IFS= read -r project_name; do
    # Common search locations
    for base in ~/Desktop ~/Documents ~/Projects ~/work ~/src; do
        if [ -d "$base/$project_name" ]; then
            echo "$project_name:$base/$project_name"
            break
        fi
    done
done < /tmp/mac-projects.txt > /tmp/mac-project-paths.txt

cat /tmp/mac-project-paths.txt
echo "Found $(wc -l < /tmp/mac-project-paths.txt) project paths"
EOF

chmod +x scripts/find-project-paths.sh
./scripts/find-project-paths.sh
```

**Expected**: List of project_name:path pairs

---

### Task 4.2: Validate Project Paths on Linux

**Step 1: Check if Mac paths exist on Linux**

```bash
cat > scripts/validate-remote-paths.sh <<'EOF'
#!/bin/bash
# Validate which Mac project paths exist on Linux

REMOTE_HOST="home.hack.ski"
REMOTE_PORT="22"
REMOTE_USER="nick"
REMOTE_PASS="Usmc12345!"

remote_ssh() {
    sshpass -p "$REMOTE_PASS" ssh -p "$REMOTE_PORT" -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" "$@"
}

echo "Checking project paths on remote..."

while IFS=: read -r project_name project_path; do
    # Check if path exists on remote
    if remote_ssh "[ -d '$project_path' ]" 2>/dev/null; then
        echo "✅ $project_name: $project_path EXISTS on remote"
        echo "$project_name:$project_path" >> /tmp/remote-valid-paths.txt
    else
        echo "❌ $project_name: $project_path MISSING on remote"
        echo "$project_name:$project_path" >> /tmp/remote-missing-paths.txt
    fi
done < /tmp/mac-project-paths.txt

echo ""
echo "Valid paths: $(wc -l < /tmp/remote-valid-paths.txt 2>/dev/null || echo 0)"
echo "Missing paths: $(wc -l < /tmp/remote-missing-paths.txt 2>/dev/null || echo 0)"
EOF

chmod +x scripts/validate-remote-paths.sh
./scripts/validate-remote-paths.sh
```

**Expected**: Most paths will be MISSING (different machines)

**Step 2: Prompt user about missing paths**

```bash
if [ -f /tmp/remote-missing-paths.txt ]; then
    echo ""
    echo "⚠️  WARNING: Projects with missing paths on remote:"
    cat /tmp/remote-missing-paths.txt
    echo ""
    echo "These projects will NOT be synced (paths don't exist on Linux)"
    echo "Skills, configs, and MCPs WILL be synced (portable)"
    echo ""
    read -p "Continue with portable sync only? (yes/no): " response
    [ "$response" = "yes" ] || exit 1
fi
```

**Expected**: User confirms to continue

---

## Phase 5: Intelligent Cross-Machine Sync (5-6 hours)

### Task 5.1: Create Smart Sync Script

**Files:**
- Create: `scripts/smart-sync.sh` (complete Mac→Linux sync with path validation)

**Step 1: Write comprehensive sync script**

```bash
cat > scripts/smart-sync.sh <<'EOF'
#!/bin/bash
# Smart Sync: Mac → Linux (portable items only)

set -e

REMOTE_HOST="home.hack.ski"
REMOTE_PORT="22"
REMOTE_USER="nick"
REMOTE_PASS="Usmc12345!"

remote_ssh() {
    sshpass -p "$REMOTE_PASS" ssh -p "$REMOTE_PORT" -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" "$@"
}

remote_scp() {
    sshpass -p "$REMOTE_PASS" scp -P "$REMOTE_PORT" -o StrictHostKeyChecking=no "$@"
}

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     Claude Code Smart Sync: Mac → Linux                     ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# 1. Sync Skills (PORTABLE)
echo "[1/5] Syncing skills..."
remote_ssh "mkdir -p ~/.claude/skills"
scp -P "$REMOTE_PORT" -r -o StrictHostKeyChecking=no \
    ~/.claude/skills/* "$REMOTE_USER@$REMOTE_HOST:~/.claude/skills/" 2>/dev/null || echo "No skills to sync"
SKILL_COUNT=$(remote_ssh "find ~/.claude/skills -name 'SKILL.md' | wc -l")
echo "✅ Skills synced: $SKILL_COUNT skills"

# 2. Sync Global Config (PORTABLE)
echo "[2/5] Syncing global configuration..."
remote_ssh "mkdir -p ~/.config/claude"
if [ -f ~/.config/claude/settings.json ]; then
    remote_scp ~/.config/claude/settings.json "$REMOTE_USER@$REMOTE_HOST:~/.config/claude/"
    echo "✅ Global settings.json synced"
fi

# 3. Sync Project Settings (PORTABLE)
echo "[3/5] Syncing project settings..."
remote_scp -r .claude "$REMOTE_USER@$REMOTE_HOST:~/claude-code-sync/" 2>/dev/null
remote_scp CLAUDE.md "$REMOTE_USER@$REMOTE_HOST:~/claude-code-sync/"
remote_scp .mcp.json "$REMOTE_USER@$REMOTE_HOST:~/claude-code-sync/"
echo "✅ Project configs synced"

# 4. Skip Project Paths (NOT PORTABLE)
echo "[4/5] Validating project paths..."
echo "⚠️  Skipping project-specific paths (different machines)"
echo "   Projects are machine-specific and won't be synced"

# 5. Sync MCP Server Configs (PORTABLE with env var substitution)
echo "[5/5] MCP configurations..."
echo "✅ MCP servers configured in .mcp.json (portable)"
echo "   Note: Environment variables (${GITHUB_TOKEN}, etc.) must be set on remote"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    Sync Complete                             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Synced (PORTABLE):"
echo "  ✓ $SKILL_COUNT skills"
echo "  ✓ Global configs"
echo "  ✓ Project settings (.claude, CLAUDE.md, .mcp.json)"
echo "  ✓ MCP server definitions"
echo ""
echo "NOT Synced (MACHINE-SPECIFIC):"
echo "  ✗ Project file paths (use different paths on Linux)"
echo "  ✗ Environment variables (set separately on Linux)"
echo "  ✗ SSH keys (machine-specific credentials)"
echo ""
EOF

chmod +x scripts/smart-sync.sh
```

**Step 2: Run smart sync**

```bash
./scripts/smart-sync.sh
```

**Expected**: All portable items synced, machine-specific skipped with warnings

**Step 3: Verify sync on remote**

```bash
/tmp/ssh-remote.sh "
echo 'Skills:' && find ~/.claude/skills -name 'SKILL.md' | wc -l
echo 'Global config:' && [ -f ~/.config/claude/settings.json ] && echo 'EXISTS' || echo 'MISSING'
echo 'Project config:' && [ -f ~/claude-code-sync/CLAUDE.md ] && echo 'EXISTS' || echo 'MISSING'
echo 'MCP config:' && [ -f ~/claude-code-sync/.mcp.json ] && echo 'EXISTS' || echo 'MISSING'
"
```

**Expected**:
- Skills: ~80
- Global config: EXISTS
- Project config: EXISTS
- MCP config: EXISTS

---

## Phase 6: Headless Claude Testing on Remote (6-8 hours)

### Task 6.1: Test Skills Are Visible to Claude

**Step 1: Create skill discovery test on remote**

```bash
# Create test script on remote
cat > /tmp/test-skills-remote.sh <<'EOF'
#!/bin/bash
# Test if Claude can see skills on Linux

cd ~/claude-code-sync

# Simulate Claude skill discovery
echo "Testing skill discovery..."

# Count SKILL.md files
SKILL_COUNT=$(find ~/.claude/skills -name "SKILL.md" -type f | wc -l)
echo "Skills found: $SKILL_COUNT"

# Test specific critical skills
CRITICAL_SKILLS=(
    "using-shannon"
    "spec-analysis"
    "wave-orchestration"
    "functional-testing"
    "test-driven-development"
)

for skill in "${CRITICAL_SKILLS[@]}"; do
    if [ -f ~/.claude/skills/$skill/SKILL.md ]; then
        echo "✅ $skill: FOUND"
    else
        echo "❌ $skill: MISSING"
        exit 1
    fi
done

echo "✅ All critical skills available"
EOF

# Copy to remote
scp -P 22 -o StrictHostKeyChecking=no /tmp/test-skills-remote.sh nick@home.hack.ski:/tmp/
```

**Step 2: Execute test on remote**

```bash
/tmp/ssh-remote.sh "bash /tmp/test-skills-remote.sh"
```

**Expected**: All critical skills FOUND

**If missing**: Debug scp transfer, check paths

---

### Task 6.2: Test Claude Can Load Configs

**Step 1: Test config loading on remote**

```bash
/tmp/ssh-remote.sh "cd ~/claude-code-sync && python3 -c '
from src.config_loader import load_config

# Load config (should use .claude/settings.json)
config = load_config(project_shared_path=\".claude/settings.json\")

# Verify config loaded
assert \"model\" in config
assert \"permissions\" in config

print(\"✅ Config loads successfully on remote\")
print(f\"   Model: {config.get(\\\"model\\\")}\")
print(f\"   Permissions: {len(config.get(\\\"permissions\\\", {}).get(\\\"allow\\\", []))} allowed tools\")
'"
```

**Expected**: Config loads with model and permissions

---

### Task 6.3: Test MCP Server Discovery

**Step 1: Test .mcp.json parsing on remote**

```bash
/tmp/ssh-remote.sh "cd ~/claude-code-sync && python3 -c '
import json

# Load .mcp.json
with open(\".mcp.json\") as f:
    mcp_config = json.load(f)

servers = mcp_config.get(\"mcpServers\", {})
print(f\"✅ MCP config loaded\")
print(f\"   Servers configured: {len(servers)}\")
for name in list(servers.keys())[:5]:
    print(f\"   - {name}\")
'"
```

**Expected**: 9 MCP servers listed

---

### Task 6.4: Test Headless CLI Execution

**Step 1: Run CLI command remotely**

```bash
/tmp/ssh-remote.sh "cd ~/claude-code-sync && python3 -m src.cli --message 'Headless test from remote' 2>&1"
```

**Expected**:
- Session created
- JSONL file written
- Message logged

**Step 2: Verify session persisted**

```bash
/tmp/ssh-remote.sh "cat ~/.config/claude/projects/*/2025-11-16.jsonl | grep 'Headless test'"
```

**Expected**: Message found in JSONL

---

## Phase 7: Complete Integration Test (3-4 hours)

### Task 7.1: End-to-End Workflow Test

**Step 1: Create comprehensive E2E test**

```bash
cat > scripts/remote-e2e-test.sh <<'EOF'
#!/bin/bash
# Complete E2E test on remote Linux machine

set -e

REMOTE_HOST="home.hack.ski"
REMOTE_PORT="22"
REMOTE_USER="nick"
REMOTE_PASS="Usmc12345!"

remote_ssh() {
    sshpass -p "$REMOTE_PASS" ssh -p "$REMOTE_PORT" -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" "$@"
}

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║          Remote E2E Integration Test                         ║"
echo "╚══════════════════════════════════════════════════════════════╝"

# Test 1: Skills available
echo "[Test 1] Skills available?"
SKILLS=$(remote_ssh "find ~/.claude/skills -name 'SKILL.md' | wc -l")
echo "   Skills: $SKILLS"
[ "$SKILLS" -gt 70 ] || (echo "❌ FAIL: Not enough skills" && exit 1)
echo "   ✅ PASS"

# Test 2: Configs loaded
echo "[Test 2] Configs loadable?"
remote_ssh "cd ~/claude-code-sync && python3 -c 'from src.config_loader import load_config; c=load_config(); print(\"✅ Config loads\")'" || (echo "❌ FAIL" && exit 1)
echo "   ✅ PASS"

# Test 3: CLI functional
echo "[Test 3] CLI creates sessions?"
SESSION_OUTPUT=$(remote_ssh "cd ~/claude-code-sync && python3 -m src.cli --message 'E2E test' 2>&1")
echo "$SESSION_OUTPUT" | grep -q "Session created" || (echo "❌ FAIL" && exit 1)
echo "   ✅ PASS"

# Test 4: Session persisted
echo "[Test 4] Session file exists?"
remote_ssh "ls ~/.config/claude/projects/*/2025-11-16.jsonl" >/dev/null || (echo "❌ FAIL" && exit 1)
echo "   ✅ PASS"

# Test 5: MCP configs present
echo "[Test 5] MCP servers configured?"
MCP_COUNT=$(remote_ssh "cd ~/claude-code-sync && python3 -c 'import json; print(len(json.load(open(\\\".mcp.json\\\")).get(\\\"mcpServers\\\", {})))'")
echo "   MCP servers: $MCP_COUNT"
[ "$MCP_COUNT" -ge 6 ] || (echo "❌ FAIL" && exit 1)
echo "   ✅ PASS"

# Test 6: CLAUDE.md accessible
echo "[Test 6] CLAUDE.md present?"
remote_ssh "[ -f ~/claude-code-sync/CLAUDE.md ]" || (echo "❌ FAIL" && exit 1)
echo "   ✅ PASS"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║            ALL TESTS PASSED                                  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Remote Linux machine is fully configured:"
echo "  ✓ Skills synced and discoverable"
echo "  ✓ Configs loaded correctly"
echo "  ✓ CLI functional (creates sessions)"
echo "  ✓ Sessions persist to JSONL"
echo "  ✓ MCP servers configured"
echo "  ✓ Project memory (CLAUDE.md) available"
echo ""
echo "✅ REMOTE DEPLOYMENT SUCCESSFUL"
EOF

chmod +x scripts/remote-e2e-test.sh
```

**Step 2: Run complete E2E test**

```bash
./scripts/remote-e2e-test.sh
```

**Expected**: All 6 tests PASS

**If any fail**: Debug specific failure, fix, retry

---

## Phase 8: Iterative Debugging and Fixes (8-12 hours buffer)

### Task 8.1: Common Failure Scenarios and Fixes

**Scenario 1: Permission Denied on Remote**

**Symptom**: `scp: permission denied` or `mkdir: cannot create directory`

**Fix**:
```bash
# Check remote permissions
/tmp/ssh-remote.sh "ls -ld ~"

# Fix if needed
/tmp/ssh-remote.sh "chmod 755 ~"
```

---

**Scenario 2: Python Import Errors on Remote**

**Symptom**: `ModuleNotFoundError: No module named 'src'`

**Fix**:
```bash
# Check PYTHONPATH
/tmp/ssh-remote.sh "cd ~/claude-code-sync && python3 -c 'import sys; print(sys.path)'"

# Run with explicit path
/tmp/ssh-remote.sh "cd ~/claude-code-sync && PYTHONPATH=. python3 -m src.cli --message 'test'"
```

---

**Scenario 3: Skills Not Discovered**

**Symptom**: Skill count = 0 on remote

**Fix**:
```bash
# Verify scp completed
/tmp/ssh-remote.sh "ls -la ~/.claude/skills/ | head -20"

# Re-sync if needed
./scripts/sync-skills.sh

# Verify again
/tmp/ssh-remote.sh "find ~/.claude/skills -name 'SKILL.md' | wc -l"
```

---

**Scenario 4: Config File Not Found**

**Symptom**: `FileNotFoundError: .claude/settings.json`

**Fix**:
```bash
# Check file exists
/tmp/ssh-remote.sh "ls -la ~/claude-code-sync/.claude/"

# Re-sync configs
./scripts/sync-to-remote.sh

# Verify
/tmp/ssh-remote.sh "cat ~/claude-code-sync/.claude/settings.json | python3 -m json.tool"
```

---

**Scenario 5: aiohttp Missing on Remote**

**Symptom**: `ModuleNotFoundError: No module named 'aiohttp'`

**Fix**:
```bash
# Install on remote
/tmp/ssh-remote.sh "python3 -m pip install aiohttp --user"

# Verify
/tmp/ssh-remote.sh "python3 -c 'import aiohttp; print(aiohttp.__version__)'"
```

---

## Summary

**Total Tasks**: 30+ bite-sized tasks
**Total Time**: 30-40 hours (including debugging)
**Approach**: Deploy → Sync → Validate → Test → Debug → Iterate

**Critical Success Factors**:
1. SSH connection stable
2. Python 3.11+ on remote
3. Skills sync correctly (portable)
4. Configs sync correctly (portable)
5. Path mismatches handled gracefully (skip project-specific)
6. Headless CLI execution works
7. Claude can discover skills/configs on remote

**All tasks follow**:
- ✅ Test-first (try → verify → fix if broken)
- ✅ Functional validation (real SSH commands, real file verification)
- ✅ Iterative debugging (expect failures, have fixes ready)
- ✅ Bite-sized (2-5 min per step)

---

**Plan saved to:** `docs/plans/2025-11-16-remote-deployment-sync-test.md`

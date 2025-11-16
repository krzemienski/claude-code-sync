# GitHub Integration Plan for claude-sync

**Status**: CRITICAL ARCHITECTURE FIX
**Context**: Initial implementation used direct Docker deployment. User requires GitHub as central hub.

---

## ❌ What Was Wrong

**My Implementation**:
```
Mac → docker cp bundle → Docker container
```
- Direct deployment via Docker API
- No GitHub involved
- Each machine deployed to separately

**Problem**:
- Not scalable (need to deploy to each machine)
- No central source of truth
- Can't sync back from remote machines
- Not what user wanted

---

## ✅ Correct Architecture

**User's Requirement**:
```
Mac → GitHub (push) ← Docker/Linux (pull)
```

**Flow**:
1. Mac: Discover and stage configs
2. Mac: Push to private GitHub repo
3. GitHub: Stores all configs (skills, agents, MCPs, settings with secrets)
4. Docker/Linux: Pull from GitHub
5. Docker/Linux: Apply to ~/.claude/skills/
6. Validation: Format check proves Claude Code can use them

**Central Hub**: GitHub repo (private, can include secrets)

---

## 🎯 Implementation Tasks

### Batch 6: GitHub Integration (3-4 hours)

#### Task 6.1: Create-Repo Command
**Purpose**: Create private GitHub repository for configs

```bash
claude-sync create-repo --name claude-code-settings --private
```

**Implementation**:
- Use `gh` CLI to create repo (already installed on Mac)
- Returns: git@github.com:user/claude-code-settings.git
- Stores in remotes.json
- Auto-adds as 'origin' remote

**Test**:
```bash
gh repo list | grep claude-code-settings
# Should show newly created repo
```

#### Task 6.2: Remote Command
**Purpose**: Manage Git remotes

```bash
claude-sync remote add origin git@github.com:user/repo.git
claude-sync remote list
claude-sync remote remove origin
```

**Implementation**:
- Use GitPython: `repo.create_remote(name, url)`
- Store in Git config (standard Git remote)
- Also track in remotes.json for metadata

**Test**:
```bash
cd ~/.claude-sync/repo && git remote -v
# Should show origin
```

#### Task 6.3: Push to Git Remote
**Purpose**: Push configs to GitHub

```bash
claude-sync push origin main
```

**Implementation**:
- Use GitPython: `repo.remote('origin').push('main')`
- Handles authentication via SSH keys or gh CLI
- Progress reporting

**Test**:
```bash
# After push
gh repo view user/claude-code-settings
# Should show pushed files
```

### Batch 7: Pull and Conflict Resolution (4-5 hours)

#### Task 7.1: Pull Command
**Purpose**: Pull configs from GitHub

```bash
claude-sync pull origin main
claude-sync pull origin main --strategy overwrite
claude-sync pull origin main --strategy keep-local
```

**Implementation**:
- GitPython: `repo.remote('origin').pull('main')`
- Detect merge conflicts
- Apply conflict resolution strategy

**Test**:
```bash
# In fresh Docker container
claude-sync pull origin main
# Should download all configs
```

#### Task 7.2: Conflict Detection
**Purpose**: Detect when local configs exist

**Implementation**:
```python
def detect_conflicts():
    local_skills = set(~/.claude/skills/)
    repo_skills = set(~/.claude-sync/repo/skills/)

    conflicts = local_skills & repo_skills  # Intersection
    new_from_repo = repo_skills - local_skills
    local_only = local_skills - repo_skills

    return conflicts, new_from_repo, local_only
```

#### Task 7.3: Conflict Resolution Strategies
**Strategies**:
- `keep-local`: Don't overwrite existing configs
- `overwrite`: Replace local with repo version
- `merge`: Keep both (repo version gets suffix)
- `ask`: Prompt for each conflict

### Batch 8: E2E GitHub Flow (2-3 hours)

#### Task 8.1: Create E2E Test Script
**Test Flow**:
```bash
#!/bin/bash
# test_e2e_github_flow.sh

# [1] Mac: Init and stage
claude-sync init
claude-sync add --all

# [2] Mac: Create GitHub repo (using gh CLI)
gh repo create claude-code-settings-test --private

# [3] Mac: Add remote and push
claude-sync remote add origin git@github.com:USER/claude-code-settings-test.git
claude-sync push origin main

# [4] Verify GitHub has files
gh api repos/USER/claude-code-settings-test/contents/skills --jq 'length'
# Should show 117 (or number of skills)

# [5] Docker: Install and init
docker exec test-container pip install claude-sync
docker exec test-container claude-sync init

# [6] Docker: Add remote and pull
docker exec test-container claude-sync remote add origin https://...
docker exec test-container claude-sync pull origin main

# [7] Docker: Apply configs
docker exec test-container claude-sync apply

# [8] Docker: Validate
docker exec test-container claude-sync validate
# Format validation proves Claude Code can use them

# Cleanup
gh repo delete USER/claude-code-settings-test --yes
```

#### Task 8.2: Authentication in Docker
**Problem**: Docker needs GitHub access for pulling

**Solutions**:
1. Pass GitHub token as env var: `GITHUB_TOKEN`
2. Use HTTPS URLs with embedded token
3. Use gh CLI in container: `gh auth login --with-token`

**Implementation**: Option 3 (gh CLI)
```bash
docker exec -e GITHUB_TOKEN=$GITHUB_TOKEN container \
  bash -c 'echo $GITHUB_TOKEN | gh auth login --with-token'

docker exec container claude-sync pull origin main
# Uses gh auth
```

---

## 🔧 Updated Commands

### claude-sync create-repo
```bash
claude-sync create-repo [--name NAME] [--private]

Creates private GitHub repository and configures as 'origin' remote.
Requires: gh CLI authenticated (gh auth login)
```

### claude-sync remote
```bash
claude-sync remote add <name> <url>     # Add Git remote
claude-sync remote remove <name>        # Remove remote
claude-sync remote list                 # List remotes
claude-sync remote show <name>          # Show remote details
```

### claude-sync push
```bash
claude-sync push origin [branch]        # Push to GitHub
claude-sync push docker://container     # Direct Docker deploy (legacy)
```

### claude-sync pull (NEW)
```bash
claude-sync pull origin [branch]                    # Pull and apply
claude-sync pull origin --strategy overwrite        # Overwrite local
claude-sync pull origin --strategy keep-local       # Keep local versions
claude-sync pull origin --no-apply                  # Pull but don't apply
```

---

## 📋 Implementation Checklist

### Batch 6: GitHub Integration
- [ ] Implement `github_ops.py` with gh CLI functions
- [ ] Add `create-repo` command to CLI
- [ ] Implement `remote` command (add/remove/list)
- [ ] Update `push` to support Git remotes
- [ ] Test: Mac → GitHub push
- [ ] Commit

### Batch 7: Pull Operations
- [ ] Implement `pull` command
- [ ] Add conflict detection
- [ ] Implement resolution strategies
- [ ] Update `apply` to handle conflicts
- [ ] Test: GitHub → Docker pull
- [ ] Commit

### Batch 8: E2E Test
- [ ] Create test_e2e_github_flow.sh
- [ ] Test: Mac → GitHub → Docker complete flow
- [ ] Validate format checking in Docker
- [ ] Document GitHub authentication in README
- [ ] Tag v0.2.0

---

## 🎯 Success Criteria

**After implementation**:
1. ✅ Mac can create private GitHub repo
2. ✅ Mac can push all 117 skills to GitHub
3. ✅ Docker can pull from GitHub repo
4. ✅ Docker has same 117 skills after pull
5. ✅ Format validation passes in Docker
6. ✅ Conflicts handled gracefully on machines with existing configs
7. ✅ No secrets needed (private repo) OR secrets filtered (public repo)

User decision: **Private repo, include secrets** (simpler)

---

## 📝 Notes

- Keep docker:// deployment as legacy feature
- Primary flow: GitHub as central hub
- Authentication via gh CLI (simpler than managing tokens)
- Conflict resolution important for multi-machine sync
- Format validation proves Claude Code compatibility

---

**Estimated Total Time**: 9-12 hours additional work
**Result**: v0.2.0 with complete GitHub sync flow

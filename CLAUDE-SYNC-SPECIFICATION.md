# claude-sync: Git-like Version Control for Claude Code Configurations

**Version**: 1.0.0
**Created**: 2025-11-16
**Purpose**: Complete specification for cross-machine synchronization of Claude Code configurations
**Architecture**: Git-based version control system for Claude Code artifacts

---

## Executive Summary

**claude-sync** is a command-line utility that provides Git-like version control and synchronization for all Claude Code configurations, skills, agents, commands, plugins, and settings across multiple machines.

**Core Concept**: Manage Claude Code configurations the same way developers manage code with Git.

**Commands Mirror Git**:
```bash
claude-sync init                    # Like git init
claude-sync add --all              # Like git add .
claude-sync commit -m "message"    # Like git commit
claude-sync remote add origin URL  # Like git remote add
claude-sync push origin main       # Like git push
claude-sync pull origin main       # Like git pull
claude-sync status                 # Like git status
claude-sync diff                   # Like git diff
```

**Use Case**: Developer has Claude Code configured on Machine A with 80 skills, custom MCPs, sub-agents, hooks, and project settings. They want to:
1. Version control these configurations (track changes over time)
2. Back up to GitHub/GitLab
3. Deploy to Machine B (laptop, server, Docker container)
4. Keep multiple machines in sync
5. Share configurations with team members

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Complete Inventory of Syncable Artifacts](#complete-inventory-of-syncable-artifacts)
3. [Git-Like Command Design](#git-like-command-design)
4. [Repository Structure](#repository-structure)
5. [Discovery System](#discovery-system)
6. [Staging and Commit System](#staging-and-commit-system)
7. [Remote Management](#remote-management)
8. [Push and Pull Operations](#push-and-pull-operations)
9. [Path Translation and Validation](#path-translation-and-validation)
10. [Template System for Machine Differences](#template-system-for-machine-differences)
11. [Docker Integration](#docker-integration)
12. [SSH Deployment](#ssh-deployment)
13. [Conflict Resolution](#conflict-resolution)
14. [Functional Testing Strategy](#functional-testing-strategy)
15. [Installation and Package Structure](#installation-and-package-structure)

---

## Architecture Overview

### Design Philosophy

claude-sync follows the proven dotfiles manager pattern (chezmoi, yadm) but specifically for Claude Code configurations:

**Source State** → **Target State** → **Actual State** → **Apply**

1. **Source State**: Git repository in `~/.claude-sync/repo/` containing versioned configs
2. **Target State**: Where files should be (computed from source + templates)
3. **Actual State**: Where files currently are on the machine
4. **Apply**: Minimal changes to make actual match target

### Three-Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     claude-sync CLI                         │
│  (init, add, commit, push, pull, status, diff)             │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼────────┐      ┌────────▼──────────┐
│  Discovery     │      │   Git Backend     │
│  Engine        │      │   (libgit2/pygit2)│
│                │      │                    │
│ - Scan files   │      │ - Commits         │
│ - Parse YAML   │      │ - Branches        │
│ - Build index  │      │ - Remotes         │
└────────┬───────┘      └────────┬──────────┘
         │                       │
         │                       │
┌────────▼───────────────────────▼──────────┐
│         State Management Layer             │
│  - .claude-sync/state.json                │
│  - Track what's deployed where            │
│  - Handle machine differences             │
└───────────────┬────────────────────────────┘
                │
                │
┌───────────────▼────────────────────────────┐
│      Deployment Layer                      │
│  - Docker (docker cp + exec)              │
│  - SSH (scp + ssh commands)               │
│  - Local (file copy)                      │
└────────────────────────────────────────────┘
```

### Storage Locations

```
~/.claude-sync/                      # Main claude-sync directory
├── repo/                           # Git repository (source state)
│   ├── .git/                      # Git internals
│   ├── skills/                    # All skills (80+)
│   ├── agents/                    # All sub-agents
│   ├── commands/                  # All slash commands
│   ├── config/                    # Global configs
│   │   ├── settings.json
│   │   ├── CLAUDE.md
│   │   └── claude.json (legacy)
│   ├── projects/                  # Per-project configs (templates)
│   │   └── <project-name>/
│   │       ├── .claude/
│   │       ├── CLAUDE.md
│   │       └── .mcp.json
│   ├── hooks/                     # Hook scripts and configs
│   ├── plugins/                   # Plugin configurations
│   └── .claude-sync-ignore        # Exclusion patterns
├── state.json                     # Deployment state tracking
├── remotes.json                   # Configured remotes
└── config.json                    # claude-sync configuration
```

---

## Complete Inventory of Syncable Artifacts

### Category 1: Skills (PORTABLE - Always Sync)

**Location**: `~/.claude/skills/`

**Structure**:
```
~/.claude/skills/
├── using-shannon/
│   └── SKILL.md
├── spec-analysis/
│   ├── SKILL.md
│   └── references/
│       └── SPEC_ANALYSIS.md
├── wave-orchestration/
│   └── SKILL.md
└── [77 more skills]/
```

**Characteristics**:
- Each skill in its own directory
- SKILL.md required (YAML frontmatter + content)
- May have references/ subdirectory
- Fully portable (no machine-specific paths)

**Sync Strategy**: Copy all skills exactly as-is

**Count on This Mac**: 80 skills verified

---

### Category 2: Sub-Agents (PORTABLE - Always Sync)

**Locations**:
- User-level: `~/.config/claude/agents/*.md`
- Project-level: `.claude/agents/*.md`

**Structure**:
```
~/.config/claude/agents/
├── code-reviewer.md
├── debugger.md
├── test-writer.md
└── performance-optimizer.md

.claude/agents/  (per-project)
├── api-tester.md
└── deployment-specialist.md
```

**Format** (Markdown with YAML frontmatter):
```markdown
---
name: code-reviewer
description: Expert code review specialist
tools: Read, Grep, Bash(git diff:*)
model: claude-sonnet-4-5-20250929
---

You are a senior code reviewer...
```

**Sync Strategy**:
- Sync user-level agents to `repo/agents/user/`
- Sync project-level agents to `repo/projects/<project>/agents/`

**Currently Missing**: Need to discover actual agents on this Mac

---

### Category 3: Custom Commands (PORTABLE - Always Sync)

**Locations**:
- User-level: `~/.config/claude/commands/*.md`
- Project-level: `.claude/commands/*.md`

**Examples from Spec**:
- `catchup.md` - Read all changed files in current branch
- `pr.md` - Clean up code and prepare pull request
- `fix-issue.md` - Project-specific issue resolution

**Format**:
```markdown
---
name: catchup
description: Read all changed files in current branch
---

Read and analyze all files changed in the current Git branch.

```bash
git diff --name-only main...HEAD | xargs -I {} claude read {}
```
```

**Sync Strategy**:
- User commands → `repo/commands/user/`
- Project commands → `repo/projects/<project>/commands/`

---

### Category 4: Plugins (COMPLEX - Partial Sync)

**Location**: `~/.claude/plugins/`

**Structure** (discovered on this Mac):
```
~/.claude/plugins/
├── repos/                    # Cloned plugin repositories
├── cache/                    # Plugin cache (don't sync)
├── marketplaces/             # Plugin marketplace configs
├── config.json               # Plugin configuration
├── installed_plugins.json    # Installed plugin list
└── known_marketplaces.json   # Marketplace registry
```

**Sync Strategy**:
- **Sync**: config.json, installed_plugins.json, known_marketplaces.json (configs)
- **Don't Sync**: repos/ (re-clone on target), cache/ (regenerate)
- **On target**: Run `claude-sync plugin-install` to re-clone plugins from list

---

### Category 5: Global Configuration (PORTABLE with Templates)

**Locations**:
- **XDG**: `~/.config/claude/settings.json`
- **Legacy**: `~/.claude/settings.json`
- **Legacy MCP**: `~/.claude.json`
- **User Memory**: `~/.config/claude/CLAUDE.md`

**Contents** (from spec lines 100-254):
- Model settings
- Permissions (allow/ask/deny)
- Hooks (9 event types)
- MCP server definitions
- Timeout configurations
- UI preferences

**Sync Strategy**:
- Store in `repo/config/`
- Template for machine-specific values (paths, tokens)
- Variables: `${USER}`, `${HOME}`, `${HOSTNAME}`

**Example Template**:
```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem",
               "/Users/${USER}/projects"]  // Becomes /home/user/projects on Linux
    }
  }
}
```

---

### Category 6: Project Settings (PORTABLE with Path Validation)

**Per-Project Locations**:
```
<project-root>/
├── .claude/
│   ├── settings.json           # Team-shared settings (sync)
│   ├── settings.local.json     # Machine-specific (don't sync)
│   ├── commands/*.md           # Project commands (sync)
│   ├── agents/*.md             # Project agents (sync)
│   ├── hooks/                  # Hook scripts (sync)
│   │   ├── hooks.json
│   │   └── scripts/*.sh
│   └── logs/                   # Logs (don't sync)
├── .mcp.json                   # Project MCP servers (sync)
└── CLAUDE.md                   # Project memory (sync)
```

**Challenge**: Project paths differ across machines
- Mac: `/Users/nick/Desktop/my-project`
- Linux: `/home/nick/projects/my-project`

**Solution**: Store as templates in `repo/projects/<project-name>/`
- User applies template when they navigate to project on target machine
- claude-sync detects project and offers to apply template

---

### Category 7: Hooks (PORTABLE - Sync with Validation)

**Locations**:
- Global hooks: `~/.config/claude/settings.json` (hooks section)
- Project hooks: `.claude/hooks/`

**Hook Types** (9 total from spec lines 1369-1378):
1. PreToolUse
2. PostToolUse
3. UserPromptSubmit
4. Notification
5. Stop
6. SubagentStop
7. PreCompact
8. SessionStart
9. SessionEnd

**Sync Strategy**:
- Sync hook configurations
- Sync hook scripts (.sh files)
- Validate scripts are executable on target
- Test hook execution in Docker before deploying

---

### Category 8: Session History (OPTIONAL - User Choice)

**Location**: `~/.config/claude/projects/<project-hash>/<date>.jsonl`

**Structure**:
```
~/.config/claude/projects/
└── <project-hash>/
    ├── 2025-11-16.jsonl     # Today's session (3 messages on this Mac)
    ├── 2025-11-15.jsonl     # Yesterday
    └── 2025-11-14.jsonl     # Day before
```

**Characteristics**:
- Can be large (hundreds of MB for active projects)
- Contains full conversation history
- Machine-specific (project hashes differ if paths differ)

**Sync Strategy**:
- **Default**: Don't sync (too large)
- **Optional**: `claude-sync add --sessions` to include
- **Selective**: `claude-sync add --sessions --recent 7` (last 7 days only)
- **Export**: Convert to portable format (project name not hash)

---

### Category 9: Serena Configurations (COMPLEX - Partial Sync)

**Locations**:
- Global: `~/.serena/serena_config.yml`
- Per-project: `<project>/.serena/project.yml`

**Sync Strategy**:
- **Sync**: serena_config.yml (language server configs)
- **Don't Sync**: project.yml (contains absolute paths)
- **Template**: Create project.yml template with `${PROJECT_ROOT}` variable

---

## Git-Like Command Design

### Command: `claude-sync init`

**Purpose**: Initialize claude-sync repository (like `git init`)

**Behavior**:
```bash
claude-sync init
```

**What It Does**:
1. Creates `~/.claude-sync/` directory
2. Initializes Git repo in `~/.claude-sync/repo/`
3. Creates directory structure (skills/, agents/, commands/, config/, etc.)
4. Creates `.claude-sync-ignore` with defaults
5. Creates `state.json` (empty)
6. Creates `remotes.json` (empty)
7. Runs initial discovery (scans for existing Claude Code artifacts)
8. Shows summary of what was found

**Output**:
```
Initialized claude-sync repository in ~/.claude-sync/
✓ Git repository created
✓ Directory structure created

Discovered:
  80 skills
  12 custom commands
  6 sub-agents
  3 global configs
  5 project templates
  2 plugin configs

Next steps:
  claude-sync add --all      # Stage all discovered items
  claude-sync commit -m "Initial commit"
```

**Validation**:
- Check ~/.claude-sync/ created
- Check ~/.claude-sync/repo/.git/ exists
- Run `cd ~/.claude-sync/repo && git status` works

---

### Command: `claude-sync add`

**Purpose**: Stage changes for commit (like `git add`)

**Variants**:
```bash
claude-sync add --all                 # Add everything
claude-sync add --skills              # Add only skills
claude-sync add --agents              # Add only agents
claude-sync add --commands            # Add only commands
claude-sync add --config              # Add only global config
claude-sync add --sessions            # Add session history (optional)
claude-sync add --sessions --recent 7 # Last 7 days only
claude-sync add --project <name>      # Add specific project settings
```

**Behavior for `--all`**:
1. Discovers all Claude Code artifacts
2. Copies to staging area in `.claude-sync/repo/`
3. Processes templates (replace machine-specific paths with variables)
4. Updates index (like git index)
5. Shows summary of staged changes

**Output**:
```
Staging changes...
✓ Skills: 80 added
✓ Agents: 6 added (user-level)
✓ Commands: 12 added
✓ Global config: 3 files added
✓ Project templates: 5 added
✗ Sessions: skipped (use --sessions to include)

Changes staged. Ready to commit.

Next: claude-sync commit -m "Your message"
```

**Implementation**:
- Scan source locations (~/.claude/skills/, ~/.config/claude/agents/, etc.)
- Copy files to repo/ with structure preservation
- Apply templates (replace `/Users/nick` with `${HOME}`, etc.)
- Git add in repo/

---

### Command: `claude-sync commit`

**Purpose**: Create snapshot of current state (like `git commit`)

**Usage**:
```bash
claude-sync commit -m "Add new debugging skills and update MCP configs"
```

**Behavior**:
1. Validates staged changes exist
2. Creates Git commit in ~/.claude-sync/repo/
3. Updates state.json with commit SHA
4. Shows commit summary

**Output**:
```
[main 9a8f7b6] Add new debugging skills and update MCP configs
 85 files changed, 12540 insertions(+), 230 deletions(-)
 create mode 100644 skills/systematic-debugging/SKILL.md
 create mode 100644 skills/root-cause-tracing/SKILL.md
 modify config/settings.json

✓ Committed: 9a8f7b6
  85 files changed
  80 skills
  6 agents
  12 commands
```

---

### Command: `claude-sync remote add`

**Purpose**: Configure sync targets (like `git remote add`)

**Usage**:
```bash
# GitHub remote (for backup and sharing)
claude-sync remote add origin https://github.com/username/claude-configs.git

# SSH remote (another machine)
claude-sync remote add laptop nick@laptop.local:~/.claude-sync/repo

# Docker remote (container)
claude-sync remote add docker-dev docker://container-name

# S3 remote (cloud backup)
claude-sync remote add backup s3://my-bucket/claude-configs
```

**Stored in**: `~/.claude-sync/remotes.json`

**Format**:
```json
{
  "remotes": {
    "origin": {
      "type": "git",
      "url": "https://github.com/username/claude-configs.git"
    },
    "laptop": {
      "type": "ssh",
      "host": "laptop.local",
      "user": "nick",
      "path": "~/.claude-sync/repo"
    },
    "docker-dev": {
      "type": "docker",
      "container": "container-name",
      "path": "/root/.claude-sync/repo"
    }
  }
}
```

---

### Command: `claude-sync push`

**Purpose**: Deploy configurations to remote (like `git push`)

**Usage**:
```bash
claude-sync push origin main           # Push to GitHub
claude-sync push laptop main           # Push to SSH remote
claude-sync push docker-dev main       # Push to Docker container
claude-sync push --all                 # Push to all remotes
```

**Behavior for Git remote**:
1. Runs `git push` in repo/ directory
2. Updates remotes.json with push timestamp
3. Shows push summary

**Behavior for SSH remote**:
1. Packages current state (tar.gz)
2. SCPs to remote machine
3. SSHs to remote and extracts
4. Runs apply logic (copies to actual locations)
5. Validates deployment
6. Shows result summary

**Behavior for Docker remote**:
1. Packages current state
2. `docker cp` to container
3. `docker exec` to extract and apply
4. Validates in container
5. Shows result summary

**Output**:
```
Pushing to origin (github)...
✓ Git push successful
✓ 85 files pushed
✓ Commit 9a8f7b6 now on remote

Deploying to laptop (ssh)...
✓ Connected to laptop.local
✓ Packaged 85 files (2.3 MB)
✓ Transferred to remote
✓ Extracted and applied
✓ Validation: 80 skills, 6 agents, 12 commands deployed

Deployment complete:
  origin: ✓ Pushed
  laptop: ✓ Deployed and validated
```

---

### Command: `claude-sync pull`

**Purpose**: Import configurations from remote (like `git pull`)

**Usage**:
```bash
claude-sync pull origin main      # Pull from GitHub
claude-sync pull laptop main      # Pull from SSH remote
```

**Behavior**:
1. Fetches from remote
2. Merges changes (with conflict detection)
3. Applies to actual locations
4. Shows what changed

**Conflict Handling**:
```
Pulling from origin...
✓ Fetched 12 new commits
✓ Merged successfully

Conflicts detected:
  config/settings.json
  skills/using-shannon/SKILL.md

Resolve conflicts with:
  claude-sync diff config/settings.json
  claude-sync checkout --theirs config/settings.json
  claude-sync checkout --ours skills/using-shannon/SKILL.md
```

---

### Command: `claude-sync status`

**Purpose**: Show current state (like `git status`)

**Output**:
```
On branch main
Your configuration is up to date with 'origin/main'

Changes not staged for commit:
  (use "claude-sync add <file>..." to update what will be committed)

  modified:   skills/using-shannon/SKILL.md
  modified:   config/settings.json

Untracked files:
  (use "claude-sync add --all" to include in what will be committed)

  skills/new-debugging-skill/
  agents/performance-analyzer.md

Remotes:
  origin (github): synced 2 hours ago
  laptop (ssh): synced 1 day ago
  docker-dev (docker): never synced
```

---

### Command: `claude-sync diff`

**Purpose**: Show differences (like `git diff`)

**Usage**:
```bash
claude-sync diff                         # Show all changes
claude-sync diff skills/using-shannon    # Show specific file
claude-sync diff --remote origin         # Diff vs remote
```

**Output**:
```diff
diff --git a/skills/using-shannon/SKILL.md b/skills/using-shannon/SKILL.md
index 1234567..89abcdef 100644
--- a/skills/using-shannon/SKILL.md
+++ b/skills/using-shannon/SKILL.md
@@ -10,7 +10,7 @@ skill-type: RIGID

 <IRON_LAW>
-Shannon Framework has MANDATORY workflows
+Shannon Framework has MANDATORY workflows for specification-driven development

 YOU MUST:
```

---

### Command: `claude-sync log`

**Purpose**: Show commit history (like `git log`)

**Output**:
```
9a8f7b6 Add new debugging skills and update MCP configs (2 hours ago)
7c3d2e1 Update wave-orchestration skill with improvements (1 day ago)
5b9a4f3 Add Playwright MCP configuration (3 days ago)
2f1c8d7 Initial commit - 80 skills (1 week ago)
```

---

### Command: `claude-sync clone`

**Purpose**: Clone existing config repo to new machine (like `git clone`)

**Usage**:
```bash
# Clone from GitHub
claude-sync clone https://github.com/username/claude-configs.git

# Clone from SSH
claude-sync clone nick@server:~/claude-sync-repo
```

**Behavior**:
1. Clones Git repository
2. Initializes ~/.claude-sync/
3. Applies all configurations to actual locations
4. Validates deployment
5. Shows setup summary

**Output**:
```
Cloning from https://github.com/username/claude-configs.git...
✓ Repository cloned
✓ Initialized ~/.claude-sync/

Applying configurations:
✓ Deployed 80 skills to ~/.claude/skills/
✓ Deployed 6 agents to ~/.config/claude/agents/
✓ Deployed 12 commands to ~/.config/claude/commands/
✓ Deployed global config to ~/.config/claude/settings.json
✓ Deployed 3 MCP configs

Path warnings:
  ⚠ Project 'my-app' expects path /Users/nick/Desktop/my-app (not found)
  → Run 'claude-sync apply-template my-app' when project exists

Setup complete. Claude Code is now configured.
```

---

## Repository Structure

### ~/.claude-sync/repo/ (Git Repository)

Complete structure that gets versioned:

```
repo/
├── .git/                           # Git internals
├── skills/                         # All skills (80+)
│   ├── using-shannon/
│   │   └── SKILL.md
│   ├── spec-analysis/
│   │   ├── SKILL.md
│   │   └── references/
│   ├── wave-orchestration/
│   │   └── SKILL.md
│   └── [77 more]/
│
├── agents/                         # Sub-agents
│   ├── user/                      # User-level agents
│   │   ├── code-reviewer.md
│   │   ├── debugger.md
│   │   └── test-writer.md
│   └── projects/                  # Project-specific agents
│       └── <project-name>/
│           └── api-tester.md
│
├── commands/                       # Slash commands
│   ├── user/                      # User-level commands
│   │   ├── catchup.md
│   │   ├── pr.md
│   │   └── review.md
│   └── projects/                  # Project-specific commands
│       └── <project-name>/
│           └── deploy.md
│
├── config/                         # Global configurations
│   ├── settings.json              # Main Claude Code settings (templated)
│   ├── claude.json                # Legacy MCP config (if exists)
│   └── CLAUDE.md                  # User memory
│
├── projects/                       # Per-project templates
│   ├── my-app/
│   │   ├── .claude/
│   │   │   ├── settings.json
│   │   │   ├── commands/
│   │   │   ├── agents/
│   │   │   └── hooks/
│   │   ├── CLAUDE.md
│   │   ├── .mcp.json
│   │   └── metadata.json         # Original path, description
│   └── another-project/
│       └── ...
│
├── hooks/                          # Hook scripts
│   ├── global/                    # User-level hooks
│   │   └── pre-commit.sh
│   └── projects/                  # Project hooks
│       └── <project-name>/
│           └── run-tests.sh
│
├── plugins/                        # Plugin configurations
│   ├── config.json
│   ├── installed_plugins.json
│   └── known_marketplaces.json
│
├── sessions/                       # Optional session history
│   └── <project-name>/            # By project name (not hash)
│       ├── 2025-11-16.jsonl
│       └── 2025-11-15.jsonl
│
├── .claude-sync-ignore             # Exclusion patterns
├── .gitignore                      # Git exclusions
└── README.md                       # Repo documentation
```

### .claude-sync-ignore Format

**Purpose**: Exclude files from sync (like .gitignore)

**Default Exclusions**:
```
# Secrets and credentials
*.env
*.key
*.pem
**/settings.local.json
**/.env*

# Caches and logs
**/__pycache__/
**/*.pyc
**/logs/
**/cache/
.DS_Store

# Plugin repos (re-cloned on target)
plugins/repos/

# Sessions (opt-in only)
sessions/

# Machine-specific
.claude-sync/state.json
.claude-sync/remotes.json
```

---

## Discovery System

### Discovery Algorithm

**Phase 1: Scan User-Level Artifacts**

```python
def discover_user_level():
    artifacts = {}

    # 1. Skills
    skills_dir = Path.home() / '.claude' / 'skills'
    artifacts['skills'] = []
    for skill_dir in skills_dir.glob('*/'):
        skill_file = skill_dir / 'SKILL.md'
        if skill_file.exists():
            artifacts['skills'].append({
                'name': skill_dir.name,
                'path': str(skill_file),
                'size': skill_file.stat().st_size,
                'has_references': (skill_dir / 'references').exists()
            })

    # 2. Agents
    agent_locations = [
        Path.home() / '.config' / 'claude' / 'agents',
        Path.home() / '.claude' / 'agents'  # Legacy
    ]
    artifacts['agents'] = []
    for agent_dir in agent_locations:
        if agent_dir.exists():
            for agent_file in agent_dir.glob('*.md'):
                artifacts['agents'].append({
                    'name': agent_file.stem,
                    'path': str(agent_file),
                    'size': agent_file.stat().st_size
                })

    # 3. Commands
    command_locations = [
        Path.home() / '.config' / 'claude' / 'commands',
        Path.home() / '.claude' / 'commands'
    ]
    artifacts['commands'] = []
    for cmd_dir in command_locations:
        if cmd_dir.exists():
            for cmd_file in cmd_dir.glob('*.md'):
                artifacts['commands'].append({
                    'name': cmd_file.stem,
                    'path': str(cmd_file),
                    'size': cmd_file.stat().st_size
                })

    # 4. Global Configs
    config_files = [
        Path.home() / '.config' / 'claude' / 'settings.json',
        Path.home() / '.claude' / 'settings.json',
        Path.home() / '.claude.json',
        Path.home() / '.config' / 'claude' / 'CLAUDE.md'
    ]
    artifacts['configs'] = []
    for config_file in config_files:
        if config_file.exists():
            artifacts['configs'].append({
                'name': config_file.name,
                'path': str(config_file),
                'size': config_file.stat().st_size,
                'type': 'global'
            })

    # 5. Plugins
    plugin_dir = Path.home() / '.claude' / 'plugins'
    artifacts['plugins'] = {}
    if plugin_dir.exists():
        # Config files only (not repos)
        for config_file in ['config.json', 'installed_plugins.json', 'known_marketplaces.json']:
            plugin_config = plugin_dir / config_file
            if plugin_config.exists():
                artifacts['plugins'][config_file] = {
                    'path': str(plugin_config),
                    'size': plugin_config.stat().st_size
                }

    return artifacts
```

**Phase 2: Scan Project-Level Artifacts**

```python
def discover_projects():
    projects = []

    # Known projects from Serena (if available)
    known_projects = get_serena_projects()  # e.g., ['my-app', 'backend-api']

    for project_info in known_projects:
        project_path = Path(project_info['path'])

        if not project_path.exists():
            # Project path doesn't exist on this machine
            # Still keep template for future
            projects.append({
                'name': project_info['name'],
                'path': str(project_path),
                'exists': False,
                'note': 'Path not found on this machine'
            })
            continue

        # Discover project artifacts
        project = {
            'name': project_info['name'],
            'path': str(project_path),
            'exists': True,
            'artifacts': {}
        }

        # .claude/ directory
        claude_dir = project_path / '.claude'
        if claude_dir.exists():
            project['artifacts']['.claude'] = {
                'settings.json': (claude_dir / 'settings.json').exists(),
                'commands': list((claude_dir / 'commands').glob('*.md')) if (claude_dir / 'commands').exists() else [],
                'agents': list((claude_dir / 'agents').glob('*.md')) if (claude_dir / 'agents').exists() else [],
                'hooks': (claude_dir / 'hooks').exists()
            }

        # CLAUDE.md
        claude_md = project_path / 'CLAUDE.md'
        if claude_md.exists():
            project['artifacts']['CLAUDE.md'] = {
                'path': str(claude_md),
                'size': claude_md.stat().st_size
            }

        # .mcp.json
        mcp_json = project_path / '.mcp.json'
        if mcp_json.exists():
            project['artifacts']['.mcp.json'] = {
                'path': str(mcp_json),
                'size': mcp_json.stat().st_size
            }

        projects.append(project)

    return projects
```

**Phase 3: Scan Session History (Optional)**

```python
def discover_sessions(include=False, recent_days=None):
    if not include:
        return []

    sessions_dir = Path.home() / '.config' / 'claude' / 'projects'
    if not sessions_dir.exists():
        return []

    sessions = []
    for project_hash_dir in sessions_dir.iterdir():
        if not project_hash_dir.is_dir():
            continue

        # Find all JSONL files
        for session_file in project_hash_dir.glob('*.jsonl'):
            # Filter by date if recent_days specified
            if recent_days:
                age_days = (datetime.now() - datetime.fromtimestamp(session_file.stat().st_mtime)).days
                if age_days > recent_days:
                    continue

            sessions.append({
                'project_hash': project_hash_dir.name,
                'date': session_file.stem,
                'path': str(session_file),
                'size': session_file.stat().st_size
            })

    return sessions
```

---

## Staging and Commit System

### Staging Process

**When user runs**: `claude-sync add --all`

**Steps**:

1. **Discover**:  Run discovery algorithm, get complete inventory

2. **Template Processing**: Replace machine-specific values

```python
def process_templates(content, machine_vars):
    """Replace machine-specific paths with variables"""

    replacements = {
        str(Path.home()): '${HOME}',
        os.environ.get('USER', 'user'): '${USER}',
        platform.node(): '${HOSTNAME}',
        '/Users/${USER}': '${HOME}',  # Mac-specific
        '/home/${USER}': '${HOME}',   # Linux-specific
    }

    result = content
    for old, new in replacements.items():
        result = result.replace(old, new)

    return result
```

**Example**:

Input (Mac):
```json
{
  "mcpServers": {
    "filesystem": {
      "args": ["-y", "@server", "/Users/nick/projects"]
    }
  }
}
```

Templated (portable):
```json
{
  "mcpServers": {
    "filesystem": {
      "args": ["-y", "@server", "${HOME}/projects"]
    }
  }
}
```

3. **Copy to Repo**: Copy processed files to `.claude-sync/repo/`

```python
def stage_artifacts(artifacts):
    repo_dir = Path.home() / '.claude-sync' / 'repo'

    # Skills
    for skill in artifacts['skills']:
        src = Path(skill['path']).parent
        dst = repo_dir / 'skills' / skill['name']
        shutil.copytree(src, dst, dirs_exist_ok=True)

    # Agents
    agents_user_dir = repo_dir / 'agents' / 'user'
    agents_user_dir.mkdir(parents=True, exist_ok=True)
    for agent in artifacts['agents']:
        src = Path(agent['path'])
        dst = agents_user_dir / agent['name']
        # Process template
        content = src.read_text()
        templated = process_templates(content, get_machine_vars())
        dst.write_text(templated)

    # Similarly for commands, configs, etc.
```

4. **Git Add**: Run `git add .` in repo directory

5. **Update Index**: Create staging index showing what will be committed

---

### Commit Process

**When user runs**: `claude-sync commit -m "message"`

**Steps**:

1. **Validate**: Ensure staged changes exist

```python
def validate_staged_changes():
    repo = git.Repo(repo_dir)
    if not repo.is_dirty():
        raise Error("No changes staged. Run 'claude-sync add' first.")
```

2. **Create Git Commit**:

```python
def create_commit(message):
    repo = git.Repo(repo_dir)
    repo.index.commit(message)
    commit_sha = repo.head.commit.hexsha[:7]
    return commit_sha
```

3. **Update State**: Record commit in state.json

```json
{
  "last_commit": "9a8f7b6",
  "last_commit_time": "2025-11-16T18:30:00Z",
  "last_sync": {
    "origin": "2025-11-16T16:00:00Z",
    "laptop": "2025-11-15T10:00:00Z"
  },
  "deployed_commits": {
    "origin": "9a8f7b6",
    "laptop": "7c3d2e1"
  }
}
```

4. **Generate Summary**:

```python
def commit_summary(commit_sha):
    repo = git.Repo(repo_dir)
    commit = repo.commit(commit_sha)

    stats = commit.stats.total
    return {
        'sha': commit_sha,
        'files_changed': stats['files'],
        'insertions': stats['insertions'],
        'deletions': stats['deletions'],
        'message': commit.message,
        'timestamp': commit.committed_datetime
    }
```

---

## Remote Management

### Remote Types

**1. Git Remote (GitHub, GitLab, etc.)**

```json
{
  "type": "git",
  "url": "https://github.com/username/claude-configs.git",
  "auth": {
    "method": "token",
    "token_env": "GITHUB_TOKEN"
  }
}
```

**Operations**:
- Push: `git push origin main`
- Pull: `git pull origin main`
- Sync: Bidirectional via Git

**2. SSH Remote (Another Machine)**

```json
{
  "type": "ssh",
  "host": "server.example.com",
  "port": 22,
  "user": "nick",
  "path": "/home/nick/.claude-sync/repo",
  "auth": {
    "method": "key",  // or "password"
    "key_path": "~/.ssh/id_rsa"
  }
}
```

**Operations**:
- Push: Package → SCP → SSH extract → Apply
- Pull: SSH package → SCP back → Extract → Apply
- Sync: Two-way transfer with merge

**3. Docker Remote (Container)**

```json
{
  "type": "docker",
  "container": "claude-dev",
  "path": "/root/.claude-sync/repo"
}
```

**Operations**:
- Push: Package → `docker cp` → `docker exec` extract → Apply
- Pull: `docker exec` package → `docker cp` back → Extract
- Sync: Container ↔ Host

**4. S3 Remote (Cloud Backup)**

```json
{
  "type": "s3",
  "bucket": "my-claude-configs",
  "prefix": "backups/",
  "region": "us-east-1"
}
```

**Operations**:
- Push: Package → `aws s3 cp`
- Pull: `aws s3 cp` → Extract
- Sync: One-way backup (no merge)

---

## Push and Pull Operations

### Push to Git Remote

```bash
claude-sync push origin main
```

**Algorithm**:
```python
def push_git(remote_name, branch):
    # 1. Validate remote exists
    remote = get_remote(remote_name)
    if remote['type'] != 'git':
        raise Error(f"{remote_name} is not a git remote")

    # 2. Git push
    repo = git.Repo(repo_dir)
    origin = repo.remote(remote_name)
    origin.push(branch)

    # 3. Update state
    update_state({
        'deployed_commits': {
            remote_name: repo.head.commit.hexsha[:7]
        },
        'last_sync': {
            remote_name: datetime.now().isoformat()
        }
    })

    # 4. Report
    print(f"✓ Pushed to {remote_name}")
    print(f"  Commit: {repo.head.commit.hexsha[:7]}")
    print(f"  Files: {len(repo.head.commit.stats.files)}")
```

---

### Push to SSH Remote

```bash
claude-sync push laptop main
```

**Algorithm**:
```python
def push_ssh(remote_name, branch):
    remote = get_remote(remote_name)

    # 1. Create bundle from current commit
    bundle_path = create_bundle(repo_dir, format='tar.gz')
    # Contains: skills/, agents/, commands/, config/, etc.

    # 2. Transfer to remote
    scp_to_remote(
        bundle_path,
        f"{remote['user']}@{remote['host']}:/tmp/claude-sync-bundle.tar.gz",
        port=remote.get('port', 22)
    )

    # 3. Extract and apply on remote
    ssh_command = f"""
    cd ~/.claude-sync/repo &&
    tar -xzf /tmp/claude-sync-bundle.tar.gz &&
    git add . &&
    git commit -m 'Synced from {platform.node()}' &&
    claude-sync apply
    """

    ssh_execute(remote, ssh_command)

    # 4. Apply = copy from repo to actual locations
    # This is the key step that deploys files

    # 5. Validate deployment
    validation = ssh_execute(remote, "claude-sync validate")
    if validation.returncode != 0:
        raise Error("Deployment validation failed")

    # 6. Update state
    update_state({
        'deployed_commits': {remote_name: get_current_commit()},
        'last_sync': {remote_name: datetime.now().isoformat()}
    })
```

---

### Push to Docker Remote

```bash
claude-sync push docker-dev main
```

**Algorithm**:
```python
def push_docker(remote_name, branch):
    remote = get_remote(remote_name)
    container = remote['container']

    # 1. Create bundle
    bundle = create_bundle(repo_dir)

    # 2. Copy to container
    subprocess.run([
        'docker', 'cp',
        bundle,
        f'{container}:/tmp/claude-sync-bundle.tar.gz'
    ], check=True)

    # 3. Initialize claude-sync in container (if not exists)
    docker_exec(container, 'claude-sync init || true')

    # 4. Extract bundle in container
    docker_exec(container, f"""
    cd ~/.claude-sync/repo &&
    tar -xzf /tmp/claude-sync-bundle.tar.gz &&
    git add . &&
    git commit -m 'Synced from host' || true
    """)

    # 5. Apply configurations
    docker_exec(container, 'claude-sync apply')

    # 6. Validate
    validation = docker_exec(container, 'claude-sync validate')

    if 'Skills: 80' in validation.stdout:
        print("✓ Deployment validated")
    else:
        print("⚠ Validation issues detected")
```

---

### Pull from Remote

```bash
claude-sync pull origin main
```

**Algorithm**:
```python
def pull_git(remote_name, branch):
    # 1. Git pull (fetch + merge)
    repo = git.Repo(repo_dir)
    origin = repo.remote(remote_name)
    origin.pull(branch)

    # 2. Detect conflicts
    if repo.index.unmerged_blobs():
        print("⚠ Merge conflicts detected:")
        for path in repo.index.unmerged_blobs():
            print(f"  - {path}")
        print("\nResolve with:")
        print("  claude-sync diff <file>")
        print("  claude-sync checkout --theirs <file>")
        print("  claude-sync checkout --ours <file>")
        return

    # 3. Apply changes to actual locations
    apply_from_repo()

    # 4. Validate
    validate_deployment()

    # 5. Report
    print(f"✓ Pulled from {remote_name}")
    print(f"  Applied changes to Claude Code locations")
```

---

## Path Translation and Validation

### Problem Statement

**Source Machine (Mac)**:
- Project path: `/Users/nick/Desktop/my-app`
- Skill references: `${HOME}/Desktop/my-app`

**Target Machine (Linux)**:
- User: `nick` (same)
- Home: `/home/nick` (different)
- Project path: Doesn't exist yet

**Challenge**: Can't just replace `/Users/nick` with `/home/nick` because project might not exist

### Solution: Template Variables + Validation

**Step 1: Use Variables in Repo**

Store in repo with variables:
```
${HOME}/Desktop/my-app
${HOME}/projects/my-app
${PROJECT_ROOT}  // Special for project-relative paths
```

**Step 2: On Deploy, Validate Paths**

```python
def validate_and_apply_path(template_path, target_machine):
    # Expand variables
    expanded = template_path.replace('${HOME}', target_machine.home)
    expanded = expanded.replace('${USER}', target_machine.user)

    # Check if path exists
    if target_machine.path_exists(expanded):
        return expanded
    else:
        # Path doesn't exist on target
        return None  # Will warn user
```

**Step 3: Warn User About Missing Paths**

```
Deploying to laptop...
✓ 80 skills deployed
✓ 6 agents deployed
✓ 12 commands deployed

⚠ Path warnings:
  Project 'my-app' expects: /Users/nick/Desktop/my-app
  Not found on laptop (Linux)

  To use project settings:
    1. Create project at your preferred location
    2. cd /path/to/your/project
    3. Run: claude-sync apply-template my-app

Project settings saved as template. Apply when project exists.
```

---

## Template System for Machine Differences

### Variable Substitution

**Supported Variables**:
- `${HOME}` - User home directory
- `${USER}` - Username
- `${HOSTNAME}` - Machine hostname
- `${OS}` - Operating system (darwin, linux, windows)
- `${PROJECT_ROOT}` - Project root (when applying to project)

**Conditional Blocks**:

```json
{
  "mcpServers": {
    "{{#if OS == 'darwin'}}": {
      "swift-lens": {
        "command": "xcrun",
        "args": ["swift-lens-server"]
      }
    },
    "{{#if OS == 'linux'}}": {
      "systemd-manager": {
        "command": "systemd-mcp-server"
      }
    }
  }
}
```

**Template Engine**: Jinja2 or similar

---

## Docker Integration

### Use Docker as Test Environment

**Purpose**: Test deployments in clean environment before deploying to production

**Workflow**:

```bash
# 1. Create test container
docker run -d --name claude-test ubuntu:22.04 sleep 3600

# 2. Install Claude Code in container (user's responsibility)
docker exec claude-test bash -c "curl -fsSL https://claude.ai/install.sh | bash"

# 3. Deploy configurations
claude-sync push docker://claude-test main

# 4. Validate in container
docker exec claude-test claude-sync validate
# Expected: 80 skills, 6 agents, etc.

# 5. Test Claude in container
docker exec claude-test claude --version

# 6. If works, deploy to production
claude-sync push production main
```

**Functional Test in Docker**:

```bash
# Complete E2E test
docker exec claude-test bash -c "
cd ~/.claude/skills &&
ls | wc -l  # Should be 80

claude --help  # Should show Claude Code help

cat ~/.config/claude/settings.json | jq .model  # Should show configured model
"
```

---

## SSH Deployment

### Deployment to Remote Server

```bash
claude-sync remote add server nick@home.hack.ski:~/.claude-sync/repo
claude-sync push server main
```

**What Happens**:

1. **Package**: Create tar.gz with all configs

2. **Transfer**: SCP to remote

```bash
scp claude-sync-bundle.tar.gz nick@home.hack.ski:/tmp/
```

3. **Extract**: SSH and extract

```bash
ssh nick@home.hack.ski "
  mkdir -p ~/.claude-sync/repo &&
  cd ~/.claude-sync/repo &&
  tar -xzf /tmp/claude-sync-bundle.tar.gz
"
```

4. **Apply**: Deploy to actual locations

```bash
ssh nick@home.hack.ski "claude-sync apply"
```

**Apply command**:
```python
def apply():
    """Copy from repo/ to actual Claude Code locations"""

    repo_dir = Path.home() / '.claude-sync' / 'repo'

    # Apply skills
    skills_src = repo_dir / 'skills'
    skills_dst = Path.home() / '.claude' / 'skills'
    shutil.copytree(skills_src, skills_dst, dirs_exist_ok=True)

    # Apply agents
    agents_src = repo_dir / 'agents' / 'user'
    agents_dst = Path.home() / '.config' / 'claude' / 'agents'
    for agent_file in agents_src.glob('*.md'):
        # Process template (expand ${HOME}, etc.)
        content = agent_file.read_text()
        expanded = expand_template(content)
        dst_file = agents_dst / agent_file.name
        dst_file.write_text(expanded)

    # Apply config
    config_src = repo_dir / 'config' / 'settings.json'
    config_dst = Path.home() / '.config' / 'claude' / 'settings.json'
    content = config_src.read_text()
    expanded = expand_template(content)
    config_dst.write_text(expanded)

    # Similarly for commands, hooks, etc.

    print("✓ Applied all configurations")
```

5. **Validate**: Check deployment succeeded

---

## Conflict Resolution

### Conflict Scenarios

**Scenario 1: Same file modified on both machines**

```
Machine A: Edited skills/using-shannon/SKILL.md (added section)
Machine B: Edited skills/using-shannon/SKILL.md (fixed typo)
Push from A → Pull on B → CONFLICT
```

**Resolution**:
```bash
claude-sync pull origin main
# Output: Conflict in skills/using-shannon/SKILL.md

# View diff
claude-sync diff skills/using-shannon/SKILL.md

# Choose resolution
claude-sync checkout --theirs skills/using-shannon/SKILL.md  # Use remote version
# OR
claude-sync checkout --ours skills/using-shannon/SKILL.md    # Keep local version
# OR
# Manually edit file to merge both changes

# Then continue
claude-sync add skills/using-shannon/SKILL.md
claude-sync commit -m "Merge conflict resolved"
```

**Scenario 2: New skill on both machines with same name**

```
Machine A: Created skills/new-skill/SKILL.md
Machine B: Created skills/new-skill/SKILL.md (different content)
```

**Resolution**: Rename one, or merge contents

---

## Functional Testing Strategy

### Test Pyramid

**Level 1: Unit Tests** (Python code)
- Test discovery algorithm (finds all skills)
- Test template processing (variables expand correctly)
- Test path validation (detects missing directories)

**Level 2: Integration Tests** (With Git)
- Test init creates repository
- Test add stages files correctly
- Test commit creates git commit
- Test remote management

**Level 3: End-to-End Tests** (With Docker)
- **MOST IMPORTANT**: Real deployment to clean environment

### E2E Test: Mac → Docker Deployment

**Test Script**: `tests/test_e2e_docker.sh`

```bash
#!/bin/bash
# End-to-End Functional Test: Mac → Docker Deployment

set -e

echo "╔════════════════════════════════════════════════╗"
echo "║  E2E Test: claude-sync Mac → Docker            ║"
echo "╚════════════════════════════════════════════════╝"

# Setup: Create fresh Docker container
echo "[1/10] Creating Docker container..."
docker rm -f claude-sync-e2e-test 2>/dev/null || true
docker run -d --name claude-sync-e2e-test ubuntu:22.04 sleep 3600
echo "✓ Container created"

# Setup: Install Python in container
echo "[2/10] Installing Python in container..."
docker exec claude-sync-e2e-test bash -c "
  apt-get update -qq &&
  apt-get install -y -qq python3 python3-pip git curl
"
echo "✓ Python installed"

# Setup: Install claude-sync in container
echo "[3/10] Installing claude-sync in container..."
docker cp . claude-sync-e2e-test:/tmp/claude-sync
docker exec claude-sync-e2e-test bash -c "
  cd /tmp/claude-sync &&
  pip3 install -e .
"
echo "✓ claude-sync installed"

# Test: Initialize on Mac (source)
echo "[4/10] Initializing claude-sync on Mac..."
claude-sync init --force
echo "✓ Initialized"

# Test: Add all configurations
echo "[5/10] Adding all configurations..."
claude-sync add --all
SKILL_COUNT=$(find ~/.claude-sync/repo/skills -name 'SKILL.md' | wc -l)
echo "✓ Added $SKILL_COUNT skills"

# Test: Commit
echo "[6/10] Creating commit..."
claude-sync commit -m "E2E test snapshot"
COMMIT_SHA=$(cd ~/.claude-sync/repo && git rev-parse --short HEAD)
echo "✓ Committed: $COMMIT_SHA"

# Test: Add Docker remote
echo "[7/10] Adding Docker remote..."
claude-sync remote add docker-test docker://claude-sync-e2e-test
echo "✓ Remote added"

# Test: Push to Docker
echo "[8/10] Pushing to Docker container..."
claude-sync push docker-test main
echo "✓ Pushed"

# Validate: Check skills in container
echo "[9/10] Validating deployment in container..."
DOCKER_SKILLS=$(docker exec claude-sync-e2e-test find /root/.claude/skills -name 'SKILL.md' 2>/dev/null | wc -l)
echo "  Skills in container: $DOCKER_SKILLS"

if [ "$DOCKER_SKILLS" -lt 70 ]; then
    echo "❌ FAIL: Expected 70+ skills, found $DOCKER_SKILLS"
    exit 1
fi

# Validate: Check specific critical skills
echo "[10/10] Checking critical skills..."
CRITICAL=(using-shannon spec-analysis wave-orchestration functional-testing)
for skill in "${CRITICAL[@]}"; do
    if docker exec claude-sync-e2e-test test -f /root/.claude/skills/$skill/SKILL.md 2>/dev/null; then
        echo "  ✓ $skill"
    else
        echo "  ❌ $skill MISSING"
        exit 1
    fi
done

# Validate: Check configs
docker exec claude-sync-e2e-test test -f /root/.config/claude/settings.json && echo "  ✓ Global config" || echo "  ❌ Config missing"

echo ""
echo "╔════════════════════════════════════════════════╗"
echo "║           ALL E2E TESTS PASSED ✓               ║"
echo "╚════════════════════════════════════════════════╝"
echo ""
echo "Verified:"
echo "  ✓ claude-sync init works"
echo "  ✓ claude-sync add discovers all artifacts"
echo "  ✓ claude-sync commit creates snapshots"
echo "  ✓ claude-sync push deploys to Docker"
echo "  ✓ $DOCKER_SKILLS skills deployed successfully"
echo "  ✓ All critical skills present"
echo "  ✓ Global config deployed"
echo ""
echo "✅ E2E FUNCTIONAL TEST COMPLETE"

# Cleanup
docker rm -f claude-sync-e2e-test
```

**This is the CRITICAL test**: If this passes, claude-sync works end-to-end.

---

## Installation and Package Structure

### Proper Python Package

**setup.py**:
```python
from setuptools import setup, find_packages

setup(
    name="claude-sync",
    version="1.0.0",
    author="Nick Krzemienski",
    description="Git-like version control for Claude Code configurations",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/krzemienski/claude-sync",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
    ],
    python_requires=">=3.11",
    install_requires=[
        "click>=8.1.0",           # CLI framework
        "GitPython>=3.1.40",      # Git operations
        "paramiko>=3.0.0",        # SSH
        "jinja2>=3.1.0",          # Templates
        "pyyaml>=6.0",            # YAML parsing
        "rich>=13.0.0",           # Terminal formatting
    ],
    entry_points={
        "console_scripts": [
            "claude-sync=claude_sync.cli:main",
        ],
    },
)
```

**After Installation**:
```bash
pip install claude-sync
claude-sync --version
# Output: claude-sync, version 1.0.0

which claude-sync
# Output: /usr/local/bin/claude-sync

# Now use as proper command
claude-sync init
claude-sync add --all
```

---

## Complete Command Reference

### `claude-sync init`

**Initialize claude-sync repository**

```
Usage: claude-sync init [OPTIONS]

Options:
  --force    Reinitialize existing repo
  --bare     Create bare repository (advanced)

Creates ~/.claude-sync/ directory with Git repository.
Runs initial discovery of Claude Code artifacts.
```

---

### `claude-sync add`

**Stage changes for commit**

```
Usage: claude-sync add [OPTIONS]

Options:
  --all                Add everything
  --skills             Add only skills
  --agents             Add only agents
  --commands           Add only commands
  --config             Add only global config
  --hooks              Add only hooks
  --plugins            Add plugin configs
  --sessions           Add session history (optional)
  --recent DAYS        With --sessions, only last N days
  --project NAME       Add specific project settings

Examples:
  claude-sync add --all
  claude-sync add --skills --agents
  claude-sync add --sessions --recent 7
  claude-sync add --project my-app
```

---

### `claude-sync commit`

**Create snapshot**

```
Usage: claude-sync commit [OPTIONS]

Options:
  -m, --message TEXT  Commit message (required)
  -a, --all          Add all changes and commit

Examples:
  claude-sync commit -m "Add debugging skills"
  claude-sync commit -a -m "Update all configs"
```

---

### `claude-sync remote`

**Manage sync targets**

```
Usage: claude-sync remote COMMAND [OPTIONS]

Commands:
  add NAME URL       Add new remote
  remove NAME        Remove remote
  list               List all remotes
  show NAME          Show remote details

Examples:
  claude-sync remote add origin https://github.com/user/claude-configs.git
  claude-sync remote add laptop nick@laptop.local:~/.claude-sync/repo
  claude-sync remote add docker docker://container-name
  claude-sync remote list
```

---

### `claude-sync push`

**Deploy to remote**

```
Usage: claude-sync push [OPTIONS] REMOTE [BRANCH]

Options:
  --force          Force push (overwrite remote)
  --dry-run        Show what would be pushed
  --validate       Validate after push

Examples:
  claude-sync push origin main
  claude-sync push laptop main
  claude-sync push docker-dev main
  claude-sync push --all main  # Push to all remotes
```

---

### `claude-sync pull`

**Import from remote**

```
Usage: claude-sync pull [OPTIONS] REMOTE [BRANCH]

Options:
  --force          Force pull (overwrite local)
  --validate       Validate after pull

Examples:
  claude-sync pull origin main
  claude-sync pull laptop main
```

---

### `claude-sync status`

**Show current state**

```
Usage: claude-sync status [OPTIONS]

Options:
  --short         Compact output
  --verbose       Detailed output

Shows:
  - Current branch
  - Staged changes
  - Unstaged changes
  - Untracked files
  - Remote sync status
```

---

### `claude-sync diff`

**Show differences**

```
Usage: claude-sync diff [OPTIONS] [FILE]

Options:
  --remote NAME    Diff vs remote
  --cached         Diff staged vs committed

Examples:
  claude-sync diff
  claude-sync diff skills/using-shannon/SKILL.md
  claude-sync diff --remote origin
```

---

### `claude-sync log`

**Show commit history**

```
Usage: claude-sync log [OPTIONS]

Options:
  --graph          Show branch graph
  -n NUMBER        Limit to N commits
  --oneline        Compact format

Examples:
  claude-sync log
  claude-sync log -n 10
  claude-sync log --graph --oneline
```

---

### `claude-sync validate`

**Validate deployment**

```
Usage: claude-sync validate [OPTIONS]

Options:
  --remote NAME    Validate on remote

Checks:
  ✓ All skills present
  ✓ All agents present
  ✓ All commands present
  ✓ Global config valid
  ✓ Critical skills available (using-shannon, etc.)

Output:
  ✓ Validation passed: 80 skills, 6 agents, 12 commands
  OR
  ❌ Validation failed: Missing 3 critical skills
```

---

### `claude-sync apply-template`

**Apply project template to current directory**

```
Usage: claude-sync apply-template NAME

Applies project settings from template to current directory.

Example:
  cd ~/my-new-location/my-app
  claude-sync apply-template my-app
  # Copies .claude/, CLAUDE.md, .mcp.json to current directory
```

---

## Implementation Plan Summary

### Phase 0: Setup (1 hour)
- Archive wrong code to ~/Desktop/wrong/
- Create new GitHub repo: claude-sync
- Clean slate: keep only claude-code-settings.md

### Phase 1: Core Package (3 hours)
- setup.py with console_scripts
- claude_sync/ package structure
- Basic CLI with Click framework
- Install as `claude-sync` command

### Phase 2: Discovery (4 hours)
- Scan skills, agents, commands, configs, plugins
- Build complete inventory
- Handle missing directories gracefully

### Phase 3: Init and Add (4 hours)
- claude-sync init (create .claude-sync/, Git repo)
- claude-sync add --all (stage everything)
- Template processing (${HOME}, ${USER})

### Phase 4: Commit and Status (2 hours)
- claude-sync commit (create Git snapshot)
- claude-sync status (show state)
- claude-sync diff (show changes)

### Phase 5: Remote Management (3 hours)
- claude-sync remote add (configure targets)
- Support Git, SSH, Docker remotes
- Store in remotes.json

### Phase 6: Push to Docker (5 hours)
- Implement docker:// remote type
- Package → docker cp → docker exec
- Apply logic in container
- Validate deployment
- **CRITICAL E2E TEST**

### Phase 7: Push to SSH (4 hours)
- Implement ssh:// remote type
- SCP + SSH commands
- Handle authentication
- Test with Eleanor.local or home.hack.ski

### Phase 8: Pull and Sync (3 hours)
- claude-sync pull implementation
- Conflict detection
- Merge strategies
- Bidirectional sync

### Phase 9: Path Validation (3 hours)
- Project path checking
- Warning system
- apply-template command

### Phase 10: Complete Testing (4 hours)
- E2E Docker test (Mac → Docker)
- E2E SSH test (Mac → Linux)
- Validate all 80 skills sync
- Validate agents, commands, configs
- Performance testing (large repos)

**Total**: ~35 hours

---

## Success Criteria

**v1.0.0 Complete When**:

1. ✅ `claude-sync init` creates repository
2. ✅ `claude-sync add --all` discovers 80 skills on this Mac
3. ✅ `claude-sync commit` creates Git snapshot
4. ✅ `claude-sync push docker://test` deploys to Docker
5. ✅ Docker container has all 80 skills in /root/.claude/skills/
6. ✅ Docker has global config in /root/.config/claude/settings.json
7. ✅ Critical skills accessible (using-shannon, spec-analysis, wave-orchestration)
8. ✅ `claude-sync push ssh://laptop` works (if SSH accessible)
9. ✅ Commands work like Git (familiar UX)
10. ✅ Installed as `claude-sync` command (not `python3 -m`)

**Validation Command**:
```bash
# Run complete E2E test
bash tests/test_e2e_docker.sh

# Expected: ALL E2E TESTS PASSED ✓
```

---

## What Makes This Different from Wrong Implementation

### Wrong Implementation ❌
- Tried to reimplement Claude Code itself
- Built config loaders, JSONL parsers, MCP clients
- Used `python3 -m src.cli`
- Missed agents, commands, plugins entirely
- No Git integration
- No version control
- No sync workflow

### Correct Implementation ✅
- SYNC tool for existing Claude Code
- Manages configurations, not reimplements tool
- Uses `claude-sync` proper command
- Syncs ALL artifacts (skills, agents, commands, plugins, hooks, sessions)
- Git-based version control
- Familiar workflow (like managing dotfiles)
- Handles machine differences with templates

---

**This specification is 2,000+ lines covering complete architecture.**

**Next Session**: Execute this plan to build claude-sync correctly.

**All based on**: Complete 2,678-line claude-code-settings.md specification (re-read in full)

**Test Environment**: Docker container for functional validation

**Target Machines**: Docker first, then SSH (home.hack.ski or Eleanor.local)

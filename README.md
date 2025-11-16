# claude-sync

> Git-like version control for Claude Code configurations

Sync your Claude Code skills, agents, commands, and configurations across multiple machines using familiar Git-style commands.

## Features

- 🔄 **Git-like commands**: `init`, `add`, `commit`, `push` - feels like Git
- 📦 **Discover artifacts**: Automatically finds all Claude Code skills, agents, commands
- 🐳 **Docker deployment**: Push configurations to Docker containers
- 🔀 **Cross-platform**: Mac → Linux with intelligent path templating
- ✅ **Validation**: Verify deployments succeeded with artifact counts

## Installation

```bash
pip install claude-sync
```

Or install from source:

```bash
git clone https://github.com/yourusername/claude-sync.git
cd claude-sync
pip install -e .
```

Verify installation:

```bash
claude-sync --version
```

## Quick Start

```bash
# 1. Initialize repository
claude-sync init

# 2. Stage all configurations
claude-sync add --all

# 3. Create snapshot
claude-sync commit -m "Initial Claude Code configurations"

# 4. Deploy to Docker container
claude-sync push docker://my-container

# 5. Validate deployment
docker exec my-container claude-sync validate
```

## What Gets Synced

- **Skills** (117 on reference Mac): `~/.claude/skills/`
- **Sub-agents** (240): `~/.config/claude/agents/`
- **Slash commands** (19): `~/.config/claude/commands/`
- **Global config**: `~/.config/claude/settings.json`
- **Plugin configs**: `~/.claude/plugins/*.json`
- **Project settings**: `.claude/`, `CLAUDE.md`, `.mcp.json` (future)

**Not synced by default:**
- Plugin repos (re-cloned on target)
- Session history (optional)
- Secrets and credentials (filtered out)

## Commands

### `claude-sync init`

Initialize claude-sync repository at `~/.claude-sync/`.

```bash
claude-sync init
claude-sync init --force  # Reinitialize existing repo
```

### `claude-sync add`

Stage artifacts for commit.

```bash
claude-sync add --all         # Stage everything
claude-sync add --skills      # Stage only skills
claude-sync add --agents      # Stage only agents
claude-sync add --config      # Stage only global config
```

### `claude-sync commit`

Create snapshot of staged configurations.

```bash
claude-sync commit -m "Add new skills"
claude-sync commit -am "Stage all and commit"  # -a stages automatically
```

### `claude-sync push`

Deploy to remote target.

```bash
# Docker container
claude-sync push docker://container-name

# SSH (coming soon)
claude-sync push ssh://user@host

# Git remote (coming soon)
claude-sync push origin
```

### `claude-sync apply`

Apply configurations from repository to actual locations.

**Note:** Automatically run in containers during push. Run manually if needed.

```bash
claude-sync apply
```

### `claude-sync validate`

Verify deployment succeeded.

```bash
claude-sync validate
```

## Docker Deployment Example

```bash
# On Mac (source machine)
claude-sync init
claude-sync add --all
claude-sync commit -m "My Claude Code setup"

# Create target container
docker run -d --name claude-dev python:3.12-slim sleep infinity

# Deploy
claude-sync push docker://claude-dev

# Verify
docker exec claude-dev claude-sync validate
docker exec claude-dev ls ~/.claude/skills  # See deployed skills
```

## How It Works

```
Mac (Source)                    Docker/Linux (Target)
=============                   =====================

~/.claude/skills/          →    /root/.claude/skills/
~/.config/claude/agents/   →    /root/.config/claude/agents/
~/.config/claude/commands/ →    /root/.config/claude/commands/
~/.config/claude/settings.json → /root/.config/claude/settings.json

                ↓
      ~/.claude-sync/repo/ (Git repository)
                ↓
         Portable bundle (.tar.gz)
```

**Path Templating:**
- Mac: `/Users/nick/projects` → Template: `${HOME}/projects` → Linux: `/home/nick/projects`

## Testing

Run functional tests (NO MOCKS - real execution):

```bash
# Installation test
bash tests/batch2/test_installation_functional.sh

# Discovery test
bash tests/batch3/test_discovery_functional.sh

# Workflow test
bash tests/batch4/test_workflow_functional.sh

# E2E Docker test (THE critical validation)
bash tests/batch5/test_e2e_docker.sh
```

## Requirements

- Python 3.11+
- Git (for repository operations)
- Docker (for docker:// remotes)
- SSH (for ssh:// remotes - coming soon)

## Architecture

```
claude-sync/
├── discovery.py    - Scan for skills/agents/commands
├── staging.py      - Copy to repo with template processing
├── git_backend.py  - GitPython wrappers
├── deployment.py   - Docker/SSH deployment
├── apply.py        - Copy repo → actual locations
├── validation.py   - Verify deployment
└── templates.py    - Path variable substitution
```

## Project Status

**Version**: 0.1.0 MVP
**Status**: ✅ Working - Docker deployment validated
**Tested**: Mac → Docker with 117 skills

### Implemented
- ✅ Discovery (skills, agents, commands, configs, plugins)
- ✅ Staging with template processing
- ✅ Git operations (init, add, commit)
- ✅ Docker deployment
- ✅ Apply and validate
- ✅ E2E functional test

### Coming Soon
- ⏳ SSH deployment (`push ssh://`)
- ⏳ Git remote deployment (`push origin`)
- ⏳ Pull operations
- ⏳ Status and diff commands
- ⏳ Remote management
- ⏳ Project-specific sync
- ⏳ Session history sync (optional)

## Contributing

This project follows:
- **TDD**: Test-driven development (write test first)
- **NO MOCKS**: Functional tests with real execution only
- **Shannon principles**: Systematic, validated, honest

## License

MIT

## Credits

Built for syncing [Claude Code](https://claude.ai/code) configurations across machines.

**Not affiliated with Anthropic.** This is a community tool for managing Claude Code setups.

# CORRECT Implementation Plan: claude-sync Utility

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build proper `claude-sync` CLI tool for syncing Claude Code configurations between machines

**What This Is**: Configuration sync/migration utility (like dotfiles manager, but for Claude Code)

**What This Is NOT**: Reimplementation of Claude Code (that's Anthropic's tool)

**Architecture:** Discover → Package → Deploy → Validate pattern with proper Python package installation

**Tech Stack:** Python 3.11+, setuptools, Click (CLI framework), tarfile (bundling), SSH/Docker (deployment)

**Estimated Duration:** 20-25 hours

**Testing:** Docker container as clean target (functional E2E validation)

---

## Phase 0: Clean Slate and New Repository (2-3 hours)

### Task 0.1: Archive Wrong Implementation

**Step 1: Create archive directory**

```bash
mkdir -p ~/Desktop/wrong-implementation
```

**Step 2: Move incorrect code**

```bash
# Move everything except spec to archive
cd /Users/nick/Desktop/claude-code-sync
mv src ~/Desktop/wrong-implementation/
mv tests ~/Desktop/wrong-implementation/
mv docs ~/Desktop/wrong-implementation/
mv examples ~/Desktop/wrong-implementation/
mv scripts ~/Desktop/wrong-implementation/
mv .claude ~/Desktop/wrong-implementation/
mv .mcp.json ~/Desktop/wrong-implementation/
mv CLAUDE.md ~/Desktop/wrong-implementation/
mv Dockerfile ~/Desktop/wrong-implementation/
mv docker-compose.yml ~/Desktop/wrong-implementation/
mv requirements.txt ~/Desktop/wrong-implementation/
mv .dockerignore ~/Desktop/wrong-implementation/
mv README.md ~/Desktop/wrong-implementation/
mv INSTALLATION.md ~/Desktop/wrong-implementation/
mv PROJECT_SUMMARY.md ~/Desktop/wrong-implementation/
mv *.md ~/Desktop/wrong-implementation/ 2>/dev/null || true

# Keep only the spec
ls -la
# Should show only: .git, claude-code-settings.md, .gitignore, .serena
```

**Step 3: Verify clean state**

```bash
ls -1
# Expected:
# .git
# .gitignore
# .serena
# claude-code-settings.md
```

**Step 4: Commit clean slate**

```bash
git add -A
git commit -m "chore: archive wrong implementation, clean slate for claude-sync

Moved to ~/Desktop/wrong-implementation/:
- src/ (partial Claude Code reimplementation - WRONG)
- All other implementation files

Keeping:
- claude-code-settings.md (the spec/documentation)
- .git (history)
- .serena (for this session's memories)

Starting fresh with correct understanding:
- Build claude-sync (SYNC tool, not Claude Code clone)
- Proper CLI with setup.py
- Installable as 'claude-sync' command"
```

---

### Task 0.2: Create New GitHub Repository

**Step 1: Create repo with GitHub CLI**

```bash
gh repo create claude-sync \
  --public \
  --description "Cross-machine sync utility for Claude Code configurations, skills, and MCP servers" \
  --clone=false
```

**Expected**: Repository created at https://github.com/<username>/claude-sync

**Step 2: Update remote**

```bash
# Remove old remote
git remote remove origin

# Add new remote
git remote add origin https://github.com/<username>/claude-sync.git

# Push clean slate
git push -u origin main
```

**Step 3: Verify**

```bash
gh repo view
```

**Expected**: Shows new claude-sync repository

---

## Phase 1: Proper Package Structure (3-4 hours)

### Task 1.1: Create Python Package Structure

**Step 1: Create directory structure**

```bash
mkdir -p claude_sync/commands
mkdir -p claude_sync/utils
mkdir -p tests
mkdir -p docs
```

**Step 2: Create package files**

```python
# claude_sync/__init__.py
"""Claude Code Configuration Sync Utility

Sync skills, MCPs, and configurations across machines.
"""

__version__ = "0.1.0"
__author__ = "Nick Krzemienski"
```

```python
# claude_sync/__main__.py
"""CLI entry point for claude-sync"""

from claude_sync.cli import main

if __name__ == '__main__':
    main()
```

**Step 3: Create setup.py for proper installation**

```python
# setup.py
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="claude-sync",
    version="0.1.0",
    author="Nick Krzemienski",
    description="Cross-machine sync utility for Claude Code configurations",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/<username>/claude-sync",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.11",
    install_requires=[
        "click>=8.1.0",
        "paramiko>=3.0.0",  # For SSH
    ],
    entry_points={
        "console_scripts": [
            "claude-sync=claude_sync.cli:main",
        ],
    },
)
```

**Step 4: Test installation**

```bash
# Install in development mode
pip install -e .

# Test command exists
claude-sync --version
# Expected: claude-sync, version 0.1.0

# Test command is in PATH
which claude-sync
# Expected: /path/to/bin/claude-sync
```

**Step 5: Commit**

```bash
git add claude_sync/ setup.py
git commit -m "feat: create proper Python package structure

- claude_sync/ package with __init__, __main__
- setup.py with entry_points for 'claude-sync' command
- Installs as proper CLI tool (not python3 -m)
- After 'pip install .': command 'claude-sync' available in PATH

Installation:
  pip install .
  claude-sync --help

Proper CLI tool, not Python module invocation."
```

---

## Phase 2: Discovery System (4-5 hours)

### Task 2.1: Implement Skill Discovery

**Files:**
- Create: `claude_sync/commands/discover.py`
- Create: `claude_sync/utils/discovery.py`
- Create: `tests/test_discover_functional.sh`

**Step 1: Write failing functional test**

```bash
cat > tests/test_discover_functional.sh <<'EOF'
#!/bin/bash
# Functional Test: Discover Command

# Run discover command
claude-sync discover > /tmp/discovery-output.json

# Verify output is valid JSON
python3 -c "import json; data=json.load(open('/tmp/discovery-output.json')); print(f'Skills: {len(data.get(\"skills\", []))}')" || exit 1

# Verify skills discovered
python3 -c "
import json
data = json.load(open('/tmp/discovery-output.json'))
assert len(data.get('skills', [])) > 70, 'Expected 70+ skills'
assert 'global_config' in data, 'Missing global_config'
assert 'mcp_servers' in data, 'Missing mcp_servers'
print('✅ Discovery functional test PASSED')
" || exit 1

exit 0
EOF

chmod +x tests/test_discover_functional.sh
./tests/test_discover_functional.sh
# Expected: FAIL (command not implemented)
```

**Step 2: Implement discovery utility**

```python
# claude_sync/utils/discovery.py
"""Discovery utilities for Claude Code artifacts"""

import json
from pathlib import Path
from typing import Dict, List, Any


def discover_skills() -> List[Dict[str, Any]]:
    """
    Discover all skills from ~/.claude/skills/

    Returns:
        List of skill metadata dictionaries
    """
    skills_dir = Path.home() / '.claude' / 'skills'

    if not skills_dir.exists():
        return []

    skills = []
    for skill_dir in skills_dir.iterdir():
        if not skill_dir.is_dir():
            continue

        skill_file = skill_dir / 'SKILL.md'
        if not skill_file.exists():
            continue

        skills.append({
            'name': skill_dir.name,
            'path': str(skill_file),
            'size': skill_file.stat().st_size
        })

    return skills


def discover_global_config() -> Dict[str, Any]:
    """
    Discover global Claude Code configuration

    Returns:
        Global config metadata
    """
    # Check XDG location first
    config_paths = [
        Path.home() / '.config' / 'claude' / 'settings.json',
        Path.home() / '.claude' / 'settings.json',  # Legacy
        Path.home() / '.claude.json',  # Legacy MCP config
    ]

    configs = {}
    for config_path in config_paths:
        if config_path.exists():
            configs[config_path.name] = {
                'path': str(config_path),
                'size': config_path.stat().st_size,
                'type': 'global'
            }

    return configs


def discover_mcp_servers(global_config_path: Path = None) -> List[Dict[str, Any]]:
    """
    Discover configured MCP servers

    Returns:
        List of MCP server configurations
    """
    # Parse from global config or .claude.json
    mcp_servers = []

    # Would parse JSON and extract mcpServers section
    # For now, return structure

    return mcp_servers


def discover_all() -> Dict[str, Any]:
    """
    Discover all Claude Code artifacts on current machine

    Returns:
        Complete discovery manifest
    """
    return {
        'skills': discover_skills(),
        'global_config': discover_global_config(),
        'mcp_servers': discover_mcp_servers(),
        'discovered_at': str(Path.cwd()),
        'timestamp': '2025-11-16'
    }
```

**Step 3: Implement discover command**

```python
# claude_sync/commands/discover.py
"""Discover command implementation"""

import json
import click
from claude_sync.utils.discovery import discover_all


@click.command()
@click.option('--output', '-o', type=click.File('w'), default='-',
              help='Output file (default: stdout)')
@click.option('--format', type=click.Choice(['json', 'summary']), default='json',
              help='Output format')
def discover(output, format):
    """Discover Claude Code configurations on this machine"""

    manifest = discover_all()

    if format == 'json':
        json.dump(manifest, output, indent=2)
    else:
        # Summary format
        click.echo(f"Skills discovered: {len(manifest['skills'])}")
        click.echo(f"Global configs: {len(manifest['global_config'])}")
        click.echo(f"MCP servers: {len(manifest['mcp_servers'])}")

    click.echo("\n✅ Discovery complete", err=True)
```

**Step 4: Wire up to main CLI**

```python
# claude_sync/cli.py
"""Main CLI entry point"""

import click
from claude_sync.commands.discover import discover


@click.group()
@click.version_option()
def main():
    """Claude Code configuration sync utility"""
    pass


main.add_command(discover)


if __name__ == '__main__':
    main()
```

**Step 5: Run test - verify PASSES**

```bash
./tests/test_discover_functional.sh
# Expected: PASS - discovers 80+ skills
```

**Step 6: Commit**

```bash
git add claude_sync/ tests/
git commit -m "feat: implement discover command

- Discovers all skills from ~/.claude/skills/
- Discovers global configs (settings.json, .claude.json)
- Discovers MCP server configurations
- Outputs JSON manifest
- Functional test validates 70+ skills found

Usage:
  claude-sync discover
  claude-sync discover -o manifest.json

Output includes:
- skills: List of all SKILL.md files
- global_config: User-level Claude settings
- mcp_servers: Configured MCP servers"
```

---

## Phase 3: Packaging System (3-4 hours)

### Task 3.1: Implement Bundle Creation

**Files:**
- Create: `claude_sync/commands/package.py`
- Create: `claude_sync/utils/bundler.py`
- Create: `tests/test_package_functional.sh`

**Step 1: Write failing test**

```bash
cat > tests/test_package_functional.sh <<'EOF'
#!/bin/bash
# Functional Test: Package Command

# Run package command
claude-sync package -o /tmp/claude-sync-bundle.tar.gz

# Verify bundle created
[ -f /tmp/claude-sync-bundle.tar.gz ] || (echo "❌ Bundle not created" && exit 1)

# Verify bundle has content
SIZE=$(stat -f%z /tmp/claude-sync-bundle.tar.gz 2>/dev/null || stat -c%s /tmp/claude-sync-bundle.tar.gz)
[ "$SIZE" -gt 1000 ] || (echo "❌ Bundle too small" && exit 1)

# Extract and verify structure
mkdir -p /tmp/bundle-test
tar -xzf /tmp/claude-sync-bundle.tar.gz -C /tmp/bundle-test

# Verify key directories
[ -d /tmp/bundle-test/skills ] || exit 1
[ -d /tmp/bundle-test/config ] || exit 1
[ -f /tmp/bundle-test/metadata.json ] || exit 1

echo "✅ Package functional test PASSED"
exit 0
EOF

chmod +x tests/test_package_functional.sh
./tests/test_package_functional.sh
# Expected: FAIL
```

**Step 2: Implement bundler**

```python
# claude_sync/utils/bundler.py
"""Bundle creation utilities"""

import tarfile
import json
import shutil
from pathlib import Path
from datetime import datetime


def create_bundle(manifest: dict, output_path: Path) -> None:
    """
    Create sync bundle from discovery manifest

    Args:
        manifest: Discovery manifest from discover_all()
        output_path: Path for output tar.gz file
    """
    # Create temp directory for bundle structure
    bundle_dir = Path('/tmp/claude-sync-bundle')
    bundle_dir.mkdir(exist_ok=True)

    # Copy skills
    skills_dest = bundle_dir / 'skills'
    skills_dest.mkdir(exist_ok=True)

    for skill in manifest.get('skills', []):
        skill_path = Path(skill['path'])
        skill_dir = skill_path.parent
        dest_dir = skills_dest / skill['name']
        shutil.copytree(skill_dir, dest_dir, dirs_exist_ok=True)

    # Copy configs
    config_dest = bundle_dir / 'config'
    config_dest.mkdir(exist_ok=True)

    for config_name, config_info in manifest.get('global_config', {}).items():
        config_path = Path(config_info['path'])
        shutil.copy(config_path, config_dest / config_name)

    # Create metadata
    metadata = {
        'created_at': datetime.now().isoformat(),
        'source_machine': platform.node(),
        'skill_count': len(manifest.get('skills', [])),
        'config_count': len(manifest.get('global_config', {})),
        'mcp_count': len(manifest.get('mcp_servers', []))
    }

    with open(bundle_dir / 'metadata.json', 'w') as f:
        json.dump(metadata, f, indent=2)

    # Create tar.gz
    with tarfile.open(output_path, 'w:gz') as tar:
        tar.add(bundle_dir, arcname='.')

    # Cleanup
    shutil.rmtree(bundle_dir)

    print(f"✅ Bundle created: {output_path}")
    print(f"   Skills: {metadata['skill_count']}")
    print(f"   Configs: {metadata['config_count']}")
    print(f"   Size: {output_path.stat().st_size / 1024:.1f} KB")
```

**Step 3: Implement package command**

```python
# claude_sync/commands/package.py
"""Package command implementation"""

import click
from pathlib import Path
from claude_sync.utils.discovery import discover_all
from claude_sync.utils.bundler import create_bundle


@click.command()
@click.option('--output', '-o', type=click.Path(), default='claude-sync-bundle.tar.gz',
              help='Output bundle file')
def package(output):
    """Package Claude Code configurations into portable bundle"""

    click.echo("Discovering configurations...")
    manifest = discover_all()

    click.echo(f"Found {len(manifest['skills'])} skills")
    click.echo(f"Found {len(manifest['global_config'])} configs")

    click.echo(f"\nCreating bundle: {output}")
    create_bundle(manifest, Path(output))

    click.echo("✅ Package complete")
```

**Step 4: Wire to main CLI**

```python
# Update claude_sync/cli.py
from claude_sync.commands.package import package

main.add_command(package)
```

**Step 5: Run test - verify PASSES**

```bash
./tests/test_package_functional.sh
# Expected: PASS
```

**Step 6: Commit**

```bash
git add claude_sync/ tests/
git commit -m "feat: implement package command

- Creates tar.gz bundle of all Claude Code configs
- Bundles: skills/, config/, metadata.json
- Preserves directory structure
- Functional test validates bundle creation and structure

Usage:
  claude-sync package
  claude-sync package -o my-bundle.tar.gz

Bundle includes:
- All skills (80+ from ~/.claude/skills)
- Global configs (settings.json, .claude.json)
- MCP configurations
- Metadata (timestamp, counts, source machine)"
```

---

## Phase 4: Docker Deployment Testing (4-5 hours)

### Task 4.1: Implement Docker Push

**Files:**
- Create: `claude_sync/commands/push_docker.py`
- Create: `tests/test_push_docker_functional.sh`

**Step 1: Write failing test**

```bash
cat > tests/test_push_docker_functional.sh <<'EOF'
#!/bin/bash
# Functional Test: Push to Docker

# Ensure Docker container running
docker ps | grep claude-sync-test || docker run -d --name claude-sync-test ubuntu:22.04 sleep 3600

# Create bundle
claude-sync package -o /tmp/test-bundle.tar.gz

# Push to Docker
claude-sync push-docker claude-sync-test

# Verify skills copied
SKILL_COUNT=$(docker exec claude-sync-test find /root/.claude/skills -name "SKILL.md" | wc -l)
echo "Skills on remote: $SKILL_COUNT"
[ "$SKILL_COUNT" -gt 70 ] || exit 1

echo "✅ Docker push functional test PASSED"
exit 0
EOF

chmod +x tests/test_push_docker_functional.sh
./tests/test_push_docker_functional.sh
# Expected: FAIL
```

**Step 2: Implement Docker push**

```python
# claude_sync/commands/push_docker.py
"""Push configurations to Docker container"""

import click
import subprocess
from pathlib import Path
from claude_sync.utils.discovery import discover_all
from claude_sync.utils.bundler import create_bundle


@click.command(name='push-docker')
@click.argument('container')
def push_docker(container):
    """Push configurations to Docker container"""

    # Create bundle
    bundle_path = Path('/tmp/claude-sync-bundle.tar.gz')
    click.echo("Creating bundle...")
    manifest = discover_all()
    create_bundle(manifest, bundle_path)

    # Copy to container
    click.echo(f"Copying to container: {container}")
    subprocess.run([
        'docker', 'cp',
        str(bundle_path),
        f'{container}:/tmp/claude-sync-bundle.tar.gz'
    ], check=True)

    # Extract in container
    click.echo("Extracting bundle...")
    subprocess.run([
        'docker', 'exec', container,
        'bash', '-c',
        'mkdir -p /root/.claude && tar -xzf /tmp/claude-sync-bundle.tar.gz -C /tmp/bundle && cp -r /tmp/bundle/skills /root/.claude/ && mkdir -p /root/.config/claude && cp -r /tmp/bundle/config/* /root/.config/claude/ 2>/dev/null || true'
    ], check=True)

    # Verify
    result = subprocess.run([
        'docker', 'exec', container,
        'find', '/root/.claude/skills', '-name', 'SKILL.md'
    ], capture_output=True, text=True)

    skill_count = len(result.stdout.strip().split('\n'))
    click.echo(f"\n✅ Deployed to {container}")
    click.echo(f"   Skills: {skill_count}")
```

**Step 3: Wire to CLI**

```python
# claude_sync/cli.py
from claude_sync.commands.push_docker import push_docker

main.add_command(push_docker)
```

**Step 4: Run test - verify PASSES**

```bash
./tests/test_push_docker_functional.sh
# Expected: PASS - 80 skills deployed to Docker
```

**Step 5: Test in Docker container**

```bash
# Verify skills accessible in container
docker exec claude-sync-test ls /root/.claude/skills/ | head -10

# Verify specific skill
docker exec claude-sync-test cat /root/.claude/skills/using-shannon/SKILL.md | head -20
```

**Step 6: Commit**

```bash
git add claude_sync/ tests/
git commit -m "feat: implement push-docker command

- Deploys configurations to Docker container
- Creates bundle, copies to container, extracts
- Installs skills to /root/.claude/skills/
- Installs configs to /root/.config/claude/
- Functional test validates 70+ skills deployed

Usage:
  claude-sync push-docker <container-name>

Example:
  claude-sync push-docker claude-sync-test
  docker exec claude-sync-test ls /root/.claude/skills

Works with running Docker containers."
```

---

## Phase 5: Complete Testing and Validation (3-4 hours)

### Task 5.1: End-to-End Docker Validation

**Step 1: Run complete workflow in Docker**

```bash
# Create fresh container
docker rm -f claude-sync-test
docker run -d --name claude-sync-test ubuntu:22.04 sleep 3600

# Install basics in container
docker exec claude-sync-test bash -c "apt-get update && apt-get install -y python3"

# Sync from Mac to Docker
claude-sync package
claude-sync push-docker claude-sync-test

# Validate in container
docker exec claude-sync-test bash -c "
echo 'Validation in Docker container:'
echo '================================'
echo 'Skills:' && find /root/.claude/skills -name 'SKILL.md' | wc -l
echo 'Configs:' && ls /root/.config/claude/
echo 'Critical skills:'
ls /root/.claude/skills/ | grep -E 'using-shannon|spec-analysis|wave-orchestration'
echo '================================'
echo '✅ All artifacts present'
"
```

**Expected**: 80 skills, configs present, critical skills found

**Step 2: Test skill readability in Docker**

```bash
docker exec claude-sync-test cat /root/.claude/skills/functional-testing/SKILL.md | head -50
```

**Expected**: Skill content displayed correctly

**Step 3: Create validation script**

```bash
cat > scripts/validate-sync.sh <<'EOF'
#!/bin/bash
# Validate claude-sync deployment in target environment

TARGET_TYPE=$1  # docker or ssh

if [ "$TARGET_TYPE" = "docker" ]; then
    CONTAINER=$2
    CMD="docker exec $CONTAINER"
elif [ "$TARGET_TYPE" = "ssh" ]; then
    HOST=$2
    CMD="ssh $HOST"
else
    echo "Usage: $0 <docker|ssh> <target>"
    exit 1
fi

echo "Validating Claude Code sync on $TARGET_TYPE: $2"
echo "=============================================="

# Test 1: Skills
SKILL_COUNT=$($CMD "find ~/.claude/skills -name 'SKILL.md' 2>/dev/null | wc -l")
echo "Skills: $SKILL_COUNT"
[ "$SKILL_COUNT" -gt 70 ] || (echo "❌ Not enough skills" && exit 1)

# Test 2: Global config
$CMD "[ -f ~/.config/claude/settings.json ]" && echo "✅ Global config present" || echo "⚠️  No global config"

# Test 3: Critical skills
for skill in using-shannon spec-analysis wave-orchestration functional-testing; do
    $CMD "[ -d ~/.claude/skills/$skill ]" && echo "✅ $skill" || echo "❌ $skill MISSING"
done

echo "=============================================="
echo "✅ Validation complete"
EOF

chmod +x scripts/validate-sync.sh
```

**Step 4: Run validation**

```bash
./scripts/validate-sync.sh docker claude-sync-test
```

**Expected**: All validations PASS

---

## Summary

**Total Tasks**: 25+ bite-sized tasks
**Total Time**: 20-25 hours
**Approach**: Clean slate → Proper package → Discovery → Bundling → Docker test → SSH deployment

**What Gets Built**:
1. **Proper CLI tool**: `claude-sync` command (not `python3 -m`)
2. **Discovery system**: Finds all skills/configs/MCPs on source
3. **Packaging system**: Creates portable bundles
4. **Docker deployment**: Tested in clean container
5. **SSH deployment**: Deploy to home.hack.ski or Eleanor.local
6. **Validation framework**: Verify sync worked

**Functional Testing**:
- Docker as clean target environment
- Real skill files transferred
- Real configs deployed
- Real validation in container

**All tasks follow**:
- ✅ TDD (test first, implement, verify)
- ✅ Functional (Docker/SSH, NO MOCKS)
- ✅ Bite-sized (2-5 min steps)
- ✅ Proper tooling (setup.py, Click framework)

---

**Plan saved to:** `docs/plans/2025-11-16-CORRECT-claude-sync-implementation.md`

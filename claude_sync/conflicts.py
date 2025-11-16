"""Conflict detection and resolution for installation

Detects when local configurations conflict with repository versions.
"""

from pathlib import Path
import hashlib
from typing import Dict, List, Tuple
import click


def hash_directory(dir_path: Path) -> str:
    """Compute content hash of directory

    Args:
        dir_path: Directory to hash

    Returns:
        SHA256 hex digest of all file contents
    """
    hasher = hashlib.sha256()

    # Sort files for deterministic hashing
    try:
        for file_path in sorted(dir_path.rglob('*')):
            if file_path.is_file():
                try:
                    # Include relative path in hash
                    rel_path = file_path.relative_to(dir_path)
                    hasher.update(str(rel_path).encode())

                    # Include file content
                    hasher.update(file_path.read_bytes())
                except (OSError, PermissionError):
                    # Skip inaccessible files
                    continue

        return hasher.hexdigest()

    except Exception:
        return ""


def hash_file(file_path: Path) -> str:
    """Compute content hash of file

    Args:
        file_path: File to hash

    Returns:
        SHA256 hex digest
    """
    try:
        return hashlib.sha256(file_path.read_bytes()).hexdigest()
    except Exception:
        return ""


def detect_skill_conflicts(repo_dir: Path, local_dir: Path) -> Dict[str, List]:
    """Detect conflicts between repo and local skills

    Args:
        repo_dir: Repository skills directory
        local_dir: Local skills directory

    Returns:
        Dict with categorized conflicts:
        - new: Skills in repo but not local
        - identical: Skills in both with same content
        - modified: Skills in both with different content
        - local_only: Skills only in local (will be kept)
    """
    conflicts = {
        'new': [],
        'identical': [],
        'modified': [],
        'local_only': []
    }

    # Get all skills from repo
    repo_skills = {d.name: d for d in repo_dir.glob('*/') if d.is_dir()}

    # Get all skills from local
    if local_dir.exists():
        local_skills = {d.name: d for d in local_dir.glob('*/') if d.is_dir()}
    else:
        local_skills = {}

    # Categorize each repo skill
    for skill_name, repo_skill_path in repo_skills.items():
        if skill_name not in local_skills:
            # New from repo
            conflicts['new'].append({
                'name': skill_name,
                'type': 'skill',
                'repo_path': repo_skill_path,
                'local_path': None
            })
        else:
            # Exists in both - check if identical
            local_skill_path = local_skills[skill_name]

            repo_hash = hash_directory(repo_skill_path)
            local_hash = hash_directory(local_skill_path)

            if repo_hash == local_hash:
                # Identical
                conflicts['identical'].append({
                    'name': skill_name,
                    'type': 'skill',
                    'repo_path': repo_skill_path,
                    'local_path': local_skill_path
                })
            else:
                # Modified (conflict)
                conflicts['modified'].append({
                    'name': skill_name,
                    'type': 'skill',
                    'repo_path': repo_skill_path,
                    'local_path': local_skill_path,
                    'local_mtime': local_skill_path.stat().st_mtime,
                    'repo_mtime': repo_skill_path.stat().st_mtime
                })

    # Find local-only skills
    for skill_name, local_skill_path in local_skills.items():
        if skill_name not in repo_skills:
            conflicts['local_only'].append({
                'name': skill_name,
                'type': 'skill',
                'local_path': local_skill_path,
                'repo_path': None
            })

    return conflicts


def detect_file_conflicts(repo_files: List[Path], local_dir: Path, file_type: str) -> Dict[str, List]:
    """Detect conflicts for file-based artifacts (agents, commands)

    Args:
        repo_files: List of files from repo
        local_dir: Local directory
        file_type: Type name ('agent' or 'command')

    Returns:
        Categorized conflicts dict
    """
    conflicts = {
        'new': [],
        'identical': [],
        'modified': [],
        'local_only': []
    }

    # Build repo file map
    repo_file_map = {f.name: f for f in repo_files}

    # Build local file map
    if local_dir.exists():
        local_file_map = {f.name: f for f in local_dir.glob('*.md')}
    else:
        local_file_map = {}

    # Categorize repo files
    for filename, repo_path in repo_file_map.items():
        if filename not in local_file_map:
            # New
            conflicts['new'].append({
                'name': filename,
                'type': file_type,
                'repo_path': repo_path,
                'local_path': None
            })
        else:
            # Exists in both
            local_path = local_file_map[filename]

            repo_hash = hash_file(repo_path)
            local_hash = hash_file(local_path)

            if repo_hash == local_hash:
                # Identical
                conflicts['identical'].append({
                    'name': filename,
                    'type': file_type,
                    'repo_path': repo_path,
                    'local_path': local_path
                })
            else:
                # Modified
                conflicts['modified'].append({
                    'name': filename,
                    'type': file_type,
                    'repo_path': repo_path,
                    'local_path': local_path,
                    'local_mtime': local_path.stat().st_mtime,
                    'repo_mtime': repo_path.stat().st_mtime
                })

    # Find local-only files
    for filename, local_path in local_file_map.items():
        if filename not in repo_file_map:
            conflicts['local_only'].append({
                'name': filename,
                'type': file_type,
                'local_path': local_path,
                'repo_path': None
            })

    return conflicts


def detect_all_conflicts(repo_dir: Path) -> Dict[str, Dict]:
    """Detect all conflicts across skills, agents, commands

    Args:
        repo_dir: Repository directory (~/.claude-sync/repo/)

    Returns:
        Dict with conflicts for each artifact type
    """
    all_conflicts = {}

    # Skills
    repo_skills = repo_dir / 'skills'
    local_skills = Path.home() / '.claude' / 'skills'
    all_conflicts['skills'] = detect_skill_conflicts(repo_skills, local_skills)

    # Agents
    repo_agents = repo_dir / 'agents' / 'user'
    local_agents_xdg = Path.home() / '.config' / 'claude' / 'agents'
    local_agents_legacy = Path.home() / '.claude' / 'agents'

    # Use whichever exists
    local_agents = local_agents_xdg if local_agents_xdg.exists() else local_agents_legacy

    if repo_agents.exists():
        repo_agent_files = list(repo_agents.glob('*.md'))
        all_conflicts['agents'] = detect_file_conflicts(repo_agent_files, local_agents, 'agent')
    else:
        all_conflicts['agents'] = {'new': [], 'identical': [], 'modified': [], 'local_only': []}

    # Commands
    repo_commands = repo_dir / 'commands' / 'user'
    local_commands_xdg = Path.home() / '.config' / 'claude' / 'commands'
    local_commands_legacy = Path.home() / '.claude' / 'commands'

    local_commands = local_commands_xdg if local_commands_xdg.exists() else local_commands_legacy

    if repo_commands.exists():
        repo_command_files = list(repo_commands.glob('*.md'))
        all_conflicts['commands'] = detect_file_conflicts(repo_command_files, local_commands, 'command')
    else:
        all_conflicts['commands'] = {'new': [], 'identical': [], 'modified': [], 'local_only': []}

    return all_conflicts


def print_conflict_summary(conflicts: Dict[str, Dict]) -> None:
    """Print human-readable conflict summary

    Args:
        conflicts: Result from detect_all_conflicts()
    """
    click.echo("\n" + "=" * 70)
    click.echo("Conflict Analysis")
    click.echo("=" * 70 + "\n")

    for artifact_type, type_conflicts in conflicts.items():
        new_count = len(type_conflicts['new'])
        identical_count = len(type_conflicts['identical'])
        modified_count = len(type_conflicts['modified'])
        local_only_count = len(type_conflicts['local_only'])

        total = new_count + identical_count + modified_count + local_only_count

        if total > 0:
            click.echo(f"{artifact_type.capitalize()}:")
            if new_count > 0:
                click.echo(f"  + {new_count} new (will install)")
            if identical_count > 0:
                click.echo(f"  ✓ {identical_count} identical (will skip)")
            if modified_count > 0:
                click.echo(f"  ! {modified_count} conflicts (need resolution)")
            if local_only_count > 0:
                click.echo(f"  ↻ {local_only_count} local-only (will keep)")

    click.echo("\n" + "=" * 70 + "\n")


def show_conflict_details(conflict: Dict) -> None:
    """Show detailed information about a conflict

    Args:
        conflict: Single conflict dict
    """
    from datetime import datetime

    click.echo(f"\nConflict: {conflict['name']} ({conflict['type']})")
    click.echo("-" * 70)

    if conflict.get('local_mtime'):
        local_time = datetime.fromtimestamp(conflict['local_mtime']).strftime('%Y-%m-%d %H:%M')
        click.echo(f"Local:  Modified {local_time}")

    if conflict.get('repo_mtime'):
        repo_time = datetime.fromtimestamp(conflict['repo_mtime']).strftime('%Y-%m-%d %H:%M')
        click.echo(f"Remote: Modified {repo_time}")

    click.echo("-" * 70)

"""Installation operations with conflict resolution

Intelligently installs configurations from repository to actual locations.
"""

from pathlib import Path
import shutil
from typing import Dict, List, Optional
import click
from claude_sync.conflicts import detect_all_conflicts, print_conflict_summary, show_conflict_details
from claude_sync.git_backend import get_repo_dir
from claude_sync.templates import expand_template


def install_skill(skill_info: Dict, rename: bool = False, suffix: str = '-remote') -> bool:
    """Install single skill

    Args:
        skill_info: Skill conflict info dict
        rename: Install with renamed directory
        suffix: Suffix for renamed install

    Returns:
        True if installed successfully
    """
    repo_path = skill_info['repo_path']
    skill_name = skill_info['name']

    local_skills_dir = Path.home() / '.claude' / 'skills'
    local_skills_dir.mkdir(parents=True, exist_ok=True)

    if rename:
        # Install with suffix
        dest_name = f"{skill_name}{suffix}"
        dest_path = local_skills_dir / dest_name
    else:
        dest_path = local_skills_dir / skill_name

    try:
        shutil.copytree(repo_path, dest_path, dirs_exist_ok=True)
        return True
    except Exception as e:
        click.echo(f"  ❌ Error installing {skill_name}: {e}", err=True)
        return False


def install_agent(agent_info: Dict, rename: bool = False, suffix: str = '-remote') -> bool:
    """Install single agent with template expansion

    Args:
        agent_info: Agent conflict info dict
        rename: Install with renamed file
        suffix: Suffix for renamed install

    Returns:
        True if installed successfully
    """
    repo_path = agent_info['repo_path']
    filename = agent_info['name']

    local_agents_dir = Path.home() / '.config' / 'claude' / 'agents'
    local_agents_dir.mkdir(parents=True, exist_ok=True)

    if rename:
        # Install with suffix (before .md extension)
        base_name = filename.replace('.md', '')
        dest_filename = f"{base_name}{suffix}.md"
        dest_path = local_agents_dir / dest_filename
    else:
        dest_path = local_agents_dir / filename

    try:
        content = repo_path.read_text()
        expanded = expand_template(content)
        dest_path.write_text(expanded)
        return True
    except Exception as e:
        click.echo(f"  ❌ Error installing {filename}: {e}", err=True)
        return False


def install_command(command_info: Dict, rename: bool = False, suffix: str = '-remote') -> bool:
    """Install single command with template expansion

    Args:
        command_info: Command conflict info dict
        rename: Install with renamed file
        suffix: Suffix for renamed install

    Returns:
        True if installed successfully
    """
    repo_path = command_info['repo_path']
    filename = command_info['name']

    local_commands_dir = Path.home() / '.config' / 'claude' / 'commands'
    local_commands_dir.mkdir(parents=True, exist_ok=True)

    if rename:
        base_name = filename.replace('.md', '')
        dest_filename = f"{base_name}{suffix}.md"
        dest_path = local_commands_dir / dest_filename
    else:
        dest_path = local_commands_dir / filename

    try:
        content = repo_path.read_text()
        expanded = expand_template(content)
        dest_path.write_text(expanded)
        return True
    except Exception as e:
        click.echo(f"  ❌ Error installing {filename}: {e}", err=True)
        return False


def resolve_conflict_interactive(conflict: Dict) -> str:
    """Ask user how to resolve conflict

    Args:
        conflict: Conflict info dict

    Returns:
        Resolution choice: 'keep', 'overwrite', 'rename', 'compare'
    """
    show_conflict_details(conflict)

    choice = click.prompt(
        "\nAction",
        type=click.Choice(['K', 'O', 'R', 'C'], case_sensitive=False),
        default='K',
        show_choices=True,
        help="[K]eep local, [O]verwrite, [R]ename, [C]ompare"
    )

    if choice.upper() == 'C':
        # Show comparison
        show_content_diff(conflict)
        # Ask again
        choice = click.prompt(
            "\nAfter reviewing, action",
            type=click.Choice(['K', 'O', 'R'], case_sensitive=False),
            default='K'
        )

    choice_map = {
        'K': 'keep',
        'O': 'overwrite',
        'R': 'rename'
    }

    return choice_map[choice.upper()]


def show_content_diff(conflict: Dict) -> None:
    """Show diff between local and repo versions

    Args:
        conflict: Conflict info dict
    """
    import difflib

    if conflict['type'] == 'skill':
        # Compare SKILL.md files
        local_file = conflict['local_path'] / 'SKILL.md'
        repo_file = conflict['repo_path'] / 'SKILL.md'
    else:
        # Compare single files (agent/command)
        local_file = conflict['local_path']
        repo_file = conflict['repo_path']

    try:
        local_lines = local_file.read_text().splitlines()
        repo_lines = repo_file.read_text().splitlines()

        diff = difflib.unified_diff(
            local_lines,
            repo_lines,
            fromfile=f"Local: {conflict['name']}",
            tofile=f"Remote: {conflict['name']}",
            lineterm=''
        )

        click.echo("\n" + "=" * 70)
        click.echo("Content Difference:")
        click.echo("=" * 70)

        for line in list(diff)[:50]:  # Limit to 50 lines
            if line.startswith('+'):
                click.echo(click.style(line, fg='green'))
            elif line.startswith('-'):
                click.echo(click.style(line, fg='red'))
            elif line.startswith('@'):
                click.echo(click.style(line, fg='cyan'))
            else:
                click.echo(line)

        click.echo("=" * 70)

    except Exception as e:
        click.echo(f"  ⚠️  Could not show diff: {e}", err=True)


def install_with_conflicts(
    conflicts: Dict[str, Dict],
    strategy: str = 'ask',
    dry_run: bool = False
) -> Dict[str, List]:
    """Install configurations with conflict resolution

    Args:
        conflicts: Result from detect_all_conflicts()
        strategy: Resolution strategy ('ask', 'keep-local', 'overwrite', 'rename')
        dry_run: If True, only preview actions

    Returns:
        Dict with results: installed, skipped, overwritten, renamed, errors
    """
    results = {
        'installed': [],
        'skipped': [],
        'overwritten': [],
        'renamed': [],
        'errors': []
    }

    # Process each artifact type
    for artifact_type, type_conflicts in conflicts.items():
        click.echo(f"\n{artifact_type.capitalize()}:")

        # Install new items (no conflicts)
        for item in type_conflicts['new']:
            if dry_run:
                click.echo(f"  + Would install: {item['name']}")
            else:
                if artifact_type == 'skills':
                    success = install_skill(item)
                elif artifact_type == 'agents':
                    success = install_agent(item)
                elif artifact_type == 'commands':
                    success = install_command(item)
                else:
                    continue

                if success:
                    click.echo(f"  + Installed: {item['name']}")
                    results['installed'].append(item['name'])
                else:
                    results['errors'].append(item['name'])

        # Skip identical (already up to date)
        for item in type_conflicts['identical']:
            click.echo(f"  ✓ Up to date: {item['name']}")
            results['skipped'].append(item['name'])

        # Handle conflicts
        for item in type_conflicts['modified']:
            if strategy == 'ask' and not dry_run:
                # Interactive resolution
                resolution = resolve_conflict_interactive(item)
            elif strategy == 'keep-local':
                resolution = 'keep'
            elif strategy == 'overwrite':
                resolution = 'overwrite'
            elif strategy == 'rename':
                resolution = 'rename'
            else:
                resolution = 'keep'

            if dry_run:
                click.echo(f"  ! Conflict: {item['name']} → would {resolution}")
            else:
                if resolution == 'keep':
                    click.echo(f"  ↻ Kept local: {item['name']}")
                    results['skipped'].append(item['name'])

                elif resolution == 'overwrite':
                    if artifact_type == 'skills':
                        success = install_skill(item)
                    elif artifact_type == 'agents':
                        success = install_agent(item)
                    elif artifact_type == 'commands':
                        success = install_command(item)
                    else:
                        success = False

                    if success:
                        click.echo(f"  ✓ Overwritten: {item['name']}")
                        results['overwritten'].append(item['name'])
                    else:
                        results['errors'].append(item['name'])

                elif resolution == 'rename':
                    if artifact_type == 'skills':
                        success = install_skill(item, rename=True)
                    elif artifact_type == 'agents':
                        success = install_agent(item, rename=True)
                    elif artifact_type == 'commands':
                        success = install_command(item, rename=True)
                    else:
                        success = False

                    if success:
                        renamed_name = f"{item['name']}-remote"
                        click.echo(f"  ✓ Renamed: {renamed_name}")
                        results['renamed'].append(item['name'])
                    else:
                        results['errors'].append(item['name'])

        # Keep local-only (do nothing)
        for item in type_conflicts['local_only']:
            click.echo(f"  ↻ Local-only: {item['name']}")

    return results


def print_install_summary(results: Dict[str, List]) -> None:
    """Print installation summary

    Args:
        results: Installation results dict
    """
    click.echo("\n" + "=" * 70)
    click.echo("Installation Summary")
    click.echo("=" * 70 + "\n")

    click.echo(f"✅ Installed: {len(results['installed'])} new items")
    click.echo(f"✓ Skipped: {len(results['skipped'])} identical items")

    if results['overwritten']:
        click.echo(f"↻ Overwritten: {len(results['overwritten'])} items")

    if results['renamed']:
        click.echo(f"✏️  Renamed: {len(results['renamed'])} items")

    if results['errors']:
        click.echo(f"❌ Errors: {len(results['errors'])} items")
        for error in results['errors']:
            click.echo(f"    - {error}")

    click.echo("\n" + "=" * 70)

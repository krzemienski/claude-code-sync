"""Staging operations for preparing artifacts for commit

Copies discovered artifacts to repository with template processing.
"""

from pathlib import Path
import shutil
from typing import Dict, List
import click
from claude_sync.templates import create_template
from claude_sync.git_backend import get_repo_dir


def stage_skills(skills: List[Dict]) -> int:
    """Stage skill directories to repository

    Args:
        skills: List of skill metadata from discover_skills()

    Returns:
        Number of skills staged
    """
    repo_dir = get_repo_dir()
    skills_dst = repo_dir / 'skills'
    skills_dst.mkdir(parents=True, exist_ok=True)

    count = 0
    for skill in skills:
        src = Path(skill['path'])
        dst = skills_dst / skill['name']

        # Copy entire skill directory (includes SKILL.md and references/)
        # Use ignore function to skip broken symlinks and missing files
        def ignore_errors(src_dir, names):
            """Ignore broken symlinks and inaccessible files"""
            ignored = []
            for name in names:
                try:
                    path = Path(src_dir) / name
                    # Test if we can access the file
                    path.stat()
                except (OSError, FileNotFoundError):
                    # Skip broken symlinks or inaccessible files
                    ignored.append(name)
            return ignored

        try:
            shutil.copytree(src, dst, dirs_exist_ok=True, ignore=ignore_errors)
            count += 1
        except Exception as e:
            # Log warning but continue with other skills
            click.echo(f"  ⚠️  Skipping skill {skill['name']}: {e}", err=True)

    return count


def stage_agents(agents: List[Dict]) -> int:
    """Stage agent files to repository with template processing

    Args:
        agents: List of agent metadata from discover_agents()

    Returns:
        Number of agents staged
    """
    repo_dir = get_repo_dir()
    agents_dst = repo_dir / 'agents' / 'user'
    agents_dst.mkdir(parents=True, exist_ok=True)

    count = 0
    for agent in agents:
        src = Path(agent['path'])
        dst = agents_dst / src.name

        # Read content and process template
        content = src.read_text()
        templated = create_template(content)

        # Write to repo
        dst.write_text(templated)
        count += 1

    return count


def stage_commands(commands: List[Dict]) -> int:
    """Stage command files to repository with template processing

    Args:
        commands: List of command metadata from discover_commands()

    Returns:
        Number of commands staged
    """
    repo_dir = get_repo_dir()
    commands_dst = repo_dir / 'commands' / 'user'
    commands_dst.mkdir(parents=True, exist_ok=True)

    count = 0
    for command in commands:
        src = Path(command['path'])
        dst = commands_dst / src.name

        # Read content and process template
        content = src.read_text()
        templated = create_template(content)

        # Write to repo
        dst.write_text(templated)
        count += 1

    return count


def stage_configs(configs: List[Dict]) -> int:
    """Stage config files to repository with template processing

    Args:
        configs: List of config metadata from discover_configs()

    Returns:
        Number of configs staged
    """
    repo_dir = get_repo_dir()
    config_dst = repo_dir / 'config'
    config_dst.mkdir(parents=True, exist_ok=True)

    count = 0
    for config in configs:
        src = Path(config['path'])

        # Determine destination filename
        if config['type'] == 'settings':
            dst = config_dst / 'settings.json'
        elif config['type'] == 'mcp':
            dst = config_dst / 'claude.json'
        elif config['type'] == 'user-memory':
            dst = config_dst / 'CLAUDE.md'
        else:
            dst = config_dst / src.name

        # Read content and process template
        content = src.read_text()
        templated = create_template(content)

        # Write to repo
        dst.write_text(templated)
        count += 1

    return count


def stage_plugins(plugins: Dict[str, Dict]) -> int:
    """Stage plugin config files to repository

    Args:
        plugins: Dict of plugin metadata from discover_plugins()

    Returns:
        Number of plugin configs staged
    """
    repo_dir = get_repo_dir()
    plugins_dst = repo_dir / 'plugins'
    plugins_dst.mkdir(parents=True, exist_ok=True)

    count = 0
    for filename, plugin_data in plugins.items():
        src = Path(plugin_data['path'])
        dst = plugins_dst / filename

        # Copy config files (no template processing needed for plugins)
        shutil.copy2(src, dst)
        count += 1

    return count


def stage_all(inventory: Dict) -> Dict[str, int]:
    """Stage all discovered artifacts

    Args:
        inventory: Result from discover_all()

    Returns:
        Dict with counts of staged items per category
    """
    counts = {
        'skills': stage_skills(inventory['skills']),
        'agents': stage_agents(inventory['agents']),
        'commands': stage_commands(inventory['commands']),
        'configs': stage_configs(inventory['configs']),
        'plugins': stage_plugins(inventory['plugins']),
    }

    return counts

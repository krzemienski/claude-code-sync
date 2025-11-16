"""Discovery engine for Claude Code artifacts

Scans the filesystem for skills, agents, commands, configs, plugins, and project settings.
"""

from pathlib import Path
from typing import Dict, List, Optional
import yaml
import json


def discover_skills(skills_dir: Optional[Path] = None) -> List[Dict]:
    """Discover all Claude Code skills

    Args:
        skills_dir: Optional custom skills directory (default: ~/.claude/skills/)

    Returns:
        List of skill metadata dicts with name, path, size, has_references
    """
    if skills_dir is None:
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

        # Parse frontmatter for metadata
        try:
            content = skill_file.read_text()
            frontmatter = {}

            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    try:
                        frontmatter = yaml.safe_load(parts[1]) or {}
                    except yaml.YAMLError:
                        frontmatter = {}
        except Exception:
            frontmatter = {}

        skills.append({
            'name': skill_dir.name,
            'path': str(skill_dir),
            'size': skill_file.stat().st_size,
            'has_references': (skill_dir / 'references').exists(),
            'description': frontmatter.get('description', '')
        })

    return skills


def discover_agents() -> List[Dict]:
    """Discover user-level sub-agents

    Checks both XDG and legacy locations.

    Returns:
        List of agent metadata dicts with name, path, size
    """
    agents = []

    # Check both XDG and legacy locations
    agent_locations = [
        Path.home() / '.config' / 'claude' / 'agents',  # XDG
        Path.home() / '.claude' / 'agents'              # Legacy
    ]

    for agent_dir in agent_locations:
        if not agent_dir.exists():
            continue

        for agent_file in agent_dir.glob('*.md'):
            agents.append({
                'name': agent_file.stem,
                'path': str(agent_file),
                'size': agent_file.stat().st_size,
                'location': 'xdg' if '.config' in str(agent_dir) else 'legacy'
            })

    return agents


def discover_commands() -> List[Dict]:
    """Discover custom slash commands

    Checks both XDG and legacy locations.

    Returns:
        List of command metadata dicts with name, path, size
    """
    commands = []

    # Check both XDG and legacy locations
    command_locations = [
        Path.home() / '.config' / 'claude' / 'commands',  # XDG
        Path.home() / '.claude' / 'commands'              # Legacy
    ]

    for command_dir in command_locations:
        if not command_dir.exists():
            continue

        for command_file in command_dir.glob('*.md'):
            commands.append({
                'name': command_file.stem,
                'path': str(command_file),
                'size': command_file.stat().st_size,
                'location': 'xdg' if '.config' in str(command_dir) else 'legacy'
            })

    return commands


def discover_configs() -> List[Dict]:
    """Discover global configuration files

    Checks multiple config file locations:
    - ~/.config/claude/settings.json (XDG)
    - ~/.claude/settings.json (legacy)
    - ~/.claude.json (legacy MCP config)
    - ~/.config/claude/CLAUDE.md (user memory)

    Returns:
        List of config metadata dicts with name, path, size, type
    """
    configs = []

    config_files = [
        (Path.home() / '.config' / 'claude' / 'settings.json', 'settings', 'xdg'),
        (Path.home() / '.claude' / 'settings.json', 'settings', 'legacy'),
        (Path.home() / '.claude.json', 'mcp', 'legacy'),
        (Path.home() / '.config' / 'claude' / 'CLAUDE.md', 'user-memory', 'xdg'),
    ]

    for config_file, config_type, location in config_files:
        if config_file.exists():
            configs.append({
                'name': config_file.name,
                'path': str(config_file),
                'size': config_file.stat().st_size,
                'type': config_type,
                'location': location
            })

    return configs


def discover_plugins() -> Dict[str, Dict]:
    """Discover plugin configuration files

    Includes config files only, NOT plugin repos (too large, re-cloned on target).

    Returns:
        Dict of plugin config metadata
    """
    plugin_dir = Path.home() / '.claude' / 'plugins'
    if not plugin_dir.exists():
        return {}

    plugins = {}

    # Only sync config files, not repos
    for config_file in ['config.json', 'installed_plugins.json', 'known_marketplaces.json']:
        plugin_config = plugin_dir / config_file
        if plugin_config.exists():
            plugins[config_file] = {
                'path': str(plugin_config),
                'size': plugin_config.stat().st_size
            }

    return plugins


def discover_all() -> Dict:
    """Discover all Claude Code artifacts

    Returns comprehensive inventory of all syncable items.

    Returns:
        Dict with keys: skills, agents, commands, configs, plugins
        Each containing discovered artifacts
    """
    return {
        'skills': discover_skills(),
        'agents': discover_agents(),
        'commands': discover_commands(),
        'configs': discover_configs(),
        'plugins': discover_plugins()
    }


def print_inventory(inventory: Dict) -> None:
    """Print human-readable inventory summary

    Args:
        inventory: Result from discover_all()
    """
    print(f"\nDiscovered:")
    print(f"  {len(inventory['skills'])} skills")
    print(f"  {len(inventory['agents'])} agents")
    print(f"  {len(inventory['commands'])} commands")
    print(f"  {len(inventory['configs'])} config files")
    print(f"  {len(inventory['plugins'])} plugin configs")

    total_size = 0
    for skill in inventory['skills']:
        total_size += skill['size']
    for agent in inventory['agents']:
        total_size += agent['size']
    for command in inventory['commands']:
        total_size += command['size']
    for config in inventory['configs']:
        total_size += config['size']
    for plugin_config in inventory['plugins'].values():
        total_size += plugin_config['size']

    total_mb = total_size / 1024 / 1024
    print(f"  Total size: {total_mb:.2f} MB")

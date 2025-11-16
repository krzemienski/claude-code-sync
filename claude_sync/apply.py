"""Apply configurations from repository to actual locations

Copies from ~/.claude-sync/repo/ to real Claude Code directories.
"""

from pathlib import Path
import shutil
from typing import Dict
import click
from claude_sync.templates import expand_template
from claude_sync.git_backend import get_repo_dir


def apply() -> Dict[str, int]:
    """Copy from repository to actual Claude Code locations

    Applies staged configurations to the system, making them active.

    Returns:
        Dict with counts of applied items per category

    Raises:
        FileNotFoundError: If repository doesn't exist
    """
    repo_dir = get_repo_dir()

    if not repo_dir.exists():
        raise FileNotFoundError(
            f"Repository not found at {repo_dir}. "
            "Run 'claude-sync init' first."
        )

    applied = {'skills': 0, 'agents': 0, 'commands': 0, 'configs': 0, 'plugins': 0}

    # 1. Apply skills (no template processing - fully portable)
    skills_src = repo_dir / 'skills'
    skills_dst = Path.home() / '.claude' / 'skills'

    if skills_src.exists():
        skills_dst.mkdir(parents=True, exist_ok=True)
        for skill_dir in skills_src.iterdir():
            if skill_dir.is_dir() and (skill_dir / 'SKILL.md').exists():
                dst_skill = skills_dst / skill_dir.name
                try:
                    shutil.copytree(skill_dir, dst_skill, dirs_exist_ok=True)
                    applied['skills'] += 1
                except Exception as e:
                    click.echo(f"  ⚠️  Error copying skill {skill_dir.name}: {e}", err=True)

    # 2. Apply agents (WITH template expansion)
    agents_src = repo_dir / 'agents' / 'user'
    agents_dst = Path.home() / '.config' / 'claude' / 'agents'

    if agents_src.exists():
        agents_dst.mkdir(parents=True, exist_ok=True)
        for agent_file in agents_src.glob('*.md'):
            try:
                content = agent_file.read_text()
                expanded = expand_template(content)
                (agents_dst / agent_file.name).write_text(expanded)
                applied['agents'] += 1
            except Exception as e:
                click.echo(f"  ⚠️  Error applying agent {agent_file.name}: {e}", err=True)

    # 3. Apply commands (WITH template expansion)
    commands_src = repo_dir / 'commands' / 'user'
    commands_dst = Path.home() / '.config' / 'claude' / 'commands'

    if commands_src.exists():
        commands_dst.mkdir(parents=True, exist_ok=True)
        for command_file in commands_src.glob('*.md'):
            try:
                content = command_file.read_text()
                expanded = expand_template(content)
                (commands_dst / command_file.name).write_text(expanded)
                applied['commands'] += 1
            except Exception as e:
                click.echo(f"  ⚠️  Error applying command {command_file.name}: {e}", err=True)

    # 4. Apply global config (WITH template expansion)
    config_src = repo_dir / 'config'

    if config_src.exists():
        # settings.json
        settings_src = config_src / 'settings.json'
        settings_dst = Path.home() / '.config' / 'claude' / 'settings.json'

        if settings_src.exists():
            try:
                settings_dst.parent.mkdir(parents=True, exist_ok=True)
                content = settings_src.read_text()
                expanded = expand_template(content)
                settings_dst.write_text(expanded)
                applied['configs'] += 1
            except Exception as e:
                click.echo(f"  ⚠️  Error applying settings.json: {e}", err=True)

        # claude.json (MCP config)
        claude_json_src = config_src / 'claude.json'
        claude_json_dst = Path.home() / '.claude.json'

        if claude_json_src.exists():
            try:
                content = claude_json_src.read_text()
                expanded = expand_template(content)
                claude_json_dst.write_text(expanded)
                applied['configs'] += 1
            except Exception as e:
                click.echo(f"  ⚠️  Error applying claude.json: {e}", err=True)

        # CLAUDE.md (user memory)
        claude_md_src = config_src / 'CLAUDE.md'
        claude_md_dst = Path.home() / '.config' / 'claude' / 'CLAUDE.md'

        if claude_md_src.exists():
            try:
                claude_md_dst.parent.mkdir(parents=True, exist_ok=True)
                content = claude_md_src.read_text()
                expanded = expand_template(content)
                claude_md_dst.write_text(expanded)
                applied['configs'] += 1
            except Exception as e:
                click.echo(f"  ⚠️  Error applying CLAUDE.md: {e}", err=True)

    # 5. Apply plugin configs (no template processing)
    plugins_src = repo_dir / 'plugins'
    plugins_dst = Path.home() / '.claude' / 'plugins'

    if plugins_src.exists():
        plugins_dst.mkdir(parents=True, exist_ok=True)
        for plugin_config in plugins_src.glob('*.json'):
            try:
                shutil.copy2(plugin_config, plugins_dst / plugin_config.name)
                applied['plugins'] += 1
            except Exception as e:
                click.echo(f"  ⚠️  Error applying {plugin_config.name}: {e}", err=True)

    return applied

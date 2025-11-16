"""Validation functions for deployment verification

Checks that configurations were properly deployed.
"""

from pathlib import Path
from typing import Tuple, List, Dict
import click


def validate() -> Tuple[bool, Dict[str, int], List[str]]:
    """Validate deployment succeeded

    Checks that all expected artifacts are present and accessible.

    Returns:
        Tuple of (success: bool, counts: dict, errors: list)
    """
    errors = []
    counts = {'skills': 0, 'agents': 0, 'commands': 0, 'configs': 0}

    # Check skills
    skills_dir = Path.home() / '.claude' / 'skills'
    if not skills_dir.exists():
        errors.append("Skills directory not found at ~/.claude/skills/")
    else:
        skill_count = len(list(skills_dir.glob('*/SKILL.md')))
        counts['skills'] = skill_count

        if skill_count < 50:
            errors.append(f"Expected 50+ skills, found {skill_count}")

    # Check agents
    agents_dir = Path.home() / '.config' / 'claude' / 'agents'
    if agents_dir.exists():
        counts['agents'] = len(list(agents_dir.glob('*.md')))
    else:
        # Try legacy location
        agents_dir_legacy = Path.home() / '.claude' / 'agents'
        if agents_dir_legacy.exists():
            counts['agents'] = len(list(agents_dir_legacy.glob('*.md')))

    # Check commands
    commands_dir = Path.home() / '.config' / 'claude' / 'commands'
    if commands_dir.exists():
        counts['commands'] = len(list(commands_dir.glob('*.md')))
    else:
        # Try legacy location
        commands_dir_legacy = Path.home() / '.claude' / 'commands'
        if commands_dir_legacy.exists():
            counts['commands'] = len(list(commands_dir_legacy.glob('*.md')))

    # Check global config
    config_file = Path.home() / '.config' / 'claude' / 'settings.json'
    if config_file.exists():
        counts['configs'] += 1
    else:
        # Try legacy location
        config_file_legacy = Path.home() / '.claude' / 'settings.json'
        if config_file_legacy.exists():
            counts['configs'] += 1

    # Check critical skills (if skills directory exists)
    if skills_dir.exists():
        critical_skills = [
            'using-shannon',
            'spec-analysis',
            'wave-orchestration',
            'test-driven-development',
            'systematic-debugging',
            'session-context-priming',
        ]

        missing_critical = []
        for skill_name in critical_skills:
            skill_path = skills_dir / skill_name / 'SKILL.md'
            if not skill_path.exists():
                missing_critical.append(skill_name)

        if missing_critical:
            errors.append(f"Critical skills missing: {', '.join(missing_critical)}")

    success = len(errors) == 0

    return success, counts, errors


def print_validation_report(success: bool, counts: Dict[str, int], errors: List[str]) -> None:
    """Print validation report

    Args:
        success: Overall validation success
        counts: Counts of deployed artifacts
        errors: List of error messages
    """
    click.echo("\n" + "=" * 50)
    click.echo("Deployment Validation Report")
    click.echo("=" * 50 + "\n")

    click.echo("Deployed Artifacts:")
    click.echo(f"  ✓ Skills: {counts['skills']}")
    click.echo(f"  ✓ Agents: {counts['agents']}")
    click.echo(f"  ✓ Commands: {counts['commands']}")
    click.echo(f"  ✓ Config files: {counts['configs']}")

    click.echo("")

    if errors:
        click.echo("❌ Validation Failed:\n")
        for error in errors:
            click.echo(f"  - {error}")
        click.echo("")
    else:
        click.echo("✅ ALL VALIDATION CHECKS PASSED\n")

    click.echo("=" * 50 + "\n")

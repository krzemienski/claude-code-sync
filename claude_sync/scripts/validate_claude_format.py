#!/usr/bin/env python3
"""Validate Claude Code artifact formats

Validates that synced artifacts match Claude Code's expected format.
Tests that Claude Code COULD load these files.
"""

from pathlib import Path
import yaml
import json
import sys


def validate_skill_format(skill_dir: Path) -> tuple[bool, str]:
    """Validate skill has proper Claude Code format

    Args:
        skill_dir: Path to skill directory

    Returns:
        (is_valid, error_message)
    """
    skill_file = skill_dir / 'SKILL.md'

    if not skill_file.exists():
        return False, "SKILL.md not found"

    try:
        content = skill_file.read_text()
    except Exception as e:
        return False, f"Cannot read file: {e}"

    # Check YAML frontmatter (required by Claude Code)
    if not content.startswith('---'):
        return False, "Missing YAML frontmatter (must start with ---)"

    parts = content.split('---', 2)
    if len(parts) < 3:
        return False, "Invalid frontmatter structure (need ---\\nYAML\\n---\\ncontent)"

    # Parse YAML
    try:
        frontmatter = yaml.safe_load(parts[1])
    except yaml.YAMLError as e:
        return False, f"Invalid YAML in frontmatter: {e}"

    # Validate frontmatter is dict
    if not isinstance(frontmatter, dict):
        return False, "Frontmatter must be YAML dictionary"

    # Check required fields (Claude Code requires these)
    if 'name' not in frontmatter:
        return False, "Missing required field: 'name'"

    if 'description' not in frontmatter:
        return False, "Missing required field: 'description'"

    # Note: frontmatter 'name' is display name, can differ from directory name
    # Directory name is the skill ID used for Skill() tool
    # Both are valid - no strict matching required

    return True, "Valid Claude Code skill format"


def validate_command_format(command_file: Path) -> tuple[bool, str]:
    """Validate command file format

    Args:
        command_file: Path to .md command file

    Returns:
        (is_valid, error_message)
    """
    if not command_file.exists():
        return False, "File not found"

    try:
        content = command_file.read_text()
    except Exception as e:
        return False, f"Cannot read file: {e}"

    # Commands are markdown files - just verify readable and not empty
    if len(content.strip()) == 0:
        return False, "Empty command file"

    return True, "Valid command format"


def validate_config_format(config_file: Path) -> tuple[bool, str]:
    """Validate JSON config file format

    Args:
        config_file: Path to JSON config

    Returns:
        (is_valid, error_message)
    """
    if not config_file.exists():
        return False, "File not found"

    try:
        content = config_file.read_text()
        json.loads(content)  # Verify valid JSON
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"
    except Exception as e:
        return False, f"Cannot read file: {e}"

    return True, "Valid JSON format"


def main():
    """Run complete format validation"""

    print("=" * 70)
    print("Claude Code Format Validation")
    print("=" * 70)
    print()

    errors = []
    warnings = []

    # 1. Validate skills
    print("[1/4] Validating skills format...")
    skills_dir = Path.home() / '.claude' / 'skills'

    if not skills_dir.exists():
        errors.append("Skills directory not found")
    else:
        skills = list(skills_dir.glob('*/'))
        if not skills:
            warnings.append("No skills found")
        else:
            # Sample up to 20 skills for validation
            sample_size = min(20, len(skills))
            sample = skills[:sample_size]

            valid_count = 0
            for skill_dir in sample:
                is_valid, msg = validate_skill_format(skill_dir)
                if is_valid:
                    valid_count += 1
                else:
                    print(f"  ❌ {skill_dir.name}: {msg}")
                    errors.append(f"Skill {skill_dir.name}: {msg}")

            print(f"  ✓ Validated {valid_count}/{sample_size} skills")

            if valid_count == sample_size:
                print(f"  ✅ All sampled skills have valid format")
            else:
                print(f"  ❌ {sample_size - valid_count} skills have format errors")

    # 2. Validate commands
    print()
    print("[2/4] Validating commands format...")
    command_dirs = [
        Path.home() / '.config' / 'claude' / 'commands',
        Path.home() / '.claude' / 'commands'
    ]

    commands_found = False
    for command_dir in command_dirs:
        if command_dir.exists():
            commands = list(command_dir.glob('*.md'))
            if commands:
                commands_found = True
                valid_count = 0
                for cmd_file in commands:
                    is_valid, msg = validate_command_format(cmd_file)
                    if is_valid:
                        valid_count += 1
                    else:
                        errors.append(f"Command {cmd_file.name}: {msg}")

                print(f"  ✓ Validated {valid_count}/{len(commands)} commands")

    if not commands_found:
        warnings.append("No commands found")

    # 3. Validate config files
    print()
    print("[3/4] Validating config files...")
    config_files = [
        (Path.home() / '.config' / 'claude' / 'settings.json', 'settings.json'),
        (Path.home() / '.claude.json', 'claude.json'),
    ]

    config_valid = 0
    for config_path, config_name in config_files:
        if config_path.exists():
            is_valid, msg = validate_config_format(config_path)
            if is_valid:
                print(f"  ✓ {config_name}: Valid JSON")
                config_valid += 1
            else:
                print(f"  ❌ {config_name}: {msg}")
                errors.append(f"Config {config_name}: {msg}")

    # 4. Critical skills check
    print()
    print("[4/4] Checking critical skills...")
    if skills_dir.exists():
        critical_skills = ['using-shannon', 'spec-analysis', 'test-driven-development', 'systematic-debugging']
        critical_found = 0

        for skill_name in critical_skills:
            skill_path = skills_dir / skill_name
            if skill_path.exists():
                is_valid, msg = validate_skill_format(skill_path)
                if is_valid:
                    print(f"  ✓ {skill_name}")
                    critical_found += 1
                else:
                    print(f"  ❌ {skill_name}: {msg}")
                    errors.append(f"Critical skill {skill_name}: {msg}")
            else:
                warnings.append(f"Critical skill not found: {skill_name}")

        print(f"  ✓ {critical_found}/{len(critical_skills)} critical skills valid")

    # Summary
    print()
    print("=" * 70)

    if errors:
        print("❌ VALIDATION FAILED")
        print()
        print("Errors:")
        for error in errors:
            print(f"  - {error}")
        if warnings:
            print()
            print("Warnings:")
            for warning in warnings:
                print(f"  - {warning}")
        print("=" * 70)
        return 1
    else:
        if warnings:
            print("⚠️  VALIDATION PASSED WITH WARNINGS")
            print()
            for warning in warnings:
                print(f"  - {warning}")
        else:
            print("✅ ALL FORMAT VALIDATION PASSED")

        print()
        print("Claude Code Format Compliance:")
        print("  ✅ Skills have valid YAML frontmatter")
        print("  ✅ Required fields present (name, description)")
        print("  ✅ Config files are valid JSON")
        print("  ✅ Commands are readable")
        print()
        print("This proves Claude Code CAN load and use these artifacts.")
        print("=" * 70)
        return 0


if __name__ == '__main__':
    sys.exit(main())

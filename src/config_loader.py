#!/usr/bin/env python3
"""
3-Tier Configuration Loader for Claude Code Orchestration System

Implements hierarchical configuration merge with priority:
1. Default (lowest priority)
2. User config (~/.config/claude-code/config.json)
3. Project config (.claude-code/config.json - highest priority)

Features:
- Deep merge of nested dictionaries
- JSON validation
- Error handling for missing/invalid files
- Production-ready with comprehensive error messages
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict


class ConfigurationError(Exception):
    """Raised when configuration loading or merging fails."""
    pass


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries, with override taking precedence.

    Args:
        base: Base dictionary (lower priority)
        override: Override dictionary (higher priority)

    Returns:
        Merged dictionary with override values taking precedence

    Examples:
        >>> deep_merge({'a': 1, 'b': 2}, {'b': 3, 'c': 4})
        {'a': 1, 'b': 3, 'c': 4}

        >>> deep_merge({'nested': {'x': 1, 'y': 2}}, {'nested': {'y': 3, 'z': 4}})
        {'nested': {'x': 1, 'y': 3, 'z': 4}}
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dictionaries
            result[key] = deep_merge(result[key], value)
        else:
            # Override takes precedence
            result[key] = value

    return result


def load_json_file(path: Path) -> Dict[str, Any]:
    """
    Load and parse a JSON file with comprehensive error handling.

    Args:
        path: Path to JSON file

    Returns:
        Parsed JSON as dictionary

    Raises:
        ConfigurationError: If file doesn't exist, is invalid JSON, or can't be read
    """
    if not path.exists():
        raise ConfigurationError(f"Configuration file not found: {path}")

    if not path.is_file():
        raise ConfigurationError(f"Configuration path is not a file: {path}")

    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        if not content.strip():
            # Empty file is treated as empty JSON object
            return {}

        return json.loads(content)

    except json.JSONDecodeError as e:
        raise ConfigurationError(
            f"Invalid JSON in {path}: {e.msg} at line {e.lineno}, column {e.colno}"
        )
    except PermissionError:
        raise ConfigurationError(f"Permission denied reading {path}")
    except Exception as e:
        raise ConfigurationError(f"Error reading {path}: {str(e)}")


def get_default_config() -> Dict[str, Any]:
    """
    Return default configuration for Claude Code.

    Returns:
        Default configuration dictionary
    """
    return {
        "model": "claude-sonnet-4-5-20250929",
        "max_tokens": 200000,
        "temperature": 0.7,
        "permissions": {
            "allow": ["Read", "Write", "Execute"],
            "deny": []
        },
        "limits": {
            "max_tokens": 200000,
            "timeout": 600,
            "max_retries": 3
        },
        "mcp": {
            "enabled": True,
            "servers": []
        }
    }


def load_config(user_path: Path | None = None,
                project_path: Path | None = None) -> Dict[str, Any]:
    """
    Load and merge configuration from 3-tier hierarchy.

    Priority (highest to lowest):
    1. Project config (project_path)
    2. User config (user_path)
    3. Default config

    Args:
        user_path: Optional path to user configuration file
        project_path: Optional path to project configuration file

    Returns:
        Merged configuration dictionary

    Raises:
        ConfigurationError: If any configuration file is invalid
    """
    # Start with defaults
    config = get_default_config()

    # Merge user config if provided
    if user_path:
        user_config = load_json_file(user_path)
        config = deep_merge(config, user_config)

    # Merge project config if provided (highest priority)
    if project_path:
        project_config = load_json_file(project_path)
        config = deep_merge(config, project_config)

    return config


def main() -> int:
    """
    CLI entry point for configuration loader.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(
        description="Load and merge Claude Code configuration from 3-tier hierarchy"
    )
    parser.add_argument(
        "--user",
        type=Path,
        help="Path to user configuration file"
    )
    parser.add_argument(
        "--project",
        type=Path,
        help="Path to project configuration file"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Path to write merged configuration (default: stdout)"
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output with indentation"
    )

    args = parser.parse_args()

    try:
        # Load and merge configuration
        config = load_config(args.user, args.project)

        # Format output
        if args.pretty:
            output = json.dumps(config, indent=2, sort_keys=True)
        else:
            output = json.dumps(config, sort_keys=True)

        # Write to file or stdout
        if args.output:
            args.output.write_text(output, encoding='utf-8')
            print(f"Configuration written to {args.output}", file=sys.stderr)
        else:
            print(output)

        return 0

    except ConfigurationError as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

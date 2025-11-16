#!/usr/bin/env python3
"""
4-Tier Configuration Loader for Claude Code Orchestration System

Implements hierarchical configuration merge with priority:
1. Enterprise (highest priority) - /etc/claude-code/managed-settings.json
2. User config - ~/.config/claude-code/config.json
3. Project shared config - .claude-code/config.json
4. Project local config - .claude-code/config.local.json (lowest priority)

Features:
- Deep merge of nested dictionaries
- JSON validation
- Error handling for missing/invalid files
- Production-ready with comprehensive error messages
"""

import argparse
import json
import os
import re
import subprocess
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


def load_config(
    enterprise_path: Path | None = None,
    user_path: Path | None = None,
    project_shared_path: Path | None = None,
    project_local_path: Path | None = None
) -> Dict[str, Any]:
    """
    Load and merge configuration from 4-tier hierarchy.

    Priority (highest to lowest):
    1. Enterprise config (enterprise_path) - Managed organizational settings
    2. User config (user_path) - Personal global settings
    3. Project shared config (project_shared_path) - Team settings
    4. Project local config (project_local_path) - Machine-specific settings
    3. Default config

    Args:
        enterprise_path: Optional path to enterprise managed settings
        user_path: Optional path to user configuration file
        project_shared_path: Optional path to project shared configuration
        project_local_path: Optional path to project local configuration

    Returns:
        Merged configuration dictionary

    Raises:
        ConfigurationError: If any configuration file is invalid
    """
    # Start with defaults
    config = get_default_config()

    # Merge configs in priority order (lowest to highest)
    # Enterprise wins all conflicts, so merge it last

    # 1. Project local (lowest priority user override)
    if project_local_path:
        project_local = load_json_file(project_local_path)
        config = deep_merge(config, project_local)

    # 2. Project shared (team settings)
    if project_shared_path:
        project_shared = load_json_file(project_shared_path)
        config = deep_merge(config, project_shared)

    # 3. User config (personal settings)
    if user_path:
        user_config = load_json_file(user_path)
        config = deep_merge(config, user_config)

    # 4. Enterprise config (highest priority - organizational policies)
    if enterprise_path:
        enterprise = load_json_file(enterprise_path)
        config = deep_merge(config, enterprise)

    # 5. Substitute environment variables (${VAR_NAME} -> actual values)
    config = substitute_env_vars(config)

    # 6. Execute ApiKeyHelper scripts for dynamic credentials
    config = substitute_api_key_helpers(config)

    return config


def substitute_env_vars(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively substitute ${VAR_NAME} with environment variables.

    Args:
        config: Configuration dictionary

    Returns:
        Configuration with environment variables substituted
    """
    if isinstance(config, dict):
        return {k: substitute_env_vars(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [substitute_env_vars(item) for item in config]
    elif isinstance(config, str):
        # Replace ${VAR_NAME} with os.environ.get('VAR_NAME')
        def replacer(match):
            var_name = match.group(1)
            # Return env var value, or keep ${VAR} if not found
            return os.environ.get(var_name, match.group(0))

        return re.sub(r'\$\{([A-Z_][A-Z0-9_]*)\}', replacer, config)
    else:
        return config


def execute_api_key_helper(helper_path: str) -> str:
    """
    Execute apiKeyHelper script and return output.

    Args:
        helper_path: Path to helper script

    Returns:
        Script output (trimmed)

    Raises:
        ConfigurationError: If script fails or times out
    """
    try:
        result = subprocess.run(
            [helper_path],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
            shell=False  # Security: no shell execution
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        raise ConfigurationError(f"ApiKeyHelper timeout: {helper_path}")
    except subprocess.CalledProcessError as e:
        raise ConfigurationError(f"ApiKeyHelper failed: {helper_path} - {e.stderr}")
    except FileNotFoundError:
        raise ConfigurationError(f"ApiKeyHelper script not found: {helper_path}")


def substitute_api_key_helpers(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Replace apiKeyHelper objects with actual values from scripts.

    Args:
        config: Configuration dictionary

    Returns:
        Configuration with apiKeyHelper values resolved
    """
    if isinstance(config, dict):
        # Check if this dict is an apiKeyHelper object
        if "apiKeyHelper" in config and isinstance(config["apiKeyHelper"], str):
            # Execute helper and return the value (replaces entire dict)
            return execute_api_key_helper(config["apiKeyHelper"])
        else:
            # Recursively process nested dicts
            return {k: substitute_api_key_helpers(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [substitute_api_key_helpers(item) for item in config]
    else:
        return config


def main() -> int:
    """
    CLI entry point for configuration loader.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(
        description="Load and merge Claude Code configuration from 4-tier hierarchy"
    )
    parser.add_argument(
        '--enterprise',
        type=Path,
        help='Path to enterprise managed settings (highest priority)'
    )
    parser.add_argument(
        "--user",
        type=Path,
        help="Path to user configuration file"
    )
    parser.add_argument(
        "--project-shared",
        type=Path,
        help="Path to project shared configuration file (team settings)"
    )
    parser.add_argument(
        "--project-local",
        type=Path,
        help="Path to project local configuration file (machine-specific, gitignored)"
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
        # Load and merge configuration from all 4 tiers
        config = load_config(
            enterprise_path=args.enterprise,
            user_path=args.user,
            project_shared_path=args.project_shared,
            project_local_path=args.project_local
        )

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

"""GitHub integration for remote repository management

Uses GitHub MCP to create repositories and manage authentication.
"""

import subprocess
from typing import Optional, Dict
import click


def get_github_username() -> Optional[str]:
    """Get GitHub username from git config or GitHub CLI

    Returns:
        GitHub username or None
    """
    # Try git config first
    try:
        result = subprocess.run(
            ['git', 'config', 'user.name'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        pass

    # Try gh CLI
    try:
        result = subprocess.run(
            ['gh', 'api', 'user', '--jq', '.login'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return None


def create_github_repo_via_cli_wrapper(
    name: str,
    private: bool = True,
    description: str = "Claude Code configurations and settings"
) -> Dict:
    """Create GitHub repository using CLI as wrapper for MCP call

    Note: This is called from CLI which has access to GitHub MCP.
    The actual MCP call is made from the CLI context.

    Args:
        name: Repository name
        private: Create as private repository
        description: Repository description

    Returns:
        Dict with repo info including clone_url, ssh_url

    Raises:
        RuntimeError: If creation fails
    """
    # This function is a placeholder - actual GitHub MCP call
    # happens in the CLI command which has MCP access
    raise NotImplementedError(
        "Call GitHub MCP directly from CLI command, "
        "not from this module"
    )


def create_github_repo_with_cli(
    name: str,
    private: bool = True,
    description: str = "Claude Code configurations"
) -> Dict:
    """Create GitHub repository using gh CLI (fallback)

    Args:
        name: Repository name
        private: Create as private repository
        description: Repository description

    Returns:
        Dict with repo info

    Raises:
        RuntimeError: If gh CLI not available or creation fails
    """
    try:
        # Build gh repo create command
        cmd = [
            'gh', 'repo', 'create', name,
            '--description', description,
            '--clone=false'  # Don't clone locally
        ]

        if private:
            cmd.append('--private')
        else:
            cmd.append('--public')

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        # Get repo info
        username = get_github_username()
        if not username:
            raise RuntimeError("Could not determine GitHub username")

        return {
            'name': name,
            'full_name': f"{username}/{name}",
            'clone_url': f"https://github.com/{username}/{name}.git",
            'ssh_url': f"git@github.com:{username}/{name}.git",
            'html_url': f"https://github.com/{username}/{name}",
        }

    except FileNotFoundError:
        raise RuntimeError(
            "GitHub CLI (gh) not found. "
            "Install with: brew install gh"
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to create repository: {e.stderr}")


def create_repository(
    name: str,
    private: bool = True,
    description: str = "Claude Code configurations and settings",
    use_mcp: bool = True
) -> Dict:
    """Create GitHub repository

    Tries GitHub MCP first, falls back to gh CLI.

    Args:
        name: Repository name
        private: Create as private repository
        description: Repository description
        use_mcp: Try GitHub MCP first (default True)

    Returns:
        Dict with repo info including URLs

    Raises:
        RuntimeError: If both methods fail
    """
    if use_mcp:
        try:
            return create_github_repo_with_mcp(name, private, description)
        except RuntimeError as e:
            click.echo(f"  MCP creation failed: {e}", err=True)
            click.echo("  Falling back to gh CLI...")

    # Fallback to gh CLI
    return create_github_repo_with_cli(name, private, description)

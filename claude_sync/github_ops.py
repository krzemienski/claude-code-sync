"""GitHub operations using gh CLI and GitPython

Manages GitHub repository creation, remote configuration, and push/pull operations.
"""

import subprocess
from pathlib import Path
from typing import Optional, Dict
import click
from claude_sync.git_backend import get_repo


def check_gh_cli() -> bool:
    """Check if GitHub CLI (gh) is installed

    Returns:
        True if gh CLI is available
    """
    result = subprocess.run(
        ['gh', '--version'],
        capture_output=True
    )
    return result.returncode == 0


def get_github_username() -> Optional[str]:
    """Get authenticated GitHub username

    Returns:
        Username or None
    """
    try:
        result = subprocess.run(
            ['gh', 'api', 'user', '--jq', '.login'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def create_github_repository(
    name: str,
    private: bool = True,
    description: str = "Claude Code configurations and settings - private backup"
) -> Dict:
    """Create GitHub repository using gh CLI

    Args:
        name: Repository name
        private: Create as private repository
        description: Repository description

    Returns:
        Dict with name, ssh_url, clone_url, html_url

    Raises:
        click.ClickException: If creation fails
    """
    if not check_gh_cli():
        raise click.ClickException(
            "GitHub CLI (gh) not found. Install with: brew install gh\n"
            "Then authenticate with: gh auth login"
        )

    # Check authentication
    username = get_github_username()
    if not username:
        raise click.ClickException(
            "Not authenticated with GitHub. Run: gh auth login"
        )

    # Create repository
    cmd = [
        'gh', 'repo', 'create', name,
        '--description', description,
        '--clone=false'  # Don't auto-clone
    ]

    if private:
        cmd.append('--private')
    else:
        cmd.append('--public')

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        # Build repo info
        full_name = f"{username}/{name}"

        # Setup git to use gh authentication
        subprocess.run(['gh', 'auth', 'setup-git'], capture_output=True)

        return {
            'name': name,
            'full_name': full_name,
            'clone_url': f"https://github.com/{full_name}.git",  # Use HTTPS (gh CLI auth)
            'ssh_url': f"git@github.com:{full_name}.git",
            'html_url': f"https://github.com/{full_name}",
        }

    except subprocess.CalledProcessError as e:
        # Check if repo already exists
        if 'already exists' in e.stderr.lower():
            # Repo exists, get its info
            full_name = f"{username}/{name}"
            return {
                'name': name,
                'full_name': full_name,
                'ssh_url': f"git@github.com:{full_name}.git",
                'clone_url': f"https://github.com/{full_name}.git",
                'html_url': f"https://github.com/{full_name}",
                'already_exists': True
            }
        else:
            raise click.ClickException(f"Failed to create repository: {e.stderr}")


def add_git_remote(remote_name: str, url: str, set_upstream: bool = False):
    """Add Git remote to claude-sync repository

    Args:
        remote_name: Name for remote (e.g., 'origin')
        url: Git URL (SSH or HTTPS)
        set_upstream: Set as upstream branch

    Raises:
        click.ClickException: If operation fails
    """
    try:
        repo = get_repo()

        # Check if remote already exists
        if remote_name in [r.name for r in repo.remotes]:
            # Update URL
            remote = repo.remote(remote_name)
            remote.set_url(url)
            click.echo(f"  ✓ Updated remote '{remote_name}': {url}")
        else:
            # Create new remote
            repo.create_remote(remote_name, url)
            click.echo(f"  ✓ Added remote '{remote_name}': {url}")

        if set_upstream:
            # Set upstream branch
            repo.git.branch('--set-upstream-to', f'{remote_name}/main', 'main')

    except Exception as e:
        raise click.ClickException(f"Failed to add remote: {e}")


def push_to_git_remote(remote_name: str, branch: str = 'main', force: bool = False):
    """Push to Git remote using GitPython

    Args:
        remote_name: Remote name (e.g., 'origin')
        branch: Branch to push
        force: Force push

    Raises:
        click.ClickException: If push fails
    """
    try:
        # Ensure gh auth is configured for git
        subprocess.run(['gh', 'auth', 'setup-git'], capture_output=True)

        repo = get_repo()

        if remote_name not in [r.name for r in repo.remotes]:
            raise click.ClickException(
                f"Remote '{remote_name}' not found. "
                f"Run: claude-sync remote add {remote_name} <url>"
            )

        remote = repo.remote(remote_name)

        # Push with progress
        click.echo(f"Pushing to {remote_name} ({remote.url})...")

        # Set upstream and push
        push_args = [f'{branch}:{branch}']
        if force:
            push_args = ['--force'] + push_args

        push_infos = remote.push(
            refspec=push_args,
            set_upstream=True
        )

        # Check push result
        for info in push_infos:
            if info.flags & info.ERROR:
                raise click.ClickException(f"Push failed: {info.summary}")

        click.echo(f"  ✓ Pushed to {remote_name}/{branch}")

    except Exception as e:
        raise click.ClickException(f"Push failed: {e}")


def pull_from_git_remote(remote_name: str, branch: str = 'main'):
    """Pull from Git remote using GitPython

    Args:
        remote_name: Remote name (e.g., 'origin')
        branch: Branch to pull

    Raises:
        click.ClickException: If pull fails
    """
    try:
        # Ensure gh auth is configured for git
        subprocess.run(['gh', 'auth', 'setup-git'], capture_output=True)

        repo = get_repo()

        # If no remotes exist yet, treat as initial clone
        if not repo.remotes:
            raise click.ClickException(
                f"No remotes configured. "
                f"Run: claude-sync remote add {remote_name} <url>"
            )

        if remote_name not in [r.name for r in repo.remotes]:
            raise click.ClickException(
                f"Remote '{remote_name}' not found. "
                f"Run: claude-sync remote add {remote_name} <url>"
            )

        remote = repo.remote(remote_name)

        click.echo(f"Pulling from {remote_name} ({remote.url})...")

        # Fetch first
        remote.fetch()

        # If local repo is empty (no commits), do initial pull
        try:
            repo.head.commit
            has_commits = True
        except:
            has_commits = False

        if not has_commits:
            # Initial pull - set up tracking
            repo.git.pull(remote_name, branch, '--set-upstream')
            click.echo(f"  ✓ Initial pull from {remote_name}/{branch}")
        else:
            # Normal pull
            pull_info = remote.pull(branch)

            # Check for conflicts
            for info in pull_info:
                if info.flags & info.ERROR:
                    raise click.ClickException(f"Pull failed: {info.note}")

            click.echo(f"  ✓ Pulled from {remote_name}/{branch}")

    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(f"Pull failed: {e}")


def list_remotes() -> list:
    """List all configured remotes

    Returns:
        List of (name, url) tuples
    """
    try:
        repo = get_repo()
        return [(r.name, r.url) for r in repo.remotes]
    except Exception:
        return []

"""Git operations backend using GitPython

Wraps GitPython operations for repository management.
"""

from pathlib import Path
from typing import Optional
import git


def get_repo_dir() -> Path:
    """Get the claude-sync repository directory

    Returns:
        Path to ~/.claude-sync/repo/
    """
    return Path.home() / '.claude-sync' / 'repo'


def init_repository(force: bool = False) -> git.Repo:
    """Initialize Git repository

    Creates ~/.claude-sync/repo/ and initializes Git.

    Args:
        force: If True, reinitialize existing repository

    Returns:
        GitPython Repo object

    Raises:
        FileExistsError: If repository exists and force=False
    """
    repo_dir = get_repo_dir()

    if repo_dir.exists() and (repo_dir / '.git').exists() and not force:
        raise FileExistsError(f"Repository already exists at {repo_dir}. Use --force to reinitialize.")

    # Create parent directory
    repo_dir.parent.mkdir(parents=True, exist_ok=True)

    # Initialize or reinit
    if force and (repo_dir / '.git').exists():
        # Reinitialize
        repo = git.Repo(repo_dir)
    else:
        # Fresh init
        repo_dir.mkdir(exist_ok=True)
        repo = git.Repo.init(repo_dir)

    return repo


def get_repo() -> git.Repo:
    """Get existing repository

    Returns:
        GitPython Repo object

    Raises:
        FileNotFoundError: If repository doesn't exist
    """
    repo_dir = get_repo_dir()

    if not repo_dir.exists() or not (repo_dir / '.git').exists():
        raise FileNotFoundError(
            f"Repository not found at {repo_dir}. "
            "Run 'claude-sync init' first."
        )

    return git.Repo(repo_dir)


def add_all():
    """Stage all changes (like git add .)

    Adds all files in repository to Git index.
    """
    repo = get_repo()
    repo.git.add('.')


def commit(message: str) -> str:
    """Create Git commit

    Args:
        message: Commit message

    Returns:
        Short commit SHA (7 characters)

    Raises:
        RuntimeError: If no changes to commit
    """
    repo = get_repo()

    if not repo.is_dirty() and not repo.untracked_files:
        raise RuntimeError("No changes to commit. Run 'claude-sync add' first.")

    commit_obj = repo.index.commit(message)
    return commit_obj.hexsha[:7]


def get_status() -> dict:
    """Get repository status

    Returns:
        Dict with staged, modified, untracked files
    """
    repo = get_repo()

    return {
        'is_dirty': repo.is_dirty(),
        'untracked': repo.untracked_files,
        'modified': [item.a_path for item in repo.index.diff(None)],
        'staged': [item.a_path for item in repo.index.diff('HEAD')],
        'current_commit': repo.head.commit.hexsha[:7] if repo.head.is_valid() else None,
    }


def get_log(max_count: int = 10) -> list:
    """Get commit history

    Args:
        max_count: Maximum number of commits to return

    Returns:
        List of commit dicts with sha, message, date
    """
    repo = get_repo()

    commits = []
    for commit_obj in repo.iter_commits(max_count=max_count):
        commits.append({
            'sha': commit_obj.hexsha[:7],
            'message': commit_obj.message.strip(),
            'author': str(commit_obj.author),
            'date': commit_obj.committed_datetime.isoformat(),
        })

    return commits

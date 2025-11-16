"""claude-sync CLI commands

Git-like command interface for syncing Claude Code configurations.
"""

import click
from pathlib import Path
from claude_sync import discovery, staging, git_backend, apply as apply_module, validation, deployment, github_ops

@click.group()
@click.version_option(version='0.1.0', prog_name='claude-sync')
def cli():
    """Git-like version control for Claude Code configurations

    Sync skills, agents, commands, and configs across machines.

    Common commands:
      claude-sync init          Initialize sync repository
      claude-sync add --all     Stage all configurations
      claude-sync commit        Create snapshot
      claude-sync push          Deploy to remote
      claude-sync status        Show current state
    """
    pass


@cli.command()
@click.option('--force', is_flag=True, help='Reinitialize existing repository')
def init(force):
    """Initialize claude-sync repository

    Creates ~/.claude-sync/ directory with Git repository for
    version controlling Claude Code configurations.
    """
    try:
        # Initialize Git repository
        repo = git_backend.init_repository(force=force)
        sync_dir = Path.home() / '.claude-sync'

        click.echo(f"Initialized claude-sync repository in {sync_dir}/")
        click.echo("✓ Git repository created")
        click.echo("✓ Directory structure created")

        # Create ignore file
        ignore_file = git_backend.get_repo_dir() / '.claude-sync-ignore'
        ignore_file.write_text("""# Secrets and credentials
*.env
*.key
*.pem
**/settings.local.json

# Caches and logs
**/__pycache__/
**/*.pyc
**/logs/
**/cache/
.DS_Store

# Plugin repos (re-cloned on target)
plugins/repos/

# Sessions (opt-in only)
sessions/
""")

        # Run initial discovery
        inventory = discovery.discover_all()

        click.echo("")
        click.echo("Discovered:")
        click.echo(f"  {len(inventory['skills'])} skills")
        click.echo(f"  {len(inventory['agents'])} agents")
        click.echo(f"  {len(inventory['commands'])} commands")
        click.echo(f"  {len(inventory['configs'])} config files")
        click.echo(f"  {len(inventory['plugins'])} plugin configs")

        click.echo("")
        click.echo("Next steps:")
        click.echo("  claude-sync add --all      # Stage all discovered items")
        click.echo("  claude-sync commit -m 'Initial commit'")

    except FileExistsError as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"Error initializing repository: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--all', 'add_all', is_flag=True, help='Add all artifacts')
@click.option('--skills', is_flag=True, help='Add only skills')
@click.option('--agents', is_flag=True, help='Add only agents')
@click.option('--commands', is_flag=True, help='Add only commands')
@click.option('--config', is_flag=True, help='Add only global config')
def add(add_all, skills, agents, commands, config):
    """Stage changes for commit

    Discovers Claude Code artifacts and stages them for version control.
    Similar to 'git add'.
    """
    try:
        # Ensure repository exists
        git_backend.get_repo()

        click.echo("Discovering artifacts...")

        # Discover what to stage
        inventory = discovery.discover_all()

        # Determine what to stage based on flags
        if not any([add_all, skills, agents, commands, config]):
            click.echo("Error: Specify what to add (--all, --skills, etc.)", err=True)
            click.echo("Try: claude-sync add --all")
            raise click.Abort()

        # Stage selected artifacts
        counts = {}

        if add_all or skills:
            counts['skills'] = staging.stage_skills(inventory['skills'])

        if add_all or agents:
            counts['agents'] = staging.stage_agents(inventory['agents'])

        if add_all or commands:
            counts['commands'] = staging.stage_commands(inventory['commands'])

        if add_all or config:
            counts['configs'] = staging.stage_configs(inventory['configs'])

        if add_all:
            counts['plugins'] = staging.stage_plugins(inventory['plugins'])

        # Git add
        git_backend.add_all()

        click.echo("")
        click.echo("Staging complete:")
        for category, count in counts.items():
            if count > 0:
                click.echo(f"  ✓ {category.capitalize()}: {count} added")

        click.echo("")
        click.echo("Changes staged. Ready to commit.")
        click.echo("")
        click.echo("Next: claude-sync commit -m 'Your message'")

    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"Error staging artifacts: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('-m', '--message', required=True, help='Commit message')
@click.option('-a', '--all', 'commit_all', is_flag=True, help='Add all changes and commit')
def commit(message, commit_all):
    """Create snapshot of current state

    Creates a Git commit with staged changes.
    Similar to 'git commit'.
    """
    try:
        # If -a flag, stage all first
        if commit_all:
            click.echo("Staging all changes...")
            inventory = discovery.discover_all()
            staging.stage_all(inventory)
            git_backend.add_all()

        # Create commit
        commit_sha = git_backend.commit(message)

        # Get stats
        repo = git_backend.get_repo()
        commit_obj = repo.head.commit
        stats = commit_obj.stats.total

        click.echo(f"[{repo.active_branch.name} {commit_sha}] {message}")
        click.echo(f" {stats['files']} files changed, "
                   f"{stats['insertions']} insertions(+), "
                   f"{stats['deletions']} deletions(-)")

        click.echo("")
        click.echo(f"✓ Committed: {commit_sha}")

    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"Error creating commit: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument('remote')
@click.argument('branch', default='main')
@click.option('--force', is_flag=True, help='Force push')
@click.option('--dry-run', is_flag=True, help='Show what would be pushed')
def push(remote, branch, force, dry_run):
    """Push configurations to remote

    Pushes to Git remote (GitHub) or directly to Docker container.

    Examples:
        claude-sync push origin main              # Push to GitHub
        claude-sync push origin                   # Push to GitHub (main branch)
        claude-sync push docker://mycontainer     # Direct Docker deployment
    """
    try:
        if dry_run:
            click.echo(f"Would push to: {remote} {branch}")
            return

        # Parse remote type
        if remote.startswith('docker://'):
            # Legacy: Direct Docker deployment
            container_name = remote.replace('docker://', '')
            deployment.push_docker(container_name)

        elif remote.startswith('ssh://'):
            raise click.ClickException("SSH remotes not yet implemented.")

        else:
            # Assume it's a Git remote name (e.g., 'origin')
            click.echo(f"Pushing to Git remote: {remote}/{branch}")
            github_ops.push_to_git_remote(remote, branch, force)
            click.echo(f"\n✅ Pushed to {remote}")

    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
    except click.ClickException:
        raise
    except Exception as e:
        click.echo(f"Error pushing: {e}", err=True)
        raise click.Abort()


@cli.command()
def status():
    """Show current state

    Displays staged changes, untracked files, and remote sync status.
    Similar to 'git status'.
    """
    click.echo("TODO: Show status")


@cli.command()
@click.argument('file', required=False)
def diff(file):
    """Show differences

    Displays changes between working directory and repository.
    Similar to 'git diff'.
    """
    click.echo(f"TODO: Show diff{' for ' + file if file else ''}")


@cli.command()
@click.option('-n', '--number', type=int, help='Limit number of commits')
@click.option('--oneline', is_flag=True, help='Compact format')
def log(number, oneline):
    """Show commit history

    Displays commit history from the repository.
    Similar to 'git log'.
    """
    click.echo("TODO: Show log")


@cli.command()
@click.option('--format-only', is_flag=True, help='Only validate format (skip counts)')
@click.option('--sdk', is_flag=True, help='Run SDK validation (requires API key)')
def validate(format_only, sdk):
    """Validate deployment

    Checks that configurations are properly deployed and in correct format.

    By default, validates both file existence and Claude Code format.
    Use --sdk to also validate via Claude Agents SDK (requires ANTHROPIC_API_KEY).
    """
    try:
        import subprocess
        import sys
        from pathlib import Path

        # Always run format validation (proves Claude Code can parse)
        click.echo("\nRunning format validation...")
        script_path = Path(__file__).parent / 'scripts' / 'validate_claude_format.py'

        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True
        )

        print(result.stdout)

        if result.returncode != 0:
            click.echo("\n❌ Format validation failed", err=True)
            if result.stderr:
                click.echo(result.stderr, err=True)
            raise click.Abort()

        # Optionally run SDK validation
        if sdk:
            click.echo("\nRunning SDK validation...")
            sdk_script = Path(__file__).parent / 'scripts' / 'validate_claude_sdk.py'

            sdk_result = subprocess.run(
                [sys.executable, str(sdk_script)],
                capture_output=True,
                text=True
            )

            print(sdk_result.stdout)

            if sdk_result.returncode == 1:  # Failed (not skipped)
                click.echo("\n❌ SDK validation failed", err=True)
                raise click.Abort()
            elif sdk_result.returncode == 2:  # Skipped
                click.echo("\n⚠️  SDK validation skipped (see output above)")

        if not format_only:
            # Also run count validation
            click.echo("\nCounting deployed artifacts...")
            success, counts, errors = validation.validate()

            if not success:
                click.echo("\n❌ Count validation failed", err=True)
                for error in errors:
                    click.echo(f"  - {error}", err=True)
                raise click.Abort()
            else:
                click.echo(f"\n✅ Artifact counts verified")
                click.echo(f"  Skills: {counts['skills']}")
                click.echo(f"  Agents: {counts['agents']}")
                click.echo(f"  Commands: {counts['commands']}")

        click.echo("\n✅ All validations passed")

    except subprocess.SubprocessError as e:
        click.echo(f"Error running validation: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"Error during validation: {e}", err=True)
        raise click.Abort()


@cli.command('apply')
def apply_cmd():
    """Apply configurations from repository

    Copies configurations from ~/.claude-sync/repo/ to actual
    Claude Code locations (~/.claude/skills/, ~/.config/claude/, etc.).

    This makes synced configurations active on the current machine.
    """
    try:
        applied = apply_module.apply()

        click.echo("\nApplied configurations:")
        click.echo(f"  ✓ Skills: {applied['skills']}")
        click.echo(f"  ✓ Agents: {applied['agents']}")
        click.echo(f"  ✓ Commands: {applied['commands']}")
        click.echo(f"  ✓ Configs: {applied['configs']}")
        click.echo(f"  ✓ Plugins: {applied['plugins']}")

        click.echo("\n✅ Configurations applied successfully")

    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"Error applying configurations: {e}", err=True)
        raise click.Abort()


@cli.command('create-repo')
@click.option('--name', default='claude-code-settings', help='Repository name')
@click.option('--private/--public', default=True, help='Create private repo (default: private)')
def create_repo(name, private):
    """Create GitHub repository for syncing configs

    Creates a private GitHub repository and configures it as 'origin' remote.

    Requires: gh CLI (brew install gh) and authentication (gh auth login)
    """
    try:
        click.echo(f"Creating GitHub repository: {name}")
        click.echo(f"  Privacy: {'Private' if private else 'Public'}")

        # Create repository using gh CLI
        repo_info = github_ops.create_github_repository(name, private)

        if repo_info.get('already_exists'):
            click.echo(f"\n⚠️  Repository already exists: {repo_info['html_url']}")
        else:
            click.echo(f"\n✓ Repository created: {repo_info['html_url']}")

        # Add as origin remote
        click.echo("\nConfiguring remote...")
        github_ops.add_git_remote('origin', repo_info['ssh_url'], set_upstream=True)

        click.echo("\n✅ Repository ready for sync")
        click.echo(f"\nNext steps:")
        click.echo(f"  claude-sync push origin main    # Push your configs to GitHub")
        click.echo(f"\nOn other machines:")
        click.echo(f"  claude-sync init")
        click.echo(f"  claude-sync remote add origin {repo_info['ssh_url']}")
        click.echo(f"  claude-sync pull origin main")

    except click.ClickException:
        raise
    except Exception as e:
        click.echo(f"Error creating repository: {e}", err=True)
        raise click.Abort()


@cli.command('remote')
@click.argument('action', type=click.Choice(['add', 'remove', 'list', 'show']))
@click.argument('name', required=False)
@click.argument('url', required=False)
def remote(action, name, url):
    """Manage Git remotes

    Examples:
        claude-sync remote add origin git@github.com:user/repo.git
        claude-sync remote list
        claude-sync remote remove origin
    """
    try:
        if action == 'add':
            if not name or not url:
                click.echo("Error: 'remote add' requires NAME and URL", err=True)
                raise click.Abort()

            github_ops.add_git_remote(name, url)
            click.echo(f"✅ Remote '{name}' added")

        elif action == 'remove':
            if not name:
                click.echo("Error: 'remote remove' requires NAME", err=True)
                raise click.Abort()

            repo = git_backend.get_repo()
            repo.delete_remote(name)
            click.echo(f"✅ Remote '{name}' removed")

        elif action == 'list':
            remotes = github_ops.list_remotes()
            if not remotes:
                click.echo("No remotes configured")
            else:
                for remote_name, remote_url in remotes:
                    click.echo(f"{remote_name}\t{remote_url}")

        elif action == 'show':
            if not name:
                click.echo("Error: 'remote show' requires NAME", err=True)
                raise click.Abort()

            repo = git_backend.get_repo()
            if name not in [r.name for r in repo.remotes]:
                click.echo(f"Error: Remote '{name}' not found", err=True)
                raise click.Abort()

            remote_obj = repo.remote(name)
            click.echo(f"Remote: {name}")
            click.echo(f"  URL: {remote_obj.url}")
            click.echo(f"  Fetch: {remote_obj.url}")
            click.echo(f"  Push: {remote_obj.url}")

    except click.ClickException:
        raise
    except Exception as e:
        click.echo(f"Error managing remote: {e}", err=True)
        raise click.Abort()


@cli.command('pull')
@click.argument('remote', default='origin')
@click.argument('branch', default='main')
@click.option('--no-apply', is_flag=True, help="Don't apply after pulling")
@click.option('--strategy', type=click.Choice(['overwrite', 'keep-local']), default='overwrite',
              help='Conflict resolution strategy')
def pull(remote, branch, no_apply, strategy):
    """Pull configurations from remote repository

    Downloads latest configs from GitHub and optionally applies them.

    Examples:
        claude-sync pull origin main                    # Pull and apply
        claude-sync pull origin --no-apply              # Pull only
        claude-sync pull origin --strategy keep-local   # Don't overwrite existing
    """
    try:
        click.echo(f"Pulling from {remote} {branch}...")

        # Pull from Git remote
        github_ops.pull_from_git_remote(remote, branch)

        # Apply unless --no-apply
        if not no_apply:
            click.echo("\nApplying configurations...")
            applied = apply_module.apply()

            click.echo(f"\n✓ Applied: {applied['skills']} skills, {applied['agents']} agents, "
                       f"{applied['commands']} commands, {applied['configs']} configs")

            if strategy == 'keep-local':
                click.echo("\n⚠️  Strategy 'keep-local' not yet fully implemented")
                click.echo("   Currently overwrites existing files")

        click.echo("\n✅ Pull complete")

    except click.ClickException:
        raise
    except Exception as e:
        click.echo(f"Error pulling from remote: {e}", err=True)
        raise click.Abort()


def main():
    """Entry point for console_scripts"""
    cli()


if __name__ == '__main__':
    main()

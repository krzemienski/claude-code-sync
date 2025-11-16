#!/usr/bin/env python3
"""Claude Code CLI Entry Point"""

import argparse
import sys
from pathlib import Path
from src.session_manager import SessionManager
from src.config_loader import load_config


def main() -> int:
    """
    CLI entry point for Claude Code Orchestration System.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(
        description='Claude Code Orchestration System',
        epilog='Example: python3 -m src.cli --model sonnet-4-5 --message "Hello"'
    )

    parser.add_argument(
        '--model',
        default='sonnet-4-5',
        help='Model to use (default: sonnet-4-5)'
    )
    parser.add_argument(
        '--message',
        help='User message to send'
    )
    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume previous session'
    )
    parser.add_argument(
        '--project-path',
        default='.',
        help='Project path (default: current directory)'
    )
    parser.add_argument(
        '--list-sessions',
        action='store_true',
        help='List all sessions for this project'
    )

    args = parser.parse_args()

    try:
        # Load configuration (4-tier hierarchy with env var + apiKeyHelper support)
        config = load_config()
        model = config.get('model', args.model)
        print(f"Configuration loaded: model={model}")

        # Create session manager
        session_mgr = SessionManager(args.project_path)

        # Handle commands
        if args.list_sessions:
            sessions = session_mgr.list_sessions()
            print(f"\nSessions for project: {session_mgr.project_path}")
            print(f"Project hash: {session_mgr.project_hash}")
            print(f"\nFound {len(sessions)} session(s):")
            for session_file in sessions:
                print(f"  - {session_file.name}")
            return 0

        elif args.resume:
            # Resume existing session
            messages = session_mgr.resume_session()
            print(f"Session resumed with {len(messages)} messages")
            # TODO: Send messages to Claude API for continuation
            return 0

        else:
            # Create new session
            writer = session_mgr.create_session()

            if args.message:
                writer.write_user_message(args.message)
                print(f"\nMessage sent: {args.message}")
                # TODO: Send to Claude API and get response
                # TODO: Write assistant response to session

            print("\n✅ CLI execution complete")
            return 0

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())

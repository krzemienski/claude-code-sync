#!/usr/bin/env python3
"""Session Monitoring Script - Production Pattern

Monitors Claude Code session activity and collects metrics.
Part of production deployment patterns from specification.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from jsonl_parser import parse_jsonl_stream


def find_session_directories() -> List[Path]:
    """Find all project session directories"""
    base = Path.home() / '.config' / 'claude' / 'projects'
    if not base.exists():
        return []

    return [d for d in base.iterdir() if d.is_dir()]


def analyze_session_file(session_file: Path) -> Dict:
    """Analyze single session JSONL file"""
    messages = list(parse_jsonl_stream(str(session_file)))

    total_input_tokens = 0
    total_output_tokens = 0
    tool_calls = 0

    for msg in messages:
        if msg.data.get('role') == 'assistant':
            usage = msg.data.get('usage', {})
            total_input_tokens += usage.get('inputTokens', 0) or usage.get('input_tokens', 0)
            total_output_tokens += usage.get('outputTokens', 0) or usage.get('output_tokens', 0)

        if msg.data.get('type') == 'tool_call':
            tool_calls += 1

    return {
        'file': session_file.name,
        'messages': len(messages),
        'input_tokens': total_input_tokens,
        'output_tokens': total_output_tokens,
        'tool_calls': tool_calls,
        'last_modified': datetime.fromtimestamp(session_file.stat().st_mtime)
    }


def main():
    """Monitor all sessions and report metrics"""
    print("=" * 60)
    print("Claude Code Session Monitor")
    print("=" * 60)

    session_dirs = find_session_directories()
    print(f"\nProjects found: {len(session_dirs)}")

    total_sessions = 0
    total_messages = 0
    total_tokens = 0

    for project_dir in session_dirs:
        sessions = list(project_dir.glob('*.jsonl'))
        if not sessions:
            continue

        print(f"\nProject: {project_dir.name}")
        print(f"Sessions: {len(sessions)}")

        for session_file in sorted(sessions)[-5:]:  # Last 5 sessions
            stats = analyze_session_file(session_file)
            total_sessions += 1
            total_messages += stats['messages']
            total_tokens += stats['input_tokens'] + stats['output_tokens']

            print(f"  {stats['file']}: {stats['messages']} msgs, "
                  f"{stats['input_tokens']}↓/{stats['output_tokens']}↑ tokens, "
                  f"{stats['tool_calls']} tools")

    print("\n" + "=" * 60)
    print(f"Total sessions: {total_sessions}")
    print(f"Total messages: {total_messages}")
    print(f"Total tokens: {total_tokens:,}")
    print("=" * 60)


if __name__ == '__main__':
    main()

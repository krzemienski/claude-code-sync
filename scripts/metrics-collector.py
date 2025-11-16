#!/usr/bin/env python3
"""Metrics Collection - Production Pattern

Collects and reports Claude Code usage metrics for observability.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from jsonl_parser import parse_jsonl_stream


class MetricsCollector:
    """Collect usage metrics from sessions"""

    def __init__(self):
        self.metrics = {
            'total_sessions': 0,
            'total_messages': 0,
            'total_tokens': 0,
            'tool_usage': {},
            'daily_activity': {},
            'average_session_length': 0
        }

    def collect_from_session(self, session_file: Path):
        """Collect metrics from single session"""
        messages = list(parse_jsonl_stream(str(session_file)))
        self.metrics['total_sessions'] += 1
        self.metrics['total_messages'] += len(messages)

        for msg in messages:
            # Token accounting
            if msg.data.get('role') == 'assistant':
                usage = msg.data.get('usage', {})
                input_tokens = usage.get('inputTokens', 0) or usage.get('input_tokens', 0)
                output_tokens = usage.get('outputTokens', 0) or usage.get('output_tokens', 0)
                self.metrics['total_tokens'] += input_tokens + output_tokens

            # Tool usage tracking
            if msg.data.get('type') == 'tool_call':
                tool = msg.data.get('tool', 'unknown')
                self.metrics['tool_usage'][tool] = self.metrics['tool_usage'].get(tool, 0) + 1

            # Daily activity
            timestamp = msg.data.get('timestamp', '')
            if timestamp:
                date = timestamp.split('T')[0]
                self.metrics['daily_activity'][date] = self.metrics['daily_activity'].get(date, 0) + 1

    def generate_report(self) -> str:
        """Generate metrics report"""
        if self.metrics['total_sessions'] > 0:
            self.metrics['average_session_length'] = (
                self.metrics['total_messages'] / self.metrics['total_sessions']
            )

        # Top tools
        sorted_tools = sorted(
            self.metrics['tool_usage'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        report = f"""
╔══════════════════════════════════════════════════════════════╗
║           Claude Code Usage Metrics Report                   ║
╚══════════════════════════════════════════════════════════════╝

Total Sessions: {self.metrics['total_sessions']}
Total Messages: {self.metrics['total_messages']:,}
Total Tokens: {self.metrics['total_tokens']:,}
Avg Messages/Session: {self.metrics['average_session_length']:.1f}

Top Tools Used:
"""
        for tool, count in sorted_tools:
            report += f"  {tool}: {count} calls\n"

        report += f"\nDaily Activity (last 7 days):\n"
        recent_days = sorted(self.metrics['daily_activity'].items())[-7:]
        for date, count in recent_days:
            report += f"  {date}: {count} messages\n"

        return report


def main():
    """Collect metrics from all sessions"""
    base = Path.home() / '.config' / 'claude' / 'projects'

    if not base.exists():
        print("No sessions found")
        return

    collector = MetricsCollector()

    # Collect from all projects
    for project_dir in base.iterdir():
        if not project_dir.is_dir():
            continue

        for session_file in project_dir.glob('*.jsonl'):
            try:
                collector.collect_from_session(session_file)
            except Exception as e:
                print(f"Warning: Failed to process {session_file}: {e}")

    # Generate and print report
    print(collector.generate_report())

    # Save metrics to JSON
    metrics_file = Path('metrics-report.json')
    with open(metrics_file, 'w') as f:
        json.dump(collector.metrics, f, indent=2)

    print(f"\n✅ Metrics saved to: {metrics_file}")


if __name__ == '__main__':
    main()

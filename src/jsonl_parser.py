#!/usr/bin/env python3
"""
JSONL Session Parser - Streaming Parser for Claude Conversation Sessions

Parses JSONL session files containing user messages, assistant messages,
tool calls, and tool results. Implements corruption recovery and streaming
parse for memory efficiency.

Based on: docs/architecture/jsonl-storage-design.md
"""

import json
import sys
from typing import Iterator, Dict, Any
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class ParsedMessage:
    """Represents a parsed message from JSONL file."""
    type: str
    data: Dict[str, Any]
    line_number: int


def parse_jsonl_stream(session_file: str) -> Iterator[ParsedMessage]:
    """
    Stream parse JSONL file, skipping corrupted lines.

    Yields:
        ParsedMessage objects with validated message types

    Notes:
        - Corrupt lines logged to stderr as warnings
        - Parsing continues after errors
        - No full-file load (memory efficient)
        - Supports types: user, assistant, tool_call, tool_result
    """
    try:
        with open(session_file, 'r', encoding='utf-8') as f:
            line_number = 0

            for line in f:
                line_number += 1

                # Skip empty lines
                if not line.strip():
                    continue

                try:
                    message_dict = json.loads(line)

                    # Validate message structure
                    if not isinstance(message_dict, dict):
                        print(
                            f"WARNING: Line {line_number} is not a JSON object, skipping",
                            file=sys.stderr
                        )
                        continue

                    # Extract and validate message type
                    message_type = message_dict.get("type") or message_dict.get("role")

                    if not message_type:
                        print(
                            f"WARNING: Line {line_number} missing 'type' or 'role' field, skipping",
                            file=sys.stderr
                        )
                        continue

                    # Normalize role to type
                    if "role" in message_dict and "type" not in message_dict:
                        message_dict["type"] = message_dict["role"]
                        message_type = message_dict["type"]

                    # Validate against known message types
                    valid_types = {"user", "assistant", "tool_call", "tool_result"}
                    if message_type not in valid_types:
                        print(
                            f"WARNING: Invalid message type '{message_type}' at line {line_number}, skipping",
                            file=sys.stderr
                        )
                        continue

                    # Yield validated message
                    yield ParsedMessage(
                        type=message_type,
                        data=message_dict,
                        line_number=line_number
                    )

                except json.JSONDecodeError as e:
                    print(
                        f"WARNING: Corrupted JSON at line {line_number}: {e}",
                        file=sys.stderr
                    )
                    print(f"  Line content: {line[:100]}...", file=sys.stderr)
                    continue

                except Exception as e:
                    print(
                        f"ERROR: Failed to parse message at line {line_number}: {e}",
                        file=sys.stderr
                    )
                    print(f"  Line content: {line[:100]}...", file=sys.stderr)
                    continue

    except FileNotFoundError:
        print(f"ERROR: Session file not found: {session_file}", file=sys.stderr)
        sys.exit(1)
    except PermissionError:
        print(f"ERROR: Permission denied reading: {session_file}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to open session file: {e}", file=sys.stderr)
        sys.exit(1)


def format_token_info(message_data: Dict[str, Any]) -> str:
    """Format token usage information for display."""
    if "usage" in message_data:
        usage = message_data["usage"]
        return (
            f"  Tokens: input={usage.get('input_tokens', 0)}, "
            f"output={usage.get('output_tokens', 0)}, "
            f"cache_creation={usage.get('cache_creation_tokens', 0)}, "
            f"cache_read={usage.get('cache_read_tokens', 0)}"
        )
    elif "inputTokens" in message_data or "outputTokens" in message_data:
        # Handle alternative token format
        return (
            f"  Tokens: input={message_data.get('inputTokens', 0)}, "
            f"output={message_data.get('outputTokens', 0)}"
        )
    return ""


def display_session(session_file: str) -> None:
    """
    Parse and display session messages in human-readable format.

    Args:
        session_file: Path to JSONL session file
    """
    print(f"=== Parsing session: {session_file} ===\n")

    message_count = 0
    type_counts = {}

    for message in parse_jsonl_stream(session_file):
        message_count += 1
        type_counts[message.type] = type_counts.get(message.type, 0) + 1

        # Display message
        print(f"[{message.line_number}] {message.type.upper()}")

        # Display content if present
        if "content" in message.data and message.data["content"]:
            content = message.data["content"]
            # Truncate long content
            if len(content) > 200:
                content = content[:200] + "..."
            print(f"  Content: {content}")

        # Display token info
        token_info = format_token_info(message.data)
        if token_info:
            print(token_info)

        # Display model if present
        if "model" in message.data:
            print(f"  Model: {message.data['model']}")

        # Display timestamp if present
        if "timestamp" in message.data:
            print(f"  Timestamp: {message.data['timestamp']}")

        print()  # Blank line between messages

    # Summary
    print("=== Session Summary ===")
    print(f"Total messages: {message_count}")
    print("Message types:")
    for msg_type, count in sorted(type_counts.items()):
        print(f"  {msg_type}: {count}")


def main():
    """Main entry point for JSONL parser CLI."""
    if len(sys.argv) < 2:
        print("Usage: python3 jsonl_parser.py <session-file.jsonl>", file=sys.stderr)
        print("\nParses and displays JSONL session files with corruption recovery.", file=sys.stderr)
        sys.exit(1)

    session_file = sys.argv[1]
    display_session(session_file)


if __name__ == "__main__":
    main()

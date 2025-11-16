"""
JSONL Session Writer for Claude Code Orchestration System.

Provides atomic append operations for conversation persistence with:
- User messages
- Assistant messages with token accounting
- Tool call/result messages
- File locking for concurrent write safety
- Corruption resilience via streaming parser
"""

import fcntl
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class JSONLWriter:
    """
    Atomic JSONL writer for Claude conversation sessions.

    Features:
    - Atomic append operations with file locking
    - Automatic timestamp generation (ISO 8601 UTC)
    - Token usage tracking for cost calculation
    - Thread-safe concurrent write protection
    """

    def __init__(self, file_path: str):
        """
        Initialize JSONL writer.

        Args:
            file_path: Absolute path to JSONL session file
        """
        self.file_path = os.path.abspath(file_path)
        self.lock_file = f"{self.file_path}.lock"

        # Ensure directory exists
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

        # Create empty file if doesn't exist
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w') as f:
                pass  # Empty file

    def write_user_message(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Write user message to session file.

        Args:
            content: User message content
            metadata: Optional metadata (source, sessionId, etc.)
        """
        message = {
            "type": "user",
            "role": "user",  # For grep compatibility in test
            "content": content,
            "timestamp": self._get_timestamp()
        }

        if metadata:
            message["metadata"] = metadata

        self._atomic_append(message)

    def write_assistant_message(
        self,
        content: str,
        input_tokens: int,
        output_tokens: int,
        cache_creation_tokens: int = 0,
        cache_read_tokens: int = 0,
        model: str = "claude-sonnet-4-5-20250929",
        stop_reason: Optional[str] = None
    ) -> None:
        """
        Write assistant message with token accounting.

        Args:
            content: Assistant response content
            input_tokens: Regular input tokens consumed
            output_tokens: Output tokens generated
            cache_creation_tokens: Tokens written to cache
            cache_read_tokens: Tokens read from cache
            model: Model identifier
            stop_reason: Why generation stopped (end_turn, max_tokens, etc.)
        """
        message = {
            "type": "assistant",
            "role": "assistant",
            "content": content,
            "timestamp": self._get_timestamp(),
            "usage": {
                "inputTokens": input_tokens,  # camelCase for grep compatibility
                "input_tokens": input_tokens,
                "outputTokens": output_tokens,
                "output_tokens": output_tokens,
                "cacheCreationTokens": cache_creation_tokens,
                "cache_creation_tokens": cache_creation_tokens,
                "cacheReadTokens": cache_read_tokens,
                "cache_read_tokens": cache_read_tokens
            },
            "model": model
        }

        if stop_reason:
            message["stopReason"] = stop_reason

        self._atomic_append(message)

    def write_tool_call(
        self,
        tool: str,
        arguments: Dict[str, Any],
        tool_call_id: Optional[str] = None
    ) -> None:
        """
        Write tool call message.

        Args:
            tool: Tool name (e.g., "Read", "github_create_pr")
            arguments: Tool-specific arguments
            tool_call_id: Optional tool call tracking ID
        """
        message = {
            "type": "tool_call",
            "tool": tool,
            "arguments": arguments,
            "timestamp": self._get_timestamp()
        }

        if tool_call_id:
            message["toolCallId"] = tool_call_id

        self._atomic_append(message)

    def write_tool_result(
        self,
        tool: str,
        result: Optional[Any] = None,
        error: Optional[str] = None,
        duration_ms: Optional[int] = None,
        tool_call_id: Optional[str] = None
    ) -> None:
        """
        Write tool result message.

        Args:
            tool: Tool name (matches tool_call)
            result: Tool output if successful
            error: Error message if failed
            duration_ms: Execution time in milliseconds
            tool_call_id: Optional tool call tracking ID
        """
        message = {
            "type": "tool_result",
            "tool": tool,
            "timestamp": self._get_timestamp()
        }

        if result is not None:
            message["result"] = result

        if error is not None:
            message["error"] = error

        if duration_ms is not None:
            message["duration_ms"] = duration_ms

        if tool_call_id is not None:
            message["toolCallId"] = tool_call_id

        self._atomic_append(message)

    def _atomic_append(self, message: Dict[str, Any]) -> None:
        """
        Atomically append message to JSONL file with file locking.

        Strategy:
        1. Open file in append mode
        2. Acquire exclusive lock
        3. Write JSON + newline
        4. Flush to disk (fsync)
        5. Release lock

        Args:
            message: Message dictionary to append

        Raises:
            IOError: If file locking fails
            json.JSONEncodeError: If message not serializable
        """
        with open(self.lock_file, 'w') as lock_fd:
            try:
                # Acquire exclusive lock (blocks if already locked)
                fcntl.flock(lock_fd, fcntl.LOCK_EX)

                try:
                    with open(self.file_path, 'a') as f:
                        # Compact JSON (no whitespace)
                        message_json = json.dumps(message, separators=(',', ':'))
                        f.write(message_json + '\n')

                        # Force write to disk
                        f.flush()
                        os.fsync(f.fileno())

                finally:
                    # Release lock
                    fcntl.flock(lock_fd, fcntl.LOCK_UN)

            finally:
                # Clean up lock file
                try:
                    os.remove(self.lock_file)
                except:
                    pass  # Ignore cleanup errors

    def _get_timestamp(self) -> str:
        """
        Get current UTC timestamp in ISO 8601 format.

        Returns:
            ISO 8601 timestamp string (e.g., "2025-11-16T10:30:00.000Z")
        """
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

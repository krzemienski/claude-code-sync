"""
Unit tests for JSONL Writer.

Tests cover:
- User message writing
- Assistant message writing with token accounting
- Tool call/result message writing
- Atomic file operations
- Concurrent write safety
- Timestamp generation
- File creation and permissions
"""

import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

# Add src to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.jsonl_writer import JSONLWriter


class TestJSONLWriter(unittest.TestCase):
    """Unit tests for JSONLWriter class."""

    def setUp(self):
        """Create temporary file for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "test-session.jsonl")
        self.writer = JSONLWriter(self.test_file)

    def tearDown(self):
        """Clean up temporary files."""
        # Remove test file and lock file
        for file_path in [self.test_file, f"{self.test_file}.lock"]:
            if os.path.exists(file_path):
                os.remove(file_path)

        # Remove temp directory
        os.rmdir(self.temp_dir)

    def _read_jsonl(self):
        """Read and parse JSONL file."""
        messages = []
        with open(self.test_file, 'r') as f:
            for line in f:
                if line.strip():
                    messages.append(json.loads(line))
        return messages

    def test_file_creation(self):
        """Test that file is created on initialization."""
        self.assertTrue(os.path.exists(self.test_file))
        self.assertEqual(os.path.getsize(self.test_file), 0)

    def test_write_user_message(self):
        """Test writing user message."""
        self.writer.write_user_message("Hello, Claude!")

        messages = self._read_jsonl()
        self.assertEqual(len(messages), 1)

        msg = messages[0]
        self.assertEqual(msg["type"], "user")
        self.assertEqual(msg["role"], "user")
        self.assertEqual(msg["content"], "Hello, Claude!")
        self.assertIn("timestamp", msg)

    def test_write_user_message_with_metadata(self):
        """Test writing user message with metadata."""
        metadata = {"source": "cli", "sessionId": "test-123"}
        self.writer.write_user_message("Test message", metadata=metadata)

        messages = self._read_jsonl()
        msg = messages[0]
        self.assertEqual(msg["metadata"], metadata)

    def test_write_assistant_message(self):
        """Test writing assistant message with token accounting."""
        self.writer.write_assistant_message(
            content="I'll help you with that.",
            input_tokens=100,
            output_tokens=50,
            cache_creation_tokens=25,
            cache_read_tokens=10
        )

        messages = self._read_jsonl()
        self.assertEqual(len(messages), 1)

        msg = messages[0]
        self.assertEqual(msg["type"], "assistant")
        self.assertEqual(msg["content"], "I'll help you with that.")
        self.assertEqual(msg["model"], "claude-sonnet-4-5-20250929")

        # Verify token usage
        usage = msg["usage"]
        self.assertEqual(usage["inputTokens"], 100)
        self.assertEqual(usage["input_tokens"], 100)
        self.assertEqual(usage["outputTokens"], 50)
        self.assertEqual(usage["output_tokens"], 50)
        self.assertEqual(usage["cacheCreationTokens"], 25)
        self.assertEqual(usage["cache_creation_tokens"], 25)
        self.assertEqual(usage["cacheReadTokens"], 10)
        self.assertEqual(usage["cache_read_tokens"], 10)

    def test_write_assistant_message_with_stop_reason(self):
        """Test writing assistant message with stop reason."""
        self.writer.write_assistant_message(
            content="Response",
            input_tokens=100,
            output_tokens=50,
            stop_reason="tool_use"
        )

        messages = self._read_jsonl()
        msg = messages[0]
        self.assertEqual(msg["stopReason"], "tool_use")

    def test_write_tool_call(self):
        """Test writing tool call message."""
        self.writer.write_tool_call(
            tool="Read",
            arguments={"file_path": "/path/to/file.py"},
            tool_call_id="call_123"
        )

        messages = self._read_jsonl()
        msg = messages[0]
        self.assertEqual(msg["type"], "tool_call")
        self.assertEqual(msg["tool"], "Read")
        self.assertEqual(msg["arguments"], {"file_path": "/path/to/file.py"})
        self.assertEqual(msg["toolCallId"], "call_123")

    def test_write_tool_result_success(self):
        """Test writing successful tool result."""
        self.writer.write_tool_result(
            tool="Read",
            result="file contents here",
            duration_ms=123,
            tool_call_id="call_123"
        )

        messages = self._read_jsonl()
        msg = messages[0]
        self.assertEqual(msg["type"], "tool_result")
        self.assertEqual(msg["tool"], "Read")
        self.assertEqual(msg["result"], "file contents here")
        self.assertEqual(msg["duration_ms"], 123)
        self.assertEqual(msg["toolCallId"], "call_123")
        self.assertNotIn("error", msg)

    def test_write_tool_result_error(self):
        """Test writing failed tool result."""
        self.writer.write_tool_result(
            tool="Read",
            error="File not found: /path/to/file.py",
            duration_ms=50
        )

        messages = self._read_jsonl()
        msg = messages[0]
        self.assertEqual(msg["error"], "File not found: /path/to/file.py")
        self.assertNotIn("result", msg)

    def test_multiple_messages(self):
        """Test writing multiple messages in sequence."""
        self.writer.write_user_message("First message")
        self.writer.write_assistant_message("Response", input_tokens=10, output_tokens=5)
        self.writer.write_tool_call("Read", {"file_path": "/test.py"})
        self.writer.write_tool_result("Read", result="contents")

        messages = self._read_jsonl()
        self.assertEqual(len(messages), 4)
        self.assertEqual(messages[0]["type"], "user")
        self.assertEqual(messages[1]["type"], "assistant")
        self.assertEqual(messages[2]["type"], "tool_call")
        self.assertEqual(messages[3]["type"], "tool_result")

    def test_timestamp_format(self):
        """Test that timestamps are in correct ISO 8601 format."""
        self.writer.write_user_message("Test")

        messages = self._read_jsonl()
        timestamp = messages[0]["timestamp"]

        # Verify format: YYYY-MM-DDTHH:MM:SS.sssZ
        self.assertRegex(timestamp, r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$')

        # Verify it's a valid datetime
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        self.assertIsNotNone(dt)

    def test_compact_json_format(self):
        """Test that JSON is compact (no unnecessary whitespace)."""
        self.writer.write_user_message("Test")

        with open(self.test_file, 'r') as f:
            line = f.readline()

        # Compact JSON should not have spaces after separators
        self.assertNotIn(', ', line)
        self.assertNotIn(': ', line)

    def test_newline_termination(self):
        """Test that each message ends with newline."""
        self.writer.write_user_message("Test")

        with open(self.test_file, 'rb') as f:
            content = f.read()

        # File should end with newline
        self.assertTrue(content.endswith(b'\n'))

    def test_atomic_append(self):
        """Test that appends are atomic (file always valid)."""
        # Write multiple messages
        for i in range(10):
            self.writer.write_user_message(f"Message {i}")

        # Verify all messages are valid JSON
        messages = self._read_jsonl()
        self.assertEqual(len(messages), 10)

        for i, msg in enumerate(messages):
            self.assertEqual(msg["content"], f"Message {i}")

    def test_directory_creation(self):
        """Test that parent directories are created automatically."""
        nested_path = os.path.join(self.temp_dir, "a", "b", "c", "session.jsonl")
        writer = JSONLWriter(nested_path)
        writer.write_user_message("Test")

        self.assertTrue(os.path.exists(nested_path))

        # Clean up
        os.remove(nested_path)
        os.removedirs(os.path.dirname(nested_path))

    def test_empty_content_allowed(self):
        """Test that empty content is allowed."""
        self.writer.write_user_message("")

        messages = self._read_jsonl()
        self.assertEqual(messages[0]["content"], "")

    def test_special_characters_in_content(self):
        """Test handling of special characters in content."""
        special_content = 'Test "quotes" and \'apostrophes\' and\nnewlines\tand\ttabs'
        self.writer.write_user_message(special_content)

        messages = self._read_jsonl()
        self.assertEqual(messages[0]["content"], special_content)

    def test_large_content(self):
        """Test handling of large content."""
        large_content = "A" * 100000  # 100KB
        self.writer.write_user_message(large_content)

        messages = self._read_jsonl()
        self.assertEqual(messages[0]["content"], large_content)


if __name__ == '__main__':
    unittest.main()

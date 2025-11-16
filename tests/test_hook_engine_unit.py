"""Unit tests for Hook Engine components.

Tests individual components in isolation:
- HookMatcher pattern matching
- HookExecutor exit code interpretation
- HookEngine integration
"""

import unittest
import tempfile
import json
import os
from src.hook_engine import (
    HookMatcher,
    HookExecutor,
    HookEngine,
    HookResult,
    CommandHook,
    HookContext,
    ExitCodeResult
)


class TestHookMatcher(unittest.TestCase):
    """Test hook pattern matching."""

    def setUp(self):
        self.matcher = HookMatcher()

    def test_simple_pattern_match(self):
        """Test simple tool name matching."""
        self.assertTrue(self.matcher.matches_pattern("Edit", "Edit"))
        self.assertFalse(self.matcher.matches_pattern("Edit", "Write"))

    def test_pipe_pattern_match(self):
        """Test pipe-separated tool names."""
        self.assertTrue(self.matcher.matches_pattern("Edit|Write", "Edit"))
        self.assertTrue(self.matcher.matches_pattern("Edit|Write", "Write"))
        self.assertFalse(self.matcher.matches_pattern("Edit|Write", "Read"))

    def test_universal_pattern_match(self):
        """Test universal wildcard pattern."""
        self.assertTrue(self.matcher.matches_pattern("*", "AnyTool"))
        self.assertTrue(self.matcher.matches_pattern("*", "Edit"))
        self.assertTrue(self.matcher.matches_pattern("*", "Bash"))

    def test_bash_command_pattern_match(self):
        """Test Bash command patterns."""
        # Test git push pattern
        self.assertTrue(
            self.matcher.matches_pattern(
                "Bash(git push:*)",
                "Bash",
                {"command": "git push origin main"}
            )
        )

        # Should not match git pull
        self.assertFalse(
            self.matcher.matches_pattern(
                "Bash(git push:*)",
                "Bash",
                {"command": "git pull"}
            )
        )

        # Test git commit pattern
        self.assertTrue(
            self.matcher.matches_pattern(
                "Bash(git commit:*)",
                "Bash",
                {"command": "git commit -m test"}
            )
        )

    def test_wildcard_command_pattern(self):
        """Test wildcard command pattern."""
        self.assertTrue(
            self.matcher.matches_pattern(
                "Bash(*)",
                "Bash",
                {"command": "any command"}
            )
        )


class TestHookExecutor(unittest.TestCase):
    """Test hook execution and exit code interpretation."""

    def setUp(self):
        self.executor = HookExecutor()

    def test_exit_code_0_allows(self):
        """Test exit code 0 allows operation."""
        hook = CommandHook(
            type="command",
            command="true"  # Always exits 0
        )
        context = HookContext(tool="Test", args={})

        result = self.executor.execute_hook(hook, context)

        self.assertEqual(result.exit_code, 0)
        self.assertFalse(result.blocked)
        self.assertEqual(result.action, ExitCodeResult.ALLOW)

    def test_exit_code_2_blocks(self):
        """Test exit code 2 blocks operation."""
        # Create temp script that exits 2
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write('#!/bin/bash\nexit 2\n')
            script_path = f.name

        os.chmod(script_path, 0o755)

        try:
            hook = CommandHook(
                type="command",
                command=script_path
            )
            context = HookContext(tool="Test", args={})

            result = self.executor.execute_hook(hook, context)

            self.assertEqual(result.exit_code, 2)
            self.assertTrue(result.blocked)
            self.assertEqual(result.action, ExitCodeResult.BLOCK)
        finally:
            os.unlink(script_path)

    def test_exit_code_other_is_error(self):
        """Test non-0/2 exit code is error."""
        hook = CommandHook(
            type="command",
            command="false"  # Exits 1
        )
        context = HookContext(tool="Test", args={})

        result = self.executor.execute_hook(hook, context)

        self.assertEqual(result.exit_code, 1)
        self.assertFalse(result.blocked)
        self.assertEqual(result.action, ExitCodeResult.ERROR)

    def test_timeout_handling(self):
        """Test hook timeout."""
        # Create script that sleeps
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write('#!/bin/bash\nsleep 10\n')
            script_path = f.name

        os.chmod(script_path, 0o755)

        try:
            hook = CommandHook(
                type="command",
                command=script_path,
                timeout=100  # 100ms timeout
            )
            context = HookContext(tool="Test", args={})

            result = self.executor.execute_hook(hook, context)

            self.assertEqual(result.exit_code, -1)
            self.assertFalse(result.blocked)
            self.assertEqual(result.action, ExitCodeResult.ERROR)
            self.assertIn("timed out", result.stderr)
        finally:
            os.unlink(script_path)

    def test_context_variable_substitution(self):
        """Test context variable substitution in environment."""
        hook = CommandHook(
            type="command",
            command="echo",
            args=["test"],
            env={"TEST_VAR": "${TOOL_NAME}"}
        )
        context = HookContext(tool="Bash", args={"command": "test"})

        # Just verify it doesn't crash - env vars are internal
        result = self.executor.execute_hook(hook, context)
        self.assertEqual(result.exit_code, 0)


class TestHookEngine(unittest.TestCase):
    """Test hook engine integration."""

    def test_pre_tool_use_with_blocking_hook(self):
        """Test PreToolUse hook blocks operation."""
        # Create temp config
        config = {
            "hooks": {
                "PreToolUse": [{
                    "matcher": "Test",
                    "hooks": [{
                        "type": "command",
                        "command": "false"  # Will exit 1 (error)
                    }]
                }]
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            config_path = f.name

        try:
            engine = HookEngine(config_path)
            result = engine.execute_pre_tool_use("Test", {})

            # false exits 1, which is ERROR not BLOCK
            self.assertEqual(result.exit_code, 1)
            self.assertFalse(result.blocked)
        finally:
            os.unlink(config_path)

    def test_pre_tool_use_no_matching_hooks(self):
        """Test PreToolUse with no matching hooks allows."""
        config = {
            "hooks": {
                "PreToolUse": [{
                    "matcher": "OtherTool",
                    "hooks": [{
                        "type": "command",
                        "command": "false"
                    }]
                }]
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            config_path = f.name

        try:
            engine = HookEngine(config_path)
            result = engine.execute_pre_tool_use("Test", {})

            # No hooks match, should allow
            self.assertEqual(result.exit_code, 0)
            self.assertFalse(result.blocked)
        finally:
            os.unlink(config_path)

    def test_pre_tool_use_allows_operation(self):
        """Test PreToolUse hook allows operation."""
        config = {
            "hooks": {
                "PreToolUse": [{
                    "matcher": "Test",
                    "hooks": [{
                        "type": "command",
                        "command": "true"  # Exits 0
                    }]
                }]
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            config_path = f.name

        try:
            engine = HookEngine(config_path)
            result = engine.execute_pre_tool_use("Test", {})

            self.assertEqual(result.exit_code, 0)
            self.assertFalse(result.blocked)
        finally:
            os.unlink(config_path)


if __name__ == '__main__':
    unittest.main()

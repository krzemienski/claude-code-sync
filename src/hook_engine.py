"""Hook Execution Engine - Validation hooks for Claude Code Orchestration System.

Implements validation hooks with exit code interpretation:
- Exit 0: Allow operation
- Exit 2: Block operation
- Other: Error
"""

import json
import subprocess
import os
import shlex
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class ExitCodeResult(Enum):
    """Exit code interpretation for hook results."""
    ALLOW = 0
    BLOCK = 2
    ERROR = -1


@dataclass
class HookResult:
    """Result of hook execution."""
    exit_code: int
    stdout: str
    stderr: str
    action: ExitCodeResult
    blocked: bool


@dataclass
class CommandHook:
    """Command hook configuration."""
    type: str
    command: str
    args: List[str] = None
    env: Dict[str, str] = None
    timeout: int = 5000
    continue_on_error: bool = False

    def __post_init__(self):
        if self.args is None:
            self.args = []
        if self.env is None:
            self.env = {}


@dataclass
class HookContext:
    """Context for hook execution."""
    tool: str
    args: Dict[str, Any]


class HookMatcher:
    """Match tool invocations against hook patterns."""

    def matches_pattern(self, pattern: str, tool: str, args: Dict = None) -> bool:
        """
        Check if tool invocation matches hook pattern.

        Pattern Syntax:
        - Literal: "Edit" matches only Edit()
        - Pipe: "Edit|Write" matches Edit() or Write()
        - Wildcard: "Bash(*)" matches any Bash command
        - Specific: "Bash(git push:*)" matches git push with any args
        - Universal: "*" matches all tools

        Args:
            pattern: Hook matcher pattern
            tool: Tool name (e.g., "Edit", "Bash")
            args: Tool arguments (optional)

        Returns:
            True if pattern matches tool invocation
        """
        # Universal matcher
        if pattern == "*":
            return True

        # Parse pattern
        if "(" in pattern:
            # Pattern with arguments: "Bash(git push:*)"
            tool_pattern, arg_pattern = pattern.split("(", 1)
            arg_pattern = arg_pattern.rstrip(")")

            # Check tool name
            if not self._matches_tool_name(tool_pattern, tool):
                return False

            # Check arguments
            if args and "command" in args:
                return self._matches_command(arg_pattern, args["command"])
            else:
                return True  # No args to check

        else:
            # Simple pattern: "Edit|Write"
            return self._matches_tool_name(pattern, tool)

    def _matches_tool_name(self, pattern: str, tool: str) -> bool:
        """Match tool name against pattern (supports pipe separator)."""
        # Split on pipe
        alternatives = pattern.split("|")

        # Check if tool matches any alternative
        return tool in alternatives

    def _matches_command(self, pattern: str, command: str) -> bool:
        """
        Match command string against pattern.

        Pattern Syntax:
        - "*": Match any command
        - "git push:*": Match "git push" with any args
        - "git commit:*": Match "git commit" with any args
        """
        if pattern == "*":
            return True

        # Convert glob pattern to regex
        # "git push:*" → "^git push"
        if pattern.endswith(":*"):
            prefix = pattern[:-2]  # Remove ":*"
            return command.startswith(prefix)

        # Exact match
        return pattern == command


class HookExecutor:
    """Execute validation hooks with exit code interpretation."""

    def execute_hook(
        self,
        hook: CommandHook,
        context: HookContext
    ) -> HookResult:
        """
        Execute hook command and interpret exit code.

        Exit Code Rules:
        - 0: Success, allow operation
        - 2: Block operation (quality gate failed)
        - Other: Error, report to user

        Args:
            hook: Hook configuration
            context: Execution context (tool, args, env vars)

        Returns:
            HookResult with exit code, stdout, stderr, action
        """
        # Build command
        command = [hook.command] + hook.args

        # Build environment
        env = {**os.environ, **(hook.env or {})}

        # Substitute context variables in env
        env = self._substitute_context_vars(env, context)

        # Execute command with timeout
        try:
            result = subprocess.run(
                command,
                env=env,
                capture_output=True,
                text=True,
                timeout=hook.timeout / 1000.0,  # Convert ms to seconds
                shell=False  # NEVER use shell=True (security)
            )

            exit_code = result.returncode
            stdout = result.stdout
            stderr = result.stderr

        except subprocess.TimeoutExpired:
            return HookResult(
                exit_code=-1,
                stdout="",
                stderr=f"Hook timed out after {hook.timeout}ms",
                action=ExitCodeResult.ERROR,
                blocked=False
            )

        # Interpret exit code
        if exit_code == 0:
            action = ExitCodeResult.ALLOW
            blocked = False
        elif exit_code == 2:
            action = ExitCodeResult.BLOCK
            blocked = True
        else:
            action = ExitCodeResult.ERROR
            blocked = False

        return HookResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            action=action,
            blocked=blocked
        )

    def _substitute_context_vars(
        self,
        env: dict,
        context: HookContext
    ) -> dict:
        """
        Substitute context variables in environment.

        Available variables:
        - ${TOOL_NAME}: Tool being executed (e.g., "Edit", "Bash")
        - ${FILE_PATH}: File path (for Edit/Write/Read)
        - ${COMMAND}: Bash command (for Bash tool)
        - ${ARGS}: Tool arguments (JSON)

        Security:
        - Use shlex.quote() to escape values
        - Never allow shell metacharacters
        """
        substitutions = {
            "TOOL_NAME": context.tool,
            "FILE_PATH": context.args.get("file_path", ""),
            "COMMAND": context.args.get("command", ""),
            "ARGS": json.dumps(context.args)
        }

        # Substitute and sanitize
        result = {}
        for key, value in env.items():
            for var_name, var_value in substitutions.items():
                placeholder = f"${{{var_name}}}"
                if placeholder in value:
                    # Sanitize value
                    safe_value = shlex.quote(str(var_value))
                    value = value.replace(placeholder, safe_value)

            result[key] = value

        return result


class HookEngine:
    """Main hook engine - loads config and executes hooks."""

    def __init__(self, config_path: str):
        """
        Initialize hook engine with configuration.

        Args:
            config_path: Path to hook configuration JSON file
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.matcher = HookMatcher()
        self.executor = HookExecutor()

    def _load_config(self) -> dict:
        """Load hook configuration from JSON file."""
        with open(self.config_path, 'r') as f:
            return json.load(f)

    def execute_pre_tool_use(self, tool: str, args: Dict[str, Any]) -> HookResult:
        """
        Execute PreToolUse hooks for a tool invocation.

        Args:
            tool: Tool name (e.g., "Bash", "Edit")
            args: Tool arguments

        Returns:
            HookResult (blocked=True if any hook blocks)
        """
        pre_tool_hooks = self.config.get("hooks", {}).get("PreToolUse", [])

        for hook_config in pre_tool_hooks:
            pattern = hook_config.get("matcher")
            hooks = hook_config.get("hooks", [])

            # Check if pattern matches
            if self.matcher.matches_pattern(pattern, tool, args):
                # Execute all hooks for this pattern
                for hook_def in hooks:
                    hook = CommandHook(
                        type=hook_def["type"],
                        command=hook_def["command"],
                        args=hook_def.get("args", []),
                        env=hook_def.get("env", {}),
                        timeout=hook_def.get("timeout", 5000),
                        continue_on_error=hook_def.get("continueOnError", False)
                    )

                    context = HookContext(tool=tool, args=args)
                    result = self.executor.execute_hook(hook, context)

                    # If hook blocks, return immediately
                    if result.blocked:
                        return result

                    # If hook errors and continueOnError=False, return
                    if result.action == ExitCodeResult.ERROR and not hook.continue_on_error:
                        return result

        # No hooks blocked
        return HookResult(
            exit_code=0,
            stdout="",
            stderr="",
            action=ExitCodeResult.ALLOW,
            blocked=False
        )

    def execute_post_tool_use(self, tool: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute PostToolUse hooks after tool completion"""
        post_tool_hooks = self.config.get("hooks", {}).get("PostToolUse", [])

        for hook_config in post_tool_hooks:
            pattern = hook_config.get("matcher")
            hooks = hook_config.get("hooks", [])

            if self.matcher.matches_pattern(pattern, tool, args):
                for hook_def in hooks:
                    hook = CommandHook(
                        type=hook_def["type"],
                        command=hook_def["command"],
                        args=hook_def.get("args", []),
                        env=hook_def.get("env", {}),
                        timeout=hook_def.get("timeout", 5000),
                        continue_on_error=hook_def.get("continueOnError", False)
                    )

                    context = HookContext(tool=tool, args=args)
                    result = self.executor.execute_hook(hook, context)

                    if result.blocked or (result.action == ExitCodeResult.ERROR and not hook.continue_on_error):
                        return result.__dict__

        return {'exit_code': 0, 'stdout': '', 'stderr': '', 'blocked': False}

    def execute_user_prompt_submit(self, prompt: str) -> Dict[str, Any]:
        """Execute UserPromptSubmit hooks"""
        hooks = self.config.get("hooks", {}).get("UserPromptSubmit", [])
        return self._execute_simple_hooks(hooks, {'PROMPT': prompt})

    def execute_notification(self, message: str) -> Dict[str, Any]:
        """Execute Notification hooks"""
        hooks = self.config.get("hooks", {}).get("Notification", [])
        return self._execute_simple_hooks(hooks, {'MESSAGE': message})

    def execute_stop(self) -> Dict[str, Any]:
        """Execute Stop hooks (when Claude finishes response)"""
        hooks = self.config.get("hooks", {}).get("Stop", [])
        return self._execute_simple_hooks(hooks, {})

    def execute_subagent_stop(self, agent_id: str) -> Dict[str, Any]:
        """Execute SubagentStop hooks"""
        hooks = self.config.get("hooks", {}).get("SubagentStop", [])
        return self._execute_simple_hooks(hooks, {'AGENT_ID': agent_id})

    def execute_pre_compact(self) -> Dict[str, Any]:
        """Execute PreCompact hooks (before context compaction)"""
        hooks = self.config.get("hooks", {}).get("PreCompact", [])
        return self._execute_simple_hooks(hooks, {})

    def execute_session_start(self) -> Dict[str, Any]:
        """Execute SessionStart hooks"""
        hooks = self.config.get("hooks", {}).get("SessionStart", [])
        return self._execute_simple_hooks(hooks, {})

    def execute_session_end(self) -> Dict[str, Any]:
        """Execute SessionEnd hooks"""
        hooks = self.config.get("hooks", {}).get("SessionEnd", [])
        return self._execute_simple_hooks(hooks, {})

    def _execute_simple_hooks(self, hook_configs: list, env_vars: dict) -> Dict[str, Any]:
        """Execute hooks without tool/matcher logic"""
        for hook_config in hook_configs:
            for hook_def in hook_config.get("hooks", []):
                hook = CommandHook(
                    type=hook_def["type"],
                    command=hook_def["command"],
                    args=hook_def.get("args", []),
                    env=hook_def.get("env", {}),
                    timeout=hook_def.get("timeout", 5000),
                    continue_on_error=hook_def.get("continueOnError", False)
                )
                context = HookContext(tool="", args={}, **env_vars)
                result = self.executor.execute_hook(hook, context)

                if result.blocked or result.action == ExitCodeResult.ERROR:
                    return result.__dict__

        return {'exit_code': 0, 'stdout': '', 'stderr': '', 'blocked': False}

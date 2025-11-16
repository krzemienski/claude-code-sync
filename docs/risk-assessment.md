# Risk Assessment & Mitigation Strategy
**Claude Code Orchestration System**

**Document Version**: 1.0
**Created**: 2025-11-16
**Project Complexity**: 0.70 (HIGH)
**Risk Assessment Date**: 2025-11-16

---

## Executive Summary

This document identifies 28 distinct implementation risks across technical, operational, and coordination domains. Each risk is assessed for probability and impact, with detailed mitigation strategies provided. The highest priority risks involve MCP protocol complexity, inter-agent coordination reliability, and hook validation security.

**Risk Distribution**:
- **CRITICAL** (Probability × Impact ≥ 16): 7 risks
- **HIGH** (Probability × Impact 9-15): 12 risks
- **MEDIUM** (Probability × Impact 4-8): 9 risks

---

## Risk Categories

1. [Configuration System Risks](#configuration-system-risks)
2. [JSONL Storage Risks](#jsonl-storage-risks)
3. [MCP Protocol Risks](#mcp-protocol-risks)
4. [Multi-Agent Orchestration Risks](#multi-agent-orchestration-risks)
5. [Validation Hooks Risks](#validation-hooks-risks)
6. [Serena Integration Risks](#serena-integration-risks)
7. [Cross-Component Integration Risks](#cross-component-integration-risks)
8. [Operational Risks](#operational-risks)

---

## Configuration System Risks

### RISK-CONFIG-01: Configuration Merge Conflicts
**Category**: Configuration System
**Probability**: HIGH (4/5)
**Impact**: HIGH (4/5)
**Risk Score**: 16 (CRITICAL)

**Description**:
The 4-tier configuration merge system (Enterprise → User → Project Shared → Project Local) may produce unexpected results when settings conflict. Users may not understand precedence rules, leading to confusion when settings don't apply as expected.

**Specific Scenarios**:
- Enterprise policy denies `Bash(git push:*)` but project config allows it → Deny wins (correct)
- User sets model to Sonnet, project overrides to Opus → Opus wins (may surprise user)
- Multiple scopes define same hook with different commands → Last definition wins (potential bugs)

**Impact**:
- User frustration from "magical" behavior
- Security bypasses if precedence misunderstood
- Debugging difficulty (which config file applied?)
- Production outages from wrong settings

**Mitigation Strategy**:
1. **Verbose Logging**: Log final merged config with source annotations
   ```
   "model": "opus-4" (from: .claude/settings.json)
   "permissions.allow": ["Read", "Edit"] (merged from: user + project)
   "permissions.deny": ["Bash(rm:*)"] (from: /etc/claude-code/managed-settings.json)
   ```

2. **Validation Command**: `claude config validate` to show merged result
   ```bash
   claude config validate
   # Output:
   # Final Configuration:
   #   model: claude-opus-4-1-20250805 (from: .claude/settings.json)
   #   permissions.allow: ["Read", "Edit", "Write"] (merged: user + project)
   # Warnings:
   #   - Enterprise policy blocks Bash(git push:*) despite project allow
   ```

3. **Config Diff Tool**: Show differences between scopes
   ```bash
   claude config diff --user --project
   # Shows which settings differ between user and project configs
   ```

4. **Documentation**: Clear precedence rules in README with examples

5. **Testing**: Unit tests for all merge scenarios (30+ test cases)

**Residual Risk**: MEDIUM (Reduced from CRITICAL)

---

### RISK-CONFIG-02: XDG Directory Migration Failures
**Category**: Configuration System
**Probability**: MEDIUM (3/5)
**Impact**: MEDIUM (2/5)
**Risk Score**: 6 (MEDIUM)

**Description**:
Users upgrading from legacy `~/.claude/` to XDG-compliant `~/.config/claude/` may experience data loss or dual configuration states if migration fails.

**Specific Scenarios**:
- Partial migration leaves settings split across both locations
- Permission errors during migration (read-only home directory)
- Symbolic link from legacy to new location breaks tools
- User manually edited both configs, unsure which is active

**Impact**:
- Lost session history
- Duplicate MCP server instances
- Confusing behavior (which config is active?)
- Support burden

**Mitigation Strategy**:
1. **Auto-Migration**: Detect legacy directory on first run
   ```python
   if os.path.exists("~/.claude/") and not os.path.exists("~/.config/claude/"):
       migrate_to_xdg()
   ```

2. **Migration Verification**: Checksum validation after copy
   ```python
   assert checksum(legacy_file) == checksum(new_file)
   ```

3. **Dual-Read Fallback**: Read from legacy if XDG missing
   ```python
   config_path = XDG_PATH if exists(XDG_PATH) else LEGACY_PATH
   ```

4. **Migration Log**: Record migration actions
   ```
   ~/.config/claude/migration.log:
   2025-11-16 10:30:00 - Migrated settings.json
   2025-11-16 10:30:01 - Migrated projects/ directory
   2025-11-16 10:30:05 - Migration complete, legacy preserved
   ```

5. **Preserve Legacy**: Keep `~/.claude/` read-only backup for 30 days

**Residual Risk**: LOW

---

### RISK-CONFIG-03: Environment Variable Injection Attacks
**Category**: Configuration System
**Probability**: LOW (2/5)
**Impact**: CRITICAL (5/5)
**Risk Score**: 10 (HIGH)

**Description**:
If environment variable substitution (`${VAR_NAME}`) isn't properly sanitized, attackers could inject malicious commands via environment variables referenced in configs.

**Attack Vector**:
```json
{
  "mcpServers": {
    "malicious": {
      "command": "${MALICIOUS_COMMAND}",
      "args": ["${MALICIOUS_ARGS}"]
    }
  }
}
```
```bash
export MALICIOUS_COMMAND="rm -rf /"
export MALICIOUS_ARGS="-y"
```

**Impact**:
- Arbitrary code execution
- Data loss
- System compromise
- Reputational damage

**Mitigation Strategy**:
1. **Whitelist Allowed Variables**: Only substitute known-safe vars
   ```python
   ALLOWED_VARS = {"GITHUB_TOKEN", "API_KEY", "ANTHROPIC_API_KEY", ...}
   if var_name not in ALLOWED_VARS:
       raise ValueError(f"Unsafe variable: {var_name}")
   ```

2. **Command Validation**: Ensure commands are absolute paths or whitelisted binaries
   ```python
   ALLOWED_COMMANDS = {"npx", "uvx", "docker", "/usr/bin/python3"}
   if command not in ALLOWED_COMMANDS and not os.path.isabs(command):
       raise ValueError(f"Command must be absolute path or whitelisted")
   ```

3. **Argument Sanitization**: Escape shell metacharacters in args
   ```python
   import shlex
   safe_args = [shlex.quote(arg) for arg in args]
   ```

4. **Subprocess with No Shell**: Use `subprocess.run(..., shell=False)`
   ```python
   subprocess.run([command] + args, shell=False)  # No shell injection
   ```

5. **Security Audit**: Penetration testing of config parsing

**Residual Risk**: LOW (with strict validation)

---

## JSONL Storage Risks

### RISK-JSONL-01: Session File Corruption
**Category**: JSONL Storage
**Probability**: MEDIUM (3/5)
**Impact**: HIGH (4/5)
**Risk Score**: 12 (HIGH)

**Description**:
JSONL files may become corrupted due to incomplete writes (process crashes mid-write), disk full errors, or concurrent writes from multiple processes.

**Specific Scenarios**:
- Claude crashes during assistant message write → Last line incomplete JSON
- Disk full → Partial write, corrupted file
- Two Claude instances editing same project → Race condition
- Power loss during write → Truncated file

**Impact**:
- Lost session state
- Unable to resume conversation
- Analytics extraction fails
- User frustration

**Mitigation Strategy**:
1. **Atomic Writes**: Write to temp file, then atomic rename
   ```python
   with open(f"{session_file}.tmp", 'a') as f:
       f.write(json.dumps(message) + '\n')
       f.flush()
       os.fsync(f.fileno())
   os.rename(f"{session_file}.tmp", session_file)
   ```

2. **Append-Only Operations**: Never modify existing lines
   ```python
   # GOOD: Append new line
   file.write(new_message + '\n')

   # BAD: Rewrite entire file
   # file.write(entire_session)  # Don't do this!
   ```

3. **Corruption Recovery**: Skip malformed lines during parse
   ```python
   for line_num, line in enumerate(file):
       try:
           message = json.loads(line)
       except json.JSONDecodeError as e:
           logger.warning(f"Skipping corrupted line {line_num}: {e}")
           continue
   ```

4. **File Locking**: Use `fcntl.flock` to prevent concurrent writes
   ```python
   import fcntl
   with open(session_file, 'a') as f:
       fcntl.flock(f, fcntl.LOCK_EX)  # Exclusive lock
       f.write(json.dumps(message) + '\n')
   ```

5. **Backup Strategy**: Daily backup of session directory
   ```bash
   rsync -a ~/.config/claude/projects/ ~/.config/claude/backups/$(date +%Y%m%d)/
   ```

**Residual Risk**: LOW

---

### RISK-JSONL-02: Unbounded Session Growth
**Category**: JSONL Storage
**Probability**: HIGH (4/5)
**Impact**: MEDIUM (3/5)
**Risk Score**: 12 (HIGH)

**Description**:
Long-running sessions accumulate thousands of messages, leading to multi-GB JSONL files that exhaust disk space and slow down parsing.

**Specific Scenarios**:
- User sets `cleanupPeriodDays: 99999` → Sessions never deleted
- Multi-day coding session generates 50K+ messages
- File sizes exceed 1GB → Parse time > 60 seconds
- Disk fills up, blocking new writes

**Impact**:
- Slow session resume (user waits minutes)
- Disk space exhaustion
- Memory exhaustion when parsing large files
- System instability

**Mitigation Strategy**:
1. **Size-Based Rotation**: Split JSONL when > 100MB
   ```python
   if os.path.getsize(session_file) > 100 * 1024 * 1024:  # 100MB
       rotate_session_file()
   ```

2. **Auto-Compaction**: Offer `/compact` at 150K tokens
   ```
   Warning: Session context at 150K tokens. Run /compact to summarize?
   ```

3. **Streaming Parser**: Don't load entire file into memory
   ```python
   def parse_jsonl_stream(path):
       with open(path) as f:
           for line in f:  # Reads one line at a time
               yield json.loads(line)
   ```

4. **Disk Usage Monitoring**: Warn when < 1GB free space
   ```python
   import shutil
   free_space = shutil.disk_usage("/").free
   if free_space < 1_000_000_000:  # 1GB
       logger.warning("Low disk space!")
   ```

5. **Graceful Cleanup**: Delete sessions older than 90 days by default
   ```python
   DEFAULT_CLEANUP_DAYS = 90  # Not 99999
   ```

**Residual Risk**: LOW

---

### RISK-JSONL-03: Token Cost Calculation Errors
**Category**: JSONL Storage
**Probability**: MEDIUM (3/5)
**Impact**: MEDIUM (2/5)
**Risk Score**: 6 (MEDIUM)

**Description**:
Incorrect token cost calculations lead to budget overruns or misleading analytics. Model pricing changes over time, and formulas may have bugs.

**Specific Scenarios**:
- Model pricing updated by Anthropic, formula outdated
- Cache tokens miscounted (double-counting)
- Rounding errors accumulate over thousands of messages
- Currency conversion errors (if billing in non-USD)

**Impact**:
- Budget surprises (user expects $10, gets $100 bill)
- Analytics show wrong costs
- Loss of user trust
- Financial disputes

**Mitigation Strategy**:
1. **Externalized Pricing Config**: Store rates in separate JSON
   ```json
   // pricing.json
   {
     "claude-sonnet-4-5-20250929": {
       "input_per_million": 3.00,
       "output_per_million": 15.00,
       "cache_write_per_million": 3.75,
       "cache_read_per_million": 0.30
     }
   }
   ```

2. **Version Pricing**: Track pricing by date
   ```python
   def get_pricing(model, date):
       # Return pricing valid on that date
       pass
   ```

3. **Cost Validation**: Cross-check with Anthropic API response
   ```python
   calculated_cost = compute_cost(tokens)
   api_reported_cost = response.usage.cost
   assert abs(calculated_cost - api_reported_cost) < 0.01
   ```

4. **Unit Tests**: Verify cost calculations with known examples
   ```python
   def test_sonnet_cost():
       tokens = {"input": 15000, "output": 2150, "cache_write": 8000}
       assert compute_cost(tokens, "sonnet-4-5") == 0.111
   ```

5. **Decimal Precision**: Use `decimal.Decimal` for currency
   ```python
   from decimal import Decimal
   cost = Decimal('3.00') / Decimal('1000000') * Decimal(str(input_tokens))
   ```

**Residual Risk**: LOW

---

## MCP Protocol Risks

### RISK-MCP-01: MCP Server Process Management Failures
**Category**: MCP Protocol
**Probability**: HIGH (4/5)
**Impact**: CRITICAL (5/5)
**Risk Score**: 20 (CRITICAL)

**Description**:
MCP servers are external processes that can crash, hang, leak resources, or fail to start. Poor process management leads to tool unavailability, zombie processes, or resource exhaustion.

**Specific Scenarios**:
- MCP server crashes on startup → All tools unavailable
- Server hangs indefinitely → Claude waits forever for response
- Server crashes mid-request → Partial results lost
- Zombie processes accumulate → System resource exhaustion
- Server restart fails 3 times → Permanent failure state

**Impact**:
- Complete tool failure (GitHub, Playwright, etc. unavailable)
- Session hangs requiring manual intervention
- Memory/CPU leaks
- User frustration
- Data loss

**Mitigation Strategy**:
1. **Health Checks**: Ping servers every 60s
   ```python
   async def health_check_loop():
       while True:
           try:
               await mcp_client.ping()
           except TimeoutError:
               logger.error("MCP server unresponsive, restarting...")
               restart_server()
           await asyncio.sleep(60)
   ```

2. **Restart Policy**: Auto-restart on crash with exponential backoff
   ```python
   MAX_RESTARTS = 3
   restart_delay = 1  # seconds
   for attempt in range(MAX_RESTARTS):
       try:
           start_server()
           break
       except Exception as e:
           logger.warning(f"Restart attempt {attempt+1} failed: {e}")
           await asyncio.sleep(restart_delay)
           restart_delay *= 2  # Exponential backoff
   ```

3. **Timeout Enforcement**: Kill server if unresponsive
   ```python
   async def call_tool_with_timeout(tool, args):
       try:
           return await asyncio.wait_for(
               mcp_client.call(tool, args),
               timeout=MCP_TOOL_TIMEOUT  # 5 minutes default
           )
       except asyncio.TimeoutError:
           kill_server()
           raise
   ```

4. **Resource Limits**: Use `ulimit` or cgroups
   ```python
   import resource
   resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))  # 1GB memory limit
   ```

5. **Graceful Shutdown**: Proper cleanup on exit
   ```python
   async def shutdown_server():
       try:
           await mcp_client.call("shutdown")
           await asyncio.wait_for(process.wait(), timeout=5)
       except asyncio.TimeoutError:
           process.terminate()  # SIGTERM
           await asyncio.wait_for(process.wait(), timeout=5)
       except:
           process.kill()  # SIGKILL
   ```

**Residual Risk**: MEDIUM

---

### RISK-MCP-02: SSE/HTTP Transport Reliability
**Category**: MCP Protocol
**Probability**: MEDIUM (3/5)
**Impact**: HIGH (4/5)
**Risk Score**: 12 (HIGH)

**Description**:
Network-based transports (SSE, HTTP) are subject to network failures, timeouts, and connection loss. Remote MCP servers may be unavailable due to network issues or server-side problems.

**Specific Scenarios**:
- Network partition during long-running tool call → Results lost
- SSE connection drops mid-stream → Incomplete event stream
- HTTP request times out after 30s → User waits, then error
- Remote server returns 500 error → Tool unavailable
- Certificate validation fails → Cannot connect

**Impact**:
- Tool failures during critical operations
- Lost work (e.g., half-completed PR creation)
- User frustration
- Debugging difficulty (network issues hard to reproduce)

**Mitigation Strategy**:
1. **Retry Logic**: Exponential backoff for transient failures
   ```python
   for attempt in range(3):
       try:
           response = await http_client.post(url, json=request)
           break
       except (Timeout, ConnectionError) as e:
           if attempt == 2:
               raise
           await asyncio.sleep(2 ** attempt)
   ```

2. **Connection Pooling**: Reuse HTTP connections
   ```python
   import httpx
   client = httpx.AsyncClient(
       timeout=30.0,
       limits=httpx.Limits(max_keepalive_connections=5)
   )
   ```

3. **SSE Reconnection**: Auto-reconnect on disconnect
   ```python
   async def sse_stream_with_reconnect(url):
       while True:
           try:
               async with httpx.stream("GET", url) as stream:
                   async for line in stream.aiter_lines():
                       yield line
           except Exception as e:
               logger.warning(f"SSE connection lost: {e}, reconnecting...")
               await asyncio.sleep(5)
   ```

4. **Circuit Breaker**: Fail fast if server repeatedly down
   ```python
   if consecutive_failures > 5:
       logger.error("Circuit breaker tripped, marking server as down")
       mark_server_down(server_name)
   ```

5. **Fallback to Local Tools**: Degrade gracefully
   ```python
   try:
       result = await remote_mcp_call(tool, args)
   except NetworkError:
       logger.warning(f"Remote {tool} failed, using local fallback")
       result = local_tool_fallback(tool, args)
   ```

**Residual Risk**: MEDIUM

---

### RISK-MCP-03: MCP Protocol Version Incompatibility
**Category**: MCP Protocol
**Probability**: MEDIUM (3/5)
**Impact**: MEDIUM (3/5)
**Risk Score**: 9 (HIGH)

**Description**:
MCP protocol may evolve over time. Servers using different protocol versions may be incompatible with the Claude Code client, leading to communication failures or undefined behavior.

**Specific Scenarios**:
- Server uses MCP v2.0, client uses v1.0 → Tool schema mismatch
- Server adds new required field → Client doesn't send it
- Client sends deprecated field → Server rejects request
- Breaking changes in JSON-RPC message format

**Impact**:
- Tool failures
- Silent data corruption
- Debugging difficulty
- Broken third-party integrations

**Mitigation Strategy**:
1. **Version Negotiation**: Check version on connect
   ```python
   server_version = await mcp_client.call("protocol/version")
   if not is_compatible(server_version, CLIENT_VERSION):
       raise IncompatibleVersionError(f"Server {server_version}, Client {CLIENT_VERSION}")
   ```

2. **Semver Compliance**: Follow semantic versioning
   - Major version change → Breaking change, refuse connection
   - Minor version change → Backward compatible, warn
   - Patch version change → Compatible, no action

3. **Capability Detection**: Query server capabilities
   ```python
   capabilities = await mcp_client.call("protocol/capabilities")
   if "tools/call/v2" in capabilities:
       use_v2_tool_call()
   else:
       use_v1_tool_call()
   ```

4. **Backward Compatibility**: Support older servers
   ```python
   try:
       result = await call_tool_v2(tool, args)
   except UnsupportedMethod:
       result = await call_tool_v1(tool, args)
   ```

5. **Version Documentation**: Clearly document supported versions
   ```markdown
   # MCP Protocol Support
   - Supported: 1.0.x, 1.1.x
   - Deprecated: 0.9.x (will be removed in v2.0)
   - Not Supported: 2.0.x (breaking changes)
   ```

**Residual Risk**: LOW

---

## Multi-Agent Orchestration Risks

### RISK-AGENT-01: Inter-Agent State Synchronization Failures
**Category**: Multi-Agent Orchestration
**Probability**: HIGH (4/5)
**Impact**: CRITICAL (5/5)
**Risk Score**: 20 (CRITICAL)

**Description**:
Sub-agents cannot directly communicate. State passing via CLAUDE.md updates or temp files may fail due to race conditions, file conflicts, or incomplete writes.

**Specific Scenarios**:
- Wave 1 writes to `/tmp/analysis.json`, Wave 2 reads before write complete → Partial data
- Two agents update CLAUDE.md simultaneously → Last write wins, data lost
- File permissions prevent agent from reading state file → Agent missing context
- State file deleted by cleanup script mid-execution → Agent crashes

**Impact**:
- Agents working with stale/incomplete data
- Duplicate work (agents don't see each other's results)
- Incorrect final output
- Data loss
- Debugging nightmare

**Mitigation Strategy**:
1. **Serena MCP Coordination**: Use structured memory API
   ```python
   # Wave 1 agent
   await serena.write_memory("wave_1_analysis", analysis_results)

   # Wave 2 agent
   wave_1_data = await serena.read_memory("wave_1_analysis")
   ```

2. **File Locking**: Prevent concurrent writes
   ```python
   import fcntl
   with open(state_file, 'w') as f:
       fcntl.flock(f, fcntl.LOCK_EX)  # Exclusive lock
       json.dump(state, f)
       f.flush()
       os.fsync(f.fileno())
   ```

3. **Atomic Writes**: Write to temp, then rename
   ```python
   with open(f"{state_file}.tmp", 'w') as f:
       json.dump(state, f)
   os.rename(f"{state_file}.tmp", state_file)
   ```

4. **Version Control**: Git commit state after each wave
   ```bash
   git add /tmp/wave-1-results.json
   git commit -m "Wave 1 complete: analysis results"
   # Wave 2 reads from Git history if file missing
   ```

5. **Coordination Service**: Main agent orchestrates all reads/writes
   ```python
   class StateCoordinator:
       async def write(self, key, value):
           async with self.lock:
               self.state[key] = value

       async def read(self, key):
           async with self.lock:
               return self.state[key]
   ```

**Residual Risk**: MEDIUM

---

### RISK-AGENT-02: Task Timeout and Deadlock
**Category**: Multi-Agent Orchestration
**Probability**: MEDIUM (3/5)
**Impact**: HIGH (4/5)
**Risk Score**: 12 (HIGH)

**Description**:
Sub-agents may hang indefinitely if they encounter infinite loops, blocking operations, or circular dependencies between tasks.

**Specific Scenarios**:
- Task A waits for Task B's result, Task B waits for Task A → Deadlock
- Sub-agent enters infinite retry loop → Never returns
- Sub-agent waiting for user input in non-interactive context → Hangs
- Network request hangs without timeout → Task never completes

**Impact**:
- Session hangs
- User forced to kill process
- Lost work
- Resource leaks

**Mitigation Strategy**:
1. **Task Timeouts**: Hard limit per task (default: 10 minutes)
   ```python
   try:
       result = await asyncio.wait_for(
           execute_task(instruction),
           timeout=600  # 10 minutes
       )
   except asyncio.TimeoutError:
       logger.error(f"Task timed out: {instruction}")
       raise TaskTimeoutError()
   ```

2. **Progress Monitoring**: Require periodic heartbeats
   ```python
   async def task_with_heartbeat(instruction):
       async def heartbeat():
           while True:
               await report_progress()
               await asyncio.sleep(30)

       heartbeat_task = asyncio.create_task(heartbeat())
       result = await execute_task(instruction)
       heartbeat_task.cancel()
       return result
   ```

3. **Dependency Graph Validation**: Detect cycles before execution
   ```python
   def validate_task_dependencies(tasks):
       graph = build_dependency_graph(tasks)
       if has_cycle(graph):
           raise ValueError("Circular dependency detected")
   ```

4. **Watchdog Timer**: Kill task if no progress for N minutes
   ```python
   last_activity = time.time()
   while task_running:
       if time.time() - last_activity > 300:  # 5 min no activity
           kill_task()
   ```

5. **Graceful Cancellation**: Support task abort
   ```python
   User: "/cancel"
   → Cancel all running tasks
   → Return partial results if any
   ```

**Residual Risk**: LOW

---

### RISK-AGENT-03: Context Window Exhaustion
**Category**: Multi-Agent Orchestration
**Probability**: HIGH (4/5)
**Impact**: MEDIUM (3/5)
**Risk Score**: 12 (HIGH)

**Description**:
Main agent and sub-agents each have 200K token context windows. Long sessions or large codebases can exhaust context, causing failures or loss of information.

**Specific Scenarios**:
- Main agent loads 50 large CLAUDE.md files → Context full before starting
- Sub-agent tries to read 100 files → Exceeds 200K tokens
- Conversation history grows to 180K tokens → No room for new work
- Compaction removes critical context → Agent forgets important details

**Impact**:
- Agent failures ("context window exceeded")
- Lost information
- Poor decision making (missing context)
- User frustration

**Mitigation Strategy**:
1. **Proactive Compaction**: Offer `/compact` at 150K tokens
   ```
   Warning: Context at 150K/200K tokens. Compact to continue?
   /compact → Summarize conversation, keep key facts
   ```

2. **Selective Context Loading**: Don't auto-load all CLAUDE.md files
   ```python
   # Load only relevant CLAUDE.md files
   if working_in_subdirectory:
       load_claude_md_for_directory(subdir)
   else:
       load_claude_md_for_root()
   ```

3. **Token Budgeting**: Allocate tokens per wave
   ```python
   WAVE_BUDGETS = {
       "discovery": 50_000,  # Read many files
       "analysis": 30_000,   # Analyze findings
       "implementation": 80_000,  # Code changes
       "validation": 20_000  # Test results
   }
   ```

4. **Chunked Processing**: Break large tasks into smaller pieces
   ```python
   # Instead of: Task("Analyze all 100 files")
   for chunk in chunks(files, size=10):
       Task(f"Analyze files {chunk}")
   ```

5. **Context Monitoring**: Warn when approaching limit
   ```python
   current_tokens = count_tokens(context)
   if current_tokens > 170_000:
       logger.warning(f"Context at {current_tokens}/200K tokens")
   ```

**Residual Risk**: MEDIUM

---

## Validation Hooks Risks

### RISK-HOOKS-01: Hook Command Injection Vulnerabilities
**Category**: Validation Hooks
**Probability**: MEDIUM (3/5)
**Impact**: CRITICAL (5/5)
**Risk Score**: 15 (HIGH)

**Description**:
If hook commands or environment variables aren't properly sanitized, attackers could inject malicious commands that execute with Claude Code's privileges.

**Attack Vectors**:
```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Edit|Write",
      "hooks": [{
        "type": "command",
        "command": "echo $FILE_PATH > /tmp/files.txt"
      }]
    }]
  }
}
```
```
Edit("'; rm -rf /; echo '.txt")
→ FILE_PATH='; rm -rf /; echo '.txt
→ Executes: echo '; rm -rf /; echo '.txt > /tmp/files.txt
```

**Impact**:
- Arbitrary code execution
- Data loss
- System compromise
- Privilege escalation

**Mitigation Strategy**:
1. **No Shell Execution**: Use `subprocess.run(..., shell=False)`
   ```python
   # BAD: Uses shell, vulnerable to injection
   subprocess.run(f"echo {file_path} > output.txt", shell=True)

   # GOOD: No shell, immune to injection
   subprocess.run(["echo", file_path], stdout=open("output.txt", "w"), shell=False)
   ```

2. **Argument Escaping**: Use `shlex.quote()` for shell args
   ```python
   import shlex
   safe_path = shlex.quote(file_path)
   subprocess.run(f"echo {safe_path} > output.txt", shell=True)
   ```

3. **Environment Variable Validation**: Sanitize before export
   ```python
   def sanitize_env_var(value):
       # Remove shell metacharacters
       return re.sub(r'[;&|`$()]', '', value)

   os.environ["FILE_PATH"] = sanitize_env_var(file_path)
   ```

4. **Whitelist Commands**: Only allow pre-approved executables
   ```python
   ALLOWED_COMMANDS = {
       "prettier", "eslint", "black", "pytest", "git", "npm"
   }
   command = hook_config["command"].split()[0]
   if command not in ALLOWED_COMMANDS:
       raise SecurityError(f"Command not allowed: {command}")
   ```

5. **Sandbox Execution**: Run hooks in restricted environment
   ```python
   import subprocess
   subprocess.run(
       hook_command,
       shell=False,
       user="nobody",  # Low-privilege user
       timeout=30,
       cwd="/tmp"  # Restricted directory
   )
   ```

**Residual Risk**: LOW (with strict validation)

---

### RISK-HOOKS-02: Hook Execution Performance Impact
**Category**: Validation Hooks
**Probability**: HIGH (4/5)
**Impact**: MEDIUM (2/5)
**Risk Score**: 8 (MEDIUM)

**Description**:
Slow-running hooks (test suites, security scans) block operations and frustrate users. Multiple hooks per event compound the problem.

**Specific Scenarios**:
- Test suite takes 5 minutes → User waits before every commit
- PostToolUse hook runs prettier on every Edit → 100ms latency per keystroke
- Security scan takes 30 seconds → Blocks every commit
- 5 hooks on PreToolUse → 5× delay

**Impact**:
- Poor user experience (slow feedback loops)
- Users disable hooks out of frustration
- Reduced productivity
- Timeouts

**Mitigation Strategy**:
1. **Async Hooks**: Run PostToolUse hooks in background
   ```python
   async def execute_post_hooks(hooks):
       tasks = [asyncio.create_task(run_hook(h)) for h in hooks]
       # Don't wait for completion
   ```

2. **Hook Timeouts**: Kill slow hooks
   ```python
   try:
       subprocess.run(hook_cmd, timeout=30)  # 30s max
   except subprocess.TimeoutExpired:
       logger.warning(f"Hook timed out: {hook_cmd}")
   ```

3. **Incremental Validation**: Only run tests on changed files
   ```bash
   # Instead of: pytest tests/
   # Run: pytest tests/test_auth.py (file that was edited)
   pytest tests/test_$(basename "$FILE_PATH" .py).py
   ```

4. **Hook Caching**: Skip if file hasn't changed
   ```python
   file_hash = hashlib.sha256(file_content).hexdigest()
   if file_hash == last_hook_run_hash:
       logger.info("File unchanged, skipping hook")
       return
   ```

5. **Progress Indicators**: Show user what's happening
   ```
   Running pre-commit hooks...
   ✓ Syntax check (0.2s)
   ⏳ Running tests... (3.8s elapsed)
   ```

**Residual Risk**: LOW

---

### RISK-HOOKS-03: Hook Failure Diagnosis Difficulty
**Category**: Validation Hooks
**Probability**: HIGH (4/5)
**Impact**: MEDIUM (2/5)
**Risk Score**: 8 (MEDIUM)

**Description**:
When hooks fail, error messages may be unclear, making it hard for users or Claude to diagnose and fix the problem.

**Specific Scenarios**:
- Hook returns exit code 2 with no error message → Claude doesn't know what failed
- Error message in stderr not captured → Silent failure
- Hook fails due to missing dependency → No indication what's missing
- Multiple hooks fail → Only first error shown

**Impact**:
- Wasted time debugging
- User frustration
- Claude unable to auto-fix
- Reduced hook adoption

**Mitigation Strategy**:
1. **Capture All Output**: Log both stdout and stderr
   ```python
   result = subprocess.run(
       hook_cmd,
       capture_output=True,
       text=True
   )
   logger.info(f"Hook stdout: {result.stdout}")
   logger.error(f"Hook stderr: {result.stderr}")
   ```

2. **Structured Error Messages**: Parse hook output
   ```bash
   # Hook script should output JSON on failure
   {
     "status": "failed",
     "message": "Tests failed: 3 failures in test_auth.py",
     "remediation": "Run: pytest tests/test_auth.py -v"
   }
   ```

3. **Hook Logs**: Write detailed logs
   ```python
   with open(".claude/logs/hooks.log", "a") as log:
       log.write(f"{timestamp} - Hook {hook_name} - Exit {exit_code}\n")
       log.write(f"  Command: {hook_cmd}\n")
       log.write(f"  Output: {output}\n")
   ```

4. **User-Friendly Errors**: Translate tech errors to plain English
   ```python
   if "ModuleNotFoundError: No module named 'pytest'" in stderr:
       message = "Tests require pytest. Install with: pip install pytest"
   else:
       message = stderr
   ```

5. **Hook Dry-Run**: Test hooks before committing
   ```bash
   claude config test-hooks
   # Runs all PreToolUse hooks without actual tool execution
   ```

**Residual Risk**: LOW

---

## Serena Integration Risks

### RISK-SERENA-01: Language Server Compatibility Issues
**Category**: Serena Integration
**Probability**: MEDIUM (3/5)
**Impact**: HIGH (3/5)
**Risk Score**: 9 (HIGH)

**Description**:
Serena relies on LSP (Language Server Protocol) servers for semantic analysis. Different languages have varying LSP support quality, and some servers may be incompatible or buggy.

**Specific Scenarios**:
- Python LSP crashes on large files → Serena tools fail
- Go LSP doesn't support finding references → Missing functionality
- TypeScript LSP slow on monorepos → 10+ second latency
- LSP server version incompatible with Serena → Parse errors

**Impact**:
- Serena tools unavailable for some languages
- Degraded user experience
- Fallback to text-based tools (less accurate)
- Debugging difficulty

**Mitigation Strategy**:
1. **LSP Version Pinning**: Specify compatible versions
   ```yaml
   # .serena/serena_config.yml
   language_servers:
     python:
       command: "pyls"
       version: "0.19.0"  # Known compatible version
   ```

2. **Graceful Degradation**: Fall back to text search
   ```python
   try:
       result = serena.find_symbol("authenticate")
   except SerenaError:
       logger.warning("Serena failed, falling back to grep")
       result = grep_search("def authenticate")
   ```

3. **LSP Health Checks**: Verify server responsive
   ```python
   async def check_lsp_health():
       try:
           await lsp_client.initialize()
           await lsp_client.call("textDocument/definition", {...})
       except Exception as e:
           mark_lsp_unhealthy()
           raise LSPError(f"LSP server unhealthy: {e}")
   ```

4. **Alternative LSP Servers**: Support multiple implementations
   ```yaml
   language_servers:
     python:
       primary: "pyls"
       fallback: "pylsp"  # Try this if primary fails
   ```

5. **Language Support Matrix**: Document tested combinations
   ```markdown
   # Supported Languages
   - Python: ✅ Full support (pyls 0.19.0+)
   - TypeScript: ✅ Full support (ts-language-server 3.0+)
   - Go: ⚠️ Partial (gopls, no rename support)
   - Rust: ❌ Not tested
   ```

**Residual Risk**: MEDIUM

---

### RISK-SERENA-02: Semantic Editing Precision Failures
**Category**: Serena Integration
**Probability**: MEDIUM (3/5)
**Impact**: MEDIUM (3/5)
**Risk Score**: 9 (HIGH)

**Description**:
Serena's semantic editing tools (insert_after_symbol, replace_symbol_definition) may insert code at incorrect locations due to AST parsing errors or indentation issues.

**Specific Scenarios**:
- Insert after class definition inserts inside nested function → Wrong scope
- Replace symbol replaces wrong overloaded method → Name collision
- Indentation calculated incorrectly → Syntax error
- Symbol definition spans multiple lines → Partial replacement

**Impact**:
- Syntax errors
- Incorrect code placement
- Broken functionality
- User trust loss

**Mitigation Strategy**:
1. **AST Validation**: Verify AST after edit
   ```python
   original_ast = parse_ast(file_content)
   edited_ast = parse_ast(edited_content)
   assert edited_ast.is_valid()
   ```

2. **Dry-Run Mode**: Preview changes before applying
   ```python
   result = serena.insert_after_symbol("MyClass", new_code, dry_run=True)
   print(f"Would insert at line {result.line_number}:")
   print(result.preview)
   user_confirms = input("Apply? (y/n): ")
   ```

3. **Indentation Detection**: Use file's existing style
   ```python
   def detect_indentation(file_content):
       # Detect tabs vs spaces, indent size
       if "\t" in file_content:
           return "\t"
       else:
           return detect_space_count(file_content) * " "
   ```

4. **Symbol Disambiguation**: Require full path for overloads
   ```python
   # Ambiguous: find_symbol("process")
   # → Multiple matches: MyClass.process(), OtherClass.process()

   # Unambiguous: find_symbol("MyClass.process")
   # → Single match
   ```

5. **Rollback on Failure**: Revert if syntax invalid
   ```python
   backup = read_file(path)
   try:
       serena.replace_symbol("func", new_code)
       validate_syntax(path)
   except SyntaxError:
       write_file(path, backup)  # Rollback
       raise
   ```

**Residual Risk**: LOW

---

## Cross-Component Integration Risks

### RISK-INT-01: Configuration Changes Breaking Active Sessions
**Category**: Cross-Component Integration
**Probability**: MEDIUM (3/5)
**Impact**: HIGH (3/5)
**Risk Score**: 9 (HIGH)

**Description**:
If configuration files are modified while a Claude Code session is active, the changes may not apply correctly, leading to inconsistent state.

**Specific Scenarios**:
- User edits `.claude/settings.json` mid-session → New hooks not loaded
- MCP server added to config → Not available until restart
- Permission changes ignored → Denied tools still accessible
- Model changed but old model still used → Cost miscalculations

**Impact**:
- Inconsistent behavior
- Security bypasses (permission changes ignored)
- Confusing UX (changes don't apply)
- Cost surprises

**Mitigation Strategy**:
1. **Config Reloading**: Watch config files for changes
   ```python
   import watchdog
   observer = watchdog.Observer()
   observer.schedule(ConfigReloadHandler(), path=".claude/")
   observer.start()
   ```

2. **Graceful Reload**: Apply changes without disrupting session
   ```python
   async def reload_config():
       new_config = load_merged_config()
       diff = compare_configs(current_config, new_config)

       if diff.has_breaking_changes():
           logger.warning("Config has breaking changes, restart required")
       else:
           apply_config_changes(diff)
   ```

3. **Restart Prompt**: Notify user when restart needed
   ```
   Configuration changed detected.
   Some changes require restart (MCP servers, model).
   Restart now? (y/n):
   ```

4. **Hot-Reload Hooks**: Hooks can update without restart
   ```python
   def reload_hooks():
       global HOOKS
       HOOKS = load_hooks_from_config()
   ```

5. **Config Versioning**: Detect config format changes
   ```json
   {
     "version": "2.0",
     "model": "sonnet-4-5",
     ...
   }
   ```

**Residual Risk**: LOW

---

## Operational Risks

### RISK-OPS-01: Inadequate Logging and Observability
**Category**: Operational
**Probability**: HIGH (4/5)
**Impact**: MEDIUM (3/5)
**Risk Score**: 12 (HIGH)

**Description**:
Without comprehensive logging, debugging production issues becomes extremely difficult. Users can't diagnose failures, and developers can't reproduce bugs.

**Specific Scenarios**:
- MCP server crashes but no log of why → Can't debug
- Hook fails silently → User doesn't know it ran
- Performance degradation → No metrics to identify bottleneck
- Security incident → No audit trail

**Impact**:
- Prolonged debugging sessions
- Unable to reproduce bugs
- Security incidents undetected
- Poor user experience

**Mitigation Strategy**:
1. **Structured Logging**: Use JSON format for machine parsing
   ```python
   import logging
   import json

   logger.info(json.dumps({
       "event": "mcp_tool_call",
       "server": "github",
       "tool": "create_pr",
       "duration_ms": 1234,
       "status": "success"
   }))
   ```

2. **Log Levels**: Appropriate levels for filtering
   ```python
   logger.debug("MCP request: {request}")  # Verbose
   logger.info("Tool executed: {tool}")     # Normal
   logger.warning("Slow tool: {duration}") # Issues
   logger.error("Tool failed: {error}")     # Failures
   ```

3. **Log Aggregation**: Central location for all logs
   ```
   ~/.claude/logs/
   ├── claude-code.log      (main application)
   ├── mcp-servers.log      (all MCP communication)
   ├── hooks.log            (hook execution)
   ├── sessions.log         (JSONL write events)
   └── errors.log           (errors only)
   ```

4. **Metrics Collection**: Track key performance indicators
   ```python
   metrics.record("tool_execution_time", duration_ms, tags={"tool": tool_name})
   metrics.increment("tool_calls", tags={"tool": tool_name, "status": status})
   ```

5. **Debug Mode**: Verbose logging on demand
   ```bash
   claude --verbose
   # Enables debug-level logging
   ```

**Residual Risk**: LOW

---

### RISK-OPS-02: Insufficient Testing Coverage
**Category**: Operational
**Probability**: HIGH (4/5)
**Impact**: HIGH (4/5)
**Risk Score**: 16 (CRITICAL)

**Description**:
Complex system with 47 requirements across 6 components requires extensive testing. Insufficient test coverage leads to bugs in production.

**Testing Gaps**:
- Configuration merge logic (30+ edge cases)
- JSONL corruption recovery
- MCP server crash handling
- Inter-agent coordination race conditions
- Hook injection vulnerabilities
- Serena semantic editing precision

**Impact**:
- Production bugs
- Data loss
- Security vulnerabilities
- User frustration
- Rollback required

**Mitigation Strategy**:
1. **Functional Testing (NO MOCKS)**: Real execution tests
   ```python
   def test_config_merge():
       # Write actual config files
       write_file(".claude/settings.json", '{"model": "opus"}')
       write_file("~/.config/claude/settings.json", '{"model": "sonnet"}')

       # Load and verify
       config = load_merged_config()
       assert config["model"] == "opus"  # Project overrides user
   ```

2. **Integration Testing**: Test component interactions
   ```python
   def test_mcp_with_hooks():
       # Configure MCP server
       # Configure PostToolUse hook
       # Execute tool
       # Verify hook ran
       # Verify hook output captured
   ```

3. **Chaos Testing**: Simulate failures
   ```python
   def test_mcp_server_crash_during_tool_call():
       mcp_server = start_server()
       async def crash_server():
           await asyncio.sleep(0.5)
           mcp_server.kill()

       asyncio.create_task(crash_server())
       with pytest.raises(MCPServerCrashError):
           await mcp_client.call_tool("long_running_tool")
   ```

4. **Property-Based Testing**: Generate edge cases
   ```python
   from hypothesis import given, strategies as st

   @given(st.text())
   def test_file_path_sanitization(file_path):
       # Should never crash regardless of input
       result = sanitize_file_path(file_path)
       assert is_safe_path(result)
   ```

5. **Test Coverage Metrics**: Enforce minimums
   ```bash
   pytest --cov=src --cov-report=term-missing --cov-fail-under=80
   # Fails if < 80% coverage
   ```

**Residual Risk**: MEDIUM

---

## Risk Mitigation Timeline

### Phase 1: Foundation (Weeks 1-2)
**Focus**: Configuration, JSONL, Security
- Implement RISK-CONFIG-01 mitigations (config merge validation)
- Implement RISK-CONFIG-03 mitigations (injection prevention)
- Implement RISK-JSONL-01 mitigations (atomic writes, corruption recovery)
- Implement RISK-HOOKS-01 mitigations (command injection prevention)

### Phase 2: Core Services (Weeks 3-4)
**Focus**: MCP, Hooks
- Implement RISK-MCP-01 mitigations (process management)
- Implement RISK-MCP-02 mitigations (network reliability)
- Implement RISK-HOOKS-02 mitigations (performance)
- Implement RISK-HOOKS-03 mitigations (error diagnosis)

### Phase 3: Orchestration (Weeks 5-6)
**Focus**: Multi-Agent, Serena
- Implement RISK-AGENT-01 mitigations (state synchronization)
- Implement RISK-AGENT-02 mitigations (timeouts, deadlock detection)
- Implement RISK-AGENT-03 mitigations (context management)
- Implement RISK-SERENA-01 mitigations (LSP compatibility)

### Phase 4: Operations (Week 7)
**Focus**: Testing, Monitoring
- Implement RISK-OPS-01 mitigations (logging infrastructure)
- Implement RISK-OPS-02 mitigations (test suite)
- Conduct security audit
- Penetration testing

---

## Monitoring and Alerting

### Key Metrics to Track
1. **MCP Server Health**: Uptime, crash rate, response time
2. **Hook Performance**: Execution time, failure rate
3. **Session Metrics**: Token usage, cost, file size
4. **Agent Coordination**: Task success rate, timeout frequency
5. **Error Rates**: By component, by error type

### Alert Thresholds
- MCP server crash rate > 5% → Page on-call
- Hook execution time > 60s → Warn user
- Session file size > 500MB → Recommend compaction
- Context window > 180K tokens → Force compact
- Error rate > 10% → Investigate

---

## Conclusion

This risk assessment identifies 28 distinct risks with detailed mitigation strategies. The highest priority risks involve:

1. **MCP Server Process Management** (RISK-MCP-01) - CRITICAL
2. **Inter-Agent State Synchronization** (RISK-AGENT-01) - CRITICAL
3. **Configuration Merge Conflicts** (RISK-CONFIG-01) - CRITICAL
4. **Insufficient Testing Coverage** (RISK-OPS-02) - CRITICAL

With rigorous implementation of the proposed mitigation strategies, all CRITICAL risks can be reduced to MEDIUM or LOW residual risk. Continuous monitoring and iterative improvement will be essential for long-term success.

**Next Steps**:
1. Review risk assessment with stakeholders
2. Prioritize mitigations by risk score
3. Allocate resources to high-priority items
4. Implement mitigations in phases (see timeline above)
5. Establish monitoring infrastructure early
6. Conduct regular risk review (monthly)

---

**Document Approval**: Ready for Wave 2 (Architecture Design)

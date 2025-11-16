# Architecture Requirements Document
**Claude Code Orchestration System**

**Document Version**: 1.0
**Created**: 2025-11-16
**Complexity**: 0.70 (HIGH)
**Source**: claude-code-settings.md (2,678 lines)

---

## Executive Summary

This document defines the technical requirements for implementing a Claude Code orchestration system based on comprehensive analysis of the official specification. The system comprises 6 core components that enable configuration management, session persistence, MCP protocol integration, multi-agent coordination, validation enforcement, and semantic code analysis.

**Total Requirements**: 47 specific requirements across 6 components

---

## Component 1: 3-Tier Configuration System

### Overview
Hierarchical configuration management system that merges settings from enterprise, user, project, and local scopes with deterministic precedence rules.

### Technical Requirements

**REQ-CONFIG-001**: Configuration File Hierarchy
- **Priority**: CRITICAL
- **Description**: Implement 4-tier configuration loading system
  1. Enterprise scope: `/etc/claude-code/managed-settings.json` (highest priority)
  2. User global: `~/.config/claude/settings.json` (XDG) or `~/.claude/settings.json` (legacy)
  3. Project shared: `.claude/settings.json` (committed to Git)
  4. Project local: `.claude/settings.local.json` (gitignored, lowest priority)
- **Technical Details**:
  - Settings load sequentially from highest to lowest priority
  - Later scopes override primitives, extend objects, append arrays
  - `permissions.deny` at ANY level blocks access (security override)
- **Validation**: Each config file must parse as valid JSON
- **Dependencies**: File system access, JSON parser

**REQ-CONFIG-002**: XDG Base Directory Support
- **Priority**: HIGH
- **Description**: Support XDG Base Directory Specification for user configs
- **Technical Details**:
  - Primary path: `$XDG_CONFIG_HOME/claude/` (defaults to `~/.config/claude/`)
  - Fallback to legacy: `~/.claude/`
  - Environment variable override: `$CLAUDE_CONFIG_DIR`
- **Platform**: Cross-platform (Linux, macOS, Windows)

**REQ-CONFIG-003**: Configuration Merge Engine
- **Priority**: CRITICAL
- **Description**: Implement deterministic merge algorithm for configuration objects
- **Technical Details**:
  - **Primitives** (string, number, boolean): Later scope overrides earlier
  - **Arrays** (permissions.allow): Later scope appends to earlier
  - **Objects** (hooks, mcpServers): Deep merge with later scope taking precedence
  - **Special Case**: `permissions.deny` combines from all scopes (union operation)
- **Example**:
  ```json
  // User Global: { "model": "sonnet", "permissions": { "allow": ["Read"] } }
  // Project Shared: { "model": "opus", "permissions": { "allow": ["Write"] } }
  // RESULT: { "model": "opus", "permissions": { "allow": ["Read", "Write"] } }
  ```

**REQ-CONFIG-004**: Environment Variable Substitution
- **Priority**: HIGH
- **Description**: Support `${VAR_NAME}` syntax in configuration values
- **Technical Details**:
  - Substitute before configuration merge
  - Undefined variables should error (fail-fast)
  - Support in: `env` blocks, API keys, URLs
- **Security**: Never log substituted values

**REQ-CONFIG-005**: MCP Server Configuration
- **Priority**: HIGH
- **Description**: Support multiple MCP configuration sources
- **Sources**:
  1. `claude.json` (legacy, user-scope)
  2. `.mcp.json` (project-scope, committed)
  3. `settings.json` → `mcpServers` block (any scope)
  4. `settings.local.json` → `mcpServers` (local only)
- **Activation Control**:
  - `enableAllProjectMcpServers`: boolean
  - `enabledMcpjsonServers`: array of server names
  - `disabledMcpjsonServers`: array of server names

**REQ-CONFIG-006**: CLAUDE.md Memory Loading
- **Priority**: MEDIUM
- **Description**: Load project memory files from hierarchical locations
- **Hierarchy** (all loaded and concatenated):
  1. `/etc/claude-code/CLAUDE.md`
  2. `~/.config/claude/CLAUDE.md`
  3. Parent directories (recursive from project root)
  4. Project root: `./CLAUDE.md`
  5. Subdirectories (loaded on-demand when files accessed)
- **Import Syntax**: Support `@path/to/file.md` for file inclusion
- **Size Limit**: Warn if total exceeds 25KB

**REQ-CONFIG-007**: Configuration Validation
- **Priority**: HIGH
- **Description**: Validate all configuration files on load
- **Checks**:
  - Valid JSON syntax
  - Required fields present for MCP servers (command, args)
  - No duplicate hook names within same file
  - Permission matchers use valid glob patterns
  - Timeout values within acceptable ranges (0-600000ms)
- **Error Handling**: Clear error messages with file path and line number

---

## Component 2: JSONL Session Storage

### Overview
Newline-delimited JSON format for storing complete conversation history with token accounting and session analytics.

### Technical Requirements

**REQ-JSONL-001**: Project Hash Calculation
- **Priority**: CRITICAL
- **Description**: Generate deterministic project identifier from absolute path
- **Algorithm**:
  ```
  project_hash = base64url_encode(sha256(absolute_project_path.encode('utf-8')))[:20]
  ```
- **Storage Location**: `~/.config/claude/projects/<project-hash>/`
- **Uniqueness**: Hash must be collision-resistant for typical project count (<10,000)

**REQ-JSONL-002**: Session File Organization
- **Priority**: HIGH
- **Description**: One JSONL file per calendar day per project
- **Naming**: `YYYY-MM-DD.jsonl` (e.g., `2025-11-16.jsonl`)
- **Rotation**: New file created at midnight UTC
- **Encoding**: UTF-8 with LF line endings
- **Append-Only**: Never modify existing lines

**REQ-JSONL-003**: Message Type Schemas
- **Priority**: CRITICAL
- **Description**: Define 4 message types with strict schemas
- **Types**:
  1. **User Message**: `{ sessionId, timestamp, role: "user", content, model, attachments[] }`
  2. **Assistant Message**: `{ sessionId, timestamp, role: "assistant", content, toolCalls[], stopReason, inputTokens, outputTokens, cacheCreationTokens, cacheReadTokens, cost }`
  3. **Tool Call**: `{ sessionId, timestamp, role: "tool_call", toolCallId, toolName, toolInput, status }`
  4. **Tool Result**: `{ sessionId, timestamp, role: "tool_result", toolCallId, toolName, status, output, exitCode, executionTimeMs }`
- **Validation**: Each line must parse as one complete JSON object
- **Required Fields**: sessionId, timestamp, role (all messages)

**REQ-JSONL-004**: Session UUID Management
- **Priority**: HIGH
- **Description**: Generate unique session identifiers
- **Format**: UUID v4 (e.g., `01234567-89ab-cdef-0123-456789abcdef`)
- **Persistence**: Same sessionId for entire conversation
- **New Session**: New UUID on `claude --new` or after 24h idle

**REQ-JSONL-005**: Token Accounting
- **Priority**: HIGH
- **Description**: Track all token types in assistant messages
- **Fields**:
  - `inputTokens`: Prompt + context sent to model
  - `outputTokens`: Generated response tokens
  - `cacheCreationTokens`: First-time context caching (charged once)
  - `cacheReadTokens`: Reading cached context (90% discount)
- **Cost Calculation**: Apply model-specific rates (Sonnet 4.5: input $3/M, output $15/M, cache write $3.75/M, cache read $0.30/M)
- **Precision**: Store cost as float with 4 decimal places

**REQ-JSONL-006**: Session Resume
- **Priority**: CRITICAL
- **Description**: Restore conversation state from JSONL file
- **Process**:
  1. Read entire JSONL file line-by-line
  2. Parse each message (skip malformed lines with warning)
  3. Reconstruct conversation array in order
  4. Verify sessionId consistency
  5. Load into context window
- **Performance**: Stream large files (don't load entire file into memory)
- **Validation**: Reject if any message missing required fields

**REQ-JSONL-007**: Session Cleanup Policy
- **Priority**: MEDIUM
- **Description**: Auto-delete old session files
- **Default**: 30 days after last modification
- **Override**: `cleanupPeriodDays` setting (99999 = never delete)
- **Mechanism**: Background job runs daily
- **Safety**: Preserve sessions with `--no-cleanup` flag

**REQ-JSONL-008**: Analytics Extraction
- **Priority**: LOW
- **Description**: Support querying session metrics
- **Metrics**:
  - Total input/output tokens
  - Total cost
  - Tool usage frequency (by tool name)
  - Average tokens per message
  - Session duration
  - Success/failure counts
- **API**: Provide Python/TypeScript utility functions
- **Performance**: Incremental parsing (don't read entire file)

---

## Component 3: MCP Client Protocol

### Overview
JSON-RPC 2.0 client implementation supporting stdio, SSE, and HTTP transports for communicating with MCP servers.

### Technical Requirements

**REQ-MCP-001**: JSON-RPC 2.0 Compliance
- **Priority**: CRITICAL
- **Description**: Implement MCP protocol according to JSON-RPC 2.0 spec
- **Message Types**:
  - Request: `{ jsonrpc: "2.0", id, method, params }`
  - Response: `{ jsonrpc: "2.0", id, result }` or `{ jsonrpc: "2.0", id, error }`
  - Notification: `{ jsonrpc: "2.0", method, params }` (no id)
- **ID Generation**: Sequential integers per session
- **Error Codes**: Standard JSON-RPC codes (-32700 to -32603)

**REQ-MCP-002**: Stdio Transport
- **Priority**: CRITICAL
- **Description**: Communicate with MCP servers via stdin/stdout
- **Process Management**:
  - Spawn subprocess with configured command + args
  - Pipe JSON-RPC messages to stdin
  - Read JSON-RPC messages from stdout
  - Capture stderr for logging (separate from protocol)
- **Line Buffering**: Read complete JSON objects (newline-delimited)
- **Process Lifecycle**: Start on first tool call, keep alive for session

**REQ-MCP-003**: SSE Transport
- **Priority**: HIGH
- **Description**: Support Server-Sent Events transport for remote MCP servers
- **Configuration**: `{ "transport": "sse", "url": "https://..." }`
- **Protocol**:
  - HTTP GET to URL with `Accept: text/event-stream`
  - Parse SSE events (`data:` lines)
  - Decode JSON-RPC from event data
  - Send requests via POST to same URL
- **Reconnection**: Auto-reconnect with exponential backoff

**REQ-MCP-004**: HTTP Transport
- **Priority**: MEDIUM
- **Description**: Support standard HTTP transport
- **Configuration**: `{ "transport": "http", "url": "https://..." }`
- **Protocol**:
  - POST JSON-RPC request to URL
  - Parse JSON-RPC response from body
  - Headers: `Content-Type: application/json`
- **Timeout**: Configurable per request (default 30s)

**REQ-MCP-005**: Tool Discovery
- **Priority**: CRITICAL
- **Description**: Enumerate available tools from MCP servers
- **Method**: Call `tools/list` JSON-RPC method
- **Response Parsing**: Extract tool names, descriptions, input schemas
- **Caching**: Cache tool list per server (invalidate on server restart)
- **Display**: `claude mcp list` command to show all tools

**REQ-MCP-006**: Tool Invocation
- **Priority**: CRITICAL
- **Description**: Execute MCP tools from Claude agent
- **Method**: Call `tools/call` with tool name and parameters
- **Parameter Validation**: Check against tool's input schema (JSON Schema)
- **Timeout**: Respect `MCP_TOOL_TIMEOUT` setting (default 5 minutes)
- **Error Handling**: Parse error response, extract message, log full error

**REQ-MCP-007**: Environment Variable Injection
- **Priority**: HIGH
- **Description**: Inject environment variables into MCP server processes
- **Sources**:
  1. System environment
  2. Config file `env` block
  3. ApiKeyHelper scripts
- **ApiKeyHelper**:
  - Execute script: `./scripts/get-token.sh`
  - Capture stdout as value
  - Timeout after 10 seconds
  - Cache result for session
- **Security**: Never log environment variable values

**REQ-MCP-008**: MCP Server Lifecycle Management
- **Priority**: HIGH
- **Description**: Manage MCP server process lifecycle
- **Startup**: Lazy initialization (start on first tool call)
- **Health Check**: Ping server every 60s with `ping` method
- **Shutdown**: Send `shutdown` notification, wait 5s, SIGTERM, wait 5s, SIGKILL
- **Restart**: Auto-restart on crash (max 3 attempts)
- **Logging**: Log all MCP communication to `~/.claude/mcp-logs/`

---

## Component 4: Multi-Agent Orchestration

### Overview
Master-clone agent coordination system with Task() tool for parallel execution and wave-based workflow management.

### Technical Requirements

**REQ-AGENT-001**: Task Tool Implementation
- **Priority**: CRITICAL
- **Description**: Implement Task() tool for spawning sub-agents
- **Signature**: `Task(instruction: string) -> Promise<string>`
- **Behavior**:
  - Creates isolated agent instance
  - Separate context window (200K tokens)
  - Inherits CLAUDE.md from parent
  - No access to parent context beyond CLAUDE.md
  - Returns final result as string
- **Execution**: Run asynchronously (non-blocking)
- **Limits**: Max 10 concurrent tasks

**REQ-AGENT-002**: Sub-Agent Definition Format
- **Priority**: HIGH
- **Description**: Markdown with YAML frontmatter for sub-agents
- **File Locations**:
  - User: `~/.config/claude/agents/*.md`
  - Project: `.claude/agents/*.md`
- **Frontmatter Fields**:
  - `name`: Agent identifier (required)
  - `description`: When to invoke (required)
  - `tools`: Allowed tool list (optional, default: all)
  - `model`: Model override (optional)
- **Body**: System prompt for sub-agent
- **Loading**: Scan directories on startup, cache agent list

**REQ-AGENT-003**: Automatic Sub-Agent Invocation
- **Priority**: MEDIUM
- **Description**: Trigger sub-agents based on keywords in description
- **Trigger Words**: "MUST BE USED", "automatically", "always invoke"
- **Logic**: If user message or context matches trigger pattern, invoke sub-agent
- **Example**: Description contains "MUST BE USED after code changes" → invoke after Edit/Write tools
- **Timing**: Check after each tool execution

**REQ-AGENT-004**: Parallel Task Execution
- **Priority**: HIGH
- **Description**: Execute multiple tasks concurrently
- **API**:
  ```python
  tasks = [
      Task("Analyze module A"),
      Task("Analyze module B"),
      Task("Analyze module C")
  ]
  results = await asyncio.gather(*tasks)
  ```
- **Scheduling**: Use asyncio/promises for concurrency
- **Resource Management**: Limit concurrent API calls to avoid rate limiting
- **Result Collection**: Wait for all tasks, aggregate results

**REQ-AGENT-005**: Wave-Based Execution
- **Priority**: MEDIUM
- **Description**: Support multi-wave orchestration pattern
- **Definition**: Sequential waves of parallel operations
- **Implementation**:
  ```python
  # Wave 1: Information gathering
  wave1 = await execute_wave([Task(...), Task(...)])
  analysis = analyze(wave1)

  # Wave 2: Implementation
  wave2 = await execute_wave([Task(...), Task(...)])
  review = review(wave2)

  # Wave 3: Validation
  wave3 = await execute_wave([Task(...)])
  ```
- **Between Waves**: Main agent synthesizes results, makes decisions
- **State Passing**: Use CLAUDE.md updates or temporary files

**REQ-AGENT-006**: Inter-Agent Communication
- **Priority**: HIGH
- **Description**: Enable coordination between agents
- **Mechanisms**:
  1. **CLAUDE.md Updates**: Main agent writes findings to CLAUDE.md for subsequent agents
  2. **State Files**: Write to `/tmp/wave-{N}-results.json` for next wave to read
  3. **MCP Coordination**: Use Serena MCP write_memory/read_memory for structured coordination
- **No Direct Communication**: Sub-agents cannot message each other
- **Orchestration**: All coordination through main agent

**REQ-AGENT-007**: Context Window Management
- **Priority**: HIGH
- **Description**: Manage context across agent hierarchy
- **Main Agent**:
  - Full 200K token context
  - All CLAUDE.md files loaded
  - Complete conversation history
- **Sub-Agents**:
  - Separate 200K context per agent
  - CLAUDE.md inherited from main
  - Task instruction + relevant context only
  - No access to main agent's conversation
- **Compaction**: Support `/compact` command to summarize context

---

## Component 5: Validation Hooks & Gates

### Overview
Event-driven hook system for enforcing quality gates at specific workflow checkpoints with blocking/non-blocking execution.

### Technical Requirements

**REQ-HOOKS-001**: Hook Event Types
- **Priority**: CRITICAL
- **Description**: Support 9 hook event types
- **Events**:
  1. `PreToolUse`: Before tool execution (can block)
  2. `PostToolUse`: After tool completion
  3. `UserPromptSubmit`: When user submits prompt
  4. `Notification`: When Claude sends notification
  5. `Stop`: When Claude finishes response
  6. `SubagentStop`: When sub-agent completes
  7. `PreCompact`: Before context compaction
  8. `SessionStart`: When session starts
  9. `SessionEnd`: When session ends
- **Timing**: Hooks execute synchronously in order defined

**REQ-HOOKS-002**: Hook Configuration Schema
- **Priority**: CRITICAL
- **Description**: Define hook configuration structure
- **Schema**:
  ```json
  {
    "hooks": {
      "EventType": [
        {
          "matcher": "Bash(git commit:*)",  // Optional pattern
          "hooks": [
            {
              "type": "command",
              "command": "script.sh || exit 2"
            }
          ]
        }
      ]
    }
  }
  ```
- **Matcher**: Glob pattern for filtering (e.g., `Edit|Write` for any file edit)
- **Multiple Hooks**: Execute in array order

**REQ-HOOKS-003**: Hook Exit Code Handling
- **Priority**: CRITICAL
- **Description**: Interpret hook script exit codes
- **Codes**:
  - `0`: Success, continue execution
  - `2`: Block tool execution, show error message to Claude (recoverable)
  - Other: Fatal error, halt session
- **Error Message**: Capture stderr and display to Claude
- **Retry**: Claude can attempt tool again after fixing issue

**REQ-HOOKS-004**: Environment Variable Injection
- **Priority**: HIGH
- **Description**: Provide context to hook scripts via environment
- **Variables**:
  - `$FILE_PATH`: For Edit/Write hooks (absolute path)
  - `$TOOL_NAME`: Name of tool being executed
  - `$TOOL_ARGS`: JSON-encoded tool arguments
  - `$CONVERSATION_SUMMARY`: High-level summary (for Stop hooks)
  - `$CLAUDE_SESSION_ID`: Current session UUID
  - `$PROJECT_ROOT`: Absolute path to project
- **Encoding**: JSON for complex values, string for simple

**REQ-HOOKS-005**: PreToolUse Blocking Validation
- **Priority**: CRITICAL
- **Description**: Implement blocking validation pattern
- **Use Case**: Enforce tests pass before commit
- **Example**:
  ```json
  {
    "PreToolUse": [{
      "matcher": "Bash(git commit:*)",
      "hooks": [{
        "type": "command",
        "command": "[ -f /tmp/tests-passing ] || exit 2"
      }]
    }]
  }
  ```
- **Behavior**:
  - Hook runs before `git commit` executes
  - If /tmp/tests-passing missing, exit 2 → block commit
  - Claude sees error, runs tests, fixes failures, retries commit
- **Atomic**: Hook must complete before tool execution

**REQ-HOOKS-006**: PostToolUse Auto-Formatting
- **Priority**: HIGH
- **Description**: Implement non-blocking post-processing
- **Use Case**: Auto-format code after Edit/Write
- **Example**:
  ```json
  {
    "PostToolUse": [{
      "matcher": "Edit|Write",
      "hooks": [{
        "type": "command",
        "command": "prettier --write \"$FILE_PATH\""
      }]
    }]
  }
  ```
- **Behavior**:
  - Hook runs after file modification completes
  - Prettier reformats file in-place
  - Claude proceeds regardless of hook result (non-blocking)
- **Async**: Hook can run in background

**REQ-HOOKS-007**: Hook Script Management
- **Priority**: MEDIUM
- **Description**: Support external hook scripts
- **Location**: `.claude/hooks/scripts/`
- **Permissions**: Executable flag required (`chmod +x`)
- **Best Practice**: Use scripts for complex validation logic
- **Example**:
  ```json
  {
    "hooks": {
      "PreToolUse": [{
        "matcher": "Bash(git commit:*)",
        "hooks": [{
          "type": "command",
          "command": "./.claude/hooks/scripts/validate-commit.sh"
        }]
      }]
    }
  }
  ```

**REQ-HOOKS-008**: Multi-Stage Validation Pipeline
- **Priority**: HIGH
- **Description**: Support sequential validation stages
- **Stages**:
  1. Syntax check (PostToolUse → Edit/Write)
  2. Lint check (PostToolUse → Edit/Write)
  3. Test execution (PreToolUse → git commit)
  4. Security scan (PreToolUse → git commit)
- **Short-Circuit**: If any stage fails, halt pipeline
- **Logging**: Log each stage result to `.claude/logs/validation.log`
- **Example**: See Appendix B in source spec

---

## Component 6: Serena Integration

### Overview
Semantic code analysis integration via Serena MCP server for symbol-level navigation, editing, and dependency mapping.

### Technical Requirements

**REQ-SERENA-001**: Serena MCP Configuration
- **Priority**: HIGH
- **Description**: Configure Serena MCP server in Claude Code
- **Installation**: Via `uvx --from git+https://github.com/serena-ai/serena serena-mcp-server`
- **Configuration**:
  ```json
  {
    "mcpServers": {
      "serena": {
        "command": "uvx",
        "args": [
          "--from",
          "git+https://github.com/serena-ai/serena",
          "serena-mcp-server"
        ]
      }
    }
  }
  ```
- **Project Config**: `.serena/project.yml` for project-specific settings

**REQ-SERENA-002**: Symbol Navigation Tools
- **Priority**: CRITICAL
- **Description**: Implement symbol-level code navigation
- **Tools**:
  1. `find_symbol(name: string) -> SymbolLocation[]`
     - Locate symbol definitions by name
     - Returns file path, line number, column
  2. `find_referencing_symbols(symbol: string) -> Reference[]`
     - Find all references to a symbol
     - Returns call sites across codebase
  3. `get_symbol_context(symbol: string) -> SymbolInfo`
     - Retrieve full context (docstrings, type hints, etc.)
- **Language Support**: Any LSP-compatible language (Python, TypeScript, Go, etc.)

**REQ-SERENA-003**: Semantic Editing Tools
- **Priority**: CRITICAL
- **Description**: Implement precise symbol-level editing
- **Tools**:
  1. `insert_after_symbol(symbol: string, code: string)`
     - Insert code immediately after symbol definition
  2. `insert_before_symbol(symbol: string, code: string)`
     - Insert code before symbol definition
  3. `replace_symbol_definition(symbol: string, code: string)`
     - Replace entire symbol definition
- **Advantages Over Text Editing**:
  - No regex fragility
  - Respects code structure
  - Handles indentation automatically

**REQ-SERENA-004**: Serena-Coordinated Multi-Wave Orchestration
- **Priority**: HIGH
- **Description**: Use Serena for wave-based refactoring workflows
- **Pattern**:
  ```
  Wave 1: Discovery (Serena maps architecture)
  Wave 2: Analysis (Serena identifies coupling points)
  Wave 3: Implementation (Serena performs surgical edits)
  Wave 4: Validation (Serena verifies references intact)
  ```
- **Benefits**:
  - No context exhaustion (targeted symbol access)
  - Complete coverage (semantic dependency analysis)
  - Validation (check for broken references)

**REQ-SERENA-005**: Language Server Integration
- **Priority**: MEDIUM
- **Description**: Configure language servers via Serena
- **Config Location**: `~/.serena/serena_config.yml`
- **Example**:
  ```yaml
  language_servers:
    python:
      command: "pyls"
    typescript:
      command: "typescript-language-server"
      args: ["--stdio"]
    go:
      command: "gopls"
  ```
- **Auto-Detection**: Serena should auto-detect language from file extensions
- **Fallback**: Graceful degradation if LSP unavailable (text-based tools)

**REQ-SERENA-006**: Dependency Graph Generation
- **Priority**: MEDIUM
- **Description**: Support automated dependency mapping
- **Process**:
  1. `find_all_symbols(directory: string)`
  2. For each symbol: `find_referencing_symbols(symbol)`
  3. Build directed graph of dependencies
  4. Generate Mermaid diagram
  5. Identify circular dependencies
- **Output**: Markdown file with diagram + analysis
- **Use Case**: Architecture understanding, refactoring planning

**REQ-SERENA-007**: Validation Hook Integration
- **Priority**: MEDIUM
- **Description**: Use Serena in validation hooks
- **Example Hook** (`.claude/hooks/scripts/serena-validate.sh`):
  ```bash
  # Check for unused symbols
  unused=$(claude -p "Use Serena to find unused symbols")
  [ -z "$unused" ] || exit 2

  # Check for broken references
  broken=$(claude -p "Use Serena to check broken references")
  [ -z "$broken" ] || exit 2
  ```
- **Benefits**: Semantic validation beyond syntax/lint

---

## Cross-Component Integration Requirements

### REQ-INTEGRATION-001: Configuration → MCP
- Load MCP server definitions from merged configuration
- Apply environment variable substitution to MCP env blocks
- Respect activation controls (enableAllProjectMcpServers, etc.)

### REQ-INTEGRATION-002: JSONL → Session Resume
- Parse JSONL to reconstruct conversation state
- Extract token costs for analytics
- Resume at exact point of previous session

### REQ-INTEGRATION-003: MCP → Agent Orchestration
- Sub-agents inherit MCP server access from main agent
- Tool discovery scoped per agent (based on allowed tools)
- MCP servers shared across all agents in session

### REQ-INTEGRATION-004: Hooks → Validation Gates
- Execute hooks at defined checkpoints
- Block operations based on exit codes
- Pass context via environment variables

### REQ-INTEGRATION-005: Serena → Multi-Agent Coordination
- Use Serena write_memory/read_memory for inter-agent communication
- Semantic analysis in discovery wave, targeted edits in implementation wave
- Validation wave uses Serena to verify reference integrity

---

## Non-Functional Requirements

### Performance
- **PERF-001**: Configuration loading < 100ms for typical project
- **PERF-002**: JSONL write latency < 10ms (append operation)
- **PERF-003**: MCP tool call overhead < 50ms (excluding tool execution)
- **PERF-004**: Support up to 10 concurrent sub-agents
- **PERF-005**: Session resume for 1000-line JSONL < 5 seconds

### Security
- **SEC-001**: Never log API keys, tokens, or credentials
- **SEC-002**: Validate all configuration files before loading (prevent code injection)
- **SEC-003**: Sanitize hook command execution (escape shell metacharacters)
- **SEC-004**: MCP server processes run with minimal privileges
- **SEC-005**: Environment variable substitution fail-fast on missing vars

### Reliability
- **REL-001**: Graceful degradation if MCP server crashes (continue with built-in tools)
- **REL-002**: JSONL corruption recovery (skip malformed lines, continue session)
- **REL-003**: Hook failure doesn't crash session (log error, continue or block)
- **REL-004**: Auto-restart MCP servers on crash (max 3 attempts)

### Maintainability
- **MAINT-001**: Modular architecture (each component independently testable)
- **MAINT-002**: Comprehensive logging to `.claude/logs/`
- **MAINT-003**: Clear error messages with actionable remediation steps
- **MAINT-004**: Configuration schema versioning for backward compatibility

---

## Technology Stack Recommendations

### Core Implementation
- **Language**: Python 3.11+ (for rapid development, rich ecosystem)
- **Alternative**: TypeScript/Node.js (for better MCP compatibility)
- **JSON Parsing**: `ujson` (Python) or native JSON (TypeScript)
- **Subprocess Management**: `asyncio.subprocess` (Python) or `child_process` (Node.js)
- **HTTP Client**: `httpx` (Python) or `axios` (TypeScript)

### Storage
- **JSONL**: Plain text files (no database needed)
- **Configuration**: JSON files
- **Session State**: In-memory + JSONL persistence

### Testing
- **Unit Tests**: pytest (Python) or Jest (TypeScript)
- **Integration Tests**: Playwright for GitHub Actions testing
- **Validation**: JSON Schema validation for configs

---

## Summary

**Total Requirements**: 47 across 6 components

| Component | Requirements | Priority Breakdown |
|-----------|--------------|-------------------|
| 3-Tier Configuration | 7 | 3 Critical, 3 High, 1 Medium |
| JSONL Session Storage | 8 | 3 Critical, 3 High, 1 Medium, 1 Low |
| MCP Client Protocol | 8 | 4 Critical, 3 High, 1 Medium |
| Multi-Agent Orchestration | 7 | 1 Critical, 4 High, 2 Medium |
| Validation Hooks & Gates | 8 | 4 Critical, 3 High, 1 Medium |
| Serena Integration | 7 | 2 Critical, 2 High, 3 Medium |
| **Cross-Component** | 5 | All High |
| **Non-Functional** | 15 | All High |

**Implementation Priority**:
1. Configuration System (foundation for everything)
2. JSONL Storage (session persistence)
3. MCP Client (tool extensibility)
4. Hooks (quality gates)
5. Multi-Agent (advanced orchestration)
6. Serena (semantic analysis)

---

**Document Approval**: Ready for Wave 2 (Architecture Design)

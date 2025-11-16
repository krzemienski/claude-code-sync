# Claude Code Orchestration System - Requirements

**Generated**: Wave 1 - Foundation Analysis
**Source**: claude-code-settings.md (2,678 lines analyzed)
**Complexity**: 0.70 (HIGH)

## Core Requirements

### 1. Configuration Architecture (3-Tier Hierarchy)
- **R1.1**: Enterprise-scope managed settings (`/etc/claude-code/managed-settings.json`)
- **R1.2**: User-scope global settings (`~/.config/claude/settings.json`)
- **R1.3**: Project-scope shared settings (`.claude/settings.json`)
- **R1.4**: Project-scope local settings (`.claude/settings.local.json`, gitignored)
- **R1.5**: Merge strategy: Enterprise → User → Project → Local
  - Lists: Append
  - Objects: Extend
  - Primitives: Override
- **R1.6**: Environment variable substitution (`${GITHUB_TOKEN}`)
- **R1.7**: ApiKeyHelper script support for dynamic credentials

### 2. Session Storage (JSONL Format)
- **R2.1**: Location: `~/.config/claude/projects/<project-hash>/<date>.jsonl`
- **R2.2**: Project hash: `base64url(sha256(absolute_path))[:20]`
- **R2.3**: Format: Newline-delimited JSON (one object per line)
- **R2.4**: Message types: user, assistant, tool_call, tool_result
- **R2.5**: Token accounting: input, output, cache_creation, cache_read
- **R2.6**: Session lifecycle: create, resume, auto-delete (30 days default)

### 3. MCP Server Integration
- **R3.1**: MCP protocol: JSON-RPC 2.0
- **R3.2**: Transport types: stdio (default), SSE, HTTP
- **R3.3**: Server scopes: user-scope, project-scope, local-scope
- **R3.4**: Tool discovery and invocation
- **R3.5**: Credential management (env vars, apiKeyHelper)
- **R3.6**: Support 18+ MCP servers (GitHub, Playwright, Serena, etc.)

### 4. Multi-Agent Orchestration
- **R4.1**: Task() tool for parallel agent spawning
- **R4.2**: Master-Clone pattern (agents inherit full context)
- **R4.3**: True parallelism (all wave agents spawn in one message)
- **R4.4**: Context sharing via CLAUDE.md and Serena MCP
- **R4.5**: Multi-wave execution for complex tasks (complexity ≥0.50)

### 5. Validation Gates & Hooks
- **R5.1**: Hook types: PreToolUse, PostToolUse, Stop, SessionStart, SessionEnd, etc.
- **R5.2**: Hook exit codes: 0 (allow), 2 (block), other (error)
- **R5.3**: Block-at-Submit pattern for quality gates
- **R5.4**: Validation checkpoints between waves
- **R5.5**: Functional testing enforcement (NO MOCKS)

### 6. Serena MCP Coordination
- **R6.1**: Semantic code analysis (symbol-level navigation)
- **R6.2**: Memory storage for cross-session context
- **R6.3**: Checkpoint/restore functionality
- **R6.4**: LSP integration for multiple languages

## Functional Testing Requirements

All components MUST be tested with actual end-user execution:
- ✅ Create real files and execute real commands
- ✅ Verify actual system behavior
- ✅ Iterate until tests pass
- ❌ NO unit tests with mocks
- ❌ NO pytest mocks
- ❌ NO stub implementations

## Validation Gates

- Every git commit BLOCKED unless functional tests pass
- PreToolUse hook checks `/tmp/functional-tests-passing`
- Agents MUST run tests before committing
- Iterative test-fix loop enforced

## Success Criteria

- All 6 requirement categories implemented
- All functional tests passing (real execution)
- Git commits throughout with validation
- 5 waves complete with synthesis checkpoints
- Production-ready system

---

**Wave 1 Analysis Complete** ✅

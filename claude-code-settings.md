# Claude Code: Comprehensive Technical Documentation & Implementation Guide

**Version**: 2.0  
**Last Updated**: November 16, 2025  
**Author**: Technical Documentation Team  
**Purpose**: Complete reference for Claude Code configuration, orchestration, and multi-agent coordination

---

## Table of Contents

1. [Executive Overview](#executive-overview)
2. [Configuration Architecture](#configuration-architecture)
3. [Session Storage & JSONL Format](#session-storage--jsonl-format)
4. [MCP Server Integration](#mcp-server-integration)
5. [Multi-Agent Orchestration](#multi-agent-orchestration)
6. [Validation Gates & Quality Control](#validation-gates--quality-control)
7. [Serena MCP Coordination Patterns](#serena-mcp-coordination-patterns)
8. [Production Implementation Patterns](#production-implementation-patterns)
9. [Appendices](#appendices)

---

## Executive Overview

### What is Claude Code?

Claude Code is Anthropic's command-line interface (CLI) agent that transforms natural language instructions into executable development workflows. Unlike traditional code completion tools, Claude Code is fully **agentic** - it can execute multi-step flows, maintain session state across tasks, and coordinate multiple specialized sub-agents to accomplish complex engineering objectives.

### Key Architectural Principles

1. **Three-Tier Configuration Hierarchy**: Settings merge from enterprise → user → project → local scopes
2. **Session-Based State Management**: Complete conversation history stored in JSONL format
3. **Multi-Agent Orchestration**: Main agent delegates to specialized sub-agents for parallel execution
4. **Validation Gates**: Hook-based quality control ensures correctness before commit
5. **Semantic Code Understanding**: Integration with tools like Serena MCP for symbolic code analysis

### Core Capabilities

- **Autonomous Code Generation**: Multi-step implementations from natural language specs
- **Parallel Task Execution**: Spawn multiple sub-agents for concurrent operations
- **Context Preservation**: 200K+ token context window with intelligent compaction
- **Tool Integration**: MCP servers extend capabilities with external services
- **Quality Assurance**: Automated validation through hooks and test execution

---

## Configuration Architecture

### Three-Tier Hierarchy (Priority Order)

Claude Code's configuration system follows a hierarchical merge strategy where settings cascade from broadest to most specific scope:

```
Enterprise (Highest Priority)
    ↓
User Global Settings
    ↓
Project Shared Settings
    ↓
Project Local Settings (Lowest Priority)
```

### Configuration File Locations

#### 1. **Enterprise Scope** (Managed Installations)
- **Location**: `/etc/claude-code/managed-settings.json`
- **Priority**: Highest
- **Purpose**: Organization-wide policies that cannot be overridden
- **Typical Use**: Security policies, approved tool lists, compliance settings
- **Scope**: All users, all projects on the system

**Example Managed Settings**:
```json
{
  "permissions": {
    "deny": [
      "Read(./**/*.env*)",
      "Bash(rm -rf:*)",
      "WebFetch(*://internal-only.company.com/*)"
    ]
  },
  "mcpServers": {
    "enterprise-audit": {
      "command": "npx",
      "args": ["-y", "@company/audit-mcp-server"]
    }
  }
}
```

#### 2. **User Global Scope**
- **Locations**: 
  - **New (XDG)**: `~/.config/claude/settings.json`
  - **Legacy**: `~/.claude/settings.json`
- **Priority**: Second highest
- **Purpose**: Personal preferences across all projects
- **Environment Variable Override**: `CLAUDE_CONFIG_DIR`

**Example User Global Settings**:
```json
{
  "model": "claude-sonnet-4-5-20250929",
  "theme": "dark",
  "autoUpdates": false,
  "includeCoAuthoredBy": false,
  "cleanupPeriodDays": 99999,
  "permissions": {
    "allow": [
      "Bash(git status)",
      "Bash(git diff)",
      "Bash(npm run:test)",
      "Edit",
      "Write",
      "Read"
    ]
  }
}
```

#### 3. **Project Shared Scope**
- **Location**: `.claude/settings.json` (in project root)
- **Priority**: Third
- **Purpose**: Team-wide project settings committed to version control
- **Scope**: All team members working on the project

**Example Project Shared Settings**:
```json
{
  "model": "claude-opus-4-1-20250805",
  "permissions": {
    "allow": [
      "Bash(npm run:*)",
      "Bash(git commit:*)",
      "Bash(docker-compose:*)"
    ],
    "ask": [
      "Bash(git push:*)",
      "Bash(npm install:*)"
    ],
    "deny": [
      "Read(./secrets/**)",
      "Read(./**/*.key)",
      "Bash(curl:*)"
    ]
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash(git commit:*)",
        "hooks": [
          {
            "type": "command",
            "command": "[ -f /tmp/tests-passing ] || exit 2"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "npx prettier --write \"$FILE_PATH\""
          }
        ]
      }
    ]
  }
}
```

#### 4. **Project Local Scope** (Git-Ignored)
- **Location**: `.claude/settings.local.json`
- **Priority**: Lowest (but overrides for specified keys)
- **Purpose**: Machine-specific settings not shared with team
- **Version Control**: Always in `.gitignore`

**Example Project Local Settings**:
```json
{
  "enableAllProjectMcpServers": true,
  "permissions": {
    "allow": [
      "Bash(./scripts/local-dev-setup.sh)"
    ]
  },
  "mcpServers": {
    "local-db": {
      "command": "npx",
      "args": ["-y", "@local/database-mcp"],
      "env": {
        "DB_URL": "postgresql://localhost:5432/dev"
      }
    }
  }
}
```

### Configuration File Types & Purposes

#### A. **settings.json** (Main Configuration)

**Purpose**: Core Claude Code behavior settings

**Key Sections**:
- `model`: Default model selection
- `permissions`: Tool access control
- `hooks`: Automation triggers
- `cleanupPeriodDays`: Session retention policy
- `spinnerTipsEnabled`: UI preferences
- `verbose`: Debug output

**Complete Example**:
```json
{
  "model": "claude-sonnet-4-5-20250929",
  "permissions": {
    "allow": ["Edit", "Write", "Read", "Bash(git:*)"],
    "ask": ["Bash(npm install:*)"],
    "deny": ["Bash(rm:*)", "Read(.env*)"]
  },
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "echo \"$(date): $CONVERSATION_SUMMARY\" >> ~/.claude/activity.log"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "npx eslint --fix \"$FILE_PATH\""
          }
        ]
      }
    ]
  },
  "cleanupPeriodDays": 99999,
  "spinnerTipsEnabled": false,
  "verbose": true,
  "ANTHROPIC_API_KEY": "sk-ant-...",
  "HTTPS_PROXY": "http://localhost:8888",
  "MCP_TOOL_TIMEOUT": 300000,
  "BASH_MAX_TIMEOUT_MS": 600000
}
```

#### B. **claude.json** (Legacy MCP Configuration)

**Purpose**: MCP server definitions and project-specific settings

**Locations**:
- User-scope: `~/.claude.json`
- Project-scope: `./.claude.json` (deprecated, use `.mcp.json` instead)

**Structure**:
```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/Users/username/projects",
        "/Users/username/documents"
      ]
    }
  },
  "projects": {
    "/absolute/path/to/project": {
      "allowedTools": ["Task", "Bash", "Edit", "Read"],
      "mcpServers": {
        "project-specific-mcp": {
          "command": "npx",
          "args": ["-y", "@company/internal-mcp"]
        }
      }
    }
  }
}
```

#### C. **.mcp.json** (Project-Scoped MCP)

**Purpose**: Team-shared MCP server configurations

**Location**: Project root (committed to version control)

**Structure**:
```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    },
    "linear": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://mcp.linear.app/sse"]
    },
    "supabase": {
      "command": "npx",
      "args": ["-y", "@supabase/mcp-server-supabase@latest"],
      "env": {
        "SUPABASE_ACCESS_TOKEN": "${SUPABASE_ACCESS_TOKEN}"
      }
    }
  }
}
```

**Activation Controls** (in `.claude/settings.json`):
```json
{
  "enableAllProjectMcpServers": true,
  // OR
  "enabledMcpjsonServers": ["playwright", "linear"],
  // OR
  "disabledMcpjsonServers": ["supabase"]
}
```

#### D. **CLAUDE.md** (Project Memory)

**Purpose**: Persistent context loaded into every session

**Hierarchy**:
1. Enterprise: `/etc/claude-code/CLAUDE.md`
2. User: `~/.config/claude/CLAUDE.md`
3. Parent directories: Recursively loaded
4. Project root: `./CLAUDE.md`
5. Subdirectories: Loaded on-demand when files accessed

**Import Syntax**:
```markdown
# Main Project Guidelines

@../shared/coding-standards.md

@~/company/security-policies.md

## Project-Specific Rules

- Use TypeScript for all new files
- Run tests before committing
- Follow conventional commit format
```

**Best Practices**:
- **Start with Guardrails**: Document what Claude gets wrong, not everything
- **Don't `@`-File Docs**: Reference files, don't embed them directly
- **Provide Alternatives**: Don't just say "never", give positive guidance
- **Use as Forcing Function**: If docs are complex, simplify the tool
- **Keep Concise**: Target 10-25KB maximum

**Example CLAUDE.md**:
```markdown
# Monorepo Development Guide

## Python Development

- Always use `uv` for package management, never `pip` directly
- Test with `uv run pytest` before committing
- Format with `black` and lint with `ruff`
- Type hints required for all public functions

For advanced Python tooling, see `docs/python-advanced.md`

## TypeScript/React

- Use `pnpm` for package management
- Run `pnpm test` before committing
- Follow component patterns in `src/components/README.md`
- Never use `any` type, prefer `unknown` + type guards

## Git Workflow

- Branch naming: `feature/`, `fix/`, `refactor/`
- Conventional commits: `feat:`, `fix:`, `docs:`, `chore:`
- Always squash commits before merging

## Critical Rules

- Never commit `.env` files or secrets
- Never use `sudo` in scripts
- Never `rm -rf` without confirmation
- Always run pre-commit hooks (they auto-format)

## MCP Servers Available

- `github`: GitHub API access
- `linear`: Linear issue management
- `supabase`: Database operations

## Custom Commands

- `/catchup`: Read all changed files in current branch
- `/pr`: Clean up code and prepare pull request
```

### Configuration Merge Strategy

**Merge Logic**:
```
FINAL_CONFIG = merge(
    ENTERPRISE_SETTINGS,
    USER_GLOBAL_SETTINGS,
    PROJECT_SHARED_SETTINGS,
    PROJECT_LOCAL_SETTINGS
)
```

**For Lists (e.g., permissions.allow)**:
- Later scopes **append** to earlier scopes
- `permissions.deny` at any level blocks access

**For Objects (e.g., hooks)**:
- Later scopes **extend** earlier scopes
- Same hook name → later scope overrides

**For Primitives (e.g., model)**:
- Later scopes **override** earlier scopes

**Example Merge**:
```json
// User Global
{
  "model": "claude-sonnet-4-5-20250929",
  "permissions": { "allow": ["Read", "Edit"] }
}

// Project Shared
{
  "model": "claude-opus-4-1-20250805",
  "permissions": { "allow": ["Bash(git:*)"] }
}

// RESULT
{
  "model": "claude-opus-4-1-20250805",  // Overridden
  "permissions": { 
    "allow": ["Read", "Edit", "Bash(git:*)"]  // Merged
  }
}
```

### Environment Variables

**Precedence**: Environment variables > Configuration files

**Key Variables**:
```bash
# API Configuration
export ANTHROPIC_API_KEY="sk-ant-..."
export ANTHROPIC_MODEL="claude-sonnet-4-5-20250929"

# Network Configuration
export HTTPS_PROXY="http://localhost:8888"
export HTTP_PROXY="http://localhost:8888"

# Path Overrides
export CLAUDE_CONFIG_DIR="~/.custom-claude-dir"

# Timeouts
export MCP_TOOL_TIMEOUT=300000  # 5 minutes
export BASH_MAX_TIMEOUT_MS=600000  # 10 minutes
```

### Directory Structure Reference

**Complete Claude Code Directory Layout**:
```
~/.config/claude/                    # New XDG-compliant location
├── settings.json                    # User global settings
├── CLAUDE.md                        # User memory
├── commands/                        # User slash commands
│   ├── catchup.md
│   └── pr.md
├── agents/                          # User sub-agents
│   ├── code-reviewer.md
│   └── debugger.md
├── skills/                          # User skills
│   ├── deploy-to-vercel/
│   │   └── SKILL.md
│   └── run-tests/
│       └── SKILL.md
└── projects/                        # Session storage
    └── <project-hash>/
        ├── 2025-11-16.jsonl
        └── 2025-11-15.jsonl

.claude/                             # Project-specific settings
├── settings.json                    # Shared (committed)
├── settings.local.json              # Local (gitignored)
├── commands/                        # Project commands
│   └── fix-issue.md
├── agents/                          # Project sub-agents
│   └── test-runner.md
├── hooks/                           # Automation hooks
│   ├── hooks.json
│   └── scripts/
│       └── run-tests.sh
└── logs/                            # Debug logs (gitignored)

.mcp.json                            # Project MCP servers
CLAUDE.md                            # Project memory
```

---

## Session Storage & JSONL Format

### Session Storage Architecture

**Location**: `~/.config/claude/projects/<project-hash>/<date>.jsonl`

**Project Hash Calculation**:
```
project_hash = base64url_encode(
    sha256(absolute_project_path.encode('utf-8'))
)[:20]
```

**Example**:
```bash
# Project: /Users/nick/work/myapp
# Hash: VGhlIHF1aWNrIGJyb3du

# Sessions stored at:
~/.config/claude/projects/VGhlIHF1aWNrIGJyb3du/2025-11-16.jsonl
~/.config/claude/projects/VGhlIHF1aWNrIGJyb3du/2025-11-15.jsonl
```

### JSONL Format Specification

**File Format**: Newline-Delimited JSON (JSONL)  
**Encoding**: UTF-8  
**Line Format**: One complete JSON object per line

**Message Types**:
1. **User Messages**: Human input
2. **Assistant Messages**: Claude's responses
3. **Tool Call Messages**: Tool invocations
4. **Tool Result Messages**: Tool outputs

### JSONL Schema

#### User Message
```json
{
  "sessionId": "01234567-89ab-cdef-0123-456789abcdef",
  "timestamp": "2025-11-16T10:30:00.000Z",
  "role": "user",
  "content": "Refactor the authentication module to use JWT tokens",
  "model": "claude-sonnet-4-5-20250929",
  "contextWindow": 200000,
  "inputTokens": 15000,
  "attachments": [
    {
      "type": "file",
      "path": "/Users/nick/work/myapp/src/auth.py",
      "content": "..."
    }
  ]
}
```

#### Assistant Message
```json
{
  "sessionId": "01234567-89ab-cdef-0123-456789abcdef",
  "timestamp": "2025-11-16T10:30:15.000Z",
  "role": "assistant",
  "content": "I'll refactor the authentication module to use JWT tokens. Here's my plan:\n\n1. Install PyJWT dependency\n2. Create token generation function\n3. Create token validation middleware\n4. Update login endpoint\n5. Write tests\n\nLet me start by installing the dependency...",
  "model": "claude-sonnet-4-5-20250929",
  "stopReason": "end_turn",
  "inputTokens": 15243,
  "outputTokens": 2150,
  "cacheCreationTokens": 8000,
  "cacheReadTokens": 12000,
  "cost": 0.045,
  "toolCalls": [
    {
      "id": "tool_call_001",
      "type": "Bash",
      "input": {
        "command": "pip install pyjwt",
        "description": "Installing PyJWT library"
      }
    }
  ]
}
```

#### Tool Call Message
```json
{
  "sessionId": "01234567-89ab-cdef-0123-456789abcdef",
  "timestamp": "2025-11-16T10:30:16.000Z",
  "role": "tool_call",
  "toolCallId": "tool_call_001",
  "toolName": "Bash",
  "toolInput": {
    "command": "pip install pyjwt",
    "description": "Installing PyJWT library"
  },
  "status": "pending"
}
```

#### Tool Result Message
```json
{
  "sessionId": "01234567-89ab-cdef-0123-456789abcdef",
  "timestamp": "2025-11-16T10:30:18.000Z",
  "role": "tool_result",
  "toolCallId": "tool_call_001",
  "toolName": "Bash",
  "status": "success",
  "output": "Collecting pyjwt\n  Downloading PyJWT-2.8.0-py3-none-any.whl (22 kB)\nInstalling collected packages: pyjwt\nSuccessfully installed pyjwt-2.8.0",
  "exitCode": 0,
  "executionTimeMs": 2340
}
```

### Session Lifecycle

**1. Session Creation**
```
claude --model sonnet-4-5
→ Creates new session with UUID
→ Initializes JSONL file at ~/.config/claude/projects/<hash>/<date>.jsonl
→ Loads CLAUDE.md into context
```

**2. Message Exchange**
```
User: "Create a new API endpoint"
→ Append user message to JSONL
→ Send to Claude API
→ Receive assistant response
→ Append assistant message to JSONL
→ Execute tool calls
→ Append tool results to JSONL
```

**3. Session Resume**
```
claude --resume
→ Load entire JSONL file into context
→ Rebuild conversation state
→ Continue from last message
```

**4. Session Auto-Deletion**
```
Default: 30 days after last modification
Override: "cleanupPeriodDays": 99999
```

### Token Accounting

**Token Types**:
- **Input Tokens**: Prompt + context sent to model
- **Output Tokens**: Model's generated response
- **Cache Creation Tokens**: First-time context caching (charged once)
- **Cache Read Tokens**: Reading from cached context (90% cheaper)

**Cost Calculation** (Sonnet 4.5 rates):
```
Input: $3.00 per 1M tokens
Output: $15.00 per 1M tokens
Cache Write: $3.75 per 1M tokens
Cache Read: $0.30 per 1M tokens

Example:
Input: 15,000 tokens × $3.00/1M = $0.045
Output: 2,150 tokens × $15.00/1M = $0.032
Cache Write: 8,000 tokens × $3.75/1M = $0.030
Cache Read: 12,000 tokens × $0.30/1M = $0.004
──────────────────────────────────────────
Total: $0.111
```

### Session Analytics

**Extracting Metrics**:
```python
import json

def analyze_session(jsonl_path):
    total_input_tokens = 0
    total_output_tokens = 0
    tool_calls_count = 0
    tools_used = {}
    
    with open(jsonl_path, 'r') as f:
        for line in f:
            msg = json.loads(line)
            if msg['role'] == 'assistant':
                total_input_tokens += msg.get('inputTokens', 0)
                total_output_tokens += msg.get('outputTokens', 0)
                
                for tool_call in msg.get('toolCalls', []):
                    tool_calls_count += 1
                    tool_name = tool_call['type']
                    tools_used[tool_name] = tools_used.get(tool_name, 0) + 1
    
    return {
        'total_input_tokens': total_input_tokens,
        'total_output_tokens': total_output_tokens,
        'tool_calls_count': tool_calls_count,
        'tools_used': tools_used
    }
```

### Session Compaction

**Manual Compaction**:
```
/compact
→ Summarizes conversation history
→ Reduces context tokens
→ Maintains key facts and decisions
```

**Compaction Strategy**:
```
Original Context (150k tokens):
- Full CLAUDE.md
- All previous messages
- All tool outputs

After Compaction (50k tokens):
- Essential facts from CLAUDE.md
- Summary of decisions made
- Key code snippets referenced
- Recent messages (last 10-20)
```

**Recommendation**: Avoid auto-compaction; use `/clear` + manual state preservation instead

---

## MCP Server Integration

### Model Context Protocol (MCP) Overview

**Purpose**: Standardized protocol for connecting AI agents to external tools and data sources

**Architecture**:
```
Claude Code (MCP Client)
    ↓
MCP Protocol (JSON-RPC 2.0)
    ↓
MCP Server (Tool Provider)
    ↓
External Service (GitHub, Database, Filesystem, etc.)
```

### MCP Server Scopes

**1. User-Scope MCP**
- **Configuration**: `~/.claude.json` (legacy) or `~/.config/claude/settings.json`
- **Availability**: All projects for the user
- **Use Case**: Personal tools, global services

**2. Project-Scope MCP**
- **Configuration**: `.mcp.json` (committed to Git)
- **Availability**: Only when working in that project
- **Use Case**: Project-specific integrations, team-shared tools

**3. Local-Scope MCP**
- **Configuration**: `.claude/settings.local.json` (gitignored)
- **Availability**: Only on local machine
- **Use Case**: Machine-specific credentials, local databases

### MCP Server Configuration

#### Basic MCP Server Definition
```json
{
  "mcpServers": {
    "server-name": {
      "command": "npx",
      "args": ["-y", "@scope/mcp-package-name", "arg1", "arg2"],
      "env": {
        "API_TOKEN": "${API_TOKEN}",
        "API_URL": "https://api.example.com"
      }
    }
  }
}
```

#### Transport Types

**1. Stdio Transport** (Default)
```json
{
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-github"]
}
```

**2. SSE Transport** (Server-Sent Events)
```json
{
  "transport": "sse",
  "url": "https://mcp.linear.app/sse"
}
```

**3. HTTP Transport**
```json
{
  "transport": "http",
  "url": "https://mcp.example.com/api"
}
```

### Credential Management

**Environment Variable Substitution**:
```json
{
  "env": {
    "GITHUB_TOKEN": "${GITHUB_TOKEN}",
    "API_KEY": "${COMPANY_API_KEY}"
  }
}
```

**ApiKeyHelper Script** (Dynamic Credential Injection):
```json
{
  "env": {
    "API_TOKEN": {
      "apiKeyHelper": "./scripts/get-api-token.sh"
    }
  }
}
```

**get-api-token.sh**:
```bash
#!/bin/bash
# Fetch token from 1Password, AWS Secrets Manager, etc.
op item get "API Token" --fields password
```

### Popular MCP Servers

#### GitHub
```json
{
  "github": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-github"],
    "env": {
      "GITHUB_TOKEN": "${GITHUB_TOKEN}"
    }
  }
}
```

**Capabilities**: Repository management, PR operations, issue tracking

#### Filesystem
```json
{
  "filesystem": {
    "command": "npx",
    "args": [
      "-y",
      "@modelcontextprotocol/server-filesystem",
      "/Users/username/projects",
      "/Users/username/documents"
    ]
  }
}
```

**Capabilities**: File read/write outside project directory

#### Playwright (Browser Automation)
```json
{
  "playwright": {
    "command": "npx",
    "args": ["@playwright/mcp@latest"]
  }
}
```

**Capabilities**: Automated browser testing, web scraping

#### Linear (Issue Management)
```json
{
  "linear": {
    "command": "npx",
    "args": ["-y", "mcp-remote", "https://mcp.linear.app/sse"],
    "transport": "sse"
  }
}
```

**Capabilities**: Issue creation, project management

#### Supabase (Database)
```json
{
  "supabase": {
    "command": "npx",
    "args": ["-y", "@supabase/mcp-server-supabase@latest"],
    "env": {
      "SUPABASE_ACCESS_TOKEN": "${SUPABASE_ACCESS_TOKEN}"
    }
  }
}
```

**Capabilities**: Database queries, CRUD operations

### MCP Tool Discovery

**Runtime Tool Enumeration**:
```bash
claude mcp list
# Output:
# MCP Servers:
#   github: 15 tools available
#   filesystem: 5 tools available
#   playwright: 8 tools available
```

**Tool Usage**:
```
User: "Use the github MCP to create a PR for this feature"
→ Claude discovers github.create_pull_request tool
→ Executes tool with appropriate parameters
→ Returns PR URL
```

### MCP Best Practices

**1. Scope Appropriately**
- User-scope: Personal tools (note-taking, personal GitHub)
- Project-scope: Team tools (project-specific APIs)
- Local-scope: Machine-specific services (local database)

**2. Minimize Tool Count**
- Don't create 50 tools for one API
- Provide high-level tools: `execute_query(sql)` not `select()`, `insert()`, `update()`
- Let Claude script against raw data dumps

**3. Secure Credentials**
- Never commit tokens to Git
- Use environment variables
- Use `apiKeyHelper` for dynamic secrets
- Rotate credentials regularly

**4. Tool Design Patterns**

**Anti-Pattern (Too Many Tools)**:
```json
{
  "tools": [
    "list_repositories",
    "get_repository",
    "create_repository",
    "update_repository",
    "delete_repository",
    "list_issues",
    "get_issue",
    // ... 50 more tools
  ]
}
```

**Good Pattern (High-Level + Scripting)**:
```json
{
  "tools": [
    "execute_github_cli(command)",  // Let Claude use gh CLI
    "fetch_repository_data(filters)",  // Raw data dump
    "execute_graphql_query(query)"  // Direct API access
  ]
}
```

---

## Multi-Agent Orchestration

### Orchestration Architecture

**Three-Tier Agent Hierarchy**:
```
Main Agent (Orchestrator)
    ↓
Sub-Agents (Specialists)
    ↓
Task Tools (Parallel Workers)
```

### Main Agent (Orchestrator)

**Role**: Coordinates workflow, delegates tasks, synthesizes results

**Capabilities**:
- Interactive conversation with user
- High-level planning and decision-making
- Context management across 200K+ tokens
- Delegation to sub-agents via `Task()` tool
- Quality assurance and result validation

**Limitations**:
- Slow for simple operations (interactive overhead)
- Context window can fill up quickly
- Cannot execute parallel operations directly

**Example Usage**:
```
User: "Refactor the entire authentication system to use OAuth2"

Main Agent:
1. Analyzes current auth system
2. Creates refactoring plan
3. Delegates research to research sub-agent
4. Delegates implementation to multiple code sub-agents
5. Delegates testing to test sub-agent
6. Reviews all results
7. Integrates changes
```

### Sub-Agents (Specialists)

**Definition**: Specialized AI assistants with narrow focus and custom system prompts

**File Format**: Markdown with YAML frontmatter

**Locations**:
- User: `~/.config/claude/agents/*.md`
- Project: `.claude/agents/*.md`

**Example Sub-Agent** (`.claude/agents/code-reviewer.md`):
```markdown
---
name: code-reviewer
description: Expert code review specialist. Use immediately after writing or modifying code.
tools: Read, Grep, Bash(git diff:*)
model: claude-sonnet-4-5-20250929
---

You are a senior code reviewer ensuring high standards of code quality and security.

When invoked:
1. Run `git diff` to see recent changes
2. Focus on modified files
3. Begin review immediately

Review checklist:
- Code is simple and readable
- Functions and variables are well-named
- No duplicated code
- Proper error handling
- No exposed secrets or API keys
- Input validation implemented
- Good test coverage
- Performance considerations addressed

Provide feedback organized by priority:
- Critical issues (must fix)
- Warnings (should fix)
- Suggestions (consider improving)

Include specific examples of how to fix issues.
```

**Sub-Agent Types**:

1. **Automatic Invocation**: Triggered by keywords in description
```markdown
---
description: MUST BE USED after code changes. Automatically reviews code.
---
```

2. **Explicit Invocation**: User requests specific sub-agent
```
User: "Use the code-reviewer sub-agent to check my changes"
```

3. **Conditional Invocation**: Claude decides based on context
```
Claude: "I'll use the debugger sub-agent to investigate this error"
```

### Task Tool (Parallel Workers)

**Purpose**: Spawn isolated agent instances for parallel execution

**Invocation**:
```
Task("Analyze the user authentication module")
Task("Research OAuth2 best practices")
Task("Read all test files and summarize coverage")
```

**Characteristics**:
- **Separate Context**: Each task has its own context window
- **Parallel Execution**: Multiple tasks run concurrently
- **No State Sharing**: Tasks cannot communicate with each other
- **Read-Heavy**: Best for analysis, research, file reading
- **Write-Careful**: Avoid parallel writes to same files

**Example Workflow**:
```
Main Agent:
  Task("Read and analyze src/auth.py")
  Task("Read and analyze src/middleware.py")
  Task("Read and analyze tests/test_auth.py")
  
  Wait for all tasks to complete
  
  Synthesize findings from all 3 tasks
  Generate refactoring plan
```

### Orchestration Patterns

#### 1. **Sequential Delegation**
```
Main Agent
  → Sub-Agent A (completes)
  → Sub-Agent B (uses A's results)
  → Sub-Agent C (uses B's results)
  → Main Agent (synthesizes)
```

**Use Case**: Dependencies between tasks
**Example**: Research → Design → Implement → Test

#### 2. **Parallel Delegation**
```
Main Agent
  → Sub-Agent A (parallel)
  → Sub-Agent B (parallel)
  → Sub-Agent C (parallel)
  → Main Agent (synthesizes all results)
```

**Use Case**: Independent tasks
**Example**: Multiple microservices, multiple repositories

#### 3. **Hierarchical Delegation**
```
Main Agent
  → Orchestrator Sub-Agent
      → Worker Sub-Agent 1
      → Worker Sub-Agent 2
      → Worker Sub-Agent 3
  → Main Agent (final review)
```

**Use Case**: Complex multi-level workflows
**Example**: Large-scale refactoring across entire codebase

#### 4. **Master-Clone Pattern** (Recommended)
```
Main Agent (has full CLAUDE.md context)
  → Task("Clone: Read module A")
  → Task("Clone: Read module B")
  → Task("Clone: Read module C")
  → Main Agent decides next steps
```

**Advantages**:
- Clones inherit full context
- No fragmented knowledge
- Dynamic delegation (not pre-defined specialists)
- Flexible workflow adaptation

**Anti-Pattern: Lead-Specialist**:
```
Main Agent (limited context)
  → Specialist 1 (narrow context for task A only)
  → Specialist 2 (narrow context for task B only)
```

**Disadvantages**:
- Gatekeeps context
- Forces human-defined workflow
- Brittle and inflexible

### Multi-Wave Execution

**Definition**: Complex tasks executed in multiple sequential "waves" of parallel operations

**Wave Structure**:
```
Wave 1: Information Gathering
  - Task: Read all source files
  - Task: Read all test files
  - Task: Read documentation
  
  Main Agent: Analyze gathered information
  
Wave 2: Detailed Analysis
  - Task: Analyze authentication flow
  - Task: Analyze authorization flow
  - Task: Analyze session management
  
  Main Agent: Identify issues and opportunities
  
Wave 3: Implementation
  - Task: Refactor auth module
  - Task: Refactor middleware
  - Task: Update tests
  
  Main Agent: Review and integrate changes
  
Wave 4: Validation
  - Task: Run unit tests
  - Task: Run integration tests
  - Task: Run security scan
  
  Main Agent: Verify all checks pass
```

**Example Multi-Wave Workflow**:
```python
# Pseudo-code for multi-wave execution

def refactor_authentication_system():
    # Wave 1: Gather Information
    wave1_tasks = [
        Task("Read src/auth/*.py"),
        Task("Read src/middleware/*.py"),
        Task("Read tests/test_auth.py"),
        Task("Research OAuth2 best practices")
    ]
    wave1_results = await execute_parallel(wave1_tasks)
    
    # Main Agent: Analyze and Plan
    analysis = analyze_results(wave1_results)
    plan = create_refactoring_plan(analysis)
    
    # Wave 2: Implement Changes
    wave2_tasks = [
        Task(f"Refactor {module}") 
        for module in plan.modules_to_change
    ]
    wave2_results = await execute_parallel(wave2_tasks)
    
    # Main Agent: Review Changes
    review = review_changes(wave2_results)
    
    # Wave 3: Testing
    wave3_tasks = [
        Task("Run pytest tests/test_auth.py"),
        Task("Run integration tests"),
        Task("Run security scan")
    ]
    wave3_results = await execute_parallel(wave3_tasks)
    
    # Main Agent: Validate
    all_tests_pass = validate_tests(wave3_results)
    
    if all_tests_pass:
        return commit_changes()
    else:
        return fix_failing_tests()
```

### Parallelization Strategies

**1. File-Level Parallelism**
```
Task("Analyze src/auth.py")
Task("Analyze src/users.py")
Task("Analyze src/tokens.py")
```

**2. Module-Level Parallelism**
```
Task("Refactor authentication module")
Task("Refactor authorization module")
Task("Refactor session module")
```

**3. Repository-Level Parallelism**
```
Task("Analyze backend-api repository")
Task("Analyze frontend repository")
Task("Analyze mobile-app repository")
```

**4. Test-Level Parallelism**
```
Task("Run unit tests")
Task("Run integration tests")
Task("Run end-to-end tests")
Task("Run performance tests")
```

### Coordination Mechanisms

**1. Main Agent Coordination**
```
Main Agent:
  - Spawns all sub-agents
  - Waits for completion
  - Synthesizes results
  - Makes final decisions
```

**2. Message Passing** (Not Supported Directly)
```
# Sub-agents cannot communicate directly
# Must go through Main Agent

Sub-Agent A → Main Agent → Sub-Agent B
```

**3. Shared Context via CLAUDE.md**
```
# All agents read same CLAUDE.md
# Main Agent updates CLAUDE.md with findings
# Subsequent agents see updated context
```

**4. State Files**
```
Main Agent: "Write your findings to /tmp/wave1-analysis.md"
Sub-Agent A: Writes to /tmp/wave1-analysis.md
Main Agent: Reads /tmp/wave1-analysis.md
Main Agent: "Sub-Agent B, read /tmp/wave1-analysis.md and continue"
```

---

## Validation Gates & Quality Control

### Hook-Based Validation Architecture

**Hooks**: Deterministic automation triggers that execute at specific events

**Hook Types**:
1. **PreToolUse**: Before tool execution (can block)
2. **PostToolUse**: After tool completion
3. **UserPromptSubmit**: When user submits prompt
4. **Notification**: When Claude sends notification
5. **Stop**: When Claude finishes response
6. **SubagentStop**: When sub-agent completes
7. **PreCompact**: Before context compaction
8. **SessionStart**: When session starts
9. **SessionEnd**: When session ends

### Validation Gate Patterns

#### 1. **Block-at-Submit** (Recommended)

**Strategy**: Allow agent to complete work, then validate before commit

**Configuration**:
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash(git commit:*)",
        "hooks": [
          {
            "type": "command",
            "command": "[ -f /tmp/tests-passing ] || exit 2"
          }
        ]
      }
    ]
  }
}
```

**Validation Script** (`scripts/run-tests.sh`):
```bash
#!/bin/bash
set -e

# Run tests
if pytest tests/; then
    touch /tmp/tests-passing
    exit 0
else
    rm -f /tmp/tests-passing
    exit 1
fi
```

**Flow**:
```
Claude: Makes code changes
Claude: "Bash(git commit -m 'feat: add OAuth2')"
PreToolUse Hook: Checks for /tmp/tests-passing
  ├─ If exists: Allow commit
  └─ If missing: Block with exit code 2
      → Claude sees error
      → Claude runs tests
      → Tests fail
      → Claude fixes issues
      → Claude runs tests again
      → Tests pass (creates /tmp/tests-passing)
      → Claude attempts commit again
      → Hook succeeds
      → Commit allowed
```

**Benefits**:
- Let agent finish plan before validation
- Forces test-and-fix loop
- Automatic quality gate

**Hook Exit Codes**:
- `0`: Success, allow tool execution
- `2`: Block and show message to Claude
- Other: Error, halt session

#### 2. **Hint Hooks** (Non-Blocking Feedback)

**Strategy**: Provide guidance without blocking

**Configuration**:
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "grep -q 'TODO' \"$FILE_PATH\" && echo 'Warning: TODO comment left in code' || true"
          }
        ]
      }
    ]
  }
}
```

**Flow**:
```
Claude: Writes code with TODO comment
PostToolUse Hook: Detects TODO
  → Prints warning
  → Does not block
Claude: Sees warning
Claude: May or may not address it
```

#### 3. **Auto-Format Hooks**

**Strategy**: Automatically fix code style

**Configuration**:
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "npx prettier --write \"$FILE_PATH\""
          },
          {
            "type": "command",
            "command": "npx eslint --fix \"$FILE_PATH\""
          }
        ]
      }
    ]
  }
}
```

**Flow**:
```
Claude: Writes code (potentially unformatted)
PostToolUse Hook: Runs prettier
PostToolUse Hook: Runs eslint --fix
Result: Code automatically formatted
```

### Multi-Stage Validation

**Stage 1: Syntax Validation**
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python -m py_compile \"$FILE_PATH\" || exit 2"
          }
        ]
      }
    ]
  }
}
```

**Stage 2: Lint Validation**
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "flake8 \"$FILE_PATH\" || exit 2"
          }
        ]
      }
    ]
  }
}
```

**Stage 3: Test Validation**
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash(git commit:*)",
        "hooks": [
          {
            "type": "command",
            "command": "./scripts/run-all-tests.sh || exit 2"
          }
        ]
      }
    ]
  }
}
```

**Stage 4: Security Validation**
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash(git commit:*)",
        "hooks": [
          {
            "type": "command",
            "command": "bandit -r . || exit 2"
          }
        ]
      }
    ]
  }
}
```

### Validation Checkpoint System

**Checkpoint Definition**: Defined points in workflow where validation occurs

**Example Checkpoint Flow**:
```
1. Code Change
   ↓
   Checkpoint A: Syntax Check
   ├─ Pass → Continue
   └─ Fail → Fix and retry
   ↓
2. Code Formatting
   ↓
   Checkpoint B: Lint Check
   ├─ Pass → Continue
   └─ Fail → Fix and retry
   ↓
3. Test Execution
   ↓
   Checkpoint C: Test Suite
   ├─ Pass → Continue
   └─ Fail → Fix and retry
   ↓
4. Commit Preparation
   ↓
   Checkpoint D: Final Validation
   ├─ Pass → Commit allowed
   └─ Fail → Block commit
```

**Implementing Checkpoints**:
```bash
#!/bin/bash
# scripts/validation-checkpoints.sh

echo "=== Checkpoint A: Syntax ==="
python -m py_compile src/**/*.py || exit 1

echo "=== Checkpoint B: Lint ==="
flake8 src/ || exit 1

echo "=== Checkpoint C: Tests ==="
pytest tests/ || exit 1

echo "=== Checkpoint D: Security ==="
bandit -r src/ || exit 1

echo "✓ All checkpoints passed"
touch /tmp/validation-complete
```

### Quality Metrics Tracking

**Logging Validation Results**:
```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "echo \"$(date),$CONVERSATION_SUMMARY,$TESTS_PASSED\" >> ~/.claude/quality-log.csv"
          }
        ]
      }
    ]
  }
}
```

**Analytics on Quality Metrics**:
```python
import pandas as pd

df = pd.read_csv('~/.claude/quality-log.csv')
success_rate = df['tests_passed'].mean()
avg_iterations = df['conversation_length'].mean()

print(f"Test Success Rate: {success_rate:.2%}")
print(f"Avg Iterations to Pass: {avg_iterations:.1f}")
```

---

## Serena MCP Coordination Patterns

### Serena MCP Overview

**Purpose**: Semantic code analysis toolkit that provides symbol-level understanding of codebases

**Architecture**:
```
Claude Code (MCP Client)
    ↓
Serena MCP Server
    ↓
Solid-LSP Framework (Language Server Wrapper)
    ↓
Language Servers (TypeScript, Python, Go, etc.)
    ↓
Codebase (Symbolic/Semantic Analysis)
```

**Key Capabilities**:
1. **Symbol-Level Navigation**: Find definitions, references, implementations
2. **Semantic Search**: Query based on code structure, not text
3. **Intelligent Editing**: Insert code at precise locations (after function, before class, etc.)
4. **Multi-Language Support**: Works with any LSP-compatible language server

### Serena Installation & Configuration

#### Installation (via uv)
```bash
# Install Serena MCP server
uvx --from git+https://github.com/serena-ai/serena serena-mcp-server

# Or install locally
git clone https://github.com/serena-ai/serena
cd serena
uv sync
```

#### Claude Code Configuration
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

#### Alternative: Local Development Setup
```json
{
  "mcpServers": {
    "serena": {
      "command": "/absolute/path/to/uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/serena",
        "serena-mcp-server"
      ]
    }
  }
}
```

### Project Configuration

**Serena Config** (`~/.serena/serena_config.yml`):
```yaml
# Global Serena configuration
language_servers:
  python:
    command: "pyls"
  typescript:
    command: "typescript-language-server"
    args: ["--stdio"]
  go:
    command: "gopls"
```

**Project Config** (`.serena/project.yml`):
```yaml
# Project-specific configuration
project_name: "my-awesome-app"
root_path: "/Users/nick/work/my-awesome-app"
language: "python"
exclude_patterns:
  - "*.test.py"
  - "venv/**"
  - "node_modules/**"
```

### Serena Tools

#### 1. **find_symbol**
**Purpose**: Locate symbol definitions by name

**Usage**:
```
Claude: Use Serena to find the definition of the "authenticate" function
→ Serena:find_symbol(name="authenticate")
→ Returns: src/auth.py:45
```

#### 2. **find_referencing_symbols**
**Purpose**: Find all references to a symbol

**Usage**:
```
Claude: Use Serena to find all places where "authenticate" is called
→ Serena:find_referencing_symbols(symbol="authenticate")
→ Returns: [
    src/middleware.py:23,
    src/api/users.py:67,
    tests/test_auth.py:12
  ]
```

#### 3. **insert_after_symbol**
**Purpose**: Insert code immediately after a symbol definition

**Usage**:
```
Claude: Use Serena to add a new method after "authenticate" function
→ Serena:insert_after_symbol(
    symbol="authenticate",
    code="def refresh_token(self): ..."
  )
```

#### 4. **get_symbol_context**
**Purpose**: Retrieve full context around a symbol (docstrings, type hints, etc.)

**Usage**:
```
Claude: Use Serena to understand the "User" class
→ Serena:get_symbol_context(symbol="User")
→ Returns: Full class definition with context
```

### Serena as Orchestration Controller

**Pattern**: Use Serena to coordinate multi-agent workflows with semantic awareness

#### Example: Large-Scale Refactoring with Serena Coordination

**Scenario**: Refactor authentication system across 50 files

**Traditional Approach** (Text-Based):
```
Claude reads all 50 files (exhausts context)
Claude tries to remember where everything is
Claude makes changes (may miss references)
```

**Serena-Coordinated Approach** (Semantic):
```
Main Agent:
  1. Use Serena to map authentication architecture
     → Serena:find_symbol("authenticate")
     → Serena:find_referencing_symbols("authenticate")
  
  2. Create task list from semantic analysis
     files_to_change = [
       "src/auth.py",
       "src/middleware.py",
       "src/api/users.py",
       "tests/test_auth.py"
     ]
  
  3. Spawn sub-agents for each file
     Task(f"Use Serena to refactor {file}")
     Task(f"Use Serena to refactor {file}")
     Task(f"Use Serena to refactor {file}")
  
  4. Sub-agents use Serena for precise edits
     Serena:insert_after_symbol(...)
     Serena:replace_symbol_definition(...)
  
  5. Validate all changes
     Serena:find_referencing_symbols (check no broken refs)
```

**Benefits**:
- **No context exhaustion**: Serena provides targeted access
- **Precise editing**: Symbol-level operations, not text search/replace
- **Complete coverage**: Semantic analysis finds all dependencies
- **Validation**: Can verify no broken references

### Multi-Wave Serena Orchestration

**Wave 1: Discovery**
```
Main Agent:
  Task("Use Serena to map authentication module structure")
  Task("Use Serena to map authorization module structure")
  Task("Use Serena to map session module structure")

Results:
  - All symbols discovered
  - All dependencies mapped
  - Architecture diagram created
```

**Wave 2: Analysis**
```
Main Agent (using Wave 1 results):
  Task("Use Serena to analyze auth coupling with user module")
  Task("Use Serena to analyze auth coupling with API module")
  Task("Use Serena to analyze auth coupling with database module")

Results:
  - Coupling points identified
  - Refactoring strategy determined
```

**Wave 3: Implementation**
```
Main Agent (using Wave 2 strategy):
  Task("Use Serena to refactor auth module at symbol X")
  Task("Use Serena to refactor middleware at symbol Y")
  Task("Use Serena to refactor API at symbol Z")

Results:
  - All changes implemented with precise symbol edits
```

**Wave 4: Validation**
```
Main Agent:
  Task("Use Serena to verify no broken references to auth symbols")
  Task("Run test suite")
  Task("Check for unused imports with Serena")

Results:
  - All references valid
  - All tests pass
  - Clean code
```

### Serena + Hooks Integration

**Validation with Serena**:
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash(git commit:*)",
        "hooks": [
          {
            "type": "command",
            "command": "./scripts/serena-validate.sh || exit 2"
          }
        ]
      }
    ]
  }
}
```

**serena-validate.sh**:
```bash
#!/bin/bash
# Use Serena to validate code before commit

echo "=== Validating with Serena ==="

# Check for unused symbols
unused=$(claude -p "Use Serena to find unused symbols in src/")
if [ -n "$unused" ]; then
    echo "ERROR: Unused symbols found: $unused"
    exit 1
fi

# Check for broken references
broken=$(claude -p "Use Serena to check for broken symbol references")
if [ -n "$broken" ]; then
    echo "ERROR: Broken references: $broken"
    exit 1
fi

echo "✓ Serena validation passed"
exit 0
```

### Serena Coordination Best Practices

**1. Discovery Before Action**
```
Always use Serena to map the codebase before making changes:
- find_symbol to locate definitions
- find_referencing_symbols to understand dependencies
- get_symbol_context to understand purpose
```

**2. Precise Surgical Edits**
```
Use Serena's semantic editing instead of text manipulation:
- insert_after_symbol (precise location)
- replace_symbol_definition (exact scope)
NOT: grep + sed (fragile text matching)
```

**3. Validation Through Symbols**
```
After changes, verify with Serena:
- find_referencing_symbols (no broken refs)
- find_unused_symbols (clean up)
- verify_symbol_types (type safety)
```

**4. Parallel Semantic Operations**
```
Safe to run in parallel:
- Reading symbols (read-only)
- Analyzing different modules
- Validating separate components

Serialize when:
- Editing same symbols
- Modifying shared dependencies
```

---

## Production Implementation Patterns

### Enterprise Deployment Architecture

**Components**:
```
1. Claude Code CLI (Local Development)
   ├─ Developer workstations
   └─ Interactive debugging

2. Claude Code GitHub Action (CI/CD)
   ├─ Automated PR generation
   ├─ Bug triage and fixes
   └─ Code review assistance

3. Claude Code SDK (Custom Agents)
   ├─ Internal chat tools
   ├─ Batch processing scripts
   └─ Non-coding agents

4. Centralized Configuration
   ├─ Managed settings (enterprise policies)
   ├─ Shared CLAUDE.md (coding standards)
   └─ MCP server registry
```

### GitHub Actions Integration

**Use Case**: PR-from-anywhere automation

**Workflow** (`.github/workflows/claude-code-agent.yml`):
```yaml
name: Claude Code Agent

on:
  issues:
    types: [labeled]
  pull_request:
    types: [labeled]
  repository_dispatch:
    types: [claude-fix]

jobs:
  claude-agent:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: |
            ${{ github.event.issue.body }}
            
            Fix the issue described above and create a pull request.
          
          hooks: |
            {
              "PreToolUse": [{
                "matcher": "Bash(git commit:*)",
                "hooks": [{
                  "type": "command",
                  "command": "npm test || exit 2"
                }]
              }]
            }
      
      - name: Create Pull Request
        if: success()
        uses: peter-evans/create-pull-request@v5
        with:
          title: "Fix: ${{ github.event.issue.title }}"
          body: "Automated fix by Claude Code"
```

**Trigger from Slack**:
```python
# Slack bot integration
@slack_app.command("/claude-fix")
def claude_fix_command(ack, command):
    ack()
    
    # Trigger GitHub Action
    github.repos.create_dispatch_event(
        repo="company/backend",
        event_type="claude-fix",
        client_payload={
            "issue": command['text'],
            "user": command['user_id']
        }
    )
    
    return "Claude Code agent triggered! PR coming soon."
```

### Batch Processing Pattern

**Use Case**: Large-scale refactoring across multiple repositories

**Script** (parallel_refactor.sh):
```bash
#!/bin/bash
# Parallel refactoring across repositories

REPOS=(
  "/path/to/backend-api"
  "/path/to/frontend"
  "/path/to/mobile-app"
  "/path/to/shared-lib"
)

# Run Claude Code in parallel
for repo in "${REPOS[@]}"; do
  (
    cd "$repo"
    claude -p "Refactor authentication to use OAuth2. Follow the plan in REFACTORING_PLAN.md" &
  )
done

# Wait for all to complete
wait

echo "All refactorings complete"
```

### Quality Assurance Pipeline

**Stage 1: Pre-Commit Validation**
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash(git commit:*)",
        "hooks": [
          {
            "type": "command",
            "command": "./qa-pipeline/run-all-checks.sh || exit 2"
          }
        ]
      }
    ]
  }
}
```

**qa-pipeline/run-all-checks.sh**:
```bash
#!/bin/bash
set -e

echo "=== Stage 1: Syntax Check ==="
python -m py_compile src/**/*.py

echo "=== Stage 2: Type Check ==="
mypy src/

echo "=== Stage 3: Lint ==="
flake8 src/

echo "=== Stage 4: Security ==="
bandit -r src/

echo "=== Stage 5: Tests ==="
pytest tests/ --cov=src --cov-report=term-missing

echo "=== Stage 6: Integration Tests ==="
docker-compose up -d
pytest tests/integration/
docker-compose down

echo "✓ All QA checks passed"
touch /tmp/qa-passed
```

**Stage 2: Post-Commit Monitoring**
```json
{
  "hooks": {
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "./qa-pipeline/log-session-metrics.sh"
          }
        ]
      }
    ]
  }
}
```

**log-session-metrics.sh**:
```bash
#!/bin/bash

# Extract metrics from session
METRICS=$(claude -p "Analyze the session and report: 
  - Total files changed
  - Total test failures encountered
  - Number of iterations to pass
  - Total token cost")

# Log to metrics database
curl -X POST https://metrics.company.com/api/claude-sessions \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$CLAUDE_SESSION_ID\",
    \"metrics\": $METRICS,
    \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"
  }"
```

### Continuous Improvement Loop

**Data Collection**:
```bash
# Collect all GHA logs
gh run list --workflow=claude-code-agent --json conclusion,databaseId,createdAt \
  | jq -r '.[] | select(.conclusion=="failure") | .databaseId' \
  | xargs -I {} gh run view {} --log > failed-runs.log

# Analyze common failures
cat failed-runs.log | \
  grep "ERROR:" | \
  sort | uniq -c | sort -rn > common-errors.txt
```

**CLAUDE.md Updates**:
```markdown
# Common Issues (Auto-Generated from Logs)

## Issue: ImportError when using new dependencies
Solution: Always run `pip install -r requirements.txt` before running code

## Issue: Tests fail due to missing environment variables
Solution: Load .env.test before running tests:
```bash
export $(cat .env.test | xargs)
pytest tests/
```

## Issue: Git conflicts when multiple agents work on same file
Solution: Use file-level locks via hooks:
```bash
# Check if file is locked
flock /tmp/file-locks/"$FILE_PATH" || exit 2
```
```

### Access Control & Security

**Enterprise Managed Settings**:
```json
{
  "permissions": {
    "deny": [
      "Read(./**/.env*)",
      "Read(./**/*secret*)",
      "Read(./**/*key*)",
      "Read(./**/*.pem)",
      "Bash(curl:*)",
      "Bash(wget:*)",
      "Bash(ssh:*)",
      "Bash(rm -rf:*)",
      "WebFetch(*://internal.company.com/*)"
    ]
  },
  "mcpServers": {
    "audit-logger": {
      "command": "npx",
      "args": ["-y", "@company/audit-mcp"],
      "env": {
        "AUDIT_ENDPOINT": "https://audit.company.com/api/log"
      }
    }
  }
}
```

**Audit MCP Server** (logs all actions):
```typescript
// @company/audit-mcp implementation
server.tool('log_action', async ({ action, details }) => {
  await fetch('https://audit.company.com/api/log', {
    method: 'POST',
    body: JSON.stringify({
      timestamp: new Date().toISOString(),
      user: process.env.USER,
      action,
      details
    })
  });
});

// Intercept all tool calls
server.interceptor('before', async (toolName, args) => {
  await logAction('tool_call', { toolName, args });
});
```

---

## Appendices

### Appendix A: Complete Settings Reference

**All Available Settings** (settings.json):
```json
{
  // Model Configuration
  "model": "claude-sonnet-4-5-20250929",
  "ANTHROPIC_MODEL": "claude-sonnet-4-5-20250929",
  
  // API Configuration
  "ANTHROPIC_API_KEY": "sk-ant-...",
  "apiKeyHelper": "./scripts/get-api-key.sh",
  
  // Network Configuration
  "HTTPS_PROXY": "http://localhost:8888",
  "HTTP_PROXY": "http://localhost:8888",
  
  // Timeout Configuration
  "MCP_TOOL_TIMEOUT": 300000,
  "BASH_MAX_TIMEOUT_MS": 600000,
  
  // Session Configuration
  "cleanupPeriodDays": 99999,
  
  // UI Configuration
  "theme": "dark",
  "spinnerTipsEnabled": false,
  "verbose": true,
  
  // Git Configuration
  "includeCoAuthoredBy": false,
  
  // Update Configuration
  "autoUpdates": false,
  
  // Permissions
  "permissions": {
    "allow": ["Read", "Edit", "Write", "Task", "Bash(git:*)"],
    "ask": ["Bash(npm install:*)"],
    "deny": ["Bash(rm:*)", "Read(.env*)"]
  },
  
  // Hooks
  "hooks": {
    "PreToolUse": [...],
    "PostToolUse": [...],
    "UserPromptSubmit": [...],
    "Notification": [...],
    "Stop": [...],
    "SubagentStop": [...],
    "PreCompact": [...],
    "SessionStart": [...],
    "SessionEnd": [...]
  },
  
  // MCP Configuration (project-specific)
  "mcpServers": {...},
  "enableAllProjectMcpServers": true,
  "enabledMcpjsonServers": ["github", "linear"],
  "disabledMcpjsonServers": ["supabase"]
}
```

### Appendix B: Hook Examples Library

**1. Auto-Format on Save**
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "npx prettier --write \"$FILE_PATH\""
          }
        ]
      }
    ]
  }
}
```

**2. Enforce Tests Before Commit**
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash(git commit:*)",
        "hooks": [
          {
            "type": "command",
            "command": "npm test || exit 2"
          }
        ]
      }
    ]
  }
}
```

**3. Log All Activity**
```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "echo \"$(date): $CONVERSATION_SUMMARY\" >> ~/.claude/activity.log"
          }
        ]
      }
    ]
  }
}
```

**4. Security Scan on Commit**
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash(git commit:*)",
        "hooks": [
          {
            "type": "command",
            "command": "bandit -r src/ || exit 2"
          }
        ]
      }
    ]
  }
}
```

**5. Notify on Completion**
```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "osascript -e 'display notification \"Claude finished!\" with title \"Claude Code\"'"
          }
        ]
      }
    ]
  }
}
```

### Appendix C: Sub-Agent Templates

**1. Code Reviewer**
```markdown
---
name: code-reviewer
description: Reviews code for bugs, security issues, and best practices
tools: Read, Grep, Bash(git diff:*)
model: claude-sonnet-4-5-20250929
---

You are a senior code reviewer.

Review checklist:
- Code quality and readability
- Security vulnerabilities
- Performance issues
- Test coverage
- Documentation

Provide prioritized feedback:
1. Critical (must fix)
2. Warnings (should fix)
3. Suggestions (nice to have)
```

**2. Test Writer**
```markdown
---
name: test-writer
description: Writes comprehensive unit and integration tests
tools: Read, Edit, Write, Bash(pytest:*)
model: claude-sonnet-4-5-20250929
---

You are a test specialist.

For each function/class:
1. Write unit tests (happy path + edge cases)
2. Write integration tests if applicable
3. Aim for >90% code coverage
4. Use clear test names

Test file naming: test_{module_name}.py
```

**3. Debugger**
```markdown
---
name: debugger
description: Investigates and fixes bugs systematically
tools: Read, Edit, Bash, Grep
model: claude-opus-4-1-20250805
---

You are a debugging specialist.

Process:
1. Reproduce the bug
2. Identify root cause
3. Form hypothesis
4. Test hypothesis
5. Implement minimal fix
6. Verify fix works
7. Add test to prevent regression
```

### Appendix D: JSONL Analysis Scripts

**Extract Token Usage**:
```python
import json

def analyze_token_usage(jsonl_path):
    total_input = 0
    total_output = 0
    total_cache_read = 0
    total_cache_write = 0
    
    with open(jsonl_path, 'r') as f:
        for line in f:
            msg = json.loads(line)
            if msg['role'] == 'assistant':
                total_input += msg.get('inputTokens', 0)
                total_output += msg.get('outputTokens', 0)
                total_cache_read += msg.get('cacheReadTokens', 0)
                total_cache_write += msg.get('cacheCreationTokens', 0)
    
    return {
        'input': total_input,
        'output': total_output,
        'cache_read': total_cache_read,
        'cache_write': total_cache_write
    }
```

**Extract Tool Usage**:
```python
def analyze_tool_usage(jsonl_path):
    tools = {}
    
    with open(jsonl_path, 'r') as f:
        for line in f:
            msg = json.loads(line)
            if msg['role'] == 'assistant':
                for tool_call in msg.get('toolCalls', []):
                    tool_name = tool_call['type']
                    tools[tool_name] = tools.get(tool_name, 0) + 1
    
    return tools
```

**Convert JSONL to Markdown**:
```python
def jsonl_to_markdown(jsonl_path, output_path):
    with open(jsonl_path, 'r') as f_in, open(output_path, 'w') as f_out:
        for line in f_in:
            msg = json.loads(line)
            
            if msg['role'] == 'user':
                f_out.write(f"## User\n\n{msg['content']}\n\n")
            elif msg['role'] == 'assistant':
                f_out.write(f"## Claude\n\n{msg['content']}\n\n")
                
                for tool_call in msg.get('toolCalls', []):
                    f_out.write(f"### Tool: {tool_call['type']}\n")
                    f_out.write(f"```\n{tool_call['input']}\n```\n\n")
```

### Appendix E: Serena Advanced Patterns

**Pattern 1: Dependency Graph Generation**
```
Main Agent: Use Serena to map all dependencies in src/

Sub-Agent (Discovery):
  Serena:find_all_symbols(directory="src/")
  → Returns: [Symbol1, Symbol2, ...]

Sub-Agent (Analysis):
  For each symbol:
    Serena:find_referencing_symbols(symbol)
    → Build dependency graph

Main Agent:
  Generate Mermaid diagram from graph
  Identify circular dependencies
  Suggest refactoring opportunities
```

**Pattern 2: Safe Refactoring**
```
Main Agent: Refactor function X to Y

Step 1: Discovery
  Serena:find_symbol("function_X")
  Serena:find_referencing_symbols("function_X")

Step 2: Validation
  Ensure no external packages reference it
  Check if it's part of public API

Step 3: Refactoring
  Serena:insert_after_symbol("function_X", "function_Y")
  For each reference:
    Serena:replace_symbol_reference("function_X", "function_Y")

Step 4: Cleanup
  Serena:delete_symbol("function_X")

Step 5: Verification
  Serena:find_referencing_symbols("function_X")
  → Should return empty list
```

---

## Conclusion

This comprehensive documentation covers the complete Claude Code ecosystem from configuration architecture through multi-agent orchestration, validation gates, and production deployment patterns. Key takeaways:

1. **Three-Tier Configuration**: Enterprise → User → Project → Local
2. **JSONL Session Storage**: Complete history with token accounting
3. **MCP Integration**: Extensible tool ecosystem with semantic capabilities
4. **Multi-Agent Orchestration**: Master-Clone pattern with wave-based execution
5. **Validation Gates**: Hook-based quality control with checkpoint systems
6. **Serena Coordination**: Semantic code analysis for precise orchestration
7. **Production Patterns**: GitHub Actions, batch processing, QA pipelines

**Next Steps**:
1. Implement basic configuration hierarchy
2. Set up validation hooks for quality control
3. Configure essential MCP servers (GitHub, Filesystem)
4. Experiment with sub-agent orchestration
5. Integrate Serena for semantic code operations
6. Deploy GitHub Actions for automated workflows

---

**Document Version**: 2.0  
**Last Updated**: November 16, 2025  
**Maintained By**: Engineering Documentation Team

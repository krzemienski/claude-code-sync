# Claude Code Orchestration System - Project Memory

## Development Guidelines

### Python Development
- Use Python 3.11+ for all code
- Type hints required for all public functions
- Async/await for I/O operations (MCP transports, agent coordination)
- Minimal external dependencies (aiohttp for SSE/HTTP only)
- Follow PEP 8 style guide

### Testing Requirements
- **Functional tests ONLY** (NO MOCKS, NO STUBS)
- Test with real file I/O, real MCP connections, real subprocess execution
- Every component must have functional `.sh` test script
- Tests must be end-user execution style
- **NO pytest unit tests** - bash scripts only

### Git Workflow
- **TDD**: Write failing test → implement → verify pass → commit
- Commit after each component completion
- **Validation gate**: `/tmp/functional-tests-passing` before commit
- Push after major milestones
- Conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`

## Critical Rules

- **NO pytest mocks or stubs** - Functional testing only
- **NO unit tests** - Only integration/functional tests
- All tests execute real commands and verify real output
- Follow Shannon principles: wave-based execution for complexity ≥0.50
- 4-tier config hierarchy (Enterprise > User > Project Shared > Project Local)

## MCP Servers Available

- **GitHub MCP**: Repository operations, PR management
- **Filesystem MCP**: File I/O outside project
- **Memory MCP**: Knowledge graph storage
- **Sequential MCP**: Step-by-step reasoning (100+ thoughts)
- **Playwright MCP**: Browser automation (when configured)
- **Linear MCP**: Issue management (SSE transport)

## Custom Commands

Run functional tests:
```bash
bash tests/run_all_tests.sh
```

Run CLI:
```bash
python3 -m src.cli --message "Your message"
```

## Architecture Principles

- **4-tier configuration hierarchy**: Enterprise > User > Project Shared > Project Local
- **JSONL session storage**: ~/.config/claude/projects/<hash>/<date>.jsonl
- **MCP JSON-RPC 2.0**: 3 transports (stdio/SSE/HTTP)
- **Multi-agent coordination**: Task() tool with wave-based execution
- **Hook-based validation gates**: 9 event types, exit code 2 = block
- **Serena MCP integration**: Semantic code analysis and state coordination

## Project Structure

```
src/
├── cli.py                 - CLI entry point
├── session_manager.py     - Session lifecycle
├── config_loader.py       - 4-tier config with env vars + ApiKeyHelper
├── jsonl_parser.py        - Streaming JSONL parser
├── jsonl_writer.py        - Atomic JSONL writer
├── mcp_client.py          - JSON-RPC 2.0 client
├── agent_coordinator.py   - Multi-agent orchestration
├── hook_engine.py         - Validation hooks (9 event types)
├── validation_gates.py    - Quality checkpoints
└── transports/            - MCP transport layer (stdio/SSE/HTTP)

tests/
└── test_*_functional.sh   - Functional test scripts only
```

## Contributing

1. Read complete specification: `claude-code-settings.md`
2. Follow TDD: Test first, then implement
3. Run functional tests before committing
4. Update documentation for new features
5. No external dependencies without approval

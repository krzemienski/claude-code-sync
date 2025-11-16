---
name: test
description: Run all functional tests
---

Run complete functional test suite for Claude Code Orchestration System.

## Test Execution

```bash
bash tests/run_all_tests.sh
```

## Test Categories

1. Configuration tests (4-tier hierarchy)
2. JSONL storage tests (parser + writer)
3. MCP protocol tests (all 3 transports)
4. Agent coordination tests
5. Hook engine tests (all 9 event types)
6. Validation gates tests
7. E2E integration tests

All tests use functional testing approach (real execution, NO MOCKS).

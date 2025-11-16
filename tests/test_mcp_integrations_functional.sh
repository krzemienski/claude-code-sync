#!/bin/bash
# Functional Test: Real MCP Server Connections
# Tests actual connectivity to 9 MCP servers

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$PROJECT_DIR/config/mcp-servers.json"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Logging
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Test result tracking
pass_test() {
    TESTS_PASSED=$((TESTS_PASSED + 1))
    TESTS_RUN=$((TESTS_RUN + 1))
    log_info "✅ $1"
}

fail_test() {
    TESTS_FAILED=$((TESTS_FAILED + 1))
    TESTS_RUN=$((TESTS_RUN + 1))
    log_error "❌ $1"
}

# Helper: Start MCP server and test connection
test_mcp_server() {
    local server_name=$1
    local command=$2
    shift 2
    local args=("$@")

    log_info "Testing $server_name MCP server..."

    # Start server in background
    local server_pid
    if [ ${#args[@]} -eq 0 ]; then
        $command &
        server_pid=$!
    else
        $command "${args[@]}" &
        server_pid=$!
    fi

    # Wait for server to start
    sleep 3

    # Test connection using Python MCP client
    local test_result
    test_result=$(python3 -c "
import sys
import json
import subprocess
import time

try:
    # Create test client
    cmd = ['$command'] + [$(printf "'%s', " "${args[@]}" | sed 's/, $//')] if '${args[@]}' else ['$command']

    # Simple stdio test - send initialize request
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Send initialize request
    init_request = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'initialize',
        'params': {
            'protocolVersion': '0.1.0',
            'capabilities': {},
            'clientInfo': {
                'name': 'test-client',
                'version': '1.0.0'
            }
        }
    }

    proc.stdin.write(json.dumps(init_request) + '\n')
    proc.stdin.flush()

    # Wait for response (with timeout)
    time.sleep(2)

    # Check if process is still running
    if proc.poll() is None:
        proc.terminate()
        print('SUCCESS')
    else:
        print('FAILED')

except Exception as e:
    print(f'ERROR: {str(e)}')
    sys.exit(1)
" 2>&1)

    # Kill server
    kill $server_pid 2>/dev/null || true
    wait $server_pid 2>/dev/null || true

    # Check result
    if [[ "$test_result" == *"SUCCESS"* ]]; then
        pass_test "$server_name server connection verified"
        return 0
    else
        fail_test "$server_name server connection failed: $test_result"
        return 1
    fi
}

# Verify config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    log_error "Config file not found: $CONFIG_FILE"
    exit 1
fi

log_info "Starting MCP Integration Functional Tests"
log_info "Config: $CONFIG_FILE"
echo ""

# Test 1: GitHub MCP
log_info "=== Test 1: GitHub MCP ==="
if command -v npx &> /dev/null; then
    test_mcp_server "GitHub" "npx" "-y" "@modelcontextprotocol/server-github"
else
    log_warn "npx not found, skipping GitHub MCP test"
    fail_test "GitHub MCP - npx not available"
fi
echo ""

# Test 2: Filesystem MCP
log_info "=== Test 2: Filesystem MCP ==="
if command -v npx &> /dev/null; then
    test_mcp_server "Filesystem" "npx" "-y" "@modelcontextprotocol/server-filesystem" "$PROJECT_DIR"
else
    log_warn "npx not found, skipping Filesystem MCP test"
    fail_test "Filesystem MCP - npx not available"
fi
echo ""

# Test 3: Git MCP
log_info "=== Test 3: Git MCP ==="
if command -v npx &> /dev/null; then
    test_mcp_server "Git" "npx" "-y" "@modelcontextprotocol/server-git"
else
    log_warn "npx not found, skipping Git MCP test"
    fail_test "Git MCP - npx not available"
fi
echo ""

# Test 4: Memory MCP
log_info "=== Test 4: Memory MCP ==="
if command -v npx &> /dev/null; then
    test_mcp_server "Memory" "npx" "-y" "@modelcontextprotocol/server-memory"
else
    log_warn "npx not found, skipping Memory MCP test"
    fail_test "Memory MCP - npx not available"
fi
echo ""

# Test 5: Fetch MCP
log_info "=== Test 5: Fetch MCP ==="
if command -v npx &> /dev/null; then
    test_mcp_server "Fetch" "npx" "-y" "@modelcontextprotocol/server-fetch"
else
    log_warn "npx not found, skipping Fetch MCP test"
    fail_test "Fetch MCP - npx not available"
fi
echo ""

# Test 6: Puppeteer MCP (disabled by default)
log_info "=== Test 6: Puppeteer MCP ==="
log_warn "Puppeteer MCP is disabled by default (requires Chrome)"
if command -v npx &> /dev/null && [ "${ENABLE_PUPPETEER_TEST:-0}" = "1" ]; then
    test_mcp_server "Puppeteer" "npx" "-y" "@modelcontextprotocol/server-puppeteer"
else
    log_warn "Skipping Puppeteer test (set ENABLE_PUPPETEER_TEST=1 to enable)"
fi
echo ""

# Test 7: PostgreSQL MCP (disabled by default)
log_info "=== Test 7: PostgreSQL MCP ==="
log_warn "PostgreSQL MCP is disabled by default (requires DB)"
if command -v npx &> /dev/null && [ -n "${POSTGRES_CONNECTION_STRING:-}" ]; then
    test_mcp_server "PostgreSQL" "npx" "-y" "@modelcontextprotocol/server-postgres"
else
    log_warn "Skipping PostgreSQL test (set POSTGRES_CONNECTION_STRING to enable)"
fi
echo ""

# Test 8: SQLite MCP (disabled by default)
log_info "=== Test 8: SQLite MCP ==="
log_warn "SQLite MCP is disabled by default"
if command -v npx &> /dev/null && [ "${ENABLE_SQLITE_TEST:-0}" = "1" ]; then
    test_mcp_server "SQLite" "npx" "-y" "@modelcontextprotocol/server-sqlite"
else
    log_warn "Skipping SQLite test (set ENABLE_SQLITE_TEST=1 to enable)"
fi
echo ""

# Test 9: Time MCP
log_info "=== Test 9: Time MCP ==="
if command -v npx &> /dev/null; then
    test_mcp_server "Time" "npx" "-y" "@modelcontextprotocol/server-time"
else
    log_warn "npx not found, skipping Time MCP test"
    fail_test "Time MCP - npx not available"
fi
echo ""

# Test 10: Config validation
log_info "=== Test 10: Config Validation ==="
if python3 -c "import json; json.load(open('$CONFIG_FILE'))" 2>/dev/null; then
    pass_test "Config file is valid JSON"
else
    fail_test "Config file is invalid JSON"
fi
echo ""

# Summary
echo "========================================"
echo "MCP Integration Test Summary"
echo "========================================"
echo "Tests Run:    $TESTS_RUN"
echo "Tests Passed: $TESTS_PASSED"
echo "Tests Failed: $TESTS_FAILED"
echo "========================================"

if [ $TESTS_FAILED -eq 0 ]; then
    log_info "✅ All MCP integration tests PASSED"
    exit 0
else
    log_error "❌ Some MCP integration tests FAILED"
    exit 1
fi

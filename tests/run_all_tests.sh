#!/bin/bash
# Comprehensive test runner for MCP Client
set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║        MCP Client - Comprehensive Test Suite              ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Track results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

run_test() {
    local name=$1
    local command=$2

    echo "┌────────────────────────────────────────────────────────────┐"
    echo "│ $name"
    echo "└────────────────────────────────────────────────────────────┘"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if eval "$command"; then
        echo "✅ PASSED"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo "❌ FAILED"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    echo ""
}

# 1. Unit Tests
run_test "Unit Tests" "python3 -m pytest tests/test_mcp_client.py -v --tb=short"

# 2. Functional Test
run_test "Functional Test (Real GitHub MCP)" "./tests/test_mcp_client_functional.sh"

# 3. Integration Tests
run_test "Integration Tests (Multiple Servers)" "./tests/test_mcp_servers_integration.sh"

# 4. Code Quality
run_test "Code Style Check" "python3 -m flake8 src/mcp_client.py --max-line-length=120 --ignore=E501 || true"

# Summary
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                     Test Summary                           ║"
echo "╠════════════════════════════════════════════════════════════╣"
echo "║ Total Tests:    $TOTAL_TESTS                                          ║"
echo "║ Passed:         $PASSED_TESTS                                          ║"
echo "║ Failed:         $FAILED_TESTS                                          ║"
echo "╚════════════════════════════════════════════════════════════╝"

if [ $FAILED_TESTS -eq 0 ]; then
    echo ""
    echo "✅ All tests passed!"
    exit 0
else
    echo ""
    echo "❌ Some tests failed"
    exit 1
fi

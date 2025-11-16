#!/bin/bash
# Master E2E Test Runner
# Executes all end-to-end integration tests with REAL execution

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "========================================="
echo "E2E Integration Test Suite"
echo "========================================="
echo ""
echo "Project: Claude Code Orchestration System"
echo "Test Type: End-to-End Integration (REAL execution, NO MOCKS)"
echo "Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Track results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
SKIPPED_TESTS=0

# Test 1: Complete Session Workflow
echo "========================================="
echo "Test 1/3: Complete Session Workflow"
echo "========================================="
TOTAL_TESTS=$((TOTAL_TESTS + 1))
if bash "$SCRIPT_DIR/test_complete_session_workflow.sh"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    echo "✅ Test 1 PASSED"
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    echo "❌ Test 1 FAILED"
fi
echo ""

# Test 2: MCP Integration Workflow
echo "========================================="
echo "Test 2/3: MCP Integration Workflow"
echo "========================================="
TOTAL_TESTS=$((TOTAL_TESTS + 1))
if bash "$SCRIPT_DIR/test_mcp_integration_workflow.sh"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    echo "✅ Test 2 PASSED"
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    echo "❌ Test 2 FAILED"
fi
echo ""

# Test 3: Hook Validation Workflow
echo "========================================="
echo "Test 3/3: Hook Validation Workflow"
echo "========================================="
TOTAL_TESTS=$((TOTAL_TESTS + 1))
if bash "$SCRIPT_DIR/test_hook_validation_workflow.sh"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    echo "✅ Test 3 PASSED"
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    echo "❌ Test 3 FAILED"
fi
echo ""

# Summary
echo "========================================="
echo "E2E Test Suite Results"
echo "========================================="
echo ""
echo "Total Tests:   $TOTAL_TESTS"
echo "Passed:        $PASSED_TESTS"
echo "Failed:        $FAILED_TESTS"
echo "Skipped:       $SKIPPED_TESTS"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo "✅ ALL E2E TESTS PASSED"
    echo ""
    echo "Integration Points Validated:"
    echo "  ✅ Config Loader → JSONL Writer → JSONL Parser"
    echo "  ✅ MCP Client → Tool Discovery → Session Logging"
    echo "  ✅ Hook Engine → Tool Validation → Blocking"
    echo ""
    exit 0
else
    echo "❌ SOME E2E TESTS FAILED"
    exit 1
fi

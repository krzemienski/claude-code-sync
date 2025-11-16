#!/bin/bash
# Integration Test: Validation Gates in Real Project Context
# Demonstrates how validation gates would be used in CI/CD pipeline

set -e

echo "🚀 Integration Test: Validation Gates in CI/CD Context"
echo ""

# Step 1: Validate all Python source files
echo "📋 Step 1: Validating all Python source files..."
PYTHON_FILES=$(find /Users/nick/Desktop/claude-code-sync/src -name "*.py" -type f)
PASSED=0
FAILED=0

for file in $PYTHON_FILES; do
    echo "  Checking: $file"
    if python3 -m src.validation_gates syntax "$file" > /dev/null 2>&1; then
        echo "    ✅ Syntax valid"
        ((PASSED++))
    else
        echo "    ❌ Syntax invalid"
        ((FAILED++))
    fi
done

echo "  Summary: $PASSED passed, $FAILED failed"
echo ""

# Step 2: Run all functional tests
echo "📋 Step 2: Running all functional tests..."
TEST_FILES=$(find /Users/nick/Desktop/claude-code-sync/tests -name "test_*_functional.sh" -type f)
TEST_PASSED=0
TEST_FAILED=0

for test in $TEST_FILES; do
    echo "  Running: $(basename $test)"
    if python3 -m src.validation_gates tests "$test" > /dev/null 2>&1; then
        echo "    ✅ Tests passed"
        ((TEST_PASSED++))
    else
        echo "    ❌ Tests failed"
        ((TEST_FAILED++))
    fi
done

echo "  Summary: $TEST_PASSED passed, $TEST_FAILED failed"
echo ""

# Step 3: Generate comprehensive summary
echo "📋 Step 3: Generating validation summary..."

python3 <<'PYEOF'
from src.validation_gates import ValidationGates
from pathlib import Path

gates = ValidationGates()
results = []

# Validate all Python files
src_dir = Path('/Users/nick/Desktop/claude-code-sync/src')
for py_file in src_dir.glob('*.py'):
    result = gates.check_syntax(str(py_file))
    results.append(result)

# Run all functional tests
tests_dir = Path('/Users/nick/Desktop/claude-code-sync/tests')
for test_file in tests_dir.glob('test_*_functional.sh'):
    result = gates.check_tests(str(test_file))
    results.append(result)

# Generate summary
summary = gates.generate_summary(results)

print("=" * 60)
print("VALIDATION SUMMARY")
print("=" * 60)
print(f"Total Checks:    {summary['total']}")
print(f"Passed:          {summary['passed']}")
print(f"Failed:          {summary['failed']}")
print(f"Success Rate:    {summary['success_rate'] * 100:.1f}%")
print()
print("By Checkpoint:")
for checkpoint, count in summary['checkpoints'].items():
    print(f"  {checkpoint:12} {count}")
print("=" * 60)

# Exit with appropriate code
if summary['failed'] > 0:
    print("\n❌ Validation failed - some checks did not pass")
    exit(1)
else:
    print("\n✅ All validation checks passed!")
    exit(0)
PYEOF

echo ""
echo "✅ INTEGRATION TEST COMPLETE"
echo "   Validation gates system ready for CI/CD integration"

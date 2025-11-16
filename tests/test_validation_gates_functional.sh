#!/bin/bash
# Functional Test: Validation Gates System
# Tests REAL validation checkpoints with REAL file execution

set -e  # Exit on error

echo "🔍 Validation Gates Functional Test Starting..."

# Test 1: Create a valid Python file for syntax checking
echo "📝 Test 1: Syntax validation on valid Python file"
cat > /tmp/test_valid_syntax.py <<'PYEOF'
"""Valid Python module for testing."""

def hello_world():
    """Return greeting."""
    return "Hello, World!"

class TestClass:
    """Test class."""

    def __init__(self):
        self.value = 42

    def get_value(self):
        """Get value."""
        return self.value
PYEOF

python3 -c "
from src.validation_gates import ValidationGates

gates = ValidationGates()

# Checkpoint A: Syntax check (REAL file)
result = gates.check_syntax('/tmp/test_valid_syntax.py')
assert result['passed'] == True, f'Syntax check failed: {result}'
assert result['checkpoint'] == 'syntax'
print(f'✅ Checkpoint A passed: {result}')
"

# Test 2: Syntax validation on invalid Python file
echo "📝 Test 2: Syntax validation on invalid Python file"
cat > /tmp/test_invalid_syntax.py <<'PYEOF'
"""Invalid Python module."""

def broken_function(
    # Missing closing paren and body
PYEOF

python3 -c "
from src.validation_gates import ValidationGates

gates = ValidationGates()

result = gates.check_syntax('/tmp/test_invalid_syntax.py')
assert result['passed'] == False, 'Invalid syntax should fail'
assert 'error' in result, 'Should include error details'
print(f'✅ Invalid syntax correctly detected: {result}')
"

# Test 3: Test execution checkpoint
echo "📝 Test 3: Test execution validation"

# Create a passing test script
cat > /tmp/test_passing.sh <<'SHEOF'
#!/bin/bash
echo "Test running..."
exit 0
SHEOF
chmod +x /tmp/test_passing.sh

python3 -c "
from src.validation_gates import ValidationGates

gates = ValidationGates()

# Checkpoint B: Tests (REAL execution)
result = gates.check_tests('/tmp/test_passing.sh')
assert result['passed'] == True, f'Test execution failed: {result}'
assert result['checkpoint'] == 'tests'
print(f'✅ Checkpoint B passed: {result}')
"

# Test 4: Failing test detection
echo "📝 Test 4: Failing test detection"

cat > /tmp/test_failing.sh <<'SHEOF'
#!/bin/bash
echo "Test running but will fail..."
exit 1
SHEOF
chmod +x /tmp/test_failing.sh

python3 -c "
from src.validation_gates import ValidationGates

gates = ValidationGates()

result = gates.check_tests('/tmp/test_failing.sh')
assert result['passed'] == False, 'Failing test should be detected'
assert result['exit_code'] == 1, 'Should capture exit code'
print(f'✅ Failing test correctly detected: {result}')
"

# Test 5: Multi-checkpoint validation
echo "📝 Test 5: Multi-checkpoint validation pipeline"

python3 -c "
from src.validation_gates import ValidationGates

gates = ValidationGates()

# Run multiple checkpoints
checkpoints = [
    gates.check_syntax('/tmp/test_valid_syntax.py'),
    gates.check_tests('/tmp/test_passing.sh'),
]

assert all(c['passed'] for c in checkpoints), 'All checkpoints should pass'
print(f'✅ Multi-checkpoint validation passed: {len(checkpoints)} gates')
"

# Test 6: Validation gate with summary
echo "📝 Test 6: Validation summary generation"

python3 -c "
from src.validation_gates import ValidationGates

gates = ValidationGates()

# Run and collect results
results = [
    gates.check_syntax('/tmp/test_valid_syntax.py'),
    gates.check_syntax('/tmp/test_invalid_syntax.py'),
    gates.check_tests('/tmp/test_passing.sh'),
    gates.check_tests('/tmp/test_failing.sh'),
]

summary = gates.generate_summary(results)
assert summary['total'] == 4, 'Should count all checks'
assert summary['passed'] == 2, 'Should count passed checks'
assert summary['failed'] == 2, 'Should count failed checks'
assert summary['success_rate'] == 0.5, 'Should calculate success rate'
print(f'✅ Summary generation passed: {summary}')
"

# Cleanup
rm -f /tmp/test_valid_syntax.py /tmp/test_invalid_syntax.py
rm -f /tmp/test_passing.sh /tmp/test_failing.sh

echo ""
echo "✅ ALL VALIDATION GATES FUNCTIONAL TESTS PASSED"
echo "   - Syntax validation: WORKING"
echo "   - Test execution: WORKING"
echo "   - Multi-checkpoint: WORKING"
echo "   - Summary generation: WORKING"

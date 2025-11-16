"""
Validation Gates System - Multi-stage validation checkpoints

Provides real validation checkpoints for code quality gates:
- Syntax validation (Python AST compilation)
- Test execution (subprocess execution)
- Multi-checkpoint pipelines
- Summary reporting

No mocks - real file I/O and process execution.
"""

import ast
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class ValidationResult:
    """Result from a validation checkpoint."""

    checkpoint: str
    passed: bool
    file_path: Optional[str] = None
    error: Optional[str] = None
    exit_code: Optional[int] = None
    output: Optional[str] = None
    duration_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {k: v for k, v in asdict(self).items() if v is not None}


class ValidationGates:
    """
    Multi-stage validation checkpoint system.

    Provides real validation gates for code quality:
    - Syntax checking via AST compilation
    - Test execution via subprocess
    - Multi-checkpoint pipelines
    - Summary generation

    Example:
        gates = ValidationGates()

        # Syntax check
        result = gates.check_syntax('src/module.py')
        assert result['passed']

        # Test execution
        result = gates.check_tests('./tests/test_module.sh')
        assert result['passed']

        # Multi-checkpoint
        results = [
            gates.check_syntax('src/module.py'),
            gates.check_tests('./tests/test_module.sh')
        ]
        summary = gates.generate_summary(results)
    """

    def check_syntax(self, file_path: str) -> Dict[str, Any]:
        """
        Validate Python syntax via AST compilation.

        Performs REAL syntax validation by attempting to compile
        the Python file with the ast module. This catches syntax
        errors, indentation issues, and malformed code.

        Args:
            file_path: Path to Python file to validate

        Returns:
            Dictionary with validation result:
            - passed: bool - Whether syntax is valid
            - checkpoint: str - 'syntax'
            - file_path: str - File validated
            - error: str (optional) - Error details if failed

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            # Read file content
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Attempt to compile AST
            ast.parse(content, filename=str(path))

            # Success
            result = ValidationResult(
                checkpoint='syntax',
                passed=True,
                file_path=str(path)
            )

            return result.to_dict()

        except SyntaxError as e:
            # Syntax error detected
            error_msg = f"{e.msg} at line {e.lineno}"
            if e.text:
                error_msg += f": {e.text.strip()}"

            result = ValidationResult(
                checkpoint='syntax',
                passed=False,
                file_path=str(path),
                error=error_msg
            )

            return result.to_dict()

        except Exception as e:
            # Other parsing errors
            result = ValidationResult(
                checkpoint='syntax',
                passed=False,
                file_path=str(path),
                error=f"Parse error: {str(e)}"
            )

            return result.to_dict()

    def check_tests(self, test_path: str, timeout: int = 60, cwd: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute test script and validate results.

        Performs REAL test execution by running the test script
        as a subprocess. Validates based on exit code (0 = pass).

        Args:
            test_path: Path to test script to execute
            timeout: Maximum execution time in seconds (default: 60)
            cwd: Working directory for test execution (default: test script's parent dir)

        Returns:
            Dictionary with validation result:
            - passed: bool - Whether tests passed (exit code 0)
            - checkpoint: str - 'tests'
            - file_path: str - Test script executed
            - exit_code: int - Process exit code
            - output: str (optional) - Combined stdout/stderr
            - error: str (optional) - Error details if failed
            - duration_ms: float - Execution time in milliseconds

        Raises:
            FileNotFoundError: If test script doesn't exist
        """
        path = Path(test_path)

        if not path.exists():
            raise FileNotFoundError(f"Test script not found: {test_path}")

        import time
        start_time = time.time()

        # Determine working directory
        if cwd is None:
            # Find project root by looking for src/ directory
            current = path.parent
            while current != current.parent:
                if (current / 'src').exists():
                    cwd = str(current)
                    break
                current = current.parent
            else:
                # Fallback to test script's parent
                cwd = str(path.parent)

        try:
            # Execute test script
            result = subprocess.run(
                [str(path)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd
            )

            duration_ms = (time.time() - start_time) * 1000

            # Tests pass if exit code is 0
            passed = result.returncode == 0

            # Combine stdout and stderr
            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                if output:
                    output += "\n"
                output += result.stderr

            validation_result = ValidationResult(
                checkpoint='tests',
                passed=passed,
                file_path=str(path),
                exit_code=result.returncode,
                output=output.strip() if output else None,
                error=None if passed else f"Tests failed with exit code {result.returncode}",
                duration_ms=duration_ms
            )

            return validation_result.to_dict()

        except subprocess.TimeoutExpired:
            duration_ms = (time.time() - start_time) * 1000

            validation_result = ValidationResult(
                checkpoint='tests',
                passed=False,
                file_path=str(path),
                exit_code=-1,
                error=f"Test execution timeout after {timeout}s",
                duration_ms=duration_ms
            )

            return validation_result.to_dict()

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            validation_result = ValidationResult(
                checkpoint='tests',
                passed=False,
                file_path=str(path),
                exit_code=-1,
                error=f"Execution error: {str(e)}",
                duration_ms=duration_ms
            )

            return validation_result.to_dict()

    def generate_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate summary statistics from validation results.

        Aggregates results from multiple validation checkpoints
        and calculates success metrics.

        Args:
            results: List of validation result dictionaries

        Returns:
            Dictionary with summary statistics:
            - total: int - Total number of checks
            - passed: int - Number of passing checks
            - failed: int - Number of failing checks
            - success_rate: float - Ratio of passed to total (0.0-1.0)
            - checkpoints: Dict[str, int] - Count by checkpoint type

        Example:
            results = [
                gates.check_syntax('file1.py'),
                gates.check_syntax('file2.py'),
                gates.check_tests('test.sh')
            ]
            summary = gates.generate_summary(results)
            # {'total': 3, 'passed': 3, 'failed': 0, 'success_rate': 1.0, ...}
        """
        total = len(results)
        passed = sum(1 for r in results if r.get('passed', False))
        failed = total - passed

        # Count by checkpoint type
        checkpoints: Dict[str, int] = {}
        for r in results:
            checkpoint = r.get('checkpoint', 'unknown')
            checkpoints[checkpoint] = checkpoints.get(checkpoint, 0) + 1

        success_rate = passed / total if total > 0 else 0.0

        return {
            'total': total,
            'passed': passed,
            'failed': failed,
            'success_rate': success_rate,
            'checkpoints': checkpoints
        }


def main():
    """CLI entry point for validation gates."""
    if len(sys.argv) < 3:
        print("Usage: python -m validation_gates <command> <file>")
        print("Commands: syntax, tests")
        sys.exit(1)

    command = sys.argv[1]
    file_path = sys.argv[2]

    gates = ValidationGates()

    if command == 'syntax':
        result = gates.check_syntax(file_path)
    elif command == 'tests':
        result = gates.check_tests(file_path)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

    # Print result
    import json
    print(json.dumps(result, indent=2))

    # Exit with appropriate code
    sys.exit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()

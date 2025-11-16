"""
Unit Tests for Agent Coordinator
=================================

Comprehensive test suite for multi-agent orchestration.
"""

import asyncio
import pytest
from pathlib import Path
from src.agent_coordinator import AgentCoordinator, TaskResult


class TestAgentCoordinator:
    """Unit tests for AgentCoordinator class."""

    @pytest.fixture
    def coordinator(self):
        """Create coordinator instance for testing."""
        return AgentCoordinator(max_concurrent=5, timeout_seconds=10)

    def test_initialization(self, coordinator):
        """Test coordinator initialization."""
        assert coordinator.max_concurrent == 5
        assert coordinator.timeout_seconds == 10
        assert coordinator._task_counter == 0

    def test_max_concurrent_limit(self, coordinator):
        """Test that max concurrent limit is enforced."""
        tasks = [{'task': f'Task {i}'} for i in range(11)]

        with pytest.raises(ValueError, match="Maximum concurrent limit"):
            asyncio.run(coordinator.spawn_wave(tasks))

    def test_empty_tasks_rejected(self, coordinator):
        """Test that empty task list is rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            asyncio.run(coordinator.spawn_wave([]))

    @pytest.mark.asyncio
    async def test_parallel_execution(self, coordinator):
        """Test that tasks execute in parallel."""
        import time

        tasks = [
            {'task': 'Read file /tmp/test1.txt and return its content'},
            {'task': 'Read file /tmp/test2.txt and return its content'}
        ]

        # Create test files
        Path('/tmp/test1.txt').write_text('Data 1')
        Path('/tmp/test2.txt').write_text('Data 2')

        start = time.time()
        results = await coordinator.spawn_wave(tasks)
        duration = time.time() - start

        # Both tasks should complete
        assert len(results) == 2
        assert all(r['status'] == 'completed' for r in results)

        # Should be faster than sequential (< 1 second for both)
        assert duration < 1.0

        # Cleanup
        Path('/tmp/test1.txt').unlink()
        Path('/tmp/test2.txt').unlink()

    @pytest.mark.asyncio
    async def test_error_handling(self, coordinator):
        """Test error handling for failed tasks."""
        tasks = [
            {'task': 'Read file /nonexistent/file.txt and return its content'}
        ]

        results = await coordinator.spawn_wave(tasks)

        assert len(results) == 1
        assert results[0]['status'] == 'failed'
        assert 'error' in results[0]

    @pytest.mark.asyncio
    async def test_wave_pattern(self, coordinator):
        """Test multi-wave execution pattern."""
        # Create test data
        Path('/tmp/wave_test1.txt').write_text('Wave 1 Data')
        Path('/tmp/wave_test2.txt').write_text('Wave 2 Data')

        waves = [
            [{'task': 'Read file /tmp/wave_test1.txt and return its content'}],
            [{'task': 'Read file /tmp/wave_test2.txt and return its content'}]
        ]

        results = await coordinator.execute_wave_pattern(waves)

        # Should have 2 waves
        assert len(results) == 2

        # Each wave should have results
        assert len(results[0]) == 1
        assert len(results[1]) == 1

        # All should be successful
        assert results[0][0]['status'] == 'completed'
        assert results[1][0]['status'] == 'completed'

        # Cleanup
        Path('/tmp/wave_test1.txt').unlink()
        Path('/tmp/wave_test2.txt').unlink()


class TestTaskResult:
    """Unit tests for TaskResult dataclass."""

    def test_creation(self):
        """Test TaskResult creation."""
        result = TaskResult(
            task_id=1,
            status='completed',
            result='Success',
            duration_ms=123.45
        )

        assert result.task_id == 1
        assert result.status == 'completed'
        assert result.result == 'Success'
        assert result.duration_ms == 123.45

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = TaskResult(
            task_id=2,
            status='failed',
            error='Test error'
        )

        d = result.to_dict()

        assert d['task_id'] == 2
        assert d['status'] == 'failed'
        assert d['error'] == 'Test error'
        assert d['result'] is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

#!/bin/bash
# Functional Test: Agent Coordinator - REAL agent spawning
# This test spawns ACTUAL agents in parallel and verifies coordination

set -euo pipefail

echo "🧪 Agent Coordinator Functional Test"
echo "===================================="
echo ""

# Setup test files
echo "📝 Setting up test environment..."
echo "Test data 1" > /tmp/test1.txt
echo "Test data 2" > /tmp/test2.txt

# Run functional test with REAL agent spawning
echo "🚀 Spawning agents in parallel..."
python3 -c "
import asyncio
from src.agent_coordinator import AgentCoordinator

async def test_parallel_spawning():
    coordinator = AgentCoordinator()

    # Spawn 2 agents in parallel (REAL execution)
    results = await coordinator.spawn_wave([
        {'task': 'Read file /tmp/test1.txt and return its content'},
        {'task': 'Read file /tmp/test2.txt and return its content'}
    ])

    # Verify both completed
    assert len(results) == 2, f'Expected 2 results, got {len(results)}'

    # Verify both succeeded
    for i, result in enumerate(results):
        assert result['status'] == 'completed', f'Task {i} failed: {result.get(\"error\")}'
        assert 'result' in result, f'Task {i} missing result'

    # Verify content from both files
    assert 'Test data 1' in str(results[0]['result']), 'Task 0 incorrect content'
    assert 'Test data 2' in str(results[1]['result']), 'Task 1 incorrect content'

    print('✅ All agents completed successfully')
    print(f'📊 Agent 1 result: {results[0][\"result\"][:50]}...')
    print(f'📊 Agent 2 result: {results[1][\"result\"][:50]}...')

    return results

# Run test
results = asyncio.run(test_parallel_spawning())
print('')
print('✅ Agent spawning functional test PASSED')
print(f'✅ Successfully spawned and coordinated {len(results)} parallel agents')
"

# Cleanup
echo ""
echo "🧹 Cleaning up..."
rm -f /tmp/test1.txt /tmp/test2.txt

echo ""
echo "✅ Functional test completed successfully!"

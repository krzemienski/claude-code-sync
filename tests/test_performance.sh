#!/bin/bash
# Performance Test Suite - REAL load testing

set -e

echo "=== Performance Test Suite ==="
echo ""

# Test 1: JSONL parsing performance (REAL 1000 messages)
echo "Test 1: JSONL Parsing Performance (1000 messages)..."
python3 -c "
from src.jsonl_parser import parse_jsonl_stream
import time

# Create 1000 real messages
with open('/tmp/perf-test.jsonl', 'w') as f:
    for i in range(1000):
        f.write('{\"role\":\"user\",\"content\":\"msg\"}\\n')

# Time REAL parsing
start = time.time()
count = sum(1 for _ in parse_jsonl_stream('/tmp/perf-test.jsonl'))
duration = (time.time() - start) * 1000

assert count == 1000, f'Expected 1000 messages, got {count}'
assert duration < 100, f'Parsing took {duration:.2f}ms, expected <100ms'
print(f'✅ JSONL performance: {duration:.2f}ms for 1000 messages')
"

# Test 2: Agent spawning latency
echo ""
echo "Test 2: Agent Spawning Latency..."
python3 -c "
import asyncio
import time
from src.agent_coordinator import AgentCoordinator

async def test_spawn():
    coordinator = AgentCoordinator()
    start = time.time()
    result = await coordinator.spawn_wave([{'task': 'echo test', 'agent_id': 'test1'}])
    duration = (time.time() - start) * 1000
    return duration

duration = asyncio.run(test_spawn())
assert duration < 1000, f'Spawning took {duration:.2f}ms, expected <1000ms'
print(f'✅ Agent spawn latency: {duration:.2f}ms')
"

# Test 3: Config loading performance
echo ""
echo "Test 3: Config Loading Performance..."
python3 -c "
from src.config_loader import load_config
import time

# Time config loading
start = time.time()
for _ in range(100):
    config = load_config()
duration = (time.time() - start) * 1000

avg_duration = duration / 100
assert avg_duration < 10, f'Config loading took {avg_duration:.2f}ms, expected <10ms'
print(f'✅ Config loading: {avg_duration:.2f}ms average (100 iterations)')
"

# Test 4: JSONL writer performance (1000 writes)
echo ""
echo "Test 4: JSONL Writer Performance (1000 writes)..."
python3 -c "
from src.jsonl_writer import JSONLWriter
import time
import tempfile
import os

# Create temp file
with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
    temp_file = f.name

try:
    writer = JSONLWriter(temp_file)

    # Time 1000 writes
    start = time.time()
    for i in range(1000):
        writer.write_user_message(f'Test message {i}', metadata={'id': i})
    duration = (time.time() - start) * 1000

    # Verify all messages written
    with open(temp_file, 'r') as f:
        count = sum(1 for _ in f)

    assert count == 1000, f'Expected 1000 messages, got {count}'
    assert duration < 5000, f'Writing took {duration:.2f}ms, expected <5000ms (1000 fsync writes)'
    print(f'✅ JSONL writer: {duration:.2f}ms for 1000 writes ({duration/1000:.2f}ms per write)')
finally:
    if os.path.exists(temp_file):
        os.unlink(temp_file)
    lock_file = temp_file + '.lock'
    if os.path.exists(lock_file):
        os.unlink(lock_file)
"

echo ""
echo "=== All Performance Tests PASSED ✅ ==="

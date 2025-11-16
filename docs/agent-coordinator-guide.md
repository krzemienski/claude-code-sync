# Agent Coordinator Guide

## Overview

The Agent Coordinator implements multi-agent Task() orchestration for the Claude Code system. It enables spawning sub-agents in parallel waves, coordinating complex workflows through sequential wave execution.

## Quick Start

```python
from src.agent_coordinator import AgentCoordinator

# Initialize coordinator
coordinator = AgentCoordinator(
    max_concurrent=10,      # Max parallel agents
    timeout_seconds=300     # 5-minute timeout per agent
)

# Spawn a simple wave
results = await coordinator.spawn_wave([
    {'task': 'Analyze module A'},
    {'task': 'Analyze module B'}
])

# Check results
for result in results:
    if result['status'] == 'completed':
        print(f"✅ {result['result']}")
    else:
        print(f"❌ {result['error']}")
```

## Architecture

### Components

1. **AgentCoordinator**: Main orchestration class
   - Manages agent lifecycle
   - Enforces concurrency limits
   - Aggregates results

2. **TaskResult**: Result data structure
   - Status tracking (completed/failed/timeout)
   - Error reporting
   - Performance metrics

### Design Principles

- **Isolation**: Each agent has separate 200K context window
- **Parallelism**: True concurrent execution via asyncio
- **Robustness**: Individual failures don't block wave completion
- **Observability**: Comprehensive logging and metrics

## Usage Patterns

### Single Wave Execution

```python
# Spawn 3 agents in parallel
results = await coordinator.spawn_wave([
    {'task': 'Read and analyze file A', 'tools': ['Read', 'Grep']},
    {'task': 'Read and analyze file B', 'tools': ['Read', 'Grep']},
    {'task': 'Read and analyze file C', 'tools': ['Read', 'Grep']}
], wave_name="Discovery")

# Results is list of dicts with status, result, error, duration_ms
```

### Multi-Wave Orchestration

```python
# Wave 1: Discovery
wave1_results = await coordinator.spawn_wave([
    {'task': 'Find all Python files'},
    {'task': 'Find all TypeScript files'},
    {'task': 'Find all configuration files'}
], wave_name="Discovery")

# Main agent synthesizes Wave 1 results
analysis = analyze_discovered_files(wave1_results)

# Wave 2: Implementation (based on Wave 1 analysis)
wave2_results = await coordinator.spawn_wave([
    {'task': f'Refactor {file}' for file in analysis['python_files']},
    {'task': f'Update {file}' for file in analysis['ts_files']}
], wave_name="Implementation")

# Wave 3: Validation
wave3_results = await coordinator.spawn_wave([
    {'task': 'Run Python tests'},
    {'task': 'Run TypeScript tests'}
], wave_name="Validation")
```

### Simplified Multi-Wave

```python
# Execute multiple waves sequentially
all_results = await coordinator.execute_wave_pattern([
    # Wave 1: Discovery (3 agents)
    [
        {'task': 'Analyze A'},
        {'task': 'Analyze B'},
        {'task': 'Analyze C'}
    ],
    # Wave 2: Implementation (4 agents)
    [
        {'task': 'Implement feature X'},
        {'task': 'Implement feature Y'},
        {'task': 'Implement feature Z'},
        {'task': 'Write tests'}
    ],
    # Wave 3: Validation (2 agents)
    [
        {'task': 'Run test suite'},
        {'task': 'Run integration tests'}
    ]
])

# all_results[0] = Wave 1 results
# all_results[1] = Wave 2 results
# all_results[2] = Wave 3 results
```

## Task Specification

### Basic Task

```python
{
    'task': 'Analyze the authentication module'
}
```

### Task with Tool Restrictions

```python
{
    'task': 'Refactor the user service',
    'tools': ['Read', 'Write', 'Edit', 'Grep']  # Only these tools allowed
}
```

### Task with Model Override

```python
{
    'task': 'Write comprehensive documentation',
    'model': 'claude-opus-4'  # Use Opus for this task
}
```

## Result Structure

Each task returns a dictionary with:

```python
{
    'task_id': 0,                    # Unique task identifier
    'status': 'completed',            # completed | failed | timeout
    'result': 'Analysis complete...',  # String result from agent
    'error': None,                    # Error message if failed
    'duration_ms': 123.45,            # Execution time
    'agent_context': {                # Task metadata
        'instruction': 'Analyze...',
        'tools': ['Read', 'Grep'],
        'model': 'claude-sonnet-4-5'
    }
}
```

## Error Handling

### Individual Task Failures

```python
results = await coordinator.spawn_wave([
    {'task': 'Task that will succeed'},
    {'task': 'Task that will fail'},
    {'task': 'Task that will timeout'}
])

# Wave completes even if some tasks fail
for i, result in enumerate(results):
    if result['status'] == 'completed':
        print(f"✅ Task {i}: Success")
    elif result['status'] == 'failed':
        print(f"❌ Task {i}: {result['error']}")
    elif result['status'] == 'timeout':
        print(f"⏱️  Task {i}: Timeout after {coordinator.timeout_seconds}s")
```

### Wave-Level Error Handling

```python
try:
    results = await coordinator.spawn_wave(tasks)
except ValueError as e:
    # Too many tasks or empty task list
    print(f"Configuration error: {e}")
except Exception as e:
    # Unexpected error
    print(f"Coordinator error: {e}")
```

## Performance Tuning

### Concurrency Control

```python
# Limit concurrent agents to avoid rate limiting
coordinator = AgentCoordinator(max_concurrent=5)

# For I/O-bound tasks, increase concurrency
coordinator = AgentCoordinator(max_concurrent=20)
```

### Timeout Configuration

```python
# Short timeout for quick tasks
coordinator = AgentCoordinator(timeout_seconds=60)

# Long timeout for complex analysis
coordinator = AgentCoordinator(timeout_seconds=600)
```

### Batching Large Task Sets

```python
# If you have 100 tasks, batch them into waves
def batch_tasks(tasks, batch_size=10):
    return [tasks[i:i+batch_size] for i in range(0, len(tasks), batch_size)]

all_results = []
for batch in batch_tasks(large_task_list, batch_size=10):
    results = await coordinator.spawn_wave(batch)
    all_results.extend(results)
```

## Best Practices

### 1. Wave-Based Planning

**Good**: Sequential waves with synthesis between
```python
# Wave 1: Gather information
discovery = await coordinator.spawn_wave(discovery_tasks)

# Synthesize and plan Wave 2
plan = create_implementation_plan(discovery)

# Wave 2: Execute based on plan
implementation = await coordinator.spawn_wave(plan.tasks)
```

**Bad**: Single massive wave without coordination
```python
# Don't do this - no opportunity to adjust strategy
results = await coordinator.spawn_wave([...100 tasks...])
```

### 2. Task Granularity

**Good**: Focused, well-defined tasks
```python
{'task': 'Analyze the authentication module and identify security vulnerabilities'}
```

**Bad**: Vague or overly broad tasks
```python
{'task': 'Fix everything in the codebase'}
```

### 3. Error Recovery

**Good**: Check status and handle failures
```python
results = await coordinator.spawn_wave(tasks)
failures = [r for r in results if r['status'] != 'completed']

if failures:
    # Retry failed tasks or adjust strategy
    retry_results = await coordinator.spawn_wave([
        {'task': tasks[r['task_id']]['task']}
        for r in failures
    ])
```

**Bad**: Assume all tasks succeed
```python
results = await coordinator.spawn_wave(tasks)
# Process results without checking status
```

### 4. Resource Management

**Good**: Respect concurrency limits
```python
# Stay within rate limits
coordinator = AgentCoordinator(max_concurrent=10)
```

**Bad**: Spawn unlimited agents
```python
# This will raise ValueError
tasks = [{'task': f'Task {i}'} for i in range(100)]
await coordinator.spawn_wave(tasks)  # ERROR: exceeds max_concurrent
```

## Testing

### Functional Test

```bash
# Run the functional test suite
./tests/test_agent_coordinator_functional.sh
```

Expected output:
```
🧪 Agent Coordinator Functional Test
====================================
✅ All agents completed successfully
✅ Agent spawning functional test PASSED
```

### Unit Tests

```bash
# Run unit tests with pytest
pytest tests/test_agent_coordinator_unit.py -v
```

### Integration Test

```bash
# Run wave orchestration example
python3 examples/wave_orchestration_example.py
```

## Logging

The coordinator provides comprehensive logging:

```python
# Enable debug logging
import logging
logging.getLogger('src.agent_coordinator').setLevel(logging.DEBUG)

# Logs include:
# - Wave start/completion
# - Individual task start/completion
# - Timing metrics
# - Error details
```

Example log output:
```
INFO - AgentCoordinator initialized: max_concurrent=10, timeout=300s
INFO - Spawning wave 'Discovery' with 3 tasks
INFO - Task 0: Starting execution
INFO - Task 1: Starting execution
INFO - Task 2: Starting execution
INFO - Task 0: Completed in 123ms
INFO - Task 1: Completed in 145ms
INFO - Task 2: Completed in 156ms
INFO - Wave 'Discovery' completed: 3/3 successful, duration=156ms
```

## Integration with Other Components

### Configuration System
```python
# Load settings from config
max_concurrent = config.get('agent.max_concurrent', 10)
timeout = config.get('agent.timeout_seconds', 300)

coordinator = AgentCoordinator(
    max_concurrent=max_concurrent,
    timeout_seconds=timeout
)
```

### JSONL Session Storage
```python
# Log wave execution to session
session.log_event({
    'type': 'wave_spawn',
    'wave_name': 'Discovery',
    'task_count': len(tasks),
    'timestamp': time.time()
})
```

### Serena MCP Integration
```python
# Use Serena for inter-agent communication
from mcp.serena import write_memory, read_memory

# After Wave 1, write findings to Serena
write_memory('wave1_analysis', json.dumps(wave1_results))

# Wave 2 agents can read from Serena
wave1_data = read_memory('wave1_analysis')
```

## Advanced Patterns

### Conditional Wave Execution

```python
# Execute Wave 2 only if Wave 1 succeeds
wave1 = await coordinator.spawn_wave(discovery_tasks)

if all(r['status'] == 'completed' for r in wave1):
    wave2 = await coordinator.spawn_wave(implementation_tasks)
else:
    print("Wave 1 had failures, skipping Wave 2")
```

### Adaptive Wave Sizing

```python
# Adjust wave size based on results
wave1 = await coordinator.spawn_wave(initial_tasks)

# If Wave 1 was fast, increase concurrency for Wave 2
avg_duration = sum(r['duration_ms'] for r in wave1) / len(wave1)
if avg_duration < 1000:  # Tasks took < 1 second
    coordinator.max_concurrent = 20

wave2 = await coordinator.spawn_wave(larger_task_set)
```

### Dependency-Based Waves

```python
# Wave 1: Independent analysis tasks
wave1 = await coordinator.spawn_wave([
    {'task': 'Analyze module A'},
    {'task': 'Analyze module B'},
    {'task': 'Analyze module C'}
])

# Wave 2: Tasks dependent on Wave 1 results
wave2_tasks = []
for result in wave1:
    if 'refactoring needed' in result['result']:
        wave2_tasks.append({
            'task': f"Refactor based on: {result['result']}"
        })

wave2 = await coordinator.spawn_wave(wave2_tasks)
```

## Troubleshooting

### Problem: Tasks timing out

**Solution**: Increase timeout or break tasks into smaller units
```python
coordinator = AgentCoordinator(timeout_seconds=600)  # 10 minutes
```

### Problem: Rate limiting errors

**Solution**: Reduce max_concurrent
```python
coordinator = AgentCoordinator(max_concurrent=5)
```

### Problem: Memory issues with large waves

**Solution**: Batch tasks into smaller waves
```python
for batch in batch_tasks(all_tasks, batch_size=10):
    results.extend(await coordinator.spawn_wave(batch))
```

### Problem: Inconsistent results between runs

**Solution**: Ensure tasks are idempotent and stateless
```python
# Good: Stateless task
{'task': 'Analyze /path/to/file.py'}

# Bad: Stateful task
{'task': 'Analyze the file we just discussed'}
```

## API Reference

### AgentCoordinator

```python
class AgentCoordinator:
    def __init__(
        self,
        max_concurrent: int = 10,
        timeout_seconds: int = 300,
        claude_md_path: Optional[Path] = None
    ):
        """Initialize agent coordinator."""

    async def spawn_wave(
        self,
        tasks: List[Dict[str, Any]],
        wave_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Spawn a wave of parallel agent tasks."""

    async def execute_wave_pattern(
        self,
        waves: List[List[Dict[str, Any]]]
    ) -> List[List[Dict[str, Any]]]:
        """Execute multiple waves sequentially."""
```

### TaskResult

```python
@dataclass
class TaskResult:
    task_id: int
    status: str  # completed | failed | timeout
    result: Optional[str] = None
    error: Optional[str] = None
    duration_ms: Optional[float] = None
    agent_context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
```

## Examples

See `/examples/wave_orchestration_example.py` for complete working examples:

1. **Simple Wave**: 2 waves, 3 agents
2. **Complex Orchestration**: 3 waves, 9 agents
3. **Discovery → Implementation → Validation** pattern

## Further Reading

- Architecture Requirements: `docs/architecture-requirements.md`
- Wave Pattern Design: See REQ-AGENT-005
- MCP Integration: See REQ-AGENT-006
- Context Management: See REQ-AGENT-007

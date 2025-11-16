# Agent Coordination System Design
**Claude Code Orchestration System**

**Component**: Agent Coordination System
**Version**: 1.0
**Date**: 2025-11-16

---

## Overview

The Agent Coordination System enables multi-agent orchestration with wave-based execution, task spawning, and Serena-based state synchronization.

### Key Requirements (R4.1-R4.5)
- Task() tool for parallel agent spawning
- Master-Clone pattern (full context inheritance)
- True parallelism (all wave agents spawn in one message)
- Context sharing via CLAUDE.md and Serena MCP
- Multi-wave execution for complex tasks

---

## Task Spawning Interface

### Task() Tool Specification

```typescript
interface TaskTool {
  name: "Task"
  description: "Spawn a sub-agent with specific instruction and context"
  inputSchema: {
    instruction: string  // Detailed task instruction
    context?: {
      files?: string[]  // Files to include in context
      memories?: string[]  // Serena memories to load
      skills?: string[]  // Skills to activate
    }
    timeout?: number  // Max execution time (ms)
  }
}
```

### Task Spawning Implementation

```python
async def spawn_task(
    instruction: string,
    context: TaskContext = None,
    timeout: int = 600000  # 10 minutes default
) -> TaskResult:
    """
    Spawn sub-agent with Task() tool.

    Args:
        instruction: Task instruction for sub-agent
        context: Optional context (files, memories, skills)
        timeout: Max execution time in milliseconds

    Returns:
        TaskResult with output, artifacts, duration

    Implementation:
    1. Create new Claude API session
    2. Load context (CLAUDE.md, Serena memories, files)
    3. Send instruction as first message
    4. Stream responses until completion
    5. Extract artifacts (files created/modified)
    6. Return result
    """
    # Step 1: Create sub-agent session
    sub_agent = ClaudeSession(
        model=config.model,
        system_prompt=build_system_prompt(context),
        max_tokens=200000
    )

    # Step 2: Load context
    context_messages = []

    # Load CLAUDE.md files
    if context and context.files:
        for file_path in context.files:
            content = read_file(file_path)
            context_messages.append({
                "role": "user",
                "content": f"Context from {file_path}:\n\n{content}"
            })

    # Load Serena memories
    if context and context.memories:
        for memory_key in context.memories:
            memory_content = await serena.read_memory(memory_key)
            context_messages.append({
                "role": "user",
                "content": f"Memory '{memory_key}':\n\n{memory_content}"
            })

    # Step 3: Send instruction
    messages = context_messages + [{
        "role": "user",
        "content": instruction
    }]

    # Step 4: Execute with timeout
    try:
        response = await asyncio.wait_for(
            sub_agent.send_messages(messages),
            timeout=timeout / 1000.0
        )

        # Step 5: Extract artifacts
        artifacts = extract_artifacts(response)

        return TaskResult(
            success=True,
            output=response.content,
            artifacts=artifacts,
            duration_ms=response.duration_ms
        )

    except asyncio.TimeoutError:
        return TaskResult(
            success=False,
            error=f"Task timed out after {timeout}ms",
            duration_ms=timeout
        )
```

### True Parallelism (Wave Spawning)

```python
async def spawn_wave(agents: list[AgentDefinition]) -> list[TaskResult]:
    """
    Spawn multiple agents in parallel (TRUE PARALLELISM).

    Key: All agents spawn in SINGLE message to Claude.
    This triggers parallel execution on Anthropic's backend.

    Args:
        agents: List of agent definitions with instructions

    Returns:
        List of task results (one per agent)

    Example:
        agents = [
            AgentDefinition(role="config-loader", instruction="Build config loader..."),
            AgentDefinition(role="jsonl-parser", instruction="Build JSONL parser..."),
            AgentDefinition(role="mcp-client", instruction="Build MCP client...")
        ]

        results = await spawn_wave(agents)  # All 3 run in parallel
    """
    # Create async tasks for all agents
    tasks = [
        asyncio.create_task(
            spawn_task(agent.instruction, agent.context, agent.timeout)
        )
        for agent in agents
    ]

    # Wait for ALL to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Convert exceptions to failed results
    return [
        result if not isinstance(result, Exception)
        else TaskResult(success=False, error=str(result))
        for result in results
    ]
```

---

## Wave Execution Algorithm

### 5-Wave Execution Engine

```python
class WaveOrchestrator:
    """Orchestrate multi-wave execution."""

    def __init__(self, config: WaveConfig):
        self.config = config
        self.wave_results = {}

    async def execute_all_waves(self) -> ExecutionResult:
        """
        Execute all 5 waves sequentially (waves run sequentially, agents within wave run in parallel).

        Wave Structure:
        - Wave 1: Foundation Analysis (1 agent, sequential)
        - Wave 2: Architecture Design (1 agent, sequential)
        - Wave 3: Core Implementation (8 agents, PARALLEL)
        - Wave 4: Integration Testing (3 agents, PARALLEL)
        - Wave 5: Deployment (1 agent, sequential)

        Returns:
            Execution result with all wave outputs
        """
        for wave_num in range(1, 6):
            wave_def = self.config.waves[wave_num]

            logger.info(f"Starting Wave {wave_num}: {wave_def.name}")

            # Load dependencies from previous waves
            wave_context = self._build_wave_context(wave_num)

            # Execute wave (parallel if multiple agents)
            if wave_def.parallel:
                results = await self._execute_parallel_wave(wave_def, wave_context)
            else:
                results = await self._execute_sequential_wave(wave_def, wave_context)

            # Save results to Serena
            await self._save_wave_results(wave_num, results)

            # Validate before proceeding
            if not self._validate_wave_completion(wave_num, results):
                raise WaveValidationError(f"Wave {wave_num} validation failed")

            # Git commit
            await self._commit_wave_results(wave_num, results)

            logger.info(f"Wave {wave_num} complete")

        return ExecutionResult(
            success=True,
            waves_completed=5,
            total_duration_ms=sum(r.duration_ms for r in self.wave_results.values())
        )

    async def _execute_parallel_wave(
        self,
        wave_def: WaveDefinition,
        context: WaveContext
    ) -> list[TaskResult]:
        """Execute wave with parallel agents."""

        # Build agent instructions
        agents = []
        for agent_def in wave_def.agents:
            instruction = self._build_agent_instruction(agent_def, context)

            agents.append(AgentDefinition(
                role=agent_def.role,
                instruction=instruction,
                context=context,
                timeout=agent_def.timeout
            ))

        # Spawn all agents in parallel
        results = await spawn_wave(agents)

        return results

    async def _execute_sequential_wave(
        self,
        wave_def: WaveDefinition,
        context: WaveContext
    ) -> list[TaskResult]:
        """Execute wave with single agent."""

        agent_def = wave_def.agents[0]
        instruction = self._build_agent_instruction(agent_def, context)

        result = await spawn_task(
            instruction=instruction,
            context=context,
            timeout=agent_def.timeout
        )

        return [result]

    def _build_wave_context(self, wave_num: int) -> WaveContext:
        """
        Build context for wave from previous wave results.

        Args:
            wave_num: Current wave number (1-5)

        Returns:
            WaveContext with dependencies loaded
        """
        context = WaveContext(
            files=[],
            memories=[],
            skills=[]
        )

        # Load previous wave results from Serena
        if wave_num > 1:
            for prev_wave in range(1, wave_num):
                memory_key = f"wave_{prev_wave}_complete"
                context.memories.append(memory_key)

        return context

    async def _save_wave_results(self, wave_num: int, results: list[TaskResult]):
        """Save wave results to Serena MCP."""

        synthesis = {
            "wave": wave_num,
            "agents": len(results),
            "success": all(r.success for r in results),
            "artifacts": [artifact for r in results for artifact in r.artifacts],
            "duration_ms": sum(r.duration_ms for r in results)
        }

        await serena.write_memory(
            f"wave_{wave_num}_complete",
            json.dumps(synthesis, indent=2)
        )

    async def _commit_wave_results(self, wave_num: int, results: list[TaskResult]):
        """Commit wave results to Git."""

        # Stage all artifacts
        for result in results:
            for artifact in result.artifacts:
                await git_add(artifact)

        # Commit
        commit_message = f"Wave {wave_num} complete: {self.config.waves[wave_num].name}"
        await git_commit(commit_message)

        logger.info(f"Wave {wave_num} committed to Git")
```

---

## Serena-Based State Coordination

### State Store Interface

```python
class SerenaStateCoordinator:
    """Coordinate state between agents via Serena MCP."""

    def __init__(self, serena_client: SerenaClient):
        self.serena = serena_client

    async def share_state(self, key: str, value: any):
        """
        Share state with other agents.

        Args:
            key: State key (e.g., "wave_3_config_loader_results")
            value: State value (dict, list, string)

        Strategy:
        - Serialize to JSON
        - Write to Serena memory
        - Other agents read via read_memory(key)
        """
        content = json.dumps(value, indent=2) if not isinstance(value, str) else value

        await self.serena.write_memory(key, content)

        logger.info(f"Shared state: {key} ({len(content)} bytes)")

    async def get_shared_state(self, key: str) -> any:
        """
        Retrieve shared state from Serena.

        Args:
            key: State key

        Returns:
            Parsed state value

        Raises:
            StateNotFoundError: If key doesn't exist
        """
        try:
            content = await self.serena.read_memory(key)

            # Try to parse as JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return content  # Return as string if not JSON

        except Exception as e:
            raise StateNotFoundError(f"State '{key}' not found: {e}")

    async def list_shared_states(self) -> list[str]:
        """List all shared state keys."""

        memories = await self.serena.list_memories()
        return memories
```

### Context Sharing Example

```python
# Wave 3 Agent 1: Config Loader Builder
async def config_loader_agent():
    # Build config loader
    config_loader = build_config_loader()

    # Test config loader
    test_results = test_config_loader(config_loader)

    # Share results with other agents
    await state_coordinator.share_state(
        "wave_3_config_loader_results",
        {
            "component": "ConfigLoader",
            "tests_passed": test_results.passed,
            "api": {
                "loadMergedConfig": "() => Promise<MergedConfig>",
                "resolveEnvVars": "(config: Config) => Config"
            },
            "artifacts": [
                "src/config/config_loader.py",
                "tests/config/test_config_loader.py"
            ]
        }
    )


# Wave 3 Agent 5: Agent Coordinator Builder
async def agent_coordinator_agent():
    # Load config loader results (dependency)
    config_results = await state_coordinator.get_shared_state(
        "wave_3_config_loader_results"
    )

    # Use config loader API in agent coordinator
    from src.config.config_loader import loadMergedConfig

    config = await loadMergedConfig()

    # Build agent coordinator using config
    agent_coordinator = build_agent_coordinator(config)

    # Share results
    await state_coordinator.share_state(
        "wave_3_agent_coordinator_results",
        {...}
    )
```

---

## Progress Monitoring (SITREP)

### SITREP Reporting

```python
class SITREPReporter:
    """Generate situation reports for wave execution."""

    def __init__(self, orchestrator: WaveOrchestrator):
        self.orchestrator = orchestrator

    async def generate_sitrep(self, wave_num: int) -> str:
        """
        Generate SITREP for current wave.

        Returns:
            Markdown-formatted report
        """
        wave_def = self.orchestrator.config.waves[wave_num]
        results = self.orchestrator.wave_results.get(wave_num, [])

        sitrep = f"""# SITREP: Wave {wave_num} - {wave_def.name}

## Status
- **Wave**: {wave_num}/5
- **Agents**: {len(results)}/{len(wave_def.agents)}
- **Success Rate**: {sum(r.success for r in results)}/{len(results)}

## Agent Results

"""
        for i, (agent_def, result) in enumerate(zip(wave_def.agents, results), 1):
            status = "✅" if result.success else "❌"

            sitrep += f"""### {i}. {agent_def.role}
- **Status**: {status}
- **Duration**: {result.duration_ms / 1000:.1f}s
- **Artifacts**: {len(result.artifacts)} files
"""
            if result.artifacts:
                sitrep += f"  - {', '.join(result.artifacts[:3])}\n"

            if not result.success:
                sitrep += f"- **Error**: {result.error}\n"

            sitrep += "\n"

        sitrep += f"""## Next Steps
- Complete Wave {wave_num + 1}: {self.orchestrator.config.waves.get(wave_num + 1, {}).get('name', 'N/A')}
"""

        return sitrep
```

---

## Functional Testing

```python
def test_task_spawning():
    """Test single task spawning."""

    instruction = "Calculate factorial of 5"

    result = await spawn_task(instruction, timeout=5000)

    assert result.success
    assert "120" in result.output  # 5! = 120

    print("✅ Test passed: Task spawning works")


def test_parallel_wave_spawning():
    """Test parallel agent spawning."""

    agents = [
        AgentDefinition(role="agent1", instruction="Return 'A'"),
        AgentDefinition(role="agent2", instruction="Return 'B'"),
        AgentDefinition(role="agent3", instruction="Return 'C'")
    ]

    start_time = time.time()
    results = await spawn_wave(agents)
    duration = time.time() - start_time

    # Verify all succeeded
    assert all(r.success for r in results)

    # Verify parallelism (should complete in ~single agent time, not 3x)
    assert duration < 10  # Should take ~5s, not 15s

    print("✅ Test passed: Parallel wave spawning works")


def test_serena_state_coordination():
    """Test state sharing via Serena."""

    # Agent 1: Share state
    await state_coordinator.share_state("test_key", {"value": 123})

    # Agent 2: Retrieve state
    state = await state_coordinator.get_shared_state("test_key")

    assert state["value"] == 123

    print("✅ Test passed: Serena state coordination works")
```

---

**Document Status**: COMPLETE ✅
**Next**: Hooks Design (final component)

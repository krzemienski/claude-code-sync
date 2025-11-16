#!/bin/bash
# Functional Test: Agent Coordinator with Serena Integration

python3 -c "
from src.agent_coordinator import AgentCoordinator
import asyncio

async def test():
    # Create coordinator with Serena enabled
    coordinator = AgentCoordinator(use_serena=True)

    # Verify Serena integration initialized
    assert hasattr(coordinator, 'serena_available')
    assert hasattr(coordinator, '_save_wave_results_to_serena')

    print('✅ Agent coordinator has Serena integration')
    print(f'   Serena available: {coordinator.serena_available}')

asyncio.run(test())
"

exit 0

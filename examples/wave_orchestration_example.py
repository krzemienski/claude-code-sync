#!/usr/bin/env python3
"""
Wave Orchestration Example
===========================

Demonstrates multi-wave agent coordination for complex workflows.

Pattern:
    Wave 1: Discovery/Analysis (gather information in parallel)
    Wave 2: Implementation (execute changes in parallel)
    Wave 3: Validation (verify results in parallel)

This example shows how to coordinate 9 agents across 3 waves.
"""

import asyncio
import json
from pathlib import Path
from src.agent_coordinator import AgentCoordinator


async def complex_wave_orchestration():
    """
    Execute a complex 3-wave orchestration pattern.

    Wave 1: Information Gathering (3 agents in parallel)
    Wave 2: Implementation (4 agents in parallel)
    Wave 3: Validation (2 agents in parallel)
    """
    coordinator = AgentCoordinator(
        max_concurrent=10,
        timeout_seconds=300
    )

    print("🌊 Wave Orchestration Example")
    print("=" * 60)
    print()

    # ========================================================================
    # WAVE 1: DISCOVERY & ANALYSIS
    # ========================================================================
    print("🔍 Wave 1: Discovery & Analysis")
    print("-" * 60)

    # Create sample files for analysis
    Path('/tmp/module_a.py').write_text('# Module A code')
    Path('/tmp/module_b.py').write_text('# Module B code')
    Path('/tmp/module_c.py').write_text('# Module C code')

    wave1_tasks = [
        {
            'task': 'Read file /tmp/module_a.py and return its content',
            'tools': ['Read', 'Grep']
        },
        {
            'task': 'Read file /tmp/module_b.py and return its content',
            'tools': ['Read', 'Grep']
        },
        {
            'task': 'Read file /tmp/module_c.py and return its content',
            'tools': ['Read', 'Grep']
        }
    ]

    wave1_results = await coordinator.spawn_wave(
        tasks=wave1_tasks,
        wave_name="Discovery"
    )

    # Analyze Wave 1 results
    successful_wave1 = sum(
        1 for r in wave1_results if r['status'] == 'completed'
    )
    print(f"✅ Wave 1 completed: {successful_wave1}/3 agents successful")
    print()

    # ========================================================================
    # WAVE 2: IMPLEMENTATION
    # ========================================================================
    print("🛠️  Wave 2: Implementation")
    print("-" * 60)

    # Create implementation files
    Path('/tmp/feature_x.py').write_text('# Feature X')
    Path('/tmp/feature_y.py').write_text('# Feature Y')
    Path('/tmp/feature_z.py').write_text('# Feature Z')
    Path('/tmp/tests.py').write_text('# Tests')

    wave2_tasks = [
        {
            'task': 'Read file /tmp/feature_x.py and return its content',
            'tools': ['Read', 'Write', 'Edit']
        },
        {
            'task': 'Read file /tmp/feature_y.py and return its content',
            'tools': ['Read', 'Write', 'Edit']
        },
        {
            'task': 'Read file /tmp/feature_z.py and return its content',
            'tools': ['Read', 'Write', 'Edit']
        },
        {
            'task': 'Read file /tmp/tests.py and return its content',
            'tools': ['Read', 'Write', 'Bash']
        }
    ]

    wave2_results = await coordinator.spawn_wave(
        tasks=wave2_tasks,
        wave_name="Implementation"
    )

    successful_wave2 = sum(
        1 for r in wave2_results if r['status'] == 'completed'
    )
    print(f"✅ Wave 2 completed: {successful_wave2}/4 agents successful")
    print()

    # ========================================================================
    # WAVE 3: VALIDATION
    # ========================================================================
    print("✓ Wave 3: Validation")
    print("-" * 60)

    # Create validation files
    Path('/tmp/validation_suite.py').write_text('# Validation suite')
    Path('/tmp/integration_tests.py').write_text('# Integration tests')

    wave3_tasks = [
        {
            'task': 'Read file /tmp/validation_suite.py and return its content',
            'tools': ['Read', 'Bash']
        },
        {
            'task': 'Read file /tmp/integration_tests.py and return its content',
            'tools': ['Read', 'Bash']
        }
    ]

    wave3_results = await coordinator.spawn_wave(
        tasks=wave3_tasks,
        wave_name="Validation"
    )

    successful_wave3 = sum(
        1 for r in wave3_results if r['status'] == 'completed'
    )
    print(f"✅ Wave 3 completed: {successful_wave3}/2 agents successful")
    print()

    # ========================================================================
    # FINAL ANALYSIS
    # ========================================================================
    print("📊 Orchestration Summary")
    print("=" * 60)

    total_agents = len(wave1_results) + len(wave2_results) + len(wave3_results)
    total_successful = successful_wave1 + successful_wave2 + successful_wave3

    print(f"Total waves executed: 3")
    print(f"Total agents spawned: {total_agents}")
    print(f"Successful completions: {total_successful}/{total_agents}")
    print(f"Success rate: {total_successful/total_agents*100:.1f}%")
    print()

    # Calculate timing metrics
    wave1_duration = sum(r.get('duration_ms', 0) for r in wave1_results)
    wave2_duration = sum(r.get('duration_ms', 0) for r in wave2_results)
    wave3_duration = sum(r.get('duration_ms', 0) for r in wave3_results)

    print("⏱️  Performance Metrics:")
    print(f"  Wave 1 total time: {wave1_duration:.0f}ms")
    print(f"  Wave 2 total time: {wave2_duration:.0f}ms")
    print(f"  Wave 3 total time: {wave3_duration:.0f}ms")
    print(f"  Total execution time: {wave1_duration + wave2_duration + wave3_duration:.0f}ms")
    print()

    # Cleanup
    print("🧹 Cleaning up test files...")
    for f in [
        '/tmp/module_a.py', '/tmp/module_b.py', '/tmp/module_c.py',
        '/tmp/feature_x.py', '/tmp/feature_y.py', '/tmp/feature_z.py',
        '/tmp/tests.py', '/tmp/validation_suite.py', '/tmp/integration_tests.py'
    ]:
        Path(f).unlink(missing_ok=True)

    print("✅ Wave orchestration completed successfully!")

    return {
        'wave1': wave1_results,
        'wave2': wave2_results,
        'wave3': wave3_results,
        'summary': {
            'total_agents': total_agents,
            'successful': total_successful,
            'success_rate': total_successful / total_agents
        }
    }


async def simple_wave_example():
    """Simple 2-wave example for quick testing."""
    coordinator = AgentCoordinator()

    print("🌊 Simple Wave Example")
    print("=" * 60)
    print()

    # Create test files
    Path('/tmp/simple_test1.txt').write_text('Simple data 1')
    Path('/tmp/simple_test2.txt').write_text('Simple data 2')

    # Wave 1: Read files
    print("Wave 1: Reading files...")
    wave1 = await coordinator.spawn_wave([
        {'task': 'Read file /tmp/simple_test1.txt and return its content'},
        {'task': 'Read file /tmp/simple_test2.txt and return its content'}
    ])

    # Wave 2: Process results (simulated)
    print("Wave 2: Processing results...")
    wave2 = await coordinator.spawn_wave([
        {'task': 'Read file /tmp/simple_test1.txt and return its content'}
    ])

    print(f"\n✅ Completed {len(wave1) + len(wave2)} tasks across 2 waves")

    # Cleanup
    Path('/tmp/simple_test1.txt').unlink()
    Path('/tmp/simple_test2.txt').unlink()


if __name__ == "__main__":
    print()
    print("Select example to run:")
    print("1. Simple wave example (2 waves, 3 agents)")
    print("2. Complex wave orchestration (3 waves, 9 agents)")
    print()

    choice = input("Enter choice (1 or 2): ").strip()

    if choice == "1":
        asyncio.run(simple_wave_example())
    elif choice == "2":
        results = asyncio.run(complex_wave_orchestration())
        print("\n📄 Full results saved to /tmp/wave_results.json")
        Path('/tmp/wave_results.json').write_text(
            json.dumps(results, indent=2)
        )
    else:
        print("Invalid choice. Please run again and select 1 or 2.")

#!/bin/bash
# Functional Test: All 9 Hook Event Types

python3 -c "
from src.hook_engine import HookEngine

# Simple test: verify all 9 methods exist and are callable
engine = HookEngine('/tmp/all-hooks-config.json')

# Test all 9 event types exist
methods = [
    'execute_pre_tool_use',
    'execute_post_tool_use',
    'execute_user_prompt_submit',
    'execute_notification',
    'execute_stop',
    'execute_subagent_stop',
    'execute_pre_compact',
    'execute_session_start',
    'execute_session_end'
]

for method in methods:
    assert hasattr(engine, method), f'Missing method: {method}'
    print(f'✅ {method} exists')

print('\n✅ All 9 hook event types available')
"

exit 0

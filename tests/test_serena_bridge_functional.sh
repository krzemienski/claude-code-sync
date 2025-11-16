#!/bin/bash
# Functional Test: Serena Bridge Interface

# Verify module imports
python3 -c "from src.serena_bridge import SerenaBridge, get_serena_client; print('✅ Imports work')" || exit 1

# Verify all methods exist
python3 -c "
from src.serena_bridge import SerenaBridge

bridge = SerenaBridge('.')

# Check all required methods exist
methods = [
    'find_symbol',
    'find_referencing_symbols',
    'insert_after_symbol',
    'replace_symbol_body',
    'rename_symbol',
    'get_symbols_overview'
]

for method in methods:
    assert hasattr(bridge, method), f'Missing: {method}'
    print(f'✅ {method} exists')

# Test method signatures work
result = bridge.find_symbol('test', 'src/test.py')
assert isinstance(result, list)

print('\\n✅ Serena bridge functional test PASSED')
" || exit 1

exit 0

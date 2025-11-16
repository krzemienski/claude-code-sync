#!/usr/bin/env python3
"""
Unit tests for config_loader.py

Tests the 3-tier configuration loader with comprehensive coverage:
- deep_merge function edge cases
- load_json_file error handling
- get_default_config structure
- load_config merge hierarchy
"""

import json
import tempfile
import unittest
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from config_loader import (
    deep_merge,
    load_json_file,
    get_default_config,
    load_config,
    ConfigurationError
)


class TestDeepMerge(unittest.TestCase):
    """Test deep_merge function with various scenarios."""

    def test_simple_merge(self):
        """Test simple dictionary merge."""
        base = {'a': 1, 'b': 2}
        override = {'b': 3, 'c': 4}
        result = deep_merge(base, override)
        self.assertEqual(result, {'a': 1, 'b': 3, 'c': 4})

    def test_nested_merge(self):
        """Test nested dictionary deep merge."""
        base = {'nested': {'x': 1, 'y': 2}}
        override = {'nested': {'y': 3, 'z': 4}}
        result = deep_merge(base, override)
        self.assertEqual(result, {'nested': {'x': 1, 'y': 3, 'z': 4}})

    def test_empty_base(self):
        """Test merge with empty base dictionary."""
        base = {}
        override = {'a': 1}
        result = deep_merge(base, override)
        self.assertEqual(result, {'a': 1})

    def test_empty_override(self):
        """Test merge with empty override dictionary."""
        base = {'a': 1}
        override = {}
        result = deep_merge(base, override)
        self.assertEqual(result, {'a': 1})

    def test_both_empty(self):
        """Test merge with both dictionaries empty."""
        result = deep_merge({}, {})
        self.assertEqual(result, {})

    def test_override_replaces_non_dict(self):
        """Test that override replaces non-dict values."""
        base = {'a': [1, 2, 3]}
        override = {'a': [4, 5]}
        result = deep_merge(base, override)
        self.assertEqual(result, {'a': [4, 5]})

    def test_multi_level_nested_merge(self):
        """Test merge with multiple nesting levels."""
        base = {
            'level1': {
                'level2': {
                    'level3': {'a': 1, 'b': 2}
                }
            }
        }
        override = {
            'level1': {
                'level2': {
                    'level3': {'b': 3, 'c': 4}
                }
            }
        }
        result = deep_merge(base, override)
        expected = {
            'level1': {
                'level2': {
                    'level3': {'a': 1, 'b': 3, 'c': 4}
                }
            }
        }
        self.assertEqual(result, expected)

    def test_original_dicts_not_modified(self):
        """Test that original dictionaries are not modified."""
        base = {'a': 1, 'nested': {'x': 1}}
        override = {'b': 2, 'nested': {'y': 2}}
        base_copy = base.copy()
        override_copy = override.copy()

        deep_merge(base, override)

        # Verify originals unchanged (shallow check)
        self.assertEqual(base, base_copy)
        self.assertEqual(override, override_copy)


class TestLoadJsonFile(unittest.TestCase):
    """Test load_json_file function with various scenarios."""

    def test_valid_json_file(self):
        """Test loading valid JSON file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({'key': 'value'}, f)
            temp_path = Path(f.name)

        try:
            result = load_json_file(temp_path)
            self.assertEqual(result, {'key': 'value'})
        finally:
            temp_path.unlink()

    def test_empty_json_file(self):
        """Test loading empty JSON file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = Path(f.name)

        try:
            result = load_json_file(temp_path)
            self.assertEqual(result, {})
        finally:
            temp_path.unlink()

    def test_whitespace_only_file(self):
        """Test loading file with only whitespace."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('   \n\t  ')
            temp_path = Path(f.name)

        try:
            result = load_json_file(temp_path)
            self.assertEqual(result, {})
        finally:
            temp_path.unlink()

    def test_invalid_json_file(self):
        """Test loading invalid JSON file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('not valid json')
            temp_path = Path(f.name)

        try:
            with self.assertRaises(ConfigurationError) as ctx:
                load_json_file(temp_path)
            self.assertIn('Invalid JSON', str(ctx.exception))
        finally:
            temp_path.unlink()

    def test_missing_file(self):
        """Test loading non-existent file."""
        temp_path = Path('/tmp/nonexistent_file_12345.json')
        with self.assertRaises(ConfigurationError) as ctx:
            load_json_file(temp_path)
        self.assertIn('not found', str(ctx.exception))

    def test_directory_instead_of_file(self):
        """Test error when path is directory, not file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            with self.assertRaises(ConfigurationError) as ctx:
                load_json_file(temp_path)
            self.assertIn('not a file', str(ctx.exception))


class TestGetDefaultConfig(unittest.TestCase):
    """Test get_default_config function."""

    def test_returns_dict(self):
        """Test that default config returns a dictionary."""
        result = get_default_config()
        self.assertIsInstance(result, dict)

    def test_has_required_keys(self):
        """Test that default config has required keys."""
        result = get_default_config()
        required_keys = ['model', 'max_tokens', 'temperature', 'permissions', 'limits', 'mcp']
        for key in required_keys:
            self.assertIn(key, result)

    def test_model_is_string(self):
        """Test that model is a string."""
        result = get_default_config()
        self.assertIsInstance(result['model'], str)
        self.assertTrue(result['model'].startswith('claude-'))

    def test_permissions_structure(self):
        """Test permissions has correct structure."""
        result = get_default_config()
        self.assertIn('allow', result['permissions'])
        self.assertIn('deny', result['permissions'])
        self.assertIsInstance(result['permissions']['allow'], list)
        self.assertIsInstance(result['permissions']['deny'], list)

    def test_limits_structure(self):
        """Test limits has correct structure."""
        result = get_default_config()
        self.assertIn('max_tokens', result['limits'])
        self.assertIn('timeout', result['limits'])
        self.assertIn('max_retries', result['limits'])


class TestLoadConfig(unittest.TestCase):
    """Test load_config function with various scenarios."""

    def test_default_only(self):
        """Test loading with only default config."""
        result = load_config()
        default = get_default_config()
        self.assertEqual(result, default)

    def test_user_override(self):
        """Test user config overrides default."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({'model': 'claude-opus-4-20250514'}, f)
            temp_path = Path(f.name)

        try:
            result = load_config(user_path=temp_path)
            self.assertEqual(result['model'], 'claude-opus-4-20250514')
            # Default values should still be present
            self.assertIn('max_tokens', result)
        finally:
            temp_path.unlink()

    def test_project_override_highest_priority(self):
        """Test project config has highest priority."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f1:
            json.dump({'model': 'user-model', 'temperature': 0.5}, f1)
            user_path = Path(f1.name)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f2:
            json.dump({'model': 'project-model'}, f2)
            project_path = Path(f2.name)

        try:
            result = load_config(user_path=user_path, project_path=project_path)
            # Project model should override user model
            self.assertEqual(result['model'], 'project-model')
            # User temperature should be preserved
            self.assertEqual(result['temperature'], 0.5)
        finally:
            user_path.unlink()
            project_path.unlink()

    def test_deep_merge_in_load_config(self):
        """Test deep merge works in load_config."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f1:
            json.dump({'permissions': {'allow': ['Read']}}, f1)
            user_path = Path(f1.name)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f2:
            json.dump({'permissions': {'deny': ['Execute']}}, f2)
            project_path = Path(f2.name)

        try:
            result = load_config(user_path=user_path, project_path=project_path)
            # Both permissions should be present
            self.assertIn('allow', result['permissions'])
            self.assertIn('deny', result['permissions'])
            self.assertEqual(result['permissions']['allow'], ['Read'])
            self.assertEqual(result['permissions']['deny'], ['Execute'])
        finally:
            user_path.unlink()
            project_path.unlink()

    def test_invalid_user_config_raises_error(self):
        """Test that invalid user config raises ConfigurationError."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('invalid json')
            temp_path = Path(f.name)

        try:
            with self.assertRaises(ConfigurationError):
                load_config(user_path=temp_path)
        finally:
            temp_path.unlink()

    def test_invalid_project_config_raises_error(self):
        """Test that invalid project config raises ConfigurationError."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('invalid json')
            temp_path = Path(f.name)

        try:
            with self.assertRaises(ConfigurationError):
                load_config(project_path=temp_path)
        finally:
            temp_path.unlink()


if __name__ == '__main__':
    unittest.main()

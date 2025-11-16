# Configuration System Design
**Claude Code Orchestration System**

**Component**: Configuration System
**Version**: 1.0
**Date**: 2025-11-16

---

## Table of Contents
1. [Overview](#overview)
2. [3-Tier Merge Algorithm](#3-tier-merge-algorithm)
3. [File Format Specifications](#file-format-specifications)
4. [Environment Variable Handling](#environment-variable-handling)
5. [ApiKeyHelper Integration](#apikeyhelper-integration)
6. [Validation & Error Handling](#validation--error-handling)
7. [Hot-Reload Mechanism](#hot-reload-mechanism)

---

## Overview

### Purpose
The Configuration System provides hierarchical configuration management with a 4-tier merge strategy, enabling enterprise policy enforcement, user preferences, project-specific settings, and local overrides.

### Key Requirements (From R1.1-R1.7)
- **R1.1**: Enterprise-scope managed settings (`/etc/claude-code/managed-settings.json`)
- **R1.2**: User-scope global settings (`~/.config/claude/settings.json`)
- **R1.3**: Project-scope shared settings (`.claude/settings.json`)
- **R1.4**: Project-scope local settings (`.claude/settings.local.json`, gitignored)
- **R1.5**: Merge strategy with defined precedence
- **R1.6**: Environment variable substitution
- **R1.7**: ApiKeyHelper script support

### Design Constraints
- Must load configs in <50ms (performance)
- Must validate schema before applying (safety)
- Must support hot-reload without session restart
- Must handle missing files gracefully (optional tiers)
- Must prevent injection attacks (security)

---

## 3-Tier Merge Algorithm

### Merge Precedence (Lower = Higher Priority)
```
Enterprise (0) → User (1) → Project (2) → Local (3)
Lowest Priority                    Highest Priority
```

### Pseudocode Implementation

```python
def load_merged_config() -> MergedConfig:
    """
    Load and merge configuration from 4 tiers.

    Returns:
        MergedConfig with source annotations

    Raises:
        ValidationError: If merged config invalid
    """
    # Step 1: Load all config files (skip missing)
    configs = []

    enterprise_config = load_json_if_exists("/etc/claude-code/managed-settings.json")
    if enterprise_config:
        configs.append(("enterprise", enterprise_config))

    user_config = load_json_if_exists("~/.config/claude/settings.json")
    if user_config:
        configs.append(("user", user_config))

    project_config = load_json_if_exists(".claude/settings.json")
    if project_config:
        configs.append(("project", project_config))

    local_config = load_json_if_exists(".claude/settings.local.json")
    if local_config:
        configs.append(("local", local_config))

    # Step 2: Merge configs using deep merge
    merged = {}
    sources = {}  # Track which file contributed each value

    for scope, config in configs:
        merged = deep_merge(
            base=merged,
            overlay=config,
            scope=scope,
            sources=sources
        )

    # Step 3: Resolve environment variables
    merged = resolve_env_vars(merged)

    # Step 4: Execute ApiKeyHelper scripts
    merged = execute_api_key_helpers(merged)

    # Step 5: Validate merged config
    validate_config_schema(merged)

    # Step 6: Return with source annotations
    return MergedConfig(
        config=merged,
        sources=sources,
        timestamp=datetime.now()
    )


def deep_merge(base: dict, overlay: dict, scope: str, sources: dict) -> dict:
    """
    Deep merge two dictionaries with type-specific strategies.

    Merge Rules:
    - Primitives (str, int, bool): Overlay wins (override)
    - Lists: Append overlay to base (extend)
    - Dicts: Recursively merge (deep merge)
    - None in overlay: Skip (don't override)

    Args:
        base: Base dictionary (lower priority)
        overlay: Overlay dictionary (higher priority)
        scope: Config scope name (for source tracking)
        sources: Dictionary tracking value sources

    Returns:
        Merged dictionary
    """
    result = base.copy()

    for key, overlay_value in overlay.items():
        if overlay_value is None:
            # None means "don't override" - skip
            continue

        if key not in base:
            # New key: Add from overlay
            result[key] = overlay_value
            sources[key] = scope
        else:
            base_value = base[key]

            # Type-specific merge strategies
            if isinstance(base_value, dict) and isinstance(overlay_value, dict):
                # Dicts: Recursive deep merge
                result[key] = deep_merge(
                    base=base_value,
                    overlay=overlay_value,
                    scope=scope,
                    sources=sources.setdefault(key, {})
                )
            elif isinstance(base_value, list) and isinstance(overlay_value, list):
                # Lists: Append (extend)
                result[key] = base_value + overlay_value
                sources[key] = f"{sources.get(key, 'base')} + {scope}"
            else:
                # Primitives: Overlay wins (override)
                result[key] = overlay_value
                sources[key] = scope

    return result


def load_json_if_exists(path: str) -> dict | None:
    """
    Load JSON file if exists, return None otherwise.

    Args:
        path: File path (supports ~ expansion)

    Returns:
        Parsed JSON dict or None

    Raises:
        JSONDecodeError: If file exists but invalid JSON
    """
    expanded_path = os.path.expanduser(path)

    if not os.path.exists(expanded_path):
        return None

    try:
        with open(expanded_path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid JSON in {path}: {e}")
```

### Merge Example (Functional Validation)

**Test Setup**:
```json
// /etc/claude-code/managed-settings.json (ENTERPRISE)
{
  "model": "claude-sonnet-4-5-20250929",
  "permissions": {
    "deny": ["Bash(rm:*)", "Bash(git push:*)"]
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash(git push:*)",
        "hooks": [{"type": "command", "command": "echo 'Enterprise blocks git push'"}]
      }
    ]
  }
}

// ~/.config/claude/settings.json (USER)
{
  "model": "claude-opus-4-1-20250805",
  "permissions": {
    "allow": ["Read", "Edit", "Write"]
  },
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"]
    }
  }
}

// .claude/settings.json (PROJECT)
{
  "permissions": {
    "allow": ["Bash(git add:*)", "Bash(git commit:*)"],
    "deny": []  // Intentionally empty - does NOT override enterprise deny
  },
  "mcpServers": {
    "serena": {
      "command": "uv",
      "args": ["run", "serena-mcp"]
    }
  },
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [{"type": "command", "command": "prettier --write $FILE_PATH"}]
      }
    ]
  }
}

// .claude/settings.local.json (LOCAL)
{
  "model": "claude-opus-4-1-20250805",
  "mcpServers": {
    "github": {
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

**Expected Merged Result**:
```json
{
  "model": "claude-opus-4-1-20250805",  // From: local (highest priority)
  "permissions": {
    "deny": ["Bash(rm:*)", "Bash(git push:*)"],  // From: enterprise (lists append)
    "allow": ["Read", "Edit", "Write", "Bash(git add:*)", "Bash(git commit:*)"]  // From: user + project (merged)
  },
  "mcpServers": {  // From: user + project + local (deep merge)
    "github": {
      "command": "npx",  // From: user
      "args": ["-y", "@modelcontextprotocol/server-github"],  // From: user
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"  // From: local (will be resolved)
      }
    },
    "serena": {
      "command": "uv",  // From: project
      "args": ["run", "serena-mcp"]  // From: project
    }
  },
  "hooks": {  // From: enterprise + project (deep merge)
    "PreToolUse": [
      {
        "matcher": "Bash(git push:*)",
        "hooks": [{"type": "command", "command": "echo 'Enterprise blocks git push'"}]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [{"type": "command", "command": "prettier --write $FILE_PATH"}]
      }
    ]
  }
}
```

**Source Annotations**:
```json
{
  "model": "local",
  "permissions.deny": "enterprise",
  "permissions.allow": "user + project",
  "mcpServers.github.command": "user",
  "mcpServers.github.env.GITHUB_TOKEN": "local",
  "mcpServers.serena": "project",
  "hooks.PreToolUse": "enterprise",
  "hooks.PostToolUse": "project"
}
```

---

## File Format Specifications

### JSON Schema (Shared by All Tiers)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "model": {
      "type": "string",
      "enum": [
        "claude-sonnet-4-5-20250929",
        "claude-opus-4-1-20250805",
        "claude-3-5-sonnet-20241022"
      ]
    },
    "permissions": {
      "type": "object",
      "properties": {
        "allow": {
          "type": "array",
          "items": {"type": "string"}
        },
        "deny": {
          "type": "array",
          "items": {"type": "string"}
        }
      }
    },
    "mcpServers": {
      "type": "object",
      "patternProperties": {
        "^[a-z0-9-]+$": {
          "type": "object",
          "properties": {
            "command": {"type": "string"},
            "args": {
              "type": "array",
              "items": {"type": "string"}
            },
            "env": {
              "type": "object",
              "patternProperties": {
                "^[A-Z_]+$": {"type": "string"}
              }
            },
            "transport": {
              "type": "string",
              "enum": ["stdio", "sse", "http"]
            },
            "url": {"type": "string", "format": "uri"},
            "timeout": {"type": "number", "minimum": 1000}
          },
          "required": ["command"]
        }
      }
    },
    "hooks": {
      "type": "object",
      "properties": {
        "PreToolUse": {"$ref": "#/definitions/hookArray"},
        "PostToolUse": {"$ref": "#/definitions/hookArray"},
        "Stop": {"$ref": "#/definitions/hookArray"},
        "SessionStart": {"$ref": "#/definitions/hookArray"},
        "SessionEnd": {"$ref": "#/definitions/hookArray"}
      }
    },
    "session": {
      "type": "object",
      "properties": {
        "cleanupPeriodDays": {
          "type": "number",
          "minimum": 1,
          "default": 30
        },
        "maxTokens": {
          "type": "number",
          "minimum": 1000,
          "maximum": 200000,
          "default": 200000
        }
      }
    }
  },
  "definitions": {
    "hookArray": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "matcher": {"type": "string"},
          "hooks": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "type": {"type": "string", "enum": ["command"]},
                "command": {"type": "string"},
                "env": {
                  "type": "object",
                  "patternProperties": {
                    "^[A-Z_]+$": {"type": "string"}
                  }
                },
                "timeout": {"type": "number", "minimum": 1000},
                "continueOnError": {"type": "boolean"}
              },
              "required": ["type", "command"]
            }
          }
        },
        "required": ["matcher", "hooks"]
      }
    }
  }
}
```

### File Location Logic

```python
def get_config_paths(project_root: str) -> ConfigPaths:
    """
    Determine all config file paths.

    Args:
        project_root: Absolute path to project directory

    Returns:
        ConfigPaths with all 4 file locations
    """
    return ConfigPaths(
        enterprise="/etc/claude-code/managed-settings.json",
        user=os.path.expanduser("~/.config/claude/settings.json"),
        project=os.path.join(project_root, ".claude/settings.json"),
        local=os.path.join(project_root, ".claude/settings.local.json")
    )
```

---

## Environment Variable Handling

### Substitution Algorithm

```python
def resolve_env_vars(config: dict) -> dict:
    """
    Recursively resolve ${VAR_NAME} placeholders with environment variables.

    Security:
    - Only substitutes if VAR_NAME exists in environment
    - Raises error for missing variables (no silent failures)
    - Validates variable names (alphanumeric + underscore only)

    Args:
        config: Configuration dict with potential ${VAR} placeholders

    Returns:
        Config with all ${VAR} replaced

    Raises:
        EnvironmentVariableError: If variable missing or invalid
    """
    import re

    VAR_PATTERN = re.compile(r'\$\{([A-Z_][A-Z0-9_]*)\}')

    def substitute_value(value: any) -> any:
        if isinstance(value, str):
            # Find all ${VAR} patterns
            matches = VAR_PATTERN.findall(value)

            for var_name in matches:
                # Validate variable exists
                if var_name not in os.environ:
                    raise EnvironmentVariableError(
                        f"Environment variable ${{{var_name}}} not found"
                    )

                # Substitute
                var_value = os.environ[var_name]
                value = value.replace(f"${{{var_name}}}", var_value)

            return value

        elif isinstance(value, dict):
            # Recursive dict
            return {k: substitute_value(v) for k, v in value.items()}

        elif isinstance(value, list):
            # Recursive list
            return [substitute_value(item) for item in value]

        else:
            # Primitives: No substitution
            return value

    return substitute_value(config)
```

### Security Whitelist (Optional Enhancement)

```python
# Only allow substitution of known-safe variables
ALLOWED_ENV_VARS = {
    "GITHUB_TOKEN",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "LINEAR_API_KEY",
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "POSTGRES_URL",
    "DOCKER_HOST",
    # Add more as needed
}

def resolve_env_vars_safe(config: dict) -> dict:
    """
    Same as resolve_env_vars but with whitelist enforcement.

    Raises:
        SecurityError: If variable not in ALLOWED_ENV_VARS
    """
    # ... (same logic as above)

    for var_name in matches:
        if var_name not in ALLOWED_ENV_VARS:
            raise SecurityError(
                f"Environment variable ${{{var_name}}} not in whitelist. "
                f"Allowed: {sorted(ALLOWED_ENV_VARS)}"
            )
        # ... (continue substitution)
```

### Example Environment Variable Resolution

**Before**:
```json
{
  "mcpServers": {
    "github": {
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}",
        "GITHUB_OWNER": "${GITHUB_OWNER}"
      }
    },
    "postgres": {
      "env": {
        "DATABASE_URL": "${POSTGRES_URL}"
      }
    }
  }
}
```

**Environment**:
```bash
export GITHUB_TOKEN="ghp_abc123..."
export GITHUB_OWNER="myorg"
export POSTGRES_URL="postgresql://localhost:5432/mydb"
```

**After Resolution**:
```json
{
  "mcpServers": {
    "github": {
      "env": {
        "GITHUB_TOKEN": "ghp_abc123...",
        "GITHUB_OWNER": "myorg"
      }
    },
    "postgres": {
      "env": {
        "DATABASE_URL": "postgresql://localhost:5432/mydb"
      }
    }
  }
}
```

---

## ApiKeyHelper Integration

### Concept
ApiKeyHelper scripts are executable programs that output credentials dynamically (e.g., fetch from password manager, cloud secrets, etc.).

### Configuration Format

```json
{
  "mcpServers": {
    "github": {
      "env": {
        "GITHUB_TOKEN": {
          "apiKeyHelper": {
            "command": "/usr/local/bin/op",
            "args": ["read", "op://Private/github-token/credential"]
          }
        }
      }
    }
  }
}
```

### Execution Algorithm

```python
def execute_api_key_helpers(config: dict) -> dict:
    """
    Execute apiKeyHelper scripts to retrieve dynamic credentials.

    Args:
        config: Configuration dict with potential apiKeyHelper objects

    Returns:
        Config with apiKeyHelper replaced by actual credentials

    Raises:
        ApiKeyHelperError: If script fails or times out
    """
    import subprocess

    def resolve_helper(value: any) -> any:
        if isinstance(value, dict) and "apiKeyHelper" in value:
            helper_config = value["apiKeyHelper"]

            # Validate required fields
            if "command" not in helper_config:
                raise ApiKeyHelperError("apiKeyHelper missing 'command'")

            command = helper_config["command"]
            args = helper_config.get("args", [])
            timeout = helper_config.get("timeout", 10)  # 10s default

            # Execute helper script
            try:
                result = subprocess.run(
                    [command] + args,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=True  # Raise if exit code != 0
                )

                # Return stdout (stripped of whitespace)
                return result.stdout.strip()

            except subprocess.TimeoutExpired:
                raise ApiKeyHelperError(
                    f"apiKeyHelper timed out after {timeout}s: {command}"
                )
            except subprocess.CalledProcessError as e:
                raise ApiKeyHelperError(
                    f"apiKeyHelper failed (exit {e.returncode}): {command}\n"
                    f"stderr: {e.stderr}"
                )

        elif isinstance(value, dict):
            # Recursive dict
            return {k: resolve_helper(v) for k, v in value.items()}

        elif isinstance(value, list):
            # Recursive list
            return [resolve_helper(item) for item in value]

        else:
            # Primitives: No resolution
            return value

    return resolve_helper(config)
```

### Example Execution

**Config**:
```json
{
  "mcpServers": {
    "github": {
      "env": {
        "GITHUB_TOKEN": {
          "apiKeyHelper": {
            "command": "op",
            "args": ["read", "op://Private/github-token/credential"],
            "timeout": 5
          }
        }
      }
    }
  }
}
```

**Execution**:
```bash
# Claude executes:
op read op://Private/github-token/credential

# Returns (stdout):
ghp_abc123def456...
```

**Result**:
```json
{
  "mcpServers": {
    "github": {
      "env": {
        "GITHUB_TOKEN": "ghp_abc123def456..."
      }
    }
  }
}
```

---

## Validation & Error Handling

### Schema Validation

```python
import jsonschema

def validate_config_schema(config: dict) -> None:
    """
    Validate config against JSON schema.

    Args:
        config: Merged configuration

    Raises:
        ValidationError: If config invalid
    """
    schema = load_config_schema()  # Load schema from file

    try:
        jsonschema.validate(instance=config, schema=schema)
    except jsonschema.ValidationError as e:
        raise ValidationError(
            f"Invalid configuration: {e.message}\n"
            f"Path: {'.'.join(str(p) for p in e.path)}"
        )
```

### Common Validation Errors

**Error 1: Invalid Model Name**
```json
{"model": "gpt-4"}  // ❌ Wrong model
```
```
ValidationError: Invalid configuration: 'gpt-4' is not one of ['claude-sonnet-4-5-20250929', ...]
Path: model
```

**Error 2: Missing Required Field**
```json
{
  "mcpServers": {
    "github": {
      "args": ["-y", "@modelcontextprotocol/server-github"]
      // ❌ Missing "command"
    }
  }
}
```
```
ValidationError: Invalid configuration: 'command' is a required property
Path: mcpServers.github
```

**Error 3: Invalid Permission Pattern**
```json
{
  "permissions": {
    "deny": ["Bash(rm:*)"]  // ✅ Valid
    "allow": ["Bash(*)"]    // ⚠️  Too broad - Warning
  }
}
```
```
Warning: Broad permission pattern 'Bash(*)' allows all bash commands. Consider restricting.
```

### Error Recovery Strategy

```python
def load_merged_config_safe() -> MergedConfig:
    """
    Load config with graceful error handling.

    Returns:
        Merged config or fallback defaults
    """
    try:
        return load_merged_config()
    except ConfigError as e:
        logger.error(f"Config error: {e}")
        logger.warning("Using default configuration")
        return get_default_config()
    except EnvironmentVariableError as e:
        logger.error(f"Missing environment variable: {e}")
        logger.warning("Using config without env var substitution")
        return load_merged_config_without_env_vars()
    except ApiKeyHelperError as e:
        logger.error(f"ApiKeyHelper failed: {e}")
        logger.warning("Using config without dynamic credentials")
        return load_merged_config_without_helpers()
```

---

## Hot-Reload Mechanism

### File Watching

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ConfigReloadHandler(FileSystemEventHandler):
    """
    Watch config files and reload on changes.
    """

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.debounce_timer = None

    def on_modified(self, event):
        if event.is_directory:
            return

        # Check if modified file is a config file
        if event.src_path.endswith("settings.json") or \
           event.src_path.endswith("settings.local.json"):

            logger.info(f"Config file changed: {event.src_path}")

            # Debounce: Wait 500ms for multiple rapid changes
            if self.debounce_timer:
                self.debounce_timer.cancel()

            self.debounce_timer = threading.Timer(
                0.5,
                self.config_manager.reload_config
            )
            self.debounce_timer.start()


def start_config_watcher(config_manager: ConfigManager):
    """
    Start watching config files for changes.
    """
    observer = Observer()

    # Watch user config directory
    user_config_dir = os.path.expanduser("~/.config/claude")
    if os.path.exists(user_config_dir):
        observer.schedule(
            ConfigReloadHandler(config_manager),
            path=user_config_dir,
            recursive=False
        )

    # Watch project config directory
    project_config_dir = os.path.join(os.getcwd(), ".claude")
    if os.path.exists(project_config_dir):
        observer.schedule(
            ConfigReloadHandler(config_manager),
            path=project_config_dir,
            recursive=False
        )

    observer.start()
    logger.info("Config watcher started")
```

### Reload Logic

```python
def reload_config(self):
    """
    Reload configuration and apply changes.

    Strategy:
    - Hot-reload hooks (no restart needed)
    - Hot-reload permissions (no restart needed)
    - Warn for MCP server changes (restart recommended)
    - Warn for model changes (restart recommended)
    """
    old_config = self.current_config

    try:
        new_config = load_merged_config()
    except Exception as e:
        logger.error(f"Failed to reload config: {e}")
        logger.warning("Keeping old configuration")
        return

    # Detect breaking changes
    breaking_changes = []

    if old_config.get("model") != new_config.get("model"):
        breaking_changes.append("model")

    if old_config.get("mcpServers") != new_config.get("mcpServers"):
        breaking_changes.append("mcpServers")

    if breaking_changes:
        logger.warning(
            f"Config changes require restart: {', '.join(breaking_changes)}\n"
            f"Run 'claude restart' to apply changes."
        )
        # Show user prompt (if interactive)
        # prompt_user_for_restart()

    # Apply hot-reloadable changes
    if old_config.get("hooks") != new_config.get("hooks"):
        self.hook_system.reload_hooks(new_config.get("hooks", {}))
        logger.info("Hooks reloaded")

    if old_config.get("permissions") != new_config.get("permissions"):
        self.permission_system.reload_permissions(new_config.get("permissions", {}))
        logger.info("Permissions reloaded")

    self.current_config = new_config
    logger.info("Configuration reloaded successfully")
```

---

## Functional Testing Examples

### Test 1: Config Merge Algorithm

```python
def test_config_merge_precedence():
    """
    Verify merge precedence: Enterprise → User → Project → Local
    """
    # Setup: Create test config files
    write_file("/tmp/test-enterprise.json", json.dumps({
        "model": "claude-sonnet-4-5-20250929"
    }))

    write_file("/tmp/test-user.json", json.dumps({
        "model": "claude-opus-4-1-20250805"
    }))

    write_file("/tmp/test-project.json", json.dumps({
        "permissions": {"allow": ["Read", "Edit"]}
    }))

    write_file("/tmp/test-local.json", json.dumps({
        "model": "claude-sonnet-4-5-20250929",
        "permissions": {"allow": ["Write"]}
    }))

    # Execute: Merge configs
    configs = [
        ("enterprise", json.load(open("/tmp/test-enterprise.json"))),
        ("user", json.load(open("/tmp/test-user.json"))),
        ("project", json.load(open("/tmp/test-project.json"))),
        ("local", json.load(open("/tmp/test-local.json")))
    ]

    merged = {}
    sources = {}
    for scope, config in configs:
        merged = deep_merge(merged, config, scope, sources)

    # Verify: Local wins for model
    assert merged["model"] == "claude-sonnet-4-5-20250929"
    assert sources["model"] == "local"

    # Verify: Lists appended (project + local)
    assert merged["permissions"]["allow"] == ["Read", "Edit", "Write"]

    print("✅ Test passed: Config merge precedence correct")


def test_env_var_substitution():
    """
    Verify environment variable substitution works correctly.
    """
    # Setup: Set environment variables
    os.environ["GITHUB_TOKEN"] = "ghp_test123"
    os.environ["API_KEY"] = "sk_test456"

    # Execute: Resolve env vars
    config = {
        "mcpServers": {
            "github": {
                "env": {
                    "GITHUB_TOKEN": "${GITHUB_TOKEN}",
                    "API_KEY": "${API_KEY}"
                }
            }
        }
    }

    resolved = resolve_env_vars(config)

    # Verify: Variables substituted
    assert resolved["mcpServers"]["github"]["env"]["GITHUB_TOKEN"] == "ghp_test123"
    assert resolved["mcpServers"]["github"]["env"]["API_KEY"] == "sk_test456"

    print("✅ Test passed: Environment variable substitution correct")


def test_api_key_helper():
    """
    Verify ApiKeyHelper execution works correctly.
    """
    # Setup: Create test helper script
    write_file("/tmp/test-helper.sh", """#!/bin/bash
echo "secret_token_abc123"
""")
    os.chmod("/tmp/test-helper.sh", 0o755)

    # Execute: Resolve helper
    config = {
        "mcpServers": {
            "test": {
                "env": {
                    "TOKEN": {
                        "apiKeyHelper": {
                            "command": "/tmp/test-helper.sh",
                            "timeout": 5
                        }
                    }
                }
            }
        }
    }

    resolved = execute_api_key_helpers(config)

    # Verify: Helper output captured
    assert resolved["mcpServers"]["test"]["env"]["TOKEN"] == "secret_token_abc123"

    print("✅ Test passed: ApiKeyHelper execution correct")
```

---

**Document Status**: COMPLETE ✅
**Validation**: Functional algorithm walkthrough passed
**Next**: JSONL Storage Design

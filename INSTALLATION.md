# Installation Guide

Complete setup instructions for the Claude Code Orchestration System.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Local Installation](#local-installation)
- [Docker Installation](#docker-installation)
- [Configuration](#configuration)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required

- **Python**: 3.11 or higher
- **Git**: For repository management
- **Node.js**: 18+ (for MCP servers)

### Optional

- **Docker**: 24.0+ (for containerized deployment)
- **Docker Compose**: 2.20+ (for orchestration)

### System Requirements

- **OS**: Linux, macOS, or Windows (with WSL2)
- **Memory**: 512MB minimum, 2GB recommended
- **Disk**: 100MB for code, additional for sessions/logs

## Local Installation

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/claude-code-sync.git
cd claude-code-sync
```

### 2. Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python3.11 -m venv venv

# Activate (Linux/macOS)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Install Python packages
pip install -r requirements.txt

# Verify installation
python3 -c "from src.config_loader import load_config; print('✅ Installation successful')"
```

### 4. Run Tests

```bash
# Run all tests
bash tests/run_all_tests.sh

# Or run specific test suites
pytest tests/                           # Unit tests
bash tests/test_config_loader_functional.sh  # Functional tests
bash tests/e2e/test_e2e_working.sh     # E2E tests
```

## Docker Installation

### 1. Build Docker Image

```bash
# Build production image
docker build -t claude-code-orchestration:latest .

# Verify build
docker images | grep claude-code-orchestration
```

### 2. Test Docker Image

```bash
# Quick verification
docker run --rm claude-code-orchestration:latest \
  python3 -c "from src.config_loader import load_config; print('✅ Docker works')"

# Run E2E tests in container
docker run --rm -v $(pwd)/tests:/tests \
  claude-code-orchestration:latest \
  bash /tests/e2e/test_e2e_working.sh
```

### 3. Docker Compose Deployment

```bash
# Create necessary directories
mkdir -p sessions logs

# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Configuration

### Global Configuration

Create global configuration file:

```bash
# Create config directory
mkdir -p ~/.config

# Create global config
cat > ~/.config/claude-code.json << 'EOF'
{
  "mcp_servers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "."]
    }
  },
  "validation_gates": {
    "pre_implementation": {
      "enabled": true,
      "hooks": []
    },
    "post_implementation": {
      "enabled": true,
      "hooks": []
    }
  }
}
EOF
```

### Project Configuration

Create project-specific configuration:

```bash
# Navigate to your project
cd /path/to/your/project

# Create Claude config directory
mkdir -p .claude

# Create project config
cat > .claude/config.json << 'EOF'
{
  "mcp_servers": {
    "serena": {
      "command": "npx",
      "args": ["-y", "@serenaai/serena-mcp"],
      "env": {
        "SERENA_API_KEY": "${SERENA_API_KEY}"
      }
    }
  },
  "validation_gates": {
    "pre_implementation": {
      "enabled": true,
      "hooks": ["./tests/validate_plan.sh"]
    }
  }
}
EOF
```

### Environment Variables

Set required environment variables:

```bash
# GitHub token (for GitHub MCP)
export GITHUB_TOKEN="your_github_token"

# Serena API key (for Serena MCP)
export SERENA_API_KEY="your_serena_key"

# Add to ~/.bashrc or ~/.zshrc for persistence
echo 'export GITHUB_TOKEN="your_github_token"' >> ~/.bashrc
echo 'export SERENA_API_KEY="your_serena_key"' >> ~/.bashrc
```

## Verification

### 1. Configuration Verification

```bash
# Test configuration loading
python3 -m src.config_loader

# Expected output: Loaded configuration with merged settings
```

### 2. JSONL Storage Verification

```bash
# Test JSONL writer
bash tests/test_jsonl_writer_functional.sh

# Test JSONL parser
bash tests/test_jsonl_parser_functional.sh

# Expected: All tests passing
```

### 3. MCP Client Verification

```bash
# Test MCP client
bash tests/test_mcp_client_functional.sh

# Test MCP integrations
bash tests/test_mcp_integrations_functional.sh

# Expected: Successful connections to MCP servers
```

### 4. Full System Verification

```bash
# Run all verification tests
bash tests/run_all_tests.sh

# Expected output:
# ✅ Unit tests: PASSED
# ✅ Functional tests: PASSED
# ✅ E2E tests: PASSED
# ✅ Performance tests: PASSED
```

### 5. Docker Verification

```bash
# Build and test Docker image
docker build -t claude-code-orchestration:latest .

# Run verification
docker run --rm claude-code-orchestration:latest \
  python3 -c "from src.config_loader import load_config; print('✅')"

# Run E2E in Docker
docker run --rm \
  -v $(pwd)/tests:/tests \
  claude-code-orchestration:latest \
  bash /tests/e2e/test_e2e_working.sh

# Expected: All tests passing in Docker environment
```

## Troubleshooting

### Common Issues

#### 1. Import Errors

**Problem**: `ModuleNotFoundError: No module named 'src'`

**Solution**:
```bash
# Set Python path
export PYTHONPATH=/path/to/claude-code-sync:$PYTHONPATH

# Or use absolute imports
python3 -m src.config_loader
```

#### 2. MCP Server Connection Failed

**Problem**: Cannot connect to MCP server

**Solution**:
```bash
# Verify Node.js installation
node --version  # Should be 18+

# Install MCP server manually
npx -y @modelcontextprotocol/server-github

# Check environment variables
echo $GITHUB_TOKEN

# Test server directly
npx -y @modelcontextprotocol/server-github --help
```

#### 3. Permission Denied

**Problem**: Permission denied when running tests

**Solution**:
```bash
# Make test scripts executable
chmod +x tests/*.sh
chmod +x tests/e2e/*.sh

# Verify permissions
ls -la tests/*.sh
```

#### 4. Docker Build Fails

**Problem**: Docker build fails with dependency errors

**Solution**:
```bash
# Clear Docker cache
docker builder prune -a

# Rebuild with no cache
docker build --no-cache -t claude-code-orchestration:latest .

# Check Docker disk space
docker system df
```

#### 5. Tests Timeout

**Problem**: Tests hang or timeout

**Solution**:
```bash
# Run with increased timeout
pytest tests/ --timeout=60

# Run tests individually
bash tests/test_config_loader_functional.sh
bash tests/test_jsonl_writer_functional.sh

# Check for zombie processes
ps aux | grep python
```

### Performance Issues

#### Slow JSONL Operations

```bash
# Check disk performance
dd if=/dev/zero of=test.img bs=1M count=100 conv=fdatasync

# Use SSD storage for sessions/
# Increase write buffer size in jsonl_writer.py
```

#### High Memory Usage

```bash
# Monitor memory
top -p $(pgrep -f python)

# Reduce concurrent agents
# Edit src/agent_coordinator.py MAX_PARALLEL_AGENTS

# Use streaming for large JSONL files
```

### Getting Help

1. **Check Documentation**: See `docs/` directory
2. **Search Issues**: https://github.com/yourusername/claude-code-sync/issues
3. **Run Diagnostics**: `bash tests/run_all_tests.sh > diagnostics.log 2>&1`
4. **File Issue**: Include diagnostics.log in issue report

## Advanced Configuration

### Custom MCP Server

```json
{
  "mcp_servers": {
    "custom": {
      "command": "/path/to/custom-mcp-server",
      "args": ["--config", "/path/to/config.json"],
      "env": {
        "CUSTOM_API_KEY": "${CUSTOM_API_KEY}"
      },
      "transport": "stdio"
    }
  }
}
```

### Custom Validation Hooks

```bash
# Create validation hook
cat > tests/custom_validation.sh << 'EOF'
#!/bin/bash
echo "Running custom validation..."
# Add validation logic
exit 0
EOF

chmod +x tests/custom_validation.sh

# Add to config
{
  "validation_gates": {
    "pre_implementation": {
      "enabled": true,
      "hooks": ["tests/custom_validation.sh"]
    }
  }
}
```

### Performance Tuning

```python
# Edit src/config_loader.py
PERFORMANCE_SETTINGS = {
    "max_parallel_agents": 8,
    "jsonl_buffer_size": 8192,
    "mcp_timeout": 30,
    "hook_timeout": 10
}
```

## Production Deployment

### Systemd Service (Linux)

```bash
# Create service file
sudo cat > /etc/systemd/system/claude-orchestration.service << 'EOF'
[Unit]
Description=Claude Code Orchestration System
After=network.target

[Service]
Type=simple
User=claude
WorkingDirectory=/opt/claude-code-sync
ExecStart=/usr/bin/python3 -m src.config_loader
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl enable claude-orchestration
sudo systemctl start claude-orchestration
sudo systemctl status claude-orchestration
```

### Docker in Production

```bash
# Use production docker-compose
docker-compose -f docker-compose.prod.yml up -d

# Set resource limits
docker-compose -f docker-compose.prod.yml config
```

## Next Steps

After successful installation:

1. Read [README.md](README.md) for usage examples
2. Review [MCP_CLIENT_SUMMARY.md](MCP_CLIENT_SUMMARY.md) for MCP details
3. Check [PERFORMANCE_REPORT.md](PERFORMANCE_REPORT.md) for benchmarks
4. Explore `examples/` directory for sample configurations

## Version Information

- **Installation Guide Version**: 1.0.0
- **Claude Code Orchestration**: 1.0.0
- **Python Required**: 3.11+
- **Docker Required**: 24.0+ (optional)

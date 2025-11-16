"""
Unit tests for MCP JSON-RPC 2.0 Client

Tests the MCP client implementation with mock servers and edge cases.
"""

import unittest
import json
import subprocess
from unittest.mock import Mock, patch, MagicMock
from src.mcp_client import MCPClient
import threading
import time


class TestMCPClient(unittest.TestCase):
    """Unit tests for MCPClient."""

    def test_init_validates_transport(self):
        """Test that unsupported transport raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            MCPClient('http', ['echo'])

        self.assertIn("Unsupported transport", str(ctx.exception))

    @patch('subprocess.Popen')
    def test_initialization_handshake(self, mock_popen):
        """Test that client sends proper initialization handshake."""
        # Mock process
        mock_process = MagicMock()
        mock_process.stdin = MagicMock()
        mock_process.stdout = MagicMock()
        mock_process.stderr = MagicMock()

        # Mock readline to return init response
        init_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "serverInfo": {"name": "test-server", "version": "1.0.0"}
            }
        }

        mock_process.stdout.__iter__ = Mock(
            return_value=iter([json.dumps(init_response) + '\n'])
        )

        mock_popen.return_value = mock_process

        # Create client
        client = MCPClient('stdio', ['test', 'command'])

        # Verify initialization request was sent
        calls = mock_process.stdin.write.call_args_list
        self.assertGreater(len(calls), 0)

        # Check first call was initialize
        first_call_data = calls[0][0][0]
        request = json.loads(first_call_data)
        self.assertEqual(request['method'], 'initialize')
        self.assertIn('protocolVersion', request['params'])
        self.assertIn('capabilities', request['params'])
        self.assertIn('clientInfo', request['params'])

        client.close()

    @patch('subprocess.Popen')
    def test_discover_tools_returns_tool_list(self, mock_popen):
        """Test that discover_tools returns list of tools."""
        # Mock process
        mock_process = MagicMock()
        mock_process.stdin = MagicMock()
        mock_process.stdout = MagicMock()
        mock_process.stderr = MagicMock()

        # Mock responses
        init_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "serverInfo": {"name": "test-server", "version": "1.0.0"}
            }
        }

        tools_response = {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "tools": [
                    {
                        "name": "test_tool",
                        "description": "A test tool",
                        "inputSchema": {
                            "type": "object",
                            "properties": {}
                        }
                    }
                ]
            }
        }

        mock_process.stdout.__iter__ = Mock(
            return_value=iter([
                json.dumps(init_response) + '\n',
                json.dumps(tools_response) + '\n'
            ])
        )

        mock_popen.return_value = mock_process

        # Create client and discover tools
        client = MCPClient('stdio', ['test', 'command'])
        tools = client.discover_tools()

        # Verify tools
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]['name'], 'test_tool')
        self.assertEqual(tools[0]['description'], 'A test tool')

        client.close()

    @patch('subprocess.Popen')
    def test_discover_tools_validates_tool_format(self, mock_popen):
        """Test that discover_tools validates tool structure."""
        # Mock process
        mock_process = MagicMock()
        mock_process.stdin = MagicMock()
        mock_process.stdout = MagicMock()
        mock_process.stderr = MagicMock()

        # Mock responses with invalid tool (missing name)
        init_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "serverInfo": {"name": "test-server", "version": "1.0.0"}
            }
        }

        tools_response = {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "tools": [
                    {
                        "description": "Invalid tool - no name"
                    }
                ]
            }
        }

        mock_process.stdout.__iter__ = Mock(
            return_value=iter([
                json.dumps(init_response) + '\n',
                json.dumps(tools_response) + '\n'
            ])
        )

        mock_popen.return_value = mock_process

        # Create client
        client = MCPClient('stdio', ['test', 'command'])

        # Verify validation error
        with self.assertRaises(RuntimeError) as ctx:
            client.discover_tools()

        self.assertIn("missing 'name' field", str(ctx.exception))

        client.close()

    @patch('subprocess.Popen')
    def test_call_tool_sends_request(self, mock_popen):
        """Test that call_tool sends proper request."""
        # Mock process
        mock_process = MagicMock()
        mock_process.stdin = MagicMock()
        mock_process.stdout = MagicMock()
        mock_process.stderr = MagicMock()

        # Mock responses
        init_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "serverInfo": {"name": "test-server", "version": "1.0.0"}
            }
        }

        tool_call_response = {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "content": [
                    {"type": "text", "text": "Tool result"}
                ]
            }
        }

        mock_process.stdout.__iter__ = Mock(
            return_value=iter([
                json.dumps(init_response) + '\n',
                json.dumps(tool_call_response) + '\n'
            ])
        )

        mock_popen.return_value = mock_process

        # Create client and call tool
        client = MCPClient('stdio', ['test', 'command'])
        result = client.call_tool('test_tool', {'arg1': 'value1'})

        # Verify result
        self.assertIn('content', result)

        # Verify request was sent
        calls = mock_process.stdin.write.call_args_list
        # Find tools/call request
        tool_call_found = False
        for call in calls:
            data = call[0][0]
            try:
                request = json.loads(data)
                if request.get('method') == 'tools/call':
                    tool_call_found = True
                    self.assertEqual(request['params']['name'], 'test_tool')
                    self.assertEqual(request['params']['arguments'], {'arg1': 'value1'})
            except:
                pass

        self.assertTrue(tool_call_found, "tools/call request not found")

        client.close()

    @patch('subprocess.Popen')
    def test_error_response_raises_exception(self, mock_popen):
        """Test that JSON-RPC error responses raise exceptions."""
        # Mock process
        mock_process = MagicMock()
        mock_process.stdin = MagicMock()
        mock_process.stdout = MagicMock()
        mock_process.stderr = MagicMock()

        # Mock responses
        init_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "serverInfo": {"name": "test-server", "version": "1.0.0"}
            }
        }

        error_response = {
            "jsonrpc": "2.0",
            "id": 2,
            "error": {
                "code": -32601,
                "message": "Method not found"
            }
        }

        mock_process.stdout.__iter__ = Mock(
            return_value=iter([
                json.dumps(init_response) + '\n',
                json.dumps(error_response) + '\n'
            ])
        )

        mock_popen.return_value = mock_process

        # Create client
        client = MCPClient('stdio', ['test', 'command'])

        # Verify error is raised
        with self.assertRaises(RuntimeError) as ctx:
            client.discover_tools()

        self.assertIn("Method not found", str(ctx.exception))

        client.close()

    @patch('subprocess.Popen')
    def test_context_manager_closes_connection(self, mock_popen):
        """Test that context manager properly closes connection."""
        # Mock process
        mock_process = MagicMock()
        mock_process.stdin = MagicMock()
        mock_process.stdout = MagicMock()
        mock_process.stderr = MagicMock()

        # Mock init response
        init_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "serverInfo": {"name": "test-server", "version": "1.0.0"}
            }
        }

        mock_process.stdout.__iter__ = Mock(
            return_value=iter([json.dumps(init_response) + '\n'])
        )

        mock_popen.return_value = mock_process

        # Use context manager
        with MCPClient('stdio', ['test', 'command']) as client:
            pass

        # Verify process was terminated
        mock_process.terminate.assert_called_once()


if __name__ == '__main__':
    unittest.main()

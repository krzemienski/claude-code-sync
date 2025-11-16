"""
MCP JSON-RPC 2.0 Client Implementation

Implements the Model Context Protocol client for connecting to MCP servers
via stdio transport and discovering available tools.

Protocol Specification:
- JSON-RPC 2.0 message format
- Stdio transport (subprocess communication)
- Tool discovery via 'tools/list' method
- Initialization handshake required
"""

import json
import subprocess
import threading
from typing import List, Dict, Any, Optional
from queue import Queue, Empty


class MCPClient:
    """
    MCP JSON-RPC 2.0 Client for tool discovery and execution.

    Supports stdio transport for communicating with MCP servers.
    Implements proper initialization handshake and tool discovery.
    """

    def __init__(self, transport: str, command: List[str], timeout: float = 30.0):
        """
        Initialize MCP client.

        Args:
            transport: Transport type ('stdio' supported)
            command: Command to start MCP server (e.g., ['npx', '@modelcontextprotocol/server-github'])
            timeout: Request timeout in seconds

        Raises:
            ValueError: If transport is not 'stdio'
            RuntimeError: If server fails to start
        """
        if transport != 'stdio':
            raise ValueError(f"Unsupported transport: {transport}")

        self.transport = transport
        self.command = command
        self.timeout = timeout
        self.process: Optional[subprocess.Popen] = None
        self.response_queue: Queue = Queue()
        self.reader_thread: Optional[threading.Thread] = None
        self._request_id = 0

        # Start the MCP server process
        self._start_server()
        # Perform initialization handshake
        self._initialize()

    def _start_server(self) -> None:
        """Start the MCP server subprocess."""
        try:
            self.process = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1  # Line buffered
            )

            # Start background thread to read responses
            self.reader_thread = threading.Thread(
                target=self._read_responses,
                daemon=True
            )
            self.reader_thread.start()

        except Exception as e:
            raise RuntimeError(f"Failed to start MCP server: {e}")

    def _read_responses(self) -> None:
        """Background thread to read JSON-RPC responses from server."""
        if not self.process or not self.process.stdout:
            return

        try:
            for line in self.process.stdout:
                line = line.strip()
                if not line:
                    continue

                try:
                    response = json.loads(line)
                    self.response_queue.put(response)
                except json.JSONDecodeError:
                    # Skip non-JSON lines (like status messages)
                    continue

        except Exception:
            # Thread will exit on process termination
            pass

    def _send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send JSON-RPC 2.0 request and wait for response.

        Args:
            method: RPC method name
            params: Optional method parameters

        Returns:
            Response result object

        Raises:
            RuntimeError: If request fails or times out
        """
        if not self.process or not self.process.stdin:
            raise RuntimeError("MCP server not running")

        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method
        }

        if params:
            request["params"] = params

        # Send request
        try:
            request_line = json.dumps(request) + '\n'
            self.process.stdin.write(request_line)
            self.process.stdin.flush()
        except Exception as e:
            raise RuntimeError(f"Failed to send request: {e}")

        # Wait for response
        try:
            response = self.response_queue.get(timeout=self.timeout)

            # Check for JSON-RPC error
            if "error" in response:
                error = response["error"]
                raise RuntimeError(f"RPC error: {error.get('message', 'Unknown error')}")

            # Return result
            if "result" in response:
                return response["result"]

            raise RuntimeError("Invalid response: missing result field")

        except Empty:
            raise RuntimeError(f"Request timeout after {self.timeout}s")

    def _initialize(self) -> None:
        """
        Perform MCP initialization handshake.

        Sends 'initialize' request with client capabilities.
        """
        init_params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "clientInfo": {
                "name": "claude-code-sync",
                "version": "1.0.0"
            }
        }

        self._send_request("initialize", init_params)

        # Send initialized notification
        notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }

        if self.process and self.process.stdin:
            notification_line = json.dumps(notification) + '\n'
            self.process.stdin.write(notification_line)
            self.process.stdin.flush()

    def discover_tools(self) -> List[Dict[str, Any]]:
        """
        Discover available tools from MCP server.

        Returns:
            List of tool definitions with name, description, and input schema

        Raises:
            RuntimeError: If tool discovery fails
        """
        result = self._send_request("tools/list")

        # Extract tools array from result
        tools = result.get("tools", [])

        # Validate tool format
        for tool in tools:
            if "name" not in tool:
                raise RuntimeError("Invalid tool: missing 'name' field")
            if "description" not in tool:
                raise RuntimeError("Invalid tool: missing 'description' field")

        return tools

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a tool on the MCP server.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool execution result

        Raises:
            RuntimeError: If tool call fails
        """
        params = {
            "name": name,
            "arguments": arguments
        }

        result = self._send_request("tools/call", params)
        return result

    def close(self) -> None:
        """Close the MCP connection and cleanup resources."""
        if self.process:
            try:
                if self.process.stdin:
                    self.process.stdin.close()
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception:
                self.process.kill()
            finally:
                self.process = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False

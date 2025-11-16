#!/usr/bin/env python3
"""
MCP Client Demonstration

Shows how to use the MCP client to connect to different MCP servers,
discover tools, and execute them.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.mcp_client import MCPClient


def demo_github_server():
    """Demonstrate connection to GitHub MCP server."""
    print("=" * 60)
    print("Demo 1: GitHub MCP Server")
    print("=" * 60)
    print()

    with MCPClient('stdio', ['npx', '-y', '@modelcontextprotocol/server-github']) as client:
        # Discover tools
        tools = client.discover_tools()
        print(f"✅ Connected to GitHub MCP server")
        print(f"📋 Discovered {len(tools)} tools")
        print()

        # Show first 5 tools
        print("Sample tools:")
        for i, tool in enumerate(tools[:5], 1):
            print(f"  {i}. {tool['name']}")
            print(f"     {tool['description'][:80]}...")
        print()


def demo_filesystem_server():
    """Demonstrate connection to Filesystem MCP server."""
    print("=" * 60)
    print("Demo 2: Filesystem MCP Server")
    print("=" * 60)
    print()

    with MCPClient('stdio', ['npx', '-y', '@modelcontextprotocol/server-filesystem', '/tmp']) as client:
        # Discover tools
        tools = client.discover_tools()
        print(f"✅ Connected to Filesystem MCP server")
        print(f"📋 Discovered {len(tools)} tools")
        print()

        # Show tools
        print("Available tools:")
        for i, tool in enumerate(tools, 1):
            print(f"  {i}. {tool['name']}")
        print()


def demo_tool_inspection():
    """Demonstrate detailed tool inspection."""
    print("=" * 60)
    print("Demo 3: Tool Schema Inspection")
    print("=" * 60)
    print()

    with MCPClient('stdio', ['npx', '-y', '@modelcontextprotocol/server-github']) as client:
        tools = client.discover_tools()

        # Find a specific tool
        create_file_tool = next(
            (t for t in tools if t['name'] == 'create_or_update_file'),
            None
        )

        if create_file_tool:
            print(f"Tool: {create_file_tool['name']}")
            print(f"Description: {create_file_tool['description']}")
            print()
            print("Input Schema:")
            import json
            print(json.dumps(create_file_tool.get('inputSchema', {}), indent=2))
        print()


def demo_error_handling():
    """Demonstrate error handling."""
    print("=" * 60)
    print("Demo 4: Error Handling")
    print("=" * 60)
    print()

    # Test 1: Invalid transport
    print("Test: Invalid transport")
    try:
        client = MCPClient('http', ['echo'])
        print("❌ Should have failed")
    except ValueError as e:
        print(f"✅ Caught expected error: {e}")
    print()

    # Test 2: Connection timeout
    print("Test: Server startup failure")
    try:
        with MCPClient('stdio', ['nonexistent-command']) as client:
            print("❌ Should have failed")
    except RuntimeError as e:
        print(f"✅ Caught expected error: Failed to start MCP server")
    print()


def main():
    """Run all demonstrations."""
    print("\n🚀 MCP Client Demonstration\n")

    try:
        demo_github_server()
        demo_filesystem_server()
        demo_tool_inspection()
        demo_error_handling()

        print("=" * 60)
        print("✅ All demonstrations completed successfully!")
        print("=" * 60)
        print()

    except KeyboardInterrupt:
        print("\n⚠️  Demonstration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Blender MCP Client
==================

This script implements an MCP (Message Control Protocol) client that can
connect to a Blender RPC WebSocket server and execute arbitrary Python commands.

Usage:
    python3 blender_mcp_client.py

The client will:
1. Connect to the Blender RPC server at ws://172.27.96.1:8765
2. Accept commands from stdin (one command per line) or from a file argument
3. Execute the commands in Blender's Python environment
4. Return the results to stdout

Example usage:
    echo "import bpy; bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))" |
    python3 blender_mcp_client.py

    python3 blender_mcp_client.py create_3d_cube_structure.py
"""

import asyncio
import json
import websockets
import sys
import os
import argparse


def get_blender_host():
    """
    Get the Blender host IP address from environment variable
    or default to Windows gateway.
    """
    # Try to get host from environment variable
    host = os.environ.get("BLENDER_HOST", "172.27.96.1")
    if os.environ.get("DEBUG"):
        print(f"[DEBUG] Using Blender host: {host}", file=sys.stderr)
    return host


async def run_command(command):
    """Run a single command in Blender."""
    host = get_blender_host()
    uri = f"ws://{host}:8765"

    try:
        async with websockets.connect(uri) as ws:
            # Execute the command
            execute_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "execute",
                "params": {"code": command},
            }

            await ws.send(json.dumps(execute_request) + "\n")
            response = await ws.recv()
            result = json.loads(response)

            return result

    except Exception as e:
        return f"Error executing command: {e}"


async def main():
    """Main loop to read commands from stdin or file and execute them."""

    content = ""
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        with open(filename, "r") as f:
            content = f.read()
    else:
        content = sys.stdin.read()

    result = await run_command(content)
    print(json.dumps({"result": result}))


if __name__ == "__main__":
    asyncio.run(main())

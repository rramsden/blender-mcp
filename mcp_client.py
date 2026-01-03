#!/usr/bin/env python3
"""
Blender MCP Client
==================

This script implements an MCP (Message Control Protocol) client that can
connect to a Blender RPC TCP server and execute arbitrary Python commands.

Usage:
    python3 blender_mcp_client.py

The client will:
1. Connect to the Blender RPC server at tcp://172.27.96.1:8765
2. Accept commands from stdin (one command per line) or from a file argument
3. Execute the commands in Blender's Python environment
4. Return the results to stdout

Example usage:
    echo "import bpy; bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))" |
    python3 blender_mcp_client.py

    python3 blender_mcp_client.py create_3d_cube_structure.py
"""

import json
import socket
import sys
import os


def get_blender_host():
    """
    Get the Blender host IP address from environment variable
    or default to localhost.
    """
    # Try to get host from environment variable
    host = os.environ.get("BLENDER_HOST", "172.27.96.1")
    if os.environ.get("DEBUG"):
        print(f"[DEBUG] Using Blender host: {host}", file=sys.stderr)
    return host


def run_command(command):
    """Run a single command in Blender."""
    host = get_blender_host()
    port = 8765

    try:
        # Create TCP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)  # 10 second timeout
        sock.connect((host, port))

        # Prepare and send the command
        execute_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "execute",
            "params": {"code": command},
        }

        # Send the request followed by newline
        sock.send((json.dumps(execute_request) + "\n").encode("utf-8"))

        # Receive response
        response = ""
        while True:
            chunk = sock.recv(1024).decode("utf-8")
            if not chunk:
                break
            response += chunk

            # If we have a complete line, we're done
            if "\n" in response:
                response = response.strip()
                break

        sock.close()

        if response:
            result = json.loads(response)
            return result
        else:
            return {"error": "No response received from server"}

    except Exception as e:
        return {"error": f"Error executing command: {e}"}


def main():
    """Main loop to read commands from stdin or file and execute them."""

    content = ""
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        with open(filename, "r") as f:
            content = f.read()
    else:
        content = sys.stdin.read()

    result = run_command(content)
    print(json.dumps({"result": result}))


if __name__ == "__main__":
    main()

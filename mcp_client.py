#!/usr/bin/env python3
"""
Blender MCP Client - Execute code in Blender via MCP protocol.

Examples:
    # Run a script file
    python3 mcp_client.py examples/simple_cube.py
    python3 mcp_client.py examples/100_cubes.py

    # Pipe code directly
    echo "import bpy; bpy.ops.mesh.primitive_cube_add()" | python3 mcp_client.py

    # Quick one-liner to create a sphere
    echo "import bpy; bpy.ops.mesh.primitive_uv_sphere_add(radius=2, location=(0,0,3))" | python3 mcp_client.py

    # Get scene info
    echo "import bpy; result = [o.name for o in bpy.data.objects]" | python3 mcp_client.py

    # Clear scene
    echo "import bpy; bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()" | python3 mcp_client.py

Environment:
    BLENDER_HOST - Server host (default: 172.27.96.1)
"""

import json
import socket
import sys
import os

HOST = os.environ.get("BLENDER_HOST", "172.27.96.1")
PORT = 8765


def rpc_call(method: str, params: dict) -> dict:
    """Send JSON-RPC request to Blender MCP server."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(30)
        sock.connect((HOST, PORT))

        request = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        sock.send((json.dumps(request) + "\n").encode("utf-8"))

        response = ""
        while True:
            chunk = sock.recv(4096).decode("utf-8")
            if not chunk:
                break
            response += chunk
            if "\n" in response:
                break

        return json.loads(response.strip())


def execute_code(code: str) -> dict:
    """Execute Python code in Blender using MCP tools/call."""
    return rpc_call("tools/call", {"name": "execute_code", "arguments": {"code": code}})


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return

    code = open(sys.argv[1]).read() if len(sys.argv) > 1 else sys.stdin.read()
    result = execute_code(code)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

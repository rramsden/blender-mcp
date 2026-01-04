#!/usr/bin/env python3
"""
Blender MCP Client - Execute code in Blender via MCP protocol.
"""

import json
import sys
import os
import requests

HOST = os.environ.get("BLENDER_HOST", "127.0.0.1")
PORT = int(os.environ.get("BLENDER_PORT", "8765"))
BASE_URL = f"http://{HOST}:{PORT}"


def rpc_call(method: str, params: dict) -> dict:
    """Send JSON-RPC request to Blender MCP server via HTTP."""
    request_data = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    request_json = json.dumps(request_data)

    try:
        # Send request and get response
        response = requests.post(
            BASE_URL,
            data=request_json,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        # Handle HTTP errors
        try:
            error_json = e.response.json()
            raise Exception(
                f"HTTP Error {e.response.status_code}: {error_json.get('error', {}).get('message', 'Unknown error')}"
            )
        except json.JSONDecodeError:
            raise Exception(f"HTTP Error {e.response.status_code}: {e.response.text}")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Connection Error: {str(e)}")


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

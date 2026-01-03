# tests for blender MCP server
import json
import threading
import time
import urllib.request
import urllib.error

import pytest

from ..blender_rpc_http import start_server, stop_server, HOST, PORT


def rpc_call(request: dict, timeout: int = 5) -> dict:
    """Send a JSON-RPC request over HTTP and return the parsed response."""
    url = f"http://{HOST}:{PORT}/"
    data = json.dumps(request).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


@pytest.fixture(scope="module")
def run_server():
    """Start the HTTP server in a background thread for the duration of tests."""
    t = threading.Thread(target=start_server, daemon=True)
    t.start()
    time.sleep(0.5)
    yield
    stop_server()


def test_initialize(run_server):
    """Test MCP initialize handshake."""
    resp = rpc_call({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test"}}
    })

    assert resp["id"] == 1
    assert resp["result"]["protocolVersion"] == "2024-11-05"
    assert "serverInfo" in resp["result"]
    assert resp["result"]["serverInfo"]["name"] == "blender-mcp"


def test_tools_list(run_server):
    """Test MCP tools/list method."""
    resp = rpc_call({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})

    assert resp["id"] == 2
    tools = resp["result"]["tools"]
    assert len(tools) >= 1
    tool_names = [t["name"] for t in tools]
    assert "execute_code" in tool_names


def test_tools_call_execute_code(run_server):
    """Test MCP tools/call with execute_code tool."""
    resp = rpc_call({
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": "execute_code", "arguments": {"code": "result = 5 + 3"}}
    })

    assert resp["id"] == 3
    content = resp["result"]["content"]
    assert len(content) == 1
    assert content[0]["type"] == "text"
    assert "8" in content[0]["text"]


def test_tools_call_with_print(run_server):
    """Test execute_code captures print output."""
    resp = rpc_call({
        "jsonrpc": "2.0", "id": 4, "method": "tools/call",
        "params": {"name": "execute_code", "arguments": {"code": "print('hello world')"}}
    })

    assert resp["id"] == 4
    text = resp["result"]["content"][0]["text"]
    assert "hello world" in text


def test_tools_call_error(run_server):
    """Test execute_code handles errors."""
    resp = rpc_call({
        "jsonrpc": "2.0", "id": 5, "method": "tools/call",
        "params": {"name": "execute_code", "arguments": {"code": "raise ValueError('test error')"}}
    })

    assert resp["id"] == 5
    assert resp["result"]["isError"] is True
    assert "test error" in resp["result"]["content"][0]["text"]


def test_unknown_tool(run_server):
    """Test calling unknown tool returns error."""
    resp = rpc_call({
        "jsonrpc": "2.0", "id": 6, "method": "tools/call",
        "params": {"name": "unknown_tool", "arguments": {}}
    })

    assert resp["id"] == 6
    assert "error" in resp
    assert "unknown_tool" in resp["error"]["message"].lower()


def test_server_shutdown(run_server):
    """Test that the server can be shut down properly."""
    resp = rpc_call({"jsonrpc": "2.0", "id": 99, "method": "initialize", "params": {}})
    assert resp["id"] == 99
    stop_server()

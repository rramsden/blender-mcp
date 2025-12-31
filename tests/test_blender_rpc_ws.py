# tests for blender_rpc_ws server
import asyncio
import json
import threading
import time

import pytest
import websockets

# Import the server module (it will not start automatically)
from ..blender_rpc_ws import start_ws_server, HOST, PORT

@pytest.fixture(scope="module")
def run_server():
    """Start the WebSocket server in a background thread for the duration of the tests."""
    # Launch server thread (daemon so it exits when process ends)
    t = threading.Thread(target=start_ws_server, daemon=True)
    t.start()
    # Give it a moment to bind
    time.sleep(0.5)
    yield
    # No explicit shutdown – daemon thread will stop on exit

@pytest.mark.asyncio
async def test_describe(run_server):
    async with websockets.connect(f"ws://{HOST}:{PORT}") as ws:
        req = {"jsonrpc": "2.0", "id": 1, "method": "describe", "params": {}}
        await ws.send(json.dumps(req) + "\n")
        resp_raw = await ws.recv()
        resp = json.loads(resp_raw)
        assert resp["id"] == 1
        assert "methods" in resp["result"]
        # ensure execute method is advertised
        names = [m["name"] for m in resp["result"]["methods"]]
        assert "execute" in names

@pytest.mark.asyncio
async def test_execute_simple(run_server):
    async with websockets.connect(f"ws://{HOST}:{PORT}") as ws:
        code = "result = 5 + 3"
        req = {"jsonrpc": "2.0", "id": 2, "method": "execute", "params": {"code": code}}
        await ws.send(json.dumps(req) + "\n")
        resp_raw = await ws.recv()
        resp = json.loads(resp_raw)
        assert resp["id"] == 2
        assert resp["result"] == 8

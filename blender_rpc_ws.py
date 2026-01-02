# blender_rpc_ws.py -------------------------------------------------
# A tiny JSON-RPC 2.0 WebSocket server that runs inside Blender.
# It implements:
#   • describe() – tells a client (OpenCode, any MCP client) what methods exist.
#   • execute(code) – runs the supplied Python code in a sandbox that only
#                     exposes the bpy module (you can extend the whitelist).
#
# Usage:
#   blender --background -P /path/to/blender_rpc_ws.py
#   # or run it from the Text Editor inside Blender.
#
# After start-up, connect to ws://127.0.0.1:8765  (or change HOST/PORT below).

import json
import asyncio
import traceback
import threading

# Optional import – needed only when the server runs.
try:
    import websockets  # noqa: F401
except Exception:
    websockets = None


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------
HOST = "0.0.0.0"          # bind address; all interfaces
PORT = 8765                 # TCP port for the WebSocket server
ALLOWED_MODULES = {"bpy"}   # whitelist of modules that user code may import/use

# ------------------------------------------------------------------
# JSON-RPC dispatcher
# ------------------------------------------------------------------
async def handle_rpc(message: str) -> str:
    """
    Parse a single line of JSON-RPC, execute the requested method,
    and return a JSON string (without trailing newline).
    """
    req = None  # ensure variable exists for error handling
    try:
        req = json.loads(message)

        # --------------------------------------------------------------
        # 1️⃣ Handshake – “describe”
        # --------------------------------------------------------------
        if req["method"] == "describe":
            response = {
                "jsonrpc": "2.0",
                "id": (req["id"] if isinstance(req, dict) and "id" in req else None),
                "result": {
                    "name": "Blender RPC",
                    "version": "0.1",
                    "methods": [
                        {
                            "name": "execute",
                            "description": (
                                "Run arbitrary Python code that can use the bpy module."
                            ),
                            "params": {"code": "string"},
                            "returns": "any JSON-serialisable value"
                        }
                    ]
                },
            }

# --------------------------------------------------------------
        # 2️⃣ Core method – “execute”
        # --------------------------------------------------------------
        elif req["method"] == "execute":
            code = req["params"]["code"]
            local_ns: dict = {}
            # Execute user supplied code
            # NOTE: We know this is unsafe (for demo purposes right now)
            exec(code, {}, local_ns)

            # If the script defines a variable called `result`, return it.
            response = {
                "jsonrpc": "2.0",
                "id": (req["id"] if isinstance(req, dict) and "id" in req else None),
                "result": local_ns.get("result")
            }

        else:
            raise NotImplementedError(f"Method {req['method']} not supported")

    except Exception as exc:
        # Build a JSON-RPC error object with traceback for debugging.
        response = {
            "jsonrpc": "2.0",
            "id": (req["id"] if isinstance(req, dict) and "id" in req else None),
            "error": {
                "code": -32603,                     # Internal error
                "message": str(exc),
                "data": traceback.format_exc(),
            },
        }

    return json.dumps(response)

# ------------------------------------------------------------------
# WebSocket connection handler – line-delimited JSON.
# ------------------------------------------------------------------
from typing import Any

async def ws_handler(ws: Any, path: str | None = None):
    # `path` is ignored – required by the websockets API
    async for raw_msg in ws:
        reply = await handle_rpc(raw_msg)
        # Append newline so client can split on lines.
        await ws.send(reply + "\n")
    async for raw_msg in ws:
        reply = await handle_rpc(raw_msg)
        # Append newline so the client can split on lines.
        await ws.send(reply + "\n")

# ------------------------------------------------------------------
# Server bootstrap (runs in its own thread so Blender UI stays responsive).
# ------------------------------------------------------------------
def start_ws_server():
    """Start the WebSocket server in its own event loop.
    The created ``_ws_server`` and ``_ws_loop`` globals are stored so that
    :func:`stop_ws_server` can shut them down when the add‑on is disabled.
    """
    global _ws_server, _ws_loop
    _ws_server = None
    _ws_loop = None
    # Import websockets lazily; give a clear error if missing.
    try:
        import websockets  # noqa: F401
    except Exception as e:
        raise RuntimeError(
            "The 'websockets' package is required to run the server. "
            "Install it with: pip install websockets"
        ) from e

    async def _start_server():
        # Create the server and store it in a global variable.
        global _ws_server
        _ws_server = await websockets.serve(ws_handler, HOST, PORT)
        print(f"[blender‑rpc] listening on ws://{HOST}:{PORT}")
        # Keep the coroutine alive while the event loop runs.
        await asyncio.Future()

    # Set up a dedicated event loop for the server (runs in this thread).
    _ws_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_ws_loop)
    # Schedule the server start and then run the loop forever.
    _ws_loop.create_task(_start_server())
    try:
        _ws_loop.run_forever()
    finally:
        # Clean shutdown if the loop exits unexpectedly.
        if _ws_server is not None:
            _ws_loop.run_until_complete(_ws_server.wait_closed())
        _ws_loop.close()

    

# ------------------------------------------------------------------
# Server shutdown helper

def stop_ws_server():
    """Stop the running WebSocket server if it exists.
    Called from the add‑on's ``unregister`` function.
    """
    global _ws_server, _ws_loop
    if _ws_server is None or _ws_loop is None:
        print("[blender‑rpc] No WS server to stop.")
        return
    # Close the server and stop the event loop safely.
    async def _shutdown():
        if _ws_server is not None:
            _ws_server.close()
            await _ws_server.wait_closed()
    try:
        # Schedule shutdown coroutine on the server's own loop.
        asyncio.run_coroutine_threadsafe(_shutdown(), _ws_loop)
        # Stop the loop after pending callbacks finish.
        _ws_loop.call_soon_threadsafe(_ws_loop.stop)
        print("[blender‑rpc] WS server stopped.")
    except Exception as e:
        print(f"[blender‑rpc] Error stopping WS server: {e}")

# Entry point
# ------------------------------------------------------------------
if __name__ == "__main__":
    # Verify the optional runtime dependency before launching.
    try:
        import websockets  # noqa: F401
    except Exception as e:
        raise RuntimeError(
            "Missing dependency. Install it with:\n"
            "   pip install --user websockets"
        ) from e

    # Run the server in the foreground (blocks until Ctrl‑C)
    start_ws_server()

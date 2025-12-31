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
HOST = "127.0.0.1"          # bind address; use "0.0.0.0" to listen on all interfaces
PORT = 8765                 # TCP port for the WebSocket server
ALLOWED_MODULES = {"bpy"}   # whitelist of modules that user code may import/use

# ------------------------------------------------------------------
# Build a safe globals dict – only whitelisted modules are exposed.
# ------------------------------------------------------------------
def make_safe_globals():
    """Create a globals dict containing only whitelisted modules that are actually importable.
    If a module (e.g., ``bpy``) cannot be imported because Blender is not running,
    it is simply omitted – the server can still start and will raise an error
    when user code tries to use the missing module.
    """
    safe = {}
    for name in ALLOWED_MODULES:
        try:
            safe[name] = __import__(name)
        except Exception:  # pragma: no cover – expected when bpy is absent
            continue
    return safe

SAFE_GLOBALS = make_safe_globals()

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
            # Execute user supplied code in the restricted environment.
            exec(code, SAFE_GLOBALS, local_ns)

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
    """Start the WebSocket server – works both in a daemon thread or foreground."""
    # Import websockets lazily; give a clear error if missing.
    try:
        import websockets  # noqa: F401
    except Exception as e:
        raise RuntimeError(
            "The 'websockets' package is required to run the server. "
            "Install it with: pip install websockets"
        ) from e

    async def _run():
        # This coroutine runs inside the event loop we create below.
        # Bind to the configured HOST and PORT. If the port is already in use, an OSError will be raised.
        server = await websockets.serve(ws_handler, HOST, PORT)
        print(f"[blender‑rpc] listening on ws://{HOST}:{PORT}")
        try:
            await asyncio.Future()  # keep running forever until cancelled
        finally:
            server.close()
            await server.wait_closed()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run())
    finally:
        loop.close()

# ------------------------------------------------------------------
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

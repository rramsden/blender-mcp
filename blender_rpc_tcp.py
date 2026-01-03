# blender_mcp_server.py -----------------------------------------------
# A minimal MCP (Model Context Protocol) server that runs inside Blender.
# Implements the MCP protocol over TCP using only Python stdlib.
#
# MCP Methods:
#   • initialize   - Handshake, returns server capabilities
#   • tools/list   - Returns available tools
#   • tools/call   - Executes a tool (e.g., execute_code)
#
# Install as a Blender add-on. Server listens on tcp://127.0.0.1:8765.
#
import json
import asyncio
import traceback
import threading
import queue

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------
HOST = "0.0.0.0"
PORT = 8765

# ------------------------------------------------------------------
# Thread-safe execution queue for main thread execution
# ------------------------------------------------------------------
_execution_queue = queue.Queue()
_timer_registered = False
_running_in_blender = False

# Check if we're running inside Blender
try:
    import bpy
    _running_in_blender = hasattr(bpy, "app") and hasattr(bpy.app, "timers")
except ImportError:
    _running_in_blender = False


# ------------------------------------------------------------------
# Shared code execution helper
# ------------------------------------------------------------------
def _run_code_sandboxed(code: str, bpy_module=None) -> dict:
    """
    Execute code in a sandboxed namespace with stdout/stderr capture.

    Args:
        code: Python code to execute
        bpy_module: Optional bpy module to inject (None = try to import)

    Returns:
        Dict with keys: result, error, output, stderr
    """
    import io
    import contextlib

    result = {"result": None, "error": None, "output": "", "stderr": ""}
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    # Build namespace
    global_ns = {"__builtins__": __builtins__}
    local_ns = {}

    if bpy_module is not None:
        global_ns["bpy"] = local_ns["bpy"] = bpy_module
    else:
        try:
            import bpy
            global_ns["bpy"] = local_ns["bpy"] = bpy
        except ImportError:
            pass

    try:
        with contextlib.redirect_stdout(stdout_capture), \
             contextlib.redirect_stderr(stderr_capture):
            exec(code, global_ns, local_ns)

        result["output"] = stdout_capture.getvalue()
        result["stderr"] = stderr_capture.getvalue()

        # Extract result: explicit 'result' variable, or parse stdout as JSON, or raw output
        if "result" in local_ns:
            result["result"] = local_ns["result"]
        else:
            stripped = result["output"].strip()
            try:
                result["result"] = json.loads(stripped)
            except Exception:
                result["result"] = stripped if stripped else None

    except Exception as exc:
        result["error"] = {"message": str(exc), "traceback": traceback.format_exc()}
        result["output"] = stdout_capture.getvalue()
        result["stderr"] = stderr_capture.getvalue()

    return result


def _execute_directly(code: str) -> dict:
    """Execute code directly (used when not running inside Blender)."""
    return _run_code_sandboxed(code)


def _execute_on_main_thread(code: str) -> dict:
    """
    Queue code for execution on Blender's main thread and wait for result.
    Thread-safe and can be called from any thread.
    """
    result_holder = {"result": None, "error": None, "output": "", "stderr": ""}
    result_event = threading.Event()
    _execution_queue.put((code, result_event, result_holder))
    result_event.wait(timeout=300)  # 5 minute timeout
    return result_holder


def _process_execution_queue() -> float:
    """
    Timer callback on Blender's main thread. Processes pending code requests.
    Returns interval until next call (0.01 seconds).
    """
    import bpy

    try:
        code, result_event, result_holder = _execution_queue.get_nowait()
    except queue.Empty:
        return 0.01

    # Run code and copy results into the shared holder
    exec_result = _run_code_sandboxed(code, bpy_module=bpy)
    result_holder.update(exec_result)
    result_event.set()
    return 0.01


def _ensure_timer_registered():
    """Register the execution queue processor timer if not already registered."""
    global _timer_registered
    if not _timer_registered:
        import bpy
        if not bpy.app.timers.is_registered(_process_execution_queue):
            bpy.app.timers.register(_process_execution_queue, persistent=True)
            _timer_registered = True
            print("[blender-rpc] Main thread executor timer registered.")


# ------------------------------------------------------------------
# MCP Protocol Constants
# ------------------------------------------------------------------
PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "blender-mcp"
SERVER_VERSION = "0.1.0"

# Tool definitions
TOOLS = [{
    "name": "execute_code",
    "description": "Execute Python code in Blender's environment with access to the bpy module.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python code to execute. Use 'result = ...' to return a value."
            }
        },
        "required": ["code"]
    }
}]


# ------------------------------------------------------------------
# MCP Method Handlers
# ------------------------------------------------------------------
def _handle_initialize(params):
    """MCP initialize handshake."""
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "capabilities": {"tools": {}},
        "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION}
    }


def _handle_tools_list(params):
    """Return available tools."""
    return {"tools": TOOLS}


async def _handle_tools_call(params):
    """Execute a tool by name."""
    tool_name = params.get("name")
    arguments = params.get("arguments", {})

    if tool_name != "execute_code":
        raise ValueError(f"Unknown tool: {tool_name}")

    code = arguments.get("code", "")

    # Use main thread execution in Blender (bpy API is not thread-safe)
    if _running_in_blender and _timer_registered:
        result = await asyncio.get_event_loop().run_in_executor(
            None, _execute_on_main_thread, code
        )
    else:
        result = _execute_directly(code)

    if result["error"]:
        return {
            "content": [{"type": "text", "text": f"Error: {result['error']['message']}"}],
            "isError": True
        }

    # Format output
    output_parts = []
    if result["result"] is not None:
        output_parts.append(f"Result: {json.dumps(result['result'])}")
    if result["output"]:
        output_parts.append(f"Output:\n{result['output']}")
    if result["stderr"]:
        output_parts.append(f"Stderr:\n{result['stderr']}")

    text = "\n".join(output_parts) if output_parts else "Code executed successfully."
    return {"content": [{"type": "text", "text": text}]}


# Method registry: name -> (handler, is_async)
_MCP_METHODS = {
    "initialize": (_handle_initialize, False),
    "tools/list": (_handle_tools_list, False),
    "tools/call": (_handle_tools_call, True),
}


async def handle_rpc(message: str) -> str | None:
    """Parse JSON-RPC request, dispatch to MCP handler, return JSON response."""
    req = None
    try:
        req = json.loads(message)
        method = req.get("method")

        # Notifications (no id) don't get responses
        if "id" not in req:
            return None

        if method not in _MCP_METHODS:
            raise NotImplementedError(f"Method '{method}' not supported")

        handler, is_async = _MCP_METHODS[method]
        params = req.get("params", {})
        result = await handler(params) if is_async else handler(params)

        response = {"jsonrpc": "2.0", "id": req["id"], "result": result}

    except Exception as exc:
        print(f"MCP Error: {exc}")
        response = {
            "jsonrpc": "2.0",
            "id": req.get("id") if req else None,
            "error": {"code": -32603, "message": str(exc)}
        }

    return json.dumps(response)


# ------------------------------------------------------------------
# TCP connection handler – line-delimited JSON.
# ------------------------------------------------------------------
async def tcp_handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    while True:
        try:
            raw_msg = await reader.readline()
            if not raw_msg:
                break

            message = raw_msg.decode("utf-8").strip()
            reply = await handle_rpc(message)

            # Notifications return None - no response needed
            if reply is not None:
                writer.write((reply + "\n").encode("utf-8"))
                await writer.drain()

        except Exception as e:
            print(f"Error handling TCP connection: {e}")
            break

    writer.close()
    await writer.wait_closed()


# ------------------------------------------------------------------
# Server bootstrap (runs in its own thread so Blender UI stays responsive).
# ------------------------------------------------------------------
def start_tcp_server():
    """Start the TCP server in its own event loop.
    The created ``_tcp_server`` and ``_tcp_loop`` globals are stored so that
    :func:`stop_tcp_server` can shut them down when the add‑on is disabled.
    """
    global _tcp_server, _tcp_loop
    _tcp_server = None
    _tcp_loop = None

    async def _start_server():
        # Create the server and store it in a global variable.
        global _tcp_server
        _tcp_server = await asyncio.start_server(tcp_handler, HOST, PORT)
        print(f"[blender‑rpc] listening on tcp://{HOST}:{PORT}")
        # Keep the coroutine alive while the event loop runs.
        await _tcp_server.serve_forever()

    # Set up a dedicated event loop for the server (runs in this thread).
    _tcp_loop = asyncio.new_event_loop()
    loop = _tcp_loop  # Local reference for finally block
    asyncio.set_event_loop(loop)
    # Schedule the server start and then run the loop forever.
    loop.create_task(_start_server())
    try:
        loop.run_forever()
    finally:
        # Clean shutdown if the loop exits unexpectedly.
        server = _tcp_server
        if server is not None:
            # Create a coroutine to close the server and wait for it
            async def close_server():
                server.close()
                await server.wait_closed()

            loop.run_until_complete(close_server())
        loop.close()


# ------------------------------------------------------------------
# Server shutdown helper
# ------------------------------------------------------------------
def stop_tcp_server():
    """Stop the running TCP server if it exists.
    Called from the add‑on's ``unregister`` function.
    """
    global _tcp_server, _tcp_loop
    if _tcp_server is None or _tcp_loop is None:
        print("[blender‑rpc] No TCP server to stop.")
        return
    if not _tcp_loop.is_running():
        print("[blender‑rpc] TCP server loop already stopped.")
        return
    # Close the server and stop the event loop safely.
    server = _tcp_server
    loop = _tcp_loop
    _tcp_server = None
    _tcp_loop = None

    async def _shutdown():
        if server is not None:
            server.close()
            await server.wait_closed()
        loop.stop()

    try:
        # Schedule shutdown coroutine on the server's own loop.
        asyncio.run_coroutine_threadsafe(_shutdown(), loop)
        print("[blender‑rpc] TCP server stopped.")
    except Exception as e:
        print(f"[blender‑rpc] Error stopping TCP server: {e}")


# Entry point
# ------------------------------------------------------------------
if __name__ == "__main__":
    # Register the main thread executor timer first
    _ensure_timer_registered()
    # Run the server in the foreground (blocks until Ctrl‑C)
    start_tcp_server()

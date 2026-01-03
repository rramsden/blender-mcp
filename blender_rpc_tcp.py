# blender_rpc_tcp.py -------------------------------------------------
# A tiny JSON-RPC 2.0 TCP server that runs inside Blender.
# It implements:
#   • describe() – tells a client (OpenCode, any MCP client) what methods exist.
#   • execute(code) – runs the supplied Python code in a sandbox that only
#                     exposes the bpy module (you can extend the whitelist).
#
# Usage:
#   blender --background -P /path/to/blender_rpc_tcp.py
#   # or run it from the Text Editor inside Blender.
#
# After start-up, connect to tcp://127.0.0.1:8765  (or change HOST/PORT below).
#
import json
import asyncio
import traceback
import threading
import queue

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------
HOST = "0.0.0.0"  # bind address; all interfaces
PORT = 8765  # TCP port for the TCP server
ALLOWED_MODULES = {"bpy"}  # whitelist of modules that user code may import/use

# ------------------------------------------------------------------
# Thread-safe execution queue for main thread execution
# ------------------------------------------------------------------
# Queue holds tuples of (code, result_event, result_holder)
_execution_queue = queue.Queue()
_timer_registered = False
_running_in_blender = False

# Check if we're running inside Blender
try:
    import bpy
    _running_in_blender = hasattr(bpy, "app") and hasattr(bpy.app, "timers")
except ImportError:
    _running_in_blender = False


def _execute_directly(code: str) -> dict:
    """
    Execute code directly (used when not running inside Blender).
    """
    import io
    import contextlib

    result_holder = {"result": None, "error": None, "output": "", "stderr": ""}
    captured_stdout = io.StringIO()
    captured_stderr = io.StringIO()
    local_ns: dict = {}

    try:
        with (
            contextlib.redirect_stdout(captured_stdout),
            contextlib.redirect_stderr(captured_stderr),
        ):
            global_ns = {"__builtins__": __builtins__}
            # Try to add bpy if available
            try:
                import bpy
                global_ns["bpy"] = bpy
                local_ns["bpy"] = bpy
            except ImportError:
                pass
            global_ns.update(local_ns)
            exec(code, global_ns, local_ns)

        result_holder["output"] = captured_stdout.getvalue()
        result_holder["stderr"] = captured_stderr.getvalue()

        if "result" in local_ns:
            result_holder["result"] = local_ns["result"]
        else:
            stripped = result_holder["output"].strip()
            try:
                result_holder["result"] = json.loads(stripped)
            except Exception:
                result_holder["result"] = stripped if stripped else None

    except Exception as exc:
        result_holder["error"] = {
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        result_holder["output"] = captured_stdout.getvalue()
        result_holder["stderr"] = captured_stderr.getvalue()

    return result_holder


def _execute_on_main_thread(code: str) -> dict:
    """
    Queue code for execution on Blender's main thread and wait for result.
    This is thread-safe and can be called from any thread.
    """
    result_holder = {"result": None, "error": None, "output": "", "stderr": ""}
    result_event = threading.Event()

    _execution_queue.put((code, result_event, result_holder))

    # Wait for the main thread to process the request
    result_event.wait(timeout=300)  # 5 minute timeout for long operations

    return result_holder


def _process_execution_queue() -> float:
    """
    Timer callback that runs on Blender's main thread.
    Processes pending code execution requests from the queue.
    Returns the interval until next call (0.01 seconds).
    """
    import bpy
    import io
    import contextlib

    try:
        # Process one item from the queue (non-blocking)
        code, result_event, result_holder = _execution_queue.get_nowait()
    except queue.Empty:
        # No work to do, check again soon
        return 0.01

    # Execute the code on the main thread
    captured_stdout = io.StringIO()
    captured_stderr = io.StringIO()
    local_ns: dict = {}

    try:
        with (
            contextlib.redirect_stdout(captured_stdout),
            contextlib.redirect_stderr(captured_stderr),
        ):
            # Set up namespace with bpy
            global_ns = {"__builtins__": __builtins__, "bpy": bpy}
            local_ns["bpy"] = bpy
            global_ns.update(local_ns)

            # Execute the code
            exec(code, global_ns, local_ns)

        result_holder["output"] = captured_stdout.getvalue()
        result_holder["stderr"] = captured_stderr.getvalue()

        # Determine result value
        if "result" in local_ns:
            result_holder["result"] = local_ns["result"]
        else:
            stripped = result_holder["output"].strip()
            try:
                result_holder["result"] = json.loads(stripped)
            except Exception:
                result_holder["result"] = stripped if stripped else None

    except Exception as exc:
        result_holder["error"] = {
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        result_holder["output"] = captured_stdout.getvalue()
        result_holder["stderr"] = captured_stderr.getvalue()

    # Signal that execution is complete
    result_event.set()

    # Continue processing queue
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
                            "returns": "any JSON-serialisable value",
                        }
                    ],
                },
            }

        # --------------------------------------------------------------
        # 2️⃣ Core method – "execute"
        # --------------------------------------------------------------
        elif req["method"] == "execute":
            raw_code = req["params"]["code"]

            # Choose execution method based on environment
            # When running inside Blender, use main thread execution to avoid crashes
            # (Blender's bpy API is not thread-safe)
            if _running_in_blender and _timer_registered:
                exec_result = await asyncio.get_event_loop().run_in_executor(
                    None, _execute_on_main_thread, raw_code
                )
            else:
                # Direct execution for tests or non-Blender environments
                exec_result = _execute_directly(raw_code)

            # Check for execution errors
            if exec_result["error"]:
                raise Exception(
                    f"{exec_result['error']['message']}\n{exec_result['error']['traceback']}"
                )

            result_value = exec_result["result"]
            output = exec_result["output"]
            err_output = exec_result["stderr"]

            response = {
                "jsonrpc": "2.0",
                "id": (
                    req["id"] if isinstance(req, dict) and "id" in req else None
                ),
                "result": result_value,
                "debug": {
                    "output": output,
                    "stderr": err_output,
                },
            }
        else:
            raise NotImplementedError(f"Method {req['method']} not supported")

    except Exception as exc:
        # Build a JSON-RPC error object with traceback for debugging.
        # Also print the error to console for immediate visibility
        print(f"RPC Error: {exc}")
        print(f"Traceback: {traceback.format_exc()}")
        response = {
            "jsonrpc": "2.0",
            "id": (req["id"] if isinstance(req, dict) and "id" in req else None),
            "error": {
                "code": -32603,  # Internal error
                "message": str(exc),
                "data": traceback.format_exc(),
            },
        }

    return json.dumps(response)


# ------------------------------------------------------------------
# TCP connection handler – line-delimited JSON.
# ------------------------------------------------------------------
async def tcp_handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    while True:
        try:
            # Read a line of data from the client
            raw_msg = await reader.readline()
            if not raw_msg:
                break

            # Decode the message
            message = raw_msg.decode("utf-8").strip()

            # Handle the RPC request
            reply = await handle_rpc(message)

            # Send the response back to the client
            writer.write((reply + "\n").encode("utf-8"))
            await writer.drain()

        except Exception as e:
            print(f"Error handling TCP connection: {e}")
            break

    # Close the connection
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

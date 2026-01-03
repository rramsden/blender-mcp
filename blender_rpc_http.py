# blender_mcp_server.py -----------------------------------------------
# A minimal MCP (Model Context Protocol) server that runs inside Blender.
# Implements the MCP protocol over HTTP using only Python stdlib.
#
# MCP Methods:
#   • initialize   - Handshake, returns server capabilities
#   • tools/list   - Returns available tools
#   • tools/call   - Executes a tool (e.g., execute_code)
#
# Install as a Blender add-on. Server listens on http://0.0.0.0:8765
#
import json
import traceback
import threading
import queue
from http.server import HTTPServer, BaseHTTPRequestHandler

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
        with (
            contextlib.redirect_stdout(stdout_capture),
            contextlib.redirect_stderr(stderr_capture),
        ):
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
TOOLS = [
    {
        "name": "execute_code",
        "description": "Execute Python code in Blender's environment with access to the bpy module.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute. Use 'result = ...' to return a value.",
                }
            },
            "required": ["code"],
        },
    }
]


# ------------------------------------------------------------------
# MCP Method Handlers
# ------------------------------------------------------------------
def _handle_initialize(params):
    """MCP initialize handshake."""
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "capabilities": {"tools": {}},
        "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
    }


def _handle_tools_list(params):
    """Return available tools."""
    return {"tools": TOOLS}


def _handle_tools_call_sync(params):
    """Execute a tool by name (synchronous version for HTTP handler)."""
    tool_name = params.get("name")
    arguments = params.get("arguments", {})

    if tool_name != "execute_code":
        raise ValueError(f"Unknown tool: {tool_name}")

    code = arguments.get("code", "")

    # Use main thread execution in Blender (bpy API is not thread-safe)
    if _running_in_blender and _timer_registered:
        result = _execute_on_main_thread(code)
    else:
        result = _execute_directly(code)

    if result["error"]:
        return {
            "content": [
                {"type": "text", "text": f"Error: {result['error']['message']}"}
            ],
            "isError": True,
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


# Method registry
_MCP_METHODS = {
    "initialize": _handle_initialize,
    "tools/list": _handle_tools_list,
    "tools/call": _handle_tools_call_sync,
}


# ------------------------------------------------------------------
# JSON-RPC Handler
# ------------------------------------------------------------------
def handle_rpc(message: str) -> str | None:
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

        handler = _MCP_METHODS[method]
        params = req.get("params", {})
        result = handler(params)

        response = {"jsonrpc": "2.0", "id": req["id"], "result": result}

    except json.JSONDecodeError as exc:
        print(f"MCP JSON Parse Error: {exc}")
        response = {
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32700, "message": "Parse error: " + str(exc)},
        }
    except Exception as exc:
        print(f"MCP Error: {exc}")
        response = {
            "jsonrpc": "2.0",
            "id": req.get("id") if req else None,
            "error": {"code": -32603, "message": str(exc)},
        }

    try:
        return json.dumps(response)
    except Exception as e:
        print(f"Error serializing response: {e}")
        return json.dumps(
            {
                "jsonrpc": "2.0",
                "id": req.get("id") if req else None,
                "error": {"code": -32603, "message": "Response serialization failed"},
            }
        )


# ------------------------------------------------------------------
# HTTP Handler for MCP Streamable HTTP transport
# ------------------------------------------------------------------
class MCPHTTPHandler(BaseHTTPRequestHandler):
    """HTTP request handler for MCP protocol."""

    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        """Override to prefix log messages."""
        print(f"[blender-rpc HTTP] {args[0]}")

    def _send_json_response(self, status_code: int, data: dict):
        """Send a JSON response with proper headers."""
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _send_error_response(self, status_code: int, error_code: int, message: str):
        """Send a JSON-RPC error response."""
        self._send_json_response(
            status_code,
            {"jsonrpc": "2.0", "id": None, "error": {"code": error_code, "message": message}},
        )

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_POST(self):
        """Handle POST requests for MCP JSON-RPC."""
        if self.path not in ("/", ""):
            self._send_error_response(404, -32600, f"Not found: {self.path}")
            return

        # Read request body
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self._send_error_response(400, -32700, "Empty request body")
            return

        try:
            body = self.rfile.read(content_length).decode("utf-8")
        except Exception as e:
            self._send_error_response(400, -32700, f"Failed to read request: {e}")
            return

        # Process the JSON-RPC request
        try:
            response = handle_rpc(body)
            if response is not None:
                self._send_json_response(200, json.loads(response))
            else:
                # Notification - no response needed, send 204
                self.send_response(204)
                self.end_headers()
        except Exception as e:
            print(f"[blender-rpc HTTP] Error processing request: {e}")
            self._send_error_response(500, -32603, f"Internal error: {e}")

    def do_GET(self):
        """Handle GET requests - return server info."""
        if self.path in ("/", ""):
            self._send_json_response(
                200,
                {
                    "name": SERVER_NAME,
                    "version": SERVER_VERSION,
                    "protocol": "MCP",
                    "protocolVersion": PROTOCOL_VERSION,
                    "transport": "HTTP",
                },
            )
        else:
            self._send_error_response(404, -32600, f"Not found: {self.path}")


# ------------------------------------------------------------------
# HTTP Server startup/shutdown
# ------------------------------------------------------------------
_http_server = None


def start_server():
    """Start the HTTP server (blocking)."""
    global _http_server
    try:
        _http_server = HTTPServer((HOST, PORT), MCPHTTPHandler)
        print(f"[blender-rpc] HTTP server listening on http://{HOST}:{PORT}")
        _http_server.serve_forever()
    except Exception as e:
        print(f"[blender-rpc] Failed to start HTTP server: {e}")


def stop_server():
    """Stop the HTTP server."""
    global _http_server
    if _http_server is not None:
        _http_server.shutdown()
        _http_server = None
        print("[blender-rpc] HTTP server stopped.")


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------
if __name__ == "__main__":
    # Register the main thread executor timer (only works in Blender)
    if _running_in_blender:
        _ensure_timer_registered()

    # Run HTTP server (blocks until Ctrl-C)
    try:
        start_server()
    except KeyboardInterrupt:
        print("\n[blender-rpc] Shutting down...")
        stop_server()

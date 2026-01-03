import importlib.util
import os
import threading

bl_info = {
    "name": "Blender RPC HTTP",
    "author": "macki",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "Text Editor > Sidebar",
    "description": "Expose an HTTP RPC interface for external control.",
    "category": "Development",
}

# Load the implementation script that lives alongside this file
module_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "blender_rpc_http.py")
)

spec = importlib.util.spec_from_file_location("blender_rpc_http_main", module_path)
if spec is None or spec.loader is None:
    raise ImportError(f"Cannot load blender_rpc_http.py from {module_path}")

_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_main)


def register():
    """Called by Blender when the add-on is enabled.
    Starts the RPC server in a background thread and prints debug info.
    """
    print("[blender-rpc] Register called – starting HTTP server…")
    try:
        # Register the main thread executor timer FIRST (must be on main thread)
        _main._ensure_timer_registered()
        # start_server blocks, so run it in a daemon thread
        t = threading.Thread(target=_main.start_server, daemon=True)
        t.start()
        print("[blender-rpc] Server thread started.")
    except Exception as e:
        raise RuntimeError(f"Failed to start HTTP server: {e}")


def unregister():
    """Called by Blender when the add-on is disabled."""
    print("[blender-rpc] Unregister called – stopping HTTP server…")
    _main.stop_server()

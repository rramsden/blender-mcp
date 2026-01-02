# Blender Remote Render Example

This repository contains a minimal example of how to control a local Blender instance from WSL (or any other machine) using a simple TCP socket.

## Files
- **blender_rpc_ws.py** – Run inside Blender's Python environment. It starts a background thread that listens for commands on port `8765`. When it receives the command `render_cube` it creates a cube in the scene and renders an image (`cube_render.png`) next to your `.blend` file.
- **client.py** – Runs in WSL (or any other Python environment). It connects to the Windows host where Blender is running and sends a command string.

## How to use
1. **Start Blender on Windows**
   - Open your `.blend` file or a new project.
   - Open the *Scripting* workspace.
   - In the text editor, open `blender_rpc_ws.py` (you can copy it from this repo into the same folder).
   - Press **Run Script**. You should see `Blender server listening on 0.0.0.0:50007` in the console.

2. **Find the host address reachable from WSL**
   - Usually `127.0.0.1` works because WSL shares the Windows localhost.
   - If that doesn't work, run `ipconfig` on Windows and use the IPv4 address of your network adapter.

3. **Run the client from WSL**
   ```bash
   cd /home/macki/Projects/blender
   python3 client.py  # defaults to render_cube command
   ```
   You can also pass a custom command:
   ```bash
   python3 client.py some_other_command
   ```

4. **Result**
   - Blender will create a cube, render it, and save `cube_render.png` next to your `.blend` file.
   - The client prints the response received from Blender (`Cube rendered`).

## Notes & Troubleshooting
- Ensure that the port `8765` is not blocked by a firewall on Windows.
- If you get a connection error, verify that the IP address used in `client.py` matches the one reachable from WSL.
- The server runs in a background thread so it won't block Blender's UI. You can stop it by restarting Blender.

## Running Tests

## Connecting via MCP

### Debugging the MCP client

To get more insight when using the MCP client (`blender_mcp_client.py`), follow these steps:

1. **Enable client‑side logging** – set the environment variable `DEBUG` to any value before running the client. The client will then echo the JSON request it sends and the raw response it receives.

2. **Ask the server for debug information** – include the top‑level field `debug: true` in the JSON‑RPC request. When using the provided MCP client, prepend the request with `debug:true` (e.g., `debug:true; import bpy; bpy.ops.mesh.primitive_cube_add(location=(0,0,0))`). The server will add a `debug` section to its response containing the captured stdout and the local namespace.

3. **Combine both** – set `DEBUG=1` and include the `debug:true` flag in the request to see both client‑side logs and the extra server‑side debugging details.

**Example command**:

```bash
DEBUG=1 echo "debug:true; import bpy; bpy.ops.mesh.primitive_cube_add(location=(0,0,0))" |
    python3 blender_mcp_client.py
```

These instructions let you troubleshoot code execution inside Blender without needing separate code snippets.



The server implements a **JSON‑RPC 2.0** interface over WebSockets, which is compatible with any MCP (Message Control Protocol) client that can speak JSON‑RPC. To connect:

```python
import asyncio, websockets, json

async def main():
    async with websockets.connect('ws://127.0.0.1:8765') as ws:
        # Handshake – ask the server what methods are available
        await ws.send(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "describe", "params": {}}) + "\n")
        describe_resp = await ws.recv()
        print('Server description:', json.loads(describe_resp))

        # Example – execute arbitrary Python code inside Blender
        payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "execute",
            "params": {"code": "import bpy; result = 'Hello from Blender'"}
        }
        await ws.send(json.dumps(payload) + "\n")
        exec_resp = await ws.recv()
        print('Execute response:', json.loads(exec_resp))

asyncio.run(main())
```

Replace the `code` string with any Python you wish to run inside Blender (subject to the whitelist defined in `blender_rpc_ws.py`). The response will contain a `result` field if your script defines a variable named `result`. This example works with any MCP‑compatible client that can open a WebSocket and exchange line‑delimited JSON‑RPC messages.

## Running Tests


You can run the unit tests for this project using **pytest**. The repository includes a virtual environment with the required dependencies listed in `requirements.txt`.

```bash
# Activate the virtual environment (if not already active)
source .venv/bin/activate

# Install test dependencies (if needed)
pip install -r requirements.txt

# Run all tests
pytest
```

The output will show the results of `tests/test_blender_rpc_ws.py`.

Enjoy remote controlling Blender!
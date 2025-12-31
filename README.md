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
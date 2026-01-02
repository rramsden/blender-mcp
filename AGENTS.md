# Blender RPC WebSocket Add-on

## Build Instructions

Always build this project using the Makefile. Do not use zip command from terminal.

```bash
make
```

This will:
1. Create a clean build environment
2. Package all necessary files into `blender_rpc_ws.zip`
3. Ensure proper structure for Blender add-on installation

## Linting

To check code style and linting issues, run:

```bash
make lint
```

Note: This project uses ruff for linting. The linting target will check all Python files in the project. Some pre-existing linting issues may be present in the codebase, but the specific errors that were originally reported have been fixed.

## Usage

1. Install the generated `blender_rpc_ws.zip` file in Blender
2. Enable the add-on in Blender's preferences
3. The WebSocket server will start automatically
4. Connect to `ws://127.0.0.1:8765` to send JSON-RPC commands

## Available Methods

- `describe()` - Returns information about available methods
- `execute(code)` - Executes Python code in Blender's environment
- `shutdown()` - Gracefully shuts down the server

## Important Notes

- The server binds to `0.0.0.0` to accept connections from any interface
- The add-on requires the `websockets` Python package
- For testing, run `pytest` in the project directory

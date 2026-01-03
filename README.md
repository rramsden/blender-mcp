# Blender RPC HTTP Add-on

This repository contains a Blender add-on that provides HTTP RPC capabilities for communicating with Blender through JSON-RPC requests. It allows external applications to execute Python code within Blender's environment and retrieve results.

## Build Instructions

Before using this add-on, you must build the package using the `Makefile` included in the repository.
Run `make` to generate the addon script for Blender.

## Usage

After building the addon, install it in Blender:
1. Open Blender
2. Go to Edit → Preferences → Add-ons
3. Click "Install..." and select the generated `blender_rpc_http.zip` file
4. Enable the add-on

After installation, any MCP protocol can connect to the running Blender instance to execute Python code and retrieve results through the HTTP RPC interface.

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

Enjoy remote controlling Blender!

# Blender Remote Render Example

This repository contains a minimal example of how to control a local Blender instance from WSL (or any other machine) using a simple TCP socket.

## Running the MCP Server

You will need to build the package using the `Makefile` included in the repository.
Run `make` to generate the the addon script for Blender.

Once you have the addon installed and running you can control blender using `mcp_client.py` or another client that can communicate over TCP.

Here is an execution example:

```
python mcp_client.py examples/100_cubes.py
```

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

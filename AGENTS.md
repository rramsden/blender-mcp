# Blender RPC WebSocket Add-on

## Build Instructions

Always build this project using the Makefile.

```bash
make
```

This will:
1. Create a clean build environment
2. Package all necessary files into `blender_rpc_ws.zip`
3. Ensure proper structure for Blender add-on installation

## Linting

Always run the linter after modifying code to check for errors:

```bash
make lint
```

For automatic fixing of linting issues, you can also run:

```bash
make lint-fix
```

Note: This project uses ruff for linting. The linting target will check all Python files in the project. Some pre-existing linting issues may be present in the codebase, but the specific errors that were originally reported have been fixed.

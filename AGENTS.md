# Blender RPC WebSocket Add-on

This Blender add-on provides WebSocket RPC capabilities for communicating with Blender through JSON-RPC requests. It allows external applications to execute Python code within Blender's environment and retrieve results.

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

## Testing

Always run the test suite after making changes to verify functionality:

```bash
make test
```

This will execute all pytest tests in the tests directory with verbose output.

## Check Command

Run all verification steps in sequence:

```bash
make check
```

This will:
1. Clean the build environment
2. Run linting to check code quality
3. Execute all pytest tests 
4. Build the final Blender add-on zip file

The check command is ideal for verifying that your changes are ready for deployment or before committing code. It ensures that your code is clean, properly linted, fully tested, and ready for deployment.

## Troubleshooting

If commands fail:
- Run `make clean` to reset the build environment
- Ensure all dependencies are installed (`pip install -r requirements.txt`)
- Check that Python and required packages are properly configured
- For test failures, review the specific error messages in the test output

# Blender RPC WebSocket Add-on

This Blender add-on provides WebSocket RPC capabilities for communicating with Blender through JSON-RPC requests. It allows external applications to execute Python code within Blender's environment and retrieve results.

## Build Instructions

Always build this project using the Makefile.

```bash
make
```

This will:
1. Create a clean build environment
2. Package all necessary files into `blender_rpc_http.zip`
3. Ensure proper structure for Blender add-on installation

## Verification

After making changes, always run the comprehensive verification:

```bash
make check
```

This command performs a comprehensive verification of your changes by executing the following steps in order:
1. Clean the build environment
2. Run linting to check code quality
3. Execute all pytest tests 
4. Build the final Blender add-on zip file

**Important**: Any agent must run `make check` after editing any file to ensure that changes are properly validated before being considered complete. This command guarantees that your code is clean, properly linted, fully tested, and packaged correctly for deployment.

## Linting

When working with Python code, always run the linter after modifying code to check for errors:

```bash
make lint
```

For automatic fixing of linting issues, you can also run:

```bash
make lint-fix
```

**Important**: If linting fails, run `make lint-fix` first to automatically fix common issues, then run `make lint` again to verify the fixes. This project uses ruff for linting. The linting target will check all Python files in the project. Some pre-existing linting issues may be present in the codebase, but the specific errors that were originally reported have been fixed.

## Check Command

Run all verification steps in sequence:

```bash
make check
```

This command performs a comprehensive verification of your changes by executing the following steps in order:
1. Clean the build environment
2. Run linting to check code quality
3. Execute all pytest tests 
4. Build the final Blender add-on zip file

**Important**: Any agent must run `make check` after editing any file to ensure that changes are properly validated before being considered complete. This command guarantees that your code is clean, properly linted, fully tested, and packaged correctly for deployment.

## Troubleshooting

If commands fail:
- Run `make clean` to reset the build environment
- Ensure all dependencies are installed (`pip install -r requirements.txt`)
- Check that Python and required packages are properly configured
- For test failures, review the specific error messages in the test output

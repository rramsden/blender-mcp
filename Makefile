# Makefile – build the Blender add‑on zip
# -------------------------------------------------
ADDON_NAME := blender_rpc_tcp
ZIP_NAME   := $(ADDON_NAME).zip
SRC_FILES  := __init__.py blender_rpc_tcp.py README.md mcp_client.py

all: build

build:
	@echo "▶ Building $(ZIP_NAME)…"
	@rm -rf tmp_pkg
	@mkdir -p tmp_pkg/$(ADDON_NAME)
	@cp -r $(SRC_FILES) tmp_pkg/$(ADDON_NAME)/
	@cd tmp_pkg && zip -qr ../$(ZIP_NAME) $(ADDON_NAME)
	@rm -rf tmp_pkg
	@echo "✅ $(ZIP_NAME) created."

lint:
	@echo "▶ Running ruff linting…"
	@python3 -m ruff check $(shell git ls-files "*.py" | grep -v __pycache__ | grep -v ".pytest_cache" | grep -v blender_rpc_ws.py | grep -v "examples/simple_cube.py" | grep -v "examples/test_basic.py")

lint-fix:
	@echo "▶ Running ruff linting with auto-fix…"
	@python3 -m ruff check --fix $(shell git ls-files "*.py" | grep -v __pycache__ | grep -v ".pytest_cache" | grep -v blender_rpc_ws.py)

test:
	@echo "▶ Running pytest tests…"
	@python3 -m pytest tests/ -v

check: lint test build clean
	@echo "✅ All checks passed: linting, testing, and build completed successfully."

# The command to add a single cube
# Note: This command requires the Blender RPC server to be running
# and the client to be connected to it.
cubes:
	echo "import bpy; bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False); bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0)); obj = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.name.startswith('Cube')][-1]; obj.name = 'Single_Cube'; mat = bpy.data.materials.new(name='Cube_Material'); mat.diffuse_color = (1.0, 0.0, 0.0, 1.0); obj.data.materials.append(mat)" | python mcp_client.py

clean:
	@rm -f $(ZIP_NAME) *.zip || true
	@rm -rf tmp_pkg blender_rpc_tcp || true
	@echo "🧹 Cleaned up."

.PHONY: all clean lint lint-fix test check

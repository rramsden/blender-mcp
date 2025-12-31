# Makefile – build the Blender add‑on zip
# -------------------------------------------------
ADDON_NAME := blender_rpc_ws
ZIP_NAME   := $(ADDON_NAME).zip
SRC_FILES  := __init__.py blender_rpc_ws.py README.md

all: $(ZIP_NAME)

$(ZIP_NAME):
	@echo "▶ Building $(ZIP_NAME)…"
	@rm -rf tmp_pkg
	@mkdir -p tmp_pkg/$(ADDON_NAME)
	@cp -r $(SRC_FILES) tmp_pkg/$(ADDON_NAME)/
	@cd tmp_pkg && zip -qr ../$(ZIP_NAME) $(ADDON_NAME)
	@rm -rf tmp_pkg
	@echo "✅ $(ZIP_NAME) created."

clean:
	@rm -f $(ZIP_NAME) *.zip || true
	@rm -rf tmp_pkg blender_rpc_ws || true
	@echo "🧹 Cleaned up."

.PHONY: all clean
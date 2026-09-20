#!/usr/bin/env bash
# Blender 4.5 LTS from inside the project (tools/blender-4.5.14-linux-x64). This VM has no GPU, no system libX11 and
# no sudo, so:
#   - X/GL libraries come from the conda env in tools/env (rebuilt from tools/environment.lock.txt)
#   - EEVEE gets a software (mesa llvmpipe) OpenGL context via surfaceless EGL
# ~/.local/bin/blender is a symlink to this file so `blender` on PATH still works.
TOOLS="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
ENV_ROOT="$TOOLS/env"
export LD_LIBRARY_PATH="$ENV_ROOT/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export __EGL_VENDOR_LIBRARY_FILENAMES="$ENV_ROOT/share/glvnd/egl_vendor.d/50_mesa.json"
export LIBGL_DRIVERS_PATH="$ENV_ROOT/lib/dri"
export LIBGL_ALWAYS_SOFTWARE=1 EGL_PLATFORM=surfaceless MESA_LOADER_DRIVER_OVERRIDE=llvmpipe
exec "$TOOLS/blender-4.5.14-linux-x64/blender" "$@"

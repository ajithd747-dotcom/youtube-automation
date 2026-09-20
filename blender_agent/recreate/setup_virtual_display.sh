#!/usr/bin/env bash
# One-time, no-root install of a virtual display (Xvfb) + xdotool + software OpenGL, so Blender's GUI can be
# launched and screen-recorded on this headless server (record_gui.py needs it).
#
# Everything lands inside the project, in blender_agent/tools_bin/ (gitignored; this script rebuilds it):
#   debs/        the downloaded .deb files          root/   their unpacked contents
#   Xvfb, xdotool, blender-gui   wrappers that put the unpacked libraries on the loader path
#
# Why not `apt install xvfb`: there is no sudo. `apt-get download` needs none, and dpkg -x unpacks anywhere. Two
# things a normal install gets for free are patched in:
#   * Xvfb hardcodes /usr/bin/xkbcomp. A private copy of Xvfb is byte-patched to look in /tmp instead, and the
#     Xvfb wrapper links /tmp/xkbcomp to the unpacked xkbcomp on every start (/tmp is cleared on reboot).
#   * The unpacked libraries are not on the loader path, so the wrappers set LD_LIBRARY_PATH / LIBGL_DRIVERS_PATH.
#
#   bash blender_agent/recreate/setup_virtual_display.sh        # safe to re-run
set -eu
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLS="$(cd "$HERE/.." && pwd)/tools_bin"
DEBS="$TOOLS/debs"
ROOT="$TOOLS/root"
LIBS="$ROOT/usr/lib/x86_64-linux-gnu:$ROOT/lib/x86_64-linux-gnu"
PACKAGES="xvfb xdotool x11-xkb-utils xkb-data xserver-common libxdo3 libxfont2 libfontenc1 libxkbfile1
 libpixman-1-0 libunwind8 libxtst6 libxinerama1 libxmuu1 xauth libgl1 libglx0 libglvnd0 libglx-mesa0
 libgl1-mesa-dri mesa-libgallium libgbm1 libxcb-glx0 libxcb-shm0 libxcb-dri3-0 libxcb-present0 libxcb-randr0
 libxcb-sync1 libxcb-xfixes0 libxshmfence1 libx11-xcb1 libxxf86vm1 libdrm-amdgpu1 libdrm-intel1 libpciaccess0
 libsensors5 libsensors-config libdisplay-info3 libvulkan1 x11-common libice6 libsm6 libxt6t64 libxmu6 libxpm4
 libxaw7 xfonts-encodings xfonts-utils xfonts-base
 libx11-6 libx11-data libxau6 libxcb1 libxdmcp6 libxext6 libxkbcommon0 libxrender1 libxrandr2 libxfixes3"

mkdir -p "$DEBS" "$ROOT"
if [ ! -x "$ROOT/usr/bin/Xvfb" ]; then
  (cd "$DEBS" && apt-get download $PACKAGES)
  for deb in "$DEBS"/*.deb; do dpkg -x "$deb" "$ROOT"; done
fi

# private copy of Xvfb whose compiled-in "/usr/bin" (the xkbcomp directory) reads "/tmp"
python3 - "$ROOT/usr/bin/Xvfb" "$ROOT/usr/bin/Xvfb-tmp-xkbcomp" <<'PY'
import sys
data = open(sys.argv[1], "rb").read()
assert data.count(b"/usr/bin\0") == 1, "unexpected Xvfb build: cannot find the xkbcomp directory string"
open(sys.argv[2], "wb").write(data.replace(b"/usr/bin\0", b"/tmp\0\0\0\0\0"))
PY
chmod +x "$ROOT/usr/bin/Xvfb-tmp-xkbcomp"

cat > "$TOOLS/Xvfb" <<EOF
#!/usr/bin/env bash
ln -sf "$ROOT/usr/bin/xkbcomp" /tmp/xkbcomp
export LD_LIBRARY_PATH="$LIBS\${LD_LIBRARY_PATH:+:\$LD_LIBRARY_PATH}"
export LIBGL_DRIVERS_PATH="$ROOT/usr/lib/x86_64-linux-gnu/dri" LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe
exec "$ROOT/usr/bin/Xvfb-tmp-xkbcomp" -xkbdir "$ROOT/usr/share/X11/xkb" -nolisten tcp "\$@"
EOF
cat > "$TOOLS/xdotool" <<EOF
#!/usr/bin/env bash
export LD_LIBRARY_PATH="$LIBS\${LD_LIBRARY_PATH:+:\$LD_LIBRARY_PATH}"
exec "$ROOT/usr/bin/xdotool" "\$@"
EOF
# Blender's GUI needs OpenGL: Mesa's software rasteriser (llvmpipe) from the unpacked packages
cat > "$TOOLS/blender-gui" <<EOF
#!/usr/bin/env bash
export LD_LIBRARY_PATH="$LIBS\${LD_LIBRARY_PATH:+:\$LD_LIBRARY_PATH}"
export LIBGL_DRIVERS_PATH="$ROOT/usr/lib/x86_64-linux-gnu/dri"
export __EGL_VENDOR_LIBRARY_DIRS="$ROOT/usr/share/glvnd/egl_vendor.d"
export LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe
exec "\${BLENDER_PATH:-\$(command -v blender)}" "\$@"
EOF
chmod +x "$TOOLS/Xvfb" "$TOOLS/xdotool" "$TOOLS/blender-gui"
echo "installed in $TOOLS: Xvfb  xdotool  blender-gui"

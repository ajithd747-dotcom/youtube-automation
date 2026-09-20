"""COOKBOOK: typewriter typing text reveal letter by letter using a frame-change handler (custom code)."""
import bpy
full = "Type this message"
root = empty("typed", None, (0, 0, 0))
t = text_part(root, full, "#ffffff", height=H * 0.12, max_width=W() * 0.85)
chars_per_second = 14

def _type(scene, depsgraph=None):
    n = int(max(0, (scene.frame_current - 1) / scene.render.fps) * chars_per_second)
    t.data.body = full[:n] + ("|" if (scene.frame_current // 6) % 2 == 0 else " ")

bpy.app.handlers.frame_change_pre.append(_type)

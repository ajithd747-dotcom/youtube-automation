"""COOKBOOK: number counter counting up text animation using a frame-change handler (custom code).
A handler runs every rendered frame, so text body can change over time. Uses text_part, empty, frame handlers."""
import bpy
root = empty("counter", None, (0, 0, 0))
t = text_part(root, "0", "#ffd23f", height=H * 0.3, max_width=W() * 0.8)
target, seconds = 1000000, 2.0

def _update(scene, depsgraph=None):
    prog = min(1.0, (scene.frame_current - 1) / (seconds * scene.render.fps))
    t.data.body = f"{int(target * (1 - (1 - prog) ** 3)):,}"

bpy.app.handlers.frame_change_pre.append(_update)

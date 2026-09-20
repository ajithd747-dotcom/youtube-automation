# TEST text fitting: measure AFTER scaling + update, and never scale text twice (parent AND font size).
import bpy
root = empty("t", None, (0, 0, 0))
t = text_part(root, "A very long headline that must fit inside the frame width", "#ffffff", height=1.0, max_width=8.0, wrap=20)
bpy.context.view_layer.update()
assert t.dimensions.x <= 8.02, f"text too wide: {t.dimensions.x:.2f}"

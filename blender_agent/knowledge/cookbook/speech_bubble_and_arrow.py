"""COOKBOOK: speech bubble callout label with text and pointing arrow annotation (custom code)."""
import math
root = empty("bubble", None, (W() * 0.2, 0, H * 0.28))
part("sphere", root, "#ffffff", scale=(W() * 0.3, 0.05, H * 0.2))
part("cone", root, "#ffffff", loc=(-W() * 0.09, 0, -H * 0.12), rot=(0, math.radians(20), math.radians(180)), scale=(0.7, 0.05, 1.0))
text_part(root, "Hmm... really?", "#111111", height=H * 0.06, max_width=W() * 0.26, loc=(0, -0.05, 0))
key(root, 1, scale=(0.001,) * 3, interp="CONSTANT")
key(root, frame(0.6), scale=(0.001,) * 3, interp="CONSTANT")
key(root, frame(1.0), scale=(1, 1, 1), interp="BEZIER")

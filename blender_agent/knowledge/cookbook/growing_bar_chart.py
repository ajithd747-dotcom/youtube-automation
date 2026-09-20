"""COOKBOOK: animated bar chart, bars grow from the baseline one after another (custom code).
Scale a cube on Z from ~0 to full height; the pivot is the bar centre so also move it up as it grows."""
values = [0.3, 0.55, 0.8, 1.0]
colors = ["#4d9de0", "#3bceac", "#ffd23f", "#ff4d6d"]
base_z, max_h = -H * 0.3, H * 0.55
for i, (v, c) in enumerate(zip(values, colors)):
    x = (i - (len(values) - 1) / 2) * W() * 0.16
    root = empty("bar", None, (x, 0, base_z))
    part("cube", root, c, scale=(W() * 0.1, 0.1, 1.0))
    h = v * max_h
    t0 = 0.3 + i * 0.35
    key(root, frame(t0), loc=(x, 0, base_z), scale=(1, 1, 0.001), interp="BEZIER")
    key(root, frame(t0 + 0.7), loc=(x, 0, base_z + h / 2), scale=(1, 1, h), interp="BEZIER")

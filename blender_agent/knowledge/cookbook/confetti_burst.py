"""COOKBOOK: confetti particles burst celebration falling colorful cubes (custom code, runs after the shot is built).
Uses scene_lib helpers: empty, part, key, frame, W, H. Coordinates: x right, z up, y = depth (camera looks along +y)."""
import random
random.seed(7)
colors = ["#ff4d6d", "#ffd23f", "#3bceac", "#4d9de0", "#b56cff"]
for i in range(40):
    root = empty("confetti", None, (0, 0, 0))
    part("cube", root, random.choice(colors), scale=(0.18, 0.02, 0.28))
    start = (random.uniform(-1, 1) * W() * 0.15, 0, -H * 0.1)
    peak = (random.uniform(-1, 1) * W() * 0.45, 0, random.uniform(0.1, 0.45) * H)
    end = (peak[0] + random.uniform(-1, 1), 0, -H * 0.6)
    t0 = random.uniform(0, 0.4)
    key(root, frame(t0), loc=start, rot=(0, 0, 0), scale=(1, 1, 1), interp="LINEAR")
    key(root, frame(t0 + 0.6), loc=peak, rot=(0, random.uniform(-6, 6), 0), interp="BEZIER")
    key(root, frame(t0 + 2.2), loc=end, rot=(0, random.uniform(-12, 12), 0), interp="LINEAR")

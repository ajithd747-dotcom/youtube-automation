"""COOKBOOK: keyframe animation basics move rotate scale object over time, insert keyframes, interpolation (custom code).
Coordinates: frame(t) converts seconds to frame numbers. Pos in world units: x in [-W()/2, W()/2], z in [-H/2, H/2]."""
root = empty("ball", None, (-W() * 0.3, 0, 0))
part("sphere", root, "#ff4d6d", scale=(1.6, 1.6, 1.6))
key(root, frame(0.0), loc=(-W() * 0.3, 0, -H * 0.2), interp="BEZIER")
key(root, frame(0.6), loc=(0, 0, H * 0.2), interp="BEZIER")     # arc up
key(root, frame(1.2), loc=(W() * 0.3, 0, -H * 0.2), interp="BEZIER")
# rotate in the picture plane: rotation about the Y axis (view axis)  ->  rot=(0, angle_radians, 0)
key(root, frame(0.0), rot=(0, 0, 0), interp="LINEAR")
key(root, frame(1.2), rot=(0, -6.28, 0), interp="LINEAR")

obj = bpy.data.objects.get("icon")
if obj:
    for f, t in sample(0.0, end_t(), None, 0.5):
        key(obj, f, scale=(1, 1, 1), interp="BEZIER")
        key(obj, frame(t + 0.25), scale=(1.07, 1.07, 1.07), interp="BEZIER")
    key(obj, frame(end_t()), scale=(1, 1, 1), interp="BEZIER")
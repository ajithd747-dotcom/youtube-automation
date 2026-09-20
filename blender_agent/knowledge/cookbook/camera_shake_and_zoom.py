"""COOKBOOK: camera shake handheld shake impact zoom punch-in (custom code). Camera is bpy.context.scene.camera,
child of the 'cam_rig' empty. Animate the rig location for shake; ortho cameras zoom via data.ortho_scale."""
import bpy, math
rig = bpy.data.objects["cam_rig"]
for f, t in sample(0.0, min(end_t(), 1.2), None, 1):
    a = math.exp(-t * 3.5) * 0.35
    key(rig, f, loc=(math.sin(t * 60) * a, 0, math.cos(t * 47) * a), interp="LINEAR")

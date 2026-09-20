"""COOKBOOK: add lights sun area point light shadows 3d scene lighting and floor (custom code; only visible in EEVEE, not Workbench)."""
import bpy, math
area = bpy.data.objects.new("key", bpy.data.lights.new("key", "AREA"))
bpy.context.scene.collection.objects.link(area)
area.data.energy, area.data.size = 900, 6
area.location = (3, -6, 6)
area.rotation_euler = (math.radians(55), 0, math.radians(20))
floor = empty("floor", None, (0, 0, -H * 0.35))
part("cube", floor, "#c9d6e6", scale=(W() * 3, 40, 0.2), loc=(0, 0, -0.1), flat=False)

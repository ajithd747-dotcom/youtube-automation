import bpy
def go():
    print("GUI TEST RUNNING")
    return None
bpy.app.timers.register(go, first_interval=1.0)
def quit_():
    bpy.ops.wm.quit_blender()
    return None
bpy.app.timers.register(quit_, first_interval=14.0)

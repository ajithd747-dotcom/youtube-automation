"""COOKBOOK: gradient background sky color ramp world shader nodes (custom code). Works in EEVEE; Workbench renders the flat world color."""
import bpy
world = bpy.context.scene.world
world.use_nodes = True
nt = world.node_tree
nt.nodes.clear()
out = nt.nodes.new("ShaderNodeOutputWorld")
bg = nt.nodes.new("ShaderNodeBackground")
ramp = nt.nodes.new("ShaderNodeValToRGB")
coord = nt.nodes.new("ShaderNodeTexCoord")
sep = nt.nodes.new("ShaderNodeSeparateXYZ")
nt.links.new(coord.outputs["Window"], sep.inputs["Vector"])
nt.links.new(sep.outputs["Y"], ramp.inputs["Fac"])
ramp.color_ramp.elements[0].color = rgba("#0b1d3a")
ramp.color_ramp.elements[1].color = rgba("#3a7bd5")
nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
nt.links.new(bg.outputs["Background"], out.inputs["Surface"])

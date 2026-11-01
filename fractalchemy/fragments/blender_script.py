"""The Blender script written beside an exported DE mesh: import it, give it a material, add a camera and a light.

    blender --python <name>_blender.py

A text template filled with the file names; it uses Blender 4's import operators (OBJ / PLY / STL / glTF / USD),
prefers the baked texture for the base colour and falls back to the vertex colour attribute.
"""

from __future__ import annotations

from pathlib import Path

IMPORTERS = {".obj": "wm.obj_import", ".ply": "wm.ply_import", ".stl": "wm.stl_import", ".glb": "import_scene.gltf", ".usdc": "wm.usd_import",
             ".usda": "wm.usd_import", ".usdz": "wm.usd_import"}

TEMPLATE = '''"""Import the {name} mesh exported by Fractalchemy's Fragments window into Blender, with a material, a camera and a light.

    blender --python {script_name}
"""
import os
import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
MESH = os.path.join(HERE, {mesh_name!r})
TEXTURE = {texture_expr}

bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.{operator}(filepath=MESH)
objects = [o for o in bpy.context.selected_objects if o.type == "MESH"] or [o for o in bpy.data.objects if o.type == "MESH"]
obj = objects[0]
obj.name = {name!r}
obj.scale = ({scale}, {scale}, {scale})
material = bpy.data.materials.new({name!r})
material.use_nodes = True
nodes, links = material.node_tree.nodes, material.node_tree.links
bsdf = nodes.get("Principled BSDF")
if TEXTURE and os.path.isfile(TEXTURE):
    image = nodes.new("ShaderNodeTexImage")
    image.image = bpy.data.images.load(TEXTURE)
    links.new(image.outputs["Color"], bsdf.inputs["Base Color"])
elif obj.data.color_attributes:
    color = nodes.new("ShaderNodeVertexColor")
    color.layer_name = obj.data.color_attributes[0].name
    links.new(color.outputs["Color"], bsdf.inputs["Base Color"])
bsdf.inputs["Roughness"].default_value = 0.45
obj.data.materials.clear()
obj.data.materials.append(material)
for polygon in obj.data.polygons:
    polygon.use_smooth = True

size = max(obj.dimensions) or 1.0
centre = obj.location
bpy.ops.object.camera_add(location=(centre.x + size * 1.6, centre.y - size * 1.6, centre.z + size * 1.1))
camera = bpy.context.object
camera.data.lens = 50
camera.rotation_euler = (centre - camera.location).to_track_quat("-Z", "Y").to_euler()
bpy.context.scene.camera = camera
bpy.ops.object.light_add(type="SUN", location=(centre.x + size, centre.y - size, centre.z + size * 2))
bpy.context.object.data.energy = 3.0
print("Imported", MESH)
'''


def blender_script(name: str, files: list[Path], texture: Path | None, meters_per_unit: float = 1.0) -> str:
    """The script text for the first importable file among `files` (a comment when there is none)."""
    mesh_file = next((Path(f) for f in files if Path(f).suffix.lower() in IMPORTERS), None)
    if mesh_file is None:
        return "# no importable mesh file was written\n"
    return TEMPLATE.format(name=name, script_name=f"{mesh_file.stem}_blender.py", mesh_name=mesh_file.name,
                           texture_expr=f"os.path.join(HERE, {Path(texture).name!r})" if texture is not None else "None",
                           operator=IMPORTERS[mesh_file.suffix.lower()], scale=1.0 if meters_per_unit == 1.0 else meters_per_unit)


__all__ = ["blender_script", "IMPORTERS", "TEMPLATE"]

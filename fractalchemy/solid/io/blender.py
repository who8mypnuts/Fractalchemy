"""A Blender scene as a script: `blender --python scene.py` (or *Scripting ▸ Run Script*) imports the mesh asset written
beside it, builds a Principled BSDF fed by the vertex colours (or the baked texture), places the scene's distant
lights as Sun lamps turned the way they are in the 3D Editor, sets the world colour and ambient strength, and
adds a camera matching the flame's 3D camera. A `.blend` cannot be written by anything but Blender, so this is
the portable form; the script runs on Blender 3.x and 4.x.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from ...fractal.scene import Camera
from ...scene3d.model import Scene3D
from ..view import light_direction

TEMPLATE = '''# Fractalchemy 3D export — {name}
# Run with:  blender --python "{script_name}"      (or open Blender's Scripting tab and Run Script)
# Set CLEAR_SCENE = False to add to the scene that is open instead of starting from an empty one.
import math
import os

import bpy
from mathutils import Matrix, Vector

CLEAR_SCENE = True
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() and __file__ else bpy.path.abspath("//")
ASSET = os.path.join(HERE, {asset!r})
TEXTURE = {texture!r}

if CLEAR_SCENE:
    bpy.ops.wm.read_homefile(use_empty=True)

# --- the mesh ---------------------------------------------------------------------------------------------------
before = set(bpy.data.objects)
ext = os.path.splitext(ASSET)[1].lower()
if ext == ".glb" or ext == ".gltf":
    bpy.ops.import_scene.gltf(filepath=ASSET)
elif ext == ".ply":
    (bpy.ops.wm.ply_import if hasattr(bpy.ops.wm, "ply_import") else bpy.ops.import_mesh.ply)(filepath=ASSET)
elif ext == ".obj":
    (bpy.ops.wm.obj_import if hasattr(bpy.ops.wm, "obj_import") else bpy.ops.import_scene.obj)(filepath=ASSET)
elif ext == ".stl":
    (bpy.ops.wm.stl_import if hasattr(bpy.ops.wm, "stl_import") else bpy.ops.import_mesh.stl)(filepath=ASSET)
else:
    bpy.ops.wm.usd_import(filepath=ASSET)
meshes = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
for obj in meshes:
    obj.name = {name!r} if len(meshes) == 1 else obj.name
    mesh = obj.data
    mesh.shade_smooth() if hasattr(mesh, "shade_smooth") else None
    material = bpy.data.materials.new({name!r} + "_material")
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Roughness"].default_value = {roughness}
        if "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = {specular}
        elif "Specular" in bsdf.inputs:
            bsdf.inputs["Specular"].default_value = {specular}
        if TEXTURE and os.path.exists(os.path.join(HERE, TEXTURE)):
            image = bpy.data.images.load(os.path.join(HERE, TEXTURE))
            tex = nodes.new("ShaderNodeTexImage")
            tex.image = image
            links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        elif mesh.color_attributes if hasattr(mesh, "color_attributes") else mesh.vertex_colors:
            attribute = nodes.new("ShaderNodeVertexColor")
            attribute.layer_name = (mesh.color_attributes[0].name if hasattr(mesh, "color_attributes") else mesh.vertex_colors[0].name)
            links.new(attribute.outputs["Color"], bsdf.inputs["Base Color"])
    if mesh.materials:
        mesh.materials[0] = material
    else:
        mesh.materials.append(material)

centre = Vector({centre!r})

# --- the camera (the flame's 3D camera) ---------------------------------------------------------------------------
camera_data = bpy.data.cameras.new("Fractalchemy camera")
camera = bpy.data.objects.new("Fractalchemy camera", camera_data)
bpy.context.scene.collection.objects.link(camera)
right, up, back = Vector({right!r}), Vector({up!r}), Vector({back!r})
camera.matrix_world = Matrix(((right.x, up.x, back.x, 0.0), (right.y, up.y, back.y, 0.0), (right.z, up.z, back.z, 0.0), (0.0, 0.0, 0.0, 1.0)))
camera.location = centre + back * {distance}
if {perspective} > 0.0:
    camera_data.type = "PERSP"
    camera_data.sensor_fit = "HORIZONTAL"
    camera_data.angle = {fov}
else:
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = {visible_width}
camera_data.clip_start = max(0.001, {distance} * 0.01)
camera_data.clip_end = {distance} * 100.0
bpy.context.scene.camera = camera
bpy.context.scene.render.resolution_x = {width}
bpy.context.scene.render.resolution_y = {height}

# --- lights (distant lights, placed relative to the camera as in the 3D Editor) ----------------------------------
for index, (direction, colour, energy, shadows) in enumerate({lights!r}):
    lamp = bpy.data.lights.new("Fractalchemy light %d" % (index + 1), type="SUN")
    lamp.color = colour
    lamp.energy = energy
    lamp.use_shadow = shadows
    lamp.angle = math.radians(2.0)
    obj = bpy.data.objects.new(lamp.name, lamp)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = centre + Vector(direction) * {distance}
    obj.rotation_euler = Vector(direction).to_track_quat("Z", "Y").to_euler()

# --- the world ------------------------------------------------------------------------------------------------------
world = bpy.context.scene.world or bpy.data.worlds.new("Fractalchemy world")
bpy.context.scene.world = world
world.use_nodes = True
background = world.node_tree.nodes.get("Background")
if background is not None:
    background.inputs["Color"].default_value = ({bg_r}, {bg_g}, {bg_b}, 1.0)
    background.inputs["Strength"].default_value = {ambient}
bpy.context.scene.render.film_transparent = {transparent}
print("Fractalchemy: imported", [o.name for o in meshes], "with", {light_count}, "lights")
'''


def blender_script(scene: Scene3D, asset_name: str, mesh_centre, mesh_extent: float, name: str = "fractal",
                   texture_name: str | None = None, script_name: str = "scene.py") -> str:
    """The script's text for `scene`, importing `asset_name` (a file beside the script)."""
    flame = scene.fractal
    camera = flame.camera if flame is not None else Camera()
    m = np.array(camera.matrix(), dtype=np.float64)
    right, up, back = m[:, 0], -m[:, 1], m[:, 2]             # world vectors of view x, −view y (screen up), view z (towards the eye)
    extent = max(float(mesh_extent), 1e-6)
    ppu = camera.scale * (2.0 ** camera.zoom)                  # pixels per unit at the flame's own width
    visible_width = max(camera.width, 1) / max(ppu, 1e-9)
    if camera.perspective > 0:
        distance = 1.0 / camera.perspective
        fov = 2.0 * math.atan(visible_width / 2.0 * camera.perspective)
    else:
        distance = extent * 3.0
        fov = math.radians(40.0)
    lights = []
    for light in scene.lights:
        d_view = light_direction(light.altitude, light.azimuth)
        d_world = d_view @ m.T
        lights.append((tuple(round(float(v), 6) for v in d_world), tuple(round(c / 255.0, 4) for c in light.color),
                       round(float(light.intensity) * 3.0, 4), bool(light.shadows)))
    material = scene.material_for(0)
    env = scene.environment
    centre = tuple(round(float(v), 6) for v in np.asarray(mesh_centre, dtype=np.float64))
    return TEMPLATE.format(
        name=name, script_name=script_name, asset=asset_name, texture=texture_name,
        roughness=round(max(0.05, min(1.0, 1.0 - material.shininess / 200.0)), 3), specular=round(min(1.0, material.specular), 3),
        centre=centre, right=tuple(round(float(v), 6) for v in right), up=tuple(round(float(v), 6) for v in up),
        back=tuple(round(float(v), 6) for v in back), distance=round(distance, 6), perspective=round(camera.perspective, 6),
        fov=round(fov, 6), visible_width=round(visible_width, 6), width=max(1, camera.width), height=max(1, camera.height),
        lights=lights, bg_r=round(env.color[0] / 255.0, 4), bg_g=round(env.color[1] / 255.0, 4), bg_b=round(env.color[2] / 255.0, 4),
        ambient=round(env.ambient, 4), transparent=not env.visible, light_count=len(lights))


def write_blender_script(scene: Scene3D, path: Path, asset: Path, mesh_centre, mesh_extent: float, name: str = "fractal",
                         texture: Path | None = None) -> list[Path]:
    """Write the script to `path`, referring to `asset` (and `texture`) by file name; returns `[path]`."""
    path = Path(path)
    text = blender_script(scene, Path(asset).name, mesh_centre, mesh_extent, name, Path(texture).name if texture else None, path.name)
    path.write_text(text, encoding="utf-8")
    return [path]


__all__ = ["blender_script", "write_blender_script", "TEMPLATE"]

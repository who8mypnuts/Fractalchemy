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




INSTANCES_TEMPLATE = '''# Fractalchemy holon IFS export — {name}
# Run with:  blender --python "{script_name}"      (or open Blender's Scripting tab and Run Script)
# Imports each instancer's asset and places its instances with a Geometry Nodes "Instance on Points" modifier
# (true instancing: any count). The instance data is read from "{data_name}" beside this script.
import json
import math
import os

import bpy
from mathutils import Euler, Matrix, Quaternion, Vector

CLEAR_SCENE = True
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() and __file__ else bpy.path.abspath("//")
with open(os.path.join(HERE, {data_name!r}), "r", encoding="utf-8") as fh:
    DATA = json.load(fh)

if CLEAR_SCENE:
    bpy.ops.wm.read_homefile(use_empty=True)


def import_asset(filename):
    before = set(bpy.data.objects)
    path = os.path.join(HERE, filename)
    ext = os.path.splitext(path)[1].lower()
    if ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=path)
    elif ext == ".ply":
        (bpy.ops.wm.ply_import if hasattr(bpy.ops.wm, "ply_import") else bpy.ops.import_mesh.ply)(filepath=path)
    elif ext == ".obj":
        (bpy.ops.wm.obj_import if hasattr(bpy.ops.wm, "obj_import") else bpy.ops.import_scene.obj)(filepath=path)
    else:
        bpy.ops.wm.usd_import(filepath=path)
    new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    return new[0] if new else None


def colour_material(name, rgb, roughness, specular):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
        key = "Specular IOR Level" if "Specular IOR Level" in bsdf.inputs else "Specular"
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = specular
    return material


def instance_on_points(points_object, asset_object, label):
    modifier = points_object.modifiers.new(label + " instances", "NODES")
    group = bpy.data.node_groups.new(label + " instances", "GeometryNodeTree")
    modifier.node_group = group
    interface = getattr(group, "interface", None)
    if interface is not None:                      # Blender 4.x
        interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
        interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    else:                                          # Blender 3.x
        group.inputs.new("NodeSocketGeometry", "Geometry")
        group.outputs.new("NodeSocketGeometry", "Geometry")
    nodes, links = group.nodes, group.links
    group_in = nodes.new("NodeGroupInput")
    group_out = nodes.new("NodeGroupOutput")
    info = nodes.new("GeometryNodeObjectInfo")
    info.inputs["Object"].default_value = asset_object
    info.transform_space = "ORIGINAL"
    rotation = nodes.new("GeometryNodeInputNamedAttribute")
    rotation.data_type = "FLOAT_VECTOR"
    rotation.inputs["Name"].default_value = "holon_rotation"
    scale = nodes.new("GeometryNodeInputNamedAttribute")
    scale.data_type = "FLOAT"
    scale.inputs["Name"].default_value = "holon_scale"
    instance = nodes.new("GeometryNodeInstanceOnPoints")
    links.new(group_in.outputs[0], instance.inputs["Points"])
    links.new(info.outputs["Geometry"], instance.inputs["Instance"])
    links.new(rotation.outputs[0], instance.inputs["Rotation"])
    links.new(scale.outputs[0], instance.inputs["Scale"])
    links.new(instance.outputs["Instances"], group_out.inputs[0])


for entry in DATA["instancers"]:
    asset = import_asset(entry["asset"])
    if asset is None:
        print("Fractalchemy: could not import", entry["asset"])
        continue
    asset.name = entry["name"] + " asset"
    asset.hide_render = True
    asset.hide_set(True)
    if entry.get("color") is not None:
        material = colour_material(entry["name"] + " material", entry["color"], entry["roughness"], entry["specular"])
        if asset.data.materials:
            asset.data.materials[0] = material
        else:
            asset.data.materials.append(material)
    mesh = bpy.data.meshes.new(entry["name"] + " points")
    positions = entry["positions"]
    mesh.from_pydata([tuple(p) for p in positions], [], [])
    rot = mesh.attributes.new("holon_rotation", "FLOAT_VECTOR", "POINT")
    for item, e in zip(rot.data, entry["rotations"]):
        item.vector = e
    sc = mesh.attributes.new("holon_scale", "FLOAT", "POINT")
    for item, s in zip(sc.data, entry["scales"]):
        item.value = s
    points = bpy.data.objects.new(entry["name"], mesh)
    bpy.context.scene.collection.objects.link(points)
    instance_on_points(points, asset, entry["name"])

# --- camera, lights and world as the Fractalchemy scene had them --------------------------------------------------------------
centre = Vector(DATA["centre"])
camera_data = bpy.data.cameras.new("Fractalchemy camera")
camera = bpy.data.objects.new("Fractalchemy camera", camera_data)
bpy.context.scene.collection.objects.link(camera)
right, up, back = Vector(DATA["right"]), Vector(DATA["up"]), Vector(DATA["back"])
camera.matrix_world = Matrix(((right.x, up.x, back.x, 0.0), (right.y, up.y, back.y, 0.0), (right.z, up.z, back.z, 0.0), (0.0, 0.0, 0.0, 1.0)))
camera.location = centre + back * DATA["distance"]
if DATA["perspective"] > 0.0:
    camera_data.type = "PERSP"
    camera_data.sensor_fit = "HORIZONTAL"
    camera_data.angle = DATA["fov"]
else:
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = DATA["visible_width"]
camera_data.clip_start = max(0.001, DATA["distance"] * 0.01)
camera_data.clip_end = DATA["distance"] * 100.0
bpy.context.scene.camera = camera
for index, (direction, colour, energy, shadows) in enumerate(DATA["lights"]):
    lamp = bpy.data.lights.new("Fractalchemy light %d" % (index + 1), type="SUN")
    lamp.color = colour
    lamp.energy = energy
    lamp.use_shadow = shadows
    lamp.angle = math.radians(2.0)
    obj = bpy.data.objects.new(lamp.name, lamp)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = centre + Vector(direction) * DATA["distance"]
    obj.rotation_euler = Vector(direction).to_track_quat("Z", "Y").to_euler()
world = bpy.context.scene.world or bpy.data.worlds.new("Fractalchemy world")
bpy.context.scene.world = world
world.use_nodes = True
background = world.node_tree.nodes.get("Background")
if background is not None:
    background.inputs["Color"].default_value = (DATA["background"][0], DATA["background"][1], DATA["background"][2], 1.0)
    background.inputs["Strength"].default_value = DATA["ambient"]
bpy.context.scene.render.film_transparent = DATA["transparent"]
print("Fractalchemy: placed", sum(len(e["positions"]) for e in DATA["instancers"]), "instances")
'''


def quaternion_to_euler_xyz(q: np.ndarray) -> np.ndarray:
    """`(N, 3)` XYZ Euler angles (radians, Blender's default order) of `(N, 4)` quaternions `(x, y, z, w)`."""
    x, y, z, w = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
    # rotation matrix entries
    r00 = 1 - 2 * (y * y + z * z)
    r12 = 2 * (y * z - x * w)
    r22 = 1 - 2 * (x * x + y * y)
    r10 = 2 * (x * y + z * w)
    r11 = 1 - 2 * (x * x + z * z)
    r20 = 2 * (x * z - y * w)
    r21 = 2 * (y * z + x * w)
    # XYZ order: R = Rz · Ry · Rx (Blender applies X first)
    ey = np.arcsin(np.clip(-r20, -1.0, 1.0))
    ex = np.arctan2(r21, r22)
    ez = np.arctan2(r10, r00)
    gimbal = np.abs(np.cos(ey)) < 1e-6
    if gimbal.any():
        ex = np.where(gimbal, np.arctan2(-r12, r11), ex)
        ez = np.where(gimbal, 0.0, ez)
    return np.stack([ex, ey, ez], axis=1)


def write_blender_instances(scene: Scene3D, path: Path, instancers: list, mesh_centre, mesh_extent: float, name: str = "holon") -> list[Path]:
    """The instanced Blender scene: a `.py` plus `name_instances.json`. `instancers` is a list of
    `(label, asset file name, positions (N, 3), quaternions (N, 4) xyzw, scales (N,), colour (r, g, b) 0..1 or None, Material)`."""
    path = Path(path)
    flame = scene.fractal
    camera = flame.camera if flame is not None else Camera()
    m = np.array(camera.matrix(), dtype=np.float64)
    extent = max(float(mesh_extent), 1e-6)
    ppu = camera.scale * (2.0 ** camera.zoom)
    visible_width = max(camera.width, 1) / max(ppu, 1e-9)
    if camera.perspective > 0:
        distance = 1.0 / camera.perspective
        fov = 2.0 * math.atan(visible_width / 2.0 * camera.perspective)
    else:
        distance = extent * 3.0
        fov = math.radians(40.0)
    lights = []
    for light in scene.lights:
        d_world = light_direction(light.altitude, light.azimuth) @ m.T
        lights.append([[round(float(v), 6) for v in d_world], [round(c / 255.0, 4) for c in light.color], round(float(light.intensity) * 3.0, 4), bool(light.shadows)])
    env = scene.environment
    data = {
        "instancers": [{"name": label, "asset": asset_name, "positions": np.round(positions, 6).tolist(),
                        "rotations": np.round(quaternion_to_euler_xyz(quaternions), 6).tolist(), "scales": np.round(scales, 6).tolist(),
                        "color": None if color is None else [round(float(c), 4) for c in color],
                        "roughness": round(max(0.05, min(1.0, 1.0 - material.shininess / 200.0)), 3), "specular": round(min(1.0, material.specular), 3)}
                       for label, asset_name, positions, quaternions, scales, color, material in instancers],
        "centre": [round(float(v), 6) for v in np.asarray(mesh_centre, dtype=np.float64)],
        "right": [round(float(v), 6) for v in m[:, 0]], "up": [round(float(v), 6) for v in -m[:, 1]], "back": [round(float(v), 6) for v in m[:, 2]],
        "distance": round(distance, 6), "perspective": round(camera.perspective, 6), "fov": round(fov, 6), "visible_width": round(visible_width, 6),
        "lights": lights, "background": [round(c / 255.0, 4) for c in env.color], "ambient": round(env.ambient, 4), "transparent": not env.visible,
    }
    import json
    data_path = path.with_name(f"{path.stem.removesuffix('_blender')}_instances.json")
    data_path.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    path.write_text(INSTANCES_TEMPLATE.format(name=name, script_name=path.name, data_name=data_path.name), encoding="utf-8")
    return [path, data_path]


__all__ = ["blender_script", "write_blender_script", "write_blender_instances", "quaternion_to_euler_xyz", "TEMPLATE", "INSTANCES_TEMPLATE"]

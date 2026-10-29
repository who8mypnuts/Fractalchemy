"""The 3D Editor's scene model (Qt-free): the fractal rendered as a solid, materials, lights, environment."""

from .format import EXTENSION, FILE_FILTER, Scene3DFormatError, load_scene, save_scene, scene_from_text, scene_to_text
from .model import DistantLight, Environment, Material, Scene3D, SolidSettings, materials_for

__all__ = ["Scene3D", "Material", "DistantLight", "Environment", "SolidSettings", "materials_for", "EXTENSION", "FILE_FILTER",
           "Scene3DFormatError", "load_scene", "save_scene", "scene_from_text", "scene_to_text"]

"""The 3D Editor's document: a `Scene3D` with change signals and an undo history.

Every edit goes through a method here so the viewport and the panels learn of it through a signal, and so it
lands in the history. The history holds snapshots (`Scene3D.to_dict()`): a scene is small, and snapshots
make undo trivially correct across every kind of edit. Slider drags coalesce: an edit with the same
`merge_key` as the previous one does not add a step, so dragging a light around is one undo.

Signals are split by what changed, so the viewport can choose how much to redo: a camera move re-renders;
a material edit re-renders too (the materials are baked into the render); `fractal_changed` also refreshes
the material list (one per transform).
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PySide6.QtCore import QObject, Signal

from ...fractal.scene import Flame, XForm
from ...scene3d.model import DistantLight, Instancer, Material, MeshAsset, Scene3D, materials_for
from ...solid import holon

UNDO_LIMIT = 200
MAX_LIGHTS = 8


class Scene3DDocument(QObject):
    """The scene being edited (see the module docstring).

    Signals:
        scene_replaced(): A different scene altogether (new, opened, *Use main fractal*).
        scene_restored(): Undo / redo put an earlier state back (everything may have changed).
        fractal_changed(): The flame changed (transforms, palette, camera) — everything re-renders.
        camera_changed(): Only the 3D camera moved.
        materials_changed(): A material edit.
        lights_changed(): A light edit.
        environment_changed(): Background / ambient / exposure.
        solid_changed(): Renderer settings (display mode, AO, fog, smoothing).
        mesh_settings_changed(): The Mesh tab's settings.
        export_settings_changed(): The Export tab's settings.
        mesh_changed(): A mesh was generated (or dropped): `mesh_result` is new.
        assets_changed(): The asset list or an asset changed.
        instancers_changed(): The instancer list, an instancer or its own IFS changed.
        asset_failed(str): An asset's file could not be read (the message).
        modified_changed(bool): The dirty flag flipped.
        undo_changed(bool, bool): (can undo, can redo) after every history change.
        path_changed(object): The scene's file (`Path` or None) changed.
    """
    scene_replaced = Signal()
    scene_restored = Signal()
    fractal_changed = Signal()
    camera_changed = Signal()
    materials_changed = Signal()
    lights_changed = Signal()
    environment_changed = Signal()
    solid_changed = Signal()
    mesh_settings_changed = Signal()
    export_settings_changed = Signal()
    mesh_changed = Signal()
    assets_changed = Signal()
    instancers_changed = Signal()
    asset_failed = Signal(str)
    modified_changed = Signal(bool)
    undo_changed = Signal(bool, bool)
    path_changed = Signal(object)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.scene = Scene3D()
        self.path: Path | None = None
        self._modified = False
        self._undo: list[tuple[str, dict]] = []       # (label, snapshot before the edit)
        self._redo: list[tuple[str, dict]] = []
        self._last_merge_key: object = None
        self.mesh_result = None                        # solid.pipeline.MeshResult of the last *Generate mesh* (not in the history)
        self.voxel_stage = None                        # its capture, reused while the fractal and the capture settings stay
        self._mesh_cache: dict[tuple, object] = {}     # asset geometry by (kind, primitive, detail, path): survives undo / redo

    # --- state ------------------------------------------------------------------------------------------------
    @property
    def flame(self) -> Flame | None:
        """The flame rendered as a solid (None before anything is loaded)."""
        return self.scene.fractal

    @property
    def modified(self) -> bool:
        return self._modified

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    @property
    def undo_label(self) -> str:
        return self._undo[-1][0] if self._undo else ""

    @property
    def redo_label(self) -> str:
        return self._redo[-1][0] if self._redo else ""

    def _set_modified(self, modified: bool) -> None:
        if modified != self._modified:
            self._modified = modified
            self.modified_changed.emit(modified)

    # --- whole scene ------------------------------------------------------------------------------------------
    def replace(self, scene: Scene3D, path: Path | None = None, modified: bool = False) -> None:
        """Show `scene` (a new or opened one): the history is cleared."""
        self.scene = scene
        self._undo.clear()
        self._redo.clear()
        self._last_merge_key = None
        self.drop_mesh()
        self.ensure_asset_meshes()
        self._set_path(path)
        self._modified = modified
        self.modified_changed.emit(modified)
        self.undo_changed.emit(False, False)
        self.scene_replaced.emit()

    def _set_path(self, path: Path | None) -> None:
        if path != self.path:
            self.path = path
            self.path_changed.emit(path)

    def mark_saved(self, path: Path) -> None:
        """The scene was written to `path`."""
        self._set_path(path)
        self._set_modified(False)

    # --- history ----------------------------------------------------------------------------------------------
    def _record(self, label: str, merge_key: object = None) -> None:
        """Remember the scene before an edit. Consecutive edits sharing a `merge_key` make one step."""
        if merge_key is not None and merge_key == self._last_merge_key and self._undo:
            return
        self._undo.append((label, self.scene.to_dict()))
        del self._undo[:-UNDO_LIMIT]
        self._redo.clear()
        self._last_merge_key = merge_key
        self.undo_changed.emit(True, False)

    def end_merge(self) -> None:
        """The next edit starts a new undo step even if it carries the last merge key (a drag ended)."""
        self._last_merge_key = None

    def undo(self) -> None:
        if not self._undo:
            return
        label, snapshot = self._undo.pop()
        self._redo.append((label, self.scene.to_dict()))
        self._restore(snapshot)

    def redo(self) -> None:
        if not self._redo:
            return
        label, snapshot = self._redo.pop()
        self._undo.append((label, self.scene.to_dict()))
        self._restore(snapshot)

    def _restore(self, snapshot: dict) -> None:
        old_fractal = self.scene.fractal.to_dict() if self.scene.fractal is not None else None
        self.scene = Scene3D.from_dict(snapshot)
        if snapshot.get("fractal") != old_fractal:
            self.drop_mesh()                            # the mesh belonged to another fractal
        self.ensure_asset_meshes()
        self._last_merge_key = None
        self._set_modified(True)
        self.undo_changed.emit(self.can_undo, self.can_redo)
        self.scene_restored.emit()

    # --- the fractal --------------------------------------------------------------------------------------------
    def set_fractal(self, flame: Flame | None, label: str = "Use fractal", keep_camera: bool = False) -> None:
        """Render `flame` (copied); the materials list follows its transform count.

        Args:
            flame: The new fractal (None clears the scene).
            label: The undo step's name.
            keep_camera: Keep the 3D camera the user set here rather than the flame's own (*follow* re-pulls).
        """
        self._record(label)
        old = self.scene.fractal
        new = flame.copy() if flame is not None else None
        if new is not None and keep_camera and old is not None:
            for field in ("pitch", "yaw", "perspective", "zpos", "pitch_y"):
                setattr(new.camera, field, getattr(old.camera, field))
        self.scene.fractal = new
        self.scene.materials = materials_for(new, self.scene.materials)
        self.drop_mesh()                                # the mesh belonged to the old fractal
        if new is not None and (self.scene.name in ("scene", "") or (old is not None and self.scene.name == old.name)):
            self.scene.name = new.name
        self._set_modified(True)
        self.fractal_changed.emit()
        self.materials_changed.emit()

    def set_camera(self, merge_key: object = "camera", **fields) -> None:
        """Move the 3D camera: any of pitch / yaw / perspective / zpos / pitch_y / zoom / center (flame camera fields)."""
        flame = self.scene.fractal
        if flame is None:
            return
        changes = {k: v for k, v in fields.items() if getattr(flame.camera, k) != v}
        if not changes:
            return
        self._record("Move camera", merge_key)
        for key, value in changes.items():
            setattr(flame.camera, key, value)
        self._set_modified(True)
        self.camera_changed.emit()

    # --- materials / lights / environment / renderer --------------------------------------------------------------
    def update_material(self, index: int, merge_key: object = None, **fields) -> None:
        """Change fields of material `index` (it is created if the list is shorter)."""
        mats = self.scene.materials
        if not 0 <= index < max(len(mats), 1):
            return
        while len(mats) <= index:
            mats.append(mats[-1].copy() if mats else Material())
        if all(getattr(mats[index], k) == v for k, v in fields.items()):
            return
        self._record("Edit material", merge_key)
        for key, value in fields.items():
            setattr(mats[index], key, value)
        self._set_modified(True)
        self.materials_changed.emit()

    def copy_material_to_all(self, index: int) -> None:
        """Every transform gets material `index`."""
        mats = self.scene.materials
        if not 0 <= index < len(mats):
            return
        self._record("Copy material to all")
        source = mats[index]
        self.scene.materials = [source.copy() for _ in mats]
        self._set_modified(True)
        self.materials_changed.emit()

    def update_light(self, index: int, merge_key: object = None, **fields) -> None:
        lights = self.scene.lights
        if not 0 <= index < len(lights):
            return
        if all(getattr(lights[index], k) == v for k, v in fields.items()):
            return
        self._record("Edit light", merge_key)
        for key, value in fields.items():
            setattr(lights[index], key, value)
        self._set_modified(True)
        self.lights_changed.emit()

    def add_light(self, light: DistantLight | None = None) -> int:
        """Append a light (a copy of `light`, or a default one); returns its index, or −1 when the limit is reached."""
        if len(self.scene.lights) >= MAX_LIGHTS:
            return -1
        self._record("Add light")
        self.scene.lights.append(light.copy() if light is not None else DistantLight())
        self._set_modified(True)
        self.lights_changed.emit()
        return len(self.scene.lights) - 1

    def remove_light(self, index: int) -> None:
        if not 0 <= index < len(self.scene.lights):
            return
        self._record("Remove light")
        del self.scene.lights[index]
        self._set_modified(True)
        self.lights_changed.emit()

    def add_key_lights(self, count: int = 2) -> int:
        """Add the HDRI's brightest regions as distant lights placed relative to the current camera (the first casts
        shadows, the others fill). Returns how many were added (0 without an HDRI)."""
        from ...solid import hdri
        env_map = hdri.environment_for(self.scene.environment)
        flame = self.scene.fractal
        if env_map is None or flame is None:
            return 0
        found = env_map.key_lights(count)
        if not found:
            return 0
        self._record("Extract key lights")
        m = np.array(flame.camera.matrix(), dtype=np.float64)
        turn = hdri.rotation_about_z(self.scene.environment.hdri_rotation).T     # a map feature at L sits at world L · Rᵀ
        added = 0
        for index, (direction, color, relative) in enumerate(found):
            if len(self.scene.lights) >= MAX_LIGHTS:
                break
            view = (np.asarray(direction) @ turn) @ m                              # world → view space
            altitude = math.degrees(math.asin(max(-1.0, min(1.0, float(view[2])))))
            azimuth = math.degrees(math.atan2(-float(view[1]), float(view[0])))
            self.scene.lights.append(DistantLight(altitude, azimuth, tuple(int(round(c * 255)) for c in color),
                                                  round(max(0.05, relative) * self.scene.environment.hdri_strength, 3),
                                                  shadows=index == 0, shadow_intensity=0.7, shadow_softness=2.0))
            added += 1
        self._set_modified(True)
        self.lights_changed.emit()
        return added

    def update_environment(self, merge_key: object = None, **fields) -> None:
        env = self.scene.environment
        if all(getattr(env, k) == v for k, v in fields.items()):
            return
        self._record("Edit environment", merge_key)
        for key, value in fields.items():
            setattr(env, key, value)
        self._set_modified(True)
        self.environment_changed.emit()

    def update_solid(self, merge_key: object = None, **fields) -> None:
        solid = self.scene.solid
        if all(getattr(solid, k) == v for k, v in fields.items()):
            return
        self._record("Render settings", merge_key)
        for key, value in fields.items():
            setattr(solid, key, value)
        self._set_modified(True)
        self.solid_changed.emit()

    def update_mesh_settings(self, merge_key: object = None, **fields) -> None:
        mesh = self.scene.mesh
        if all(getattr(mesh, k) == v for k, v in fields.items()):
            return
        self._record("Mesh settings", merge_key)
        for key, value in fields.items():
            setattr(mesh, key, value)
        self._set_modified(True)
        self.mesh_settings_changed.emit()

    def update_export_settings(self, **fields) -> None:
        """Export options (not an undo step: they describe where files go, not the scene)."""
        export = self.scene.export
        if all(getattr(export, k) == v for k, v in fields.items()):
            return
        for key, value in fields.items():
            setattr(export, key, value)
        self._set_modified(True)
        self.export_settings_changed.emit()

    def set_mesh_result(self, result, stage) -> None:
        """A generated mesh (and the capture it came from) — kept beside the scene, outside the history."""
        self.mesh_result = result
        self.voxel_stage = stage
        self.mesh_changed.emit()

    def drop_mesh(self) -> None:
        """Forget the generated mesh (the fractal changed, or a new scene)."""
        if self.mesh_result is not None or self.voxel_stage is not None:
            self.mesh_result = None
            self.voxel_stage = None
            self.mesh_changed.emit()

    # --- assets and instancers (the Holon IFS) ----------------------------------------------------------------------------
    def ensure_asset_meshes(self) -> None:
        """Load the geometry of every asset that has none (primitives are built, files read; failures are reported)."""
        for asset in self.scene.assets:
            if asset.mesh is not None:
                continue
            key = (asset.kind, asset.primitive, asset.detail, asset.path)
            mesh = self._mesh_cache.get(key)
            if mesh is None:
                try:
                    if asset.kind == "primitive":
                        mesh = holon.primitive(asset.primitive, asset.detail)
                    else:
                        from ...solid.io import read_mesh
                        mesh = read_mesh(asset.path)
                except (OSError, ValueError) as exc:
                    self.asset_failed.emit(f"{asset.name}: {exc}")
                    continue
                self._mesh_cache[key] = mesh
            asset.mesh = mesh

    def unique_asset_name(self, base: str) -> str:
        names = {a.name for a in self.scene.assets}
        if base not in names:
            return base
        index = 2
        while f"{base} {index}" in names:
            index += 1
        return f"{base} {index}"

    def add_asset(self, asset: MeshAsset) -> int:
        """Add an asset (its name made unique, its geometry loaded); returns its index."""
        self._record("Add asset")
        asset.name = self.unique_asset_name(asset.name or "asset")
        self.scene.assets.append(asset)
        if asset.mesh is not None:
            self._mesh_cache[(asset.kind, asset.primitive, asset.detail, asset.path)] = asset.mesh
        self.ensure_asset_meshes()
        self._set_modified(True)
        self.assets_changed.emit()
        return len(self.scene.assets) - 1

    def remove_asset(self, index: int) -> None:
        """Remove an asset; instancers using it lose their asset."""
        if not 0 <= index < len(self.scene.assets):
            return
        self._record("Remove asset")
        name = self.scene.assets[index].name
        del self.scene.assets[index]
        for inst in self.scene.instancers:
            if inst.asset == name:
                inst.asset = ""
        self._set_modified(True)
        self.assets_changed.emit()
        self.instancers_changed.emit()

    def update_asset(self, index: int, merge_key: object = None, **fields) -> None:
        if not 0 <= index < len(self.scene.assets):
            return
        asset = self.scene.assets[index]
        if all(getattr(asset, k) == v for k, v in fields.items()):
            return
        self._record("Edit asset", merge_key)
        old_name = asset.name
        for key, value in fields.items():
            setattr(asset, key, value)
        if "name" in fields and asset.name != old_name:
            asset.name = self.unique_asset_name(asset.name)
            for inst in self.scene.instancers:
                if inst.asset == old_name:
                    inst.asset = asset.name
        if {"primitive", "detail", "path", "kind"} & set(fields):
            asset.mesh = None
            self.ensure_asset_meshes()
        self._set_modified(True)
        self.assets_changed.emit()
        self.instancers_changed.emit()

    def add_instancer(self, instancer: Instancer | None = None) -> int:
        """Append an instancer (a default one on the first asset when None); returns its index."""
        self._record("Add instancer")
        if instancer is None:
            instancer = Instancer(asset=self.scene.assets[0].name if self.scene.assets else "")
        names = {i.name for i in self.scene.instancers}
        base = instancer.name or "instancer"
        name, index = base, 2
        while name in names:
            name, index = f"{base} {index}", index + 1
        instancer.name = name
        self.scene.instancers.append(instancer)
        self._set_modified(True)
        self.instancers_changed.emit()
        return len(self.scene.instancers) - 1

    def remove_instancer(self, index: int) -> None:
        if not 0 <= index < len(self.scene.instancers):
            return
        self._record("Remove instancer")
        del self.scene.instancers[index]
        self._set_modified(True)
        self.instancers_changed.emit()

    def update_instancer(self, index: int, merge_key: object = None, **fields) -> None:
        if not 0 <= index < len(self.scene.instancers):
            return
        inst = self.scene.instancers[index]
        if all(getattr(inst, k) == v for k, v in fields.items()):
            return
        self._record("Edit instancer", merge_key)
        for key, value in fields.items():
            setattr(inst, key, value)
        if inst.source == "own" and inst.flame is None:
            inst.flame = holon.default_own_ifs()
        self._set_modified(True)
        self.instancers_changed.emit()

    def update_instancer_material(self, index: int, merge_key: object = None, **fields) -> None:
        if not 0 <= index < len(self.scene.instancers):
            return
        material = self.scene.instancers[index].material
        if all(getattr(material, k) == v for k, v in fields.items()):
            return
        self._record("Edit instancer material", merge_key)
        for key, value in fields.items():
            setattr(material, key, value)
        self._set_modified(True)
        self.instancers_changed.emit()

    def set_own_ifs(self, index: int, flame: Flame | None, label: str = "Own IFS") -> None:
        """Give instancer `index` its own fractal (None: the starter IFS)."""
        if not 0 <= index < len(self.scene.instancers):
            return
        self._record(label)
        inst = self.scene.instancers[index]
        inst.flame = flame.copy() if flame is not None else holon.default_own_ifs()
        inst.source = "own"
        self._set_modified(True)
        self.instancers_changed.emit()

    def set_own_xform(self, index: int, xform_index: int, xform: XForm | None, merge_key: object = None) -> None:
        """Replace (or append when `xform_index` is past the end, or remove when `xform` is None) a transform of an own IFS."""
        if not 0 <= index < len(self.scene.instancers):
            return
        inst = self.scene.instancers[index]
        if inst.flame is None:
            inst.flame = holon.default_own_ifs()
        xforms = inst.flame.xforms
        if xform is None:
            if not 0 <= xform_index < len(xforms) or len(xforms) <= 1:
                return
            self._record("Remove transform")
            del xforms[xform_index]
        elif 0 <= xform_index < len(xforms):
            self._record("Edit transform", merge_key)
            xforms[xform_index] = xform
        else:
            self._record("Add transform")
            xforms.append(xform)
        self._set_modified(True)
        self.instancers_changed.emit()

    def set_follow(self, follow: bool) -> None:
        """The *follow the main window* flag (not an undo step)."""
        if self.scene.follow_main != follow:
            self.scene.follow_main = follow
            self._set_modified(True)


__all__ = ["Scene3DDocument", "UNDO_LIMIT", "MAX_LIGHTS"]

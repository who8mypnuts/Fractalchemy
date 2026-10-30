"""The Holon IFS: frames along the orbit, chaos and tree instancing, primitives, the 3D-affine transform representation,
instances in both renderers, the instanced exports and the Instances tab."""

import numpy as np
import pytest

from fractalchemy.render.compiled import CompiledXForm
from fractalchemy.render.cpu_engine import CpuEngine
from fractalchemy.render.gpu_engine import gpu_available
from fractalchemy.render.settings import RenderSettings
from fractalchemy.scene3d import format as fa3d
from fractalchemy.scene3d.model import ExportSettings, Instancer, Material, MeshAsset, Scene3D
from fractalchemy.solid import holon as H
from fractalchemy.solid import pipeline
from fractalchemy.solid.io import read_mesh
from fractalchemy.solid.io.blender import quaternion_to_euler_xyz
from fractalchemy.solid.io.gltf import read_gltf_instances
from fractalchemy.solid.io.usd import read_usd_instances, usd_core_available
from tests.conftest import spin, wait_until

needs_gl = pytest.mark.skipif(not gpu_available()[0], reason=f"no OpenGL: {gpu_available()[1]}")


def holon_scene(show_fractal: bool = False) -> Scene3D:
    flame = H.default_own_ifs()
    scene = Scene3D("holon", flame)
    scene.assets.append(MeshAsset("ball", "primitive", "sphere", 1, mesh=H.primitive("sphere", 1)))
    scene.instancers.append(Instancer("balls", "ball", "main", None, "tree", depth=3, tree_levels="all", size=0.5, color_mode="palette"))
    scene.solid.show_fractal = show_fractal
    return scene


# --- frames ---------------------------------------------------------------------------------------------------------------
def test_affine3d_transform_round_trips_and_its_jacobian_is_the_rotation_times_the_scale():
    xform = H.affine3d_xform((0.3, -0.2, 0.5), (20, -35, 60), 0.4, 2.0, 0.3, "t")
    values = H.read_affine3d(xform)
    assert values["position"] == pytest.approx((0.3, -0.2, 0.5)) and values["rotation"] == pytest.approx((20, -35, 60))
    assert values["scale"] == pytest.approx(0.4) and values["weight"] == 2.0 and values["color"] == 0.3
    compiled = CompiledXForm.build(xform)
    x, y, z, _c, jac = H.apply_with_jacobian(compiled, np.array([0.1]), np.array([0.2]), np.array([0.3]), np.array([0.5]), np.random.default_rng(0))
    rotation = H._rotation_matrix(20, -35, 60)
    assert np.allclose(jac[0], rotation * 0.4, atol=1e-6)
    assert np.allclose([x[0], y[0], z[0]], rotation @ (0.4 * np.array([0.1, 0.2, 0.3])) + np.array([0.3, -0.2, 0.5]), atol=1e-9)
    rot, scale = H.polar_decompose(jac)
    assert np.allclose(rot[0], rotation, atol=1e-6) and scale[0] == pytest.approx(0.4)
    assert np.allclose(np.linalg.det(rot), 1.0)
    q = H.rotation_to_quaternion(rot)
    assert np.linalg.norm(q, axis=1) == pytest.approx(1.0)
    euler = quaternion_to_euler_xyz(q)[0]
    cx, sx, cy, sy, cz, sz = np.cos(euler[0]), np.sin(euler[0]), np.cos(euler[1]), np.sin(euler[1]), np.cos(euler[2]), np.sin(euler[2])
    rebuilt = (np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]) @ np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
               @ np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]]))
    assert np.allclose(rebuilt, rotation, atol=1e-9)
    # a flame transform that is not a plain affine map is reported as such
    other = H.affine3d_xform()
    other.variations["spherical"] = 1.0
    assert H.read_affine3d(other) is None
    # a reflection is still decomposed into a proper rotation
    rot, scale = H.polar_decompose(np.array([[[-1.0, 0, 0], [0, 1, 0], [0, 0, 1]]]))
    assert np.linalg.det(rot[0]) == pytest.approx(1.0) and scale[0] == pytest.approx(1.0)


def test_tree_and_chaos_instances_have_the_expected_counts_and_scales():
    flame = H.default_own_ifs()
    tree = H.tree_instances(flame, 4, "all")
    assert len(tree) == 4 + 16 + 64 + 256 and np.bincount(tree.level)[1:].tolist() == [4, 16, 64, 256]
    assert np.allclose(tree.scales[tree.level == 3], 0.125)
    leaves = H.tree_instances(flame, 3, "leaves")
    assert len(leaves) == 64 and (leaves.level == 3).all()
    capped = H.tree_instances(flame, 6, "leaves", cap=500)
    assert len(capped) == 500
    chaos = H.chaos_instances(flame, 3000, depth=5, seed=2)
    assert len(chaos) == 3000 and np.allclose(chaos.scales, 0.5 ** 5, atol=1e-6) and chaos.colors.dtype == np.uint8
    again = H.chaos_instances(flame, 3000, depth=5, seed=2)
    assert np.array_equal(chaos.positions, again.positions)
    upright = H.chaos_instances(flame, 200, depth=3, frame_mode="translation")
    assert np.allclose(upright.rotations, np.eye(3))
    sized = chaos.sized(0.2, 1.0, 0.004, 1000)
    assert len(sized) == 1000 and sized.scales.max() == pytest.approx(0.2 * 0.5 ** 5)
    assert len(chaos.sized(1.0, 1.0, 0.5)) == 0                   # everything smaller than the minimum
    assert chaos.transforms(2.0).shape == (3000, 4, 4) and chaos.quaternions().shape == (3000, 4)
    assert H.chaos_instances(flame, 100, cancelled=lambda: True) is None
    assert H.tree_instances(flame, 3, cancelled=lambda: True) is None
    inst = Instancer("i", "a", mode="tree", depth=2, size=0.3, max_instances=10)
    assert len(H.instances_for(flame, inst)) == 10
    assert len(H.cached_instances(flame, inst)) == 10 and H._instancer_key(flame, inst) == H._instancer_key(flame.copy(), inst)


def test_primitives_are_watertight_unit_sized_and_the_default_ifs_is_editable():
    for kind in H.PRIMITIVES:
        mesh = H.primitive(kind, 1)
        rep = mesh.report()
        assert rep.watertight and rep.consistent and mesh.signed_volume() > 0, kind
        assert mesh.extent().max() == pytest.approx(1.0) and np.allclose(mesh.bounds()[0] + mesh.bounds()[1], 0, atol=1e-9), kind
    assert H.primitive("sphere", 3).face_count == 20 * 4 ** 3
    with pytest.raises(ValueError):
        H.primitive("teapot")
    flame = H.default_own_ifs()
    assert len(flame.xforms) == 4 and all(H.read_affine3d(x) is not None for x in flame.xforms) and flame.renderable()


def test_instance_points_bake_and_colours():
    mesh = H.primitive("cube", 0)
    instances = H.tree_instances(H.default_own_ifs(), 2, "all").sized(0.5)
    points, normals, nearest, instance_of = H.instance_points(mesh, instances, 20_000)
    assert points.shape == normals.shape and points.shape[0] >= 20_000 * 0.9 and instance_of.max() == len(instances) - 1
    assert np.allclose(np.linalg.norm(normals, axis=1), 1.0, atol=1e-6)
    # every sample lies inside its instance's bounding sphere
    centres = instances.positions[instance_of]
    radii = instances.scales[instance_of] * np.sqrt(3) / 2
    assert (np.linalg.norm(points - centres, axis=1) <= radii + 1e-9).all()
    baked = H.bake_instances(mesh, instances)
    assert baked.face_count == mesh.face_count * len(instances) and baked.report().watertight and baked.report().components == len(instances)
    assert H.bake_instances(mesh, instances, max_faces=mesh.face_count * 3).face_count == mesh.face_count * 3
    palette = np.asarray(H.default_own_ifs().palette, dtype=np.uint8)
    assert H.instance_colors(instances, "palette", mesh, nearest, instance_of, palette).shape == (points.shape[0],)
    assert (H.instance_colors(instances, "fixed", mesh, nearest, instance_of, palette) == 0).all()
    scene = holon_scene()
    cloud = H.scene_instance_cloud(scene, 30_000)
    assert cloud is not None and cloud.count == 84 and cloud.material.min() == scene.instancer_material_index(0)
    scene.instancers[0].visible = False
    assert H.scene_instance_cloud(scene) is None


# --- renderers -------------------------------------------------------------------------------------------------------------
def test_cpu_solid_render_draws_the_instances_with_and_without_the_fractal():
    scene = holon_scene(show_fractal=False)
    scene.instancers[0].color_mode = "fixed"
    scene.instancers[0].material = Material(color=(255, 40, 40))
    settings = RenderSettings(96, 72, passes=1, quality=6, points=4096, fuse=10, oversample=1).with_solid(scene)
    job = CpuEngine(threads=1).start(scene.fractal, settings)
    image = job.run_pass()
    assert job.instances is not None and job.instances.count == 84 and "84 instances" in job.stats.notes
    assert job.stats.finished and job.gbuffer.normal is not None
    hit = job.gbuffer.hits
    assert hit.mean() > 0.02
    red = image[..., 0].astype(int) - image[..., 1].astype(int)
    assert red.max() > 60                                  # the fixed red shows
    job.close()
    scene.solid.show_fractal = True
    job = CpuEngine(threads=1).start(scene.fractal, settings)
    job.run_pass()
    assert job.gbuffer.hits.sum() > hit.sum()            # the fractal's points join the instances
    job.close()
    # the render material table: transforms first, then the instancers
    mats = scene.render_materials()
    assert len(mats) == 5 and mats[4].color == (255, 40, 40) and mats[4].color_mode == "fixed"


@needs_gl
def test_gpu_solid_render_agrees_with_the_cpu_on_an_instanced_scene():
    from fractalchemy.render.gpu_engine import GpuEngine
    scene = holon_scene(show_fractal=False)
    scene.instancers[0].color_mode = "fixed"
    scene.instancers[0].material = Material(color=(200, 200, 60))
    scene.solid.ao = False
    settings = RenderSettings(96, 72, passes=1, quality=6, points=4096, fuse=10, oversample=1).with_solid(scene)
    engine = GpuEngine()
    gpu_job = engine.start(scene.fractal, settings)
    gpu = gpu_job.run_pass().astype(float)
    assert "84 instances" in gpu_job.stats.notes and gpu_job.instance_vbo is not None
    gpu_job.close()
    engine.close()
    cpu_job = CpuEngine(threads=1).start(scene.fractal, settings)
    cpu = cpu_job.run_pass().astype(float)
    cpu_job.close()
    gpu_hits = gpu[..., :3].sum(axis=2) != cpu[0, 0, :3].sum()
    cpu_hits = cpu[..., :3].sum(axis=2) != cpu[0, 0, :3].sum()
    overlap = (gpu_hits & cpu_hits).sum() / max(1, (gpu_hits | cpu_hits).sum())
    assert overlap > 0.5 and abs(gpu[..., :3].mean() - cpu[..., :3].mean()) < 8   # the CPU closes pin-holes, so its coverage is a little larger


# --- exports -----------------------------------------------------------------------------------------------------------
def test_instanced_exports_round_trip_and_bake(tmp_path):
    scene = holon_scene()
    scene.instancers.append(Instancer("red", "ball", "main", None, "chaos", count=40, depth=3, size=0.3, color_mode="fixed",
                                      material=Material(color=(255, 0, 0))))
    settings = ExportSettings(subject="instances", formats=["glb", "usda", "stl"], units="mm", size_mm=80.0)
    outcome = pipeline.export_instances(scene, settings, tmp_path / "inst", "h", progress=lambda f, m: None)
    names = sorted(p.name for p in outcome.files)
    assert names == ["h.glb", "h.stl", "h.usda", "h_asset_balls.glb", "h_asset_red.glb", "h_blender.py", "h_instances.json"]
    assert any("cannot carry instances" in n for n in outcome.notes) and outcome.report.exists()
    glb = read_gltf_instances(tmp_path / "inst" / "h.glb")
    assert [len(g[0]) for g in glb] == [84, 40] and glb[0][3] == 80
    if usd_core_available():
        usd = read_usd_instances(tmp_path / "inst" / "h.usda")
        assert [len(u[0]) for u in usd] == [84, 40]
        assert np.allclose(usd[0][0], glb[0][0], atol=1e-3)
    baked_stl = read_mesh(tmp_path / "inst" / "h.stl")
    assert baked_stl.extent().max() == pytest.approx(80.0, rel=0.02) and baked_stl.face_count == 80 * 124
    compile((tmp_path / "inst" / "h_blender.py").read_text(), "h_blender.py", "exec")
    import json
    data = json.loads((tmp_path / "inst" / "h_instances.json").read_text())
    assert [len(e["positions"]) for e in data["instancers"]] == [84, 40] and data["instancers"][1]["color"] == [1.0, 0.0, 0.0]
    report = outcome.report.read_text()
    assert "124 instances" in report and "| balls |" in report
    baked = pipeline.export_instances(scene, ExportSettings(subject="baked", formats=["ply"], blender=False), tmp_path / "baked", "b")
    mesh = read_mesh(baked.files[0])
    assert mesh.face_count == 80 * 124 and mesh.colors is not None and mesh.colors.max() > 0.9
    with pytest.raises(ValueError):
        pipeline.export_instances(Scene3D("empty", H.default_own_ifs()), settings, tmp_path, "x")


def test_assets_and_instancers_live_in_the_scene_file():
    scene = holon_scene()
    scene.instancers[0].source = "own"
    scene.instancers[0].flame = H.default_own_ifs()
    copy = fa3d.scene_from_text(fa3d.scene_to_text(scene))
    assert copy.assets[0].name == "ball" and copy.assets[0].mesh is None and copy.assets[0].primitive == "sphere"
    assert copy.instancers[0].flame is not None and len(copy.instancers[0].flame.xforms) == 4 and copy.instancers[0].asset == "ball"
    assert copy.solid.show_fractal is False and copy.instancers[0].material.color == (200, 200, 200)
    assert copy.visible_instancers() == []                  # no geometry loaded yet
    assert copy.copy().instancers[0].flame is not copy.instancers[0].flame


# --- the window -----------------------------------------------------------------------------------------------------------
@pytest.fixture
def main(main_window_factory):
    win = main_window_factory(cheap_renders=True)
    yield win
    if win._three_d is not None:
        win._three_d.wait_for_jobs()
        win._three_d.document._modified = False


def test_instances_tab_builds_a_holon_scene_and_exports_it(main, tmp_path):
    flame = H.default_own_ifs()
    main.show_flame(flame)
    main.actionThreeDEditor.trigger()
    editor = main.three_d_editor
    editor.resize(900, 600)
    editor.viewport.set_quality("Draft")
    wait_until(lambda: editor.isVisible())
    panel = editor.instances_panel
    doc = editor.document
    editor.tabs.setCurrentWidget(panel)
    assert editor.tabs.tabText(6) == "Instances" and not panel.own_group.isVisibleTo(panel) and panel.asset_list.count() == 0
    # assets: a primitive, an imported file, and the name is kept unique
    panel._add_primitive("torus")
    assert [a.name for a in doc.scene.assets] == ["torus"] and doc.scene.assets[0].mesh is not None and doc.undo_label == "Add asset"
    from fractalchemy.solid.io import write_mesh
    write_mesh(H.primitive("cube", 0), tmp_path / "box.ply", "ply")
    assert panel.import_mesh(tmp_path / "box.ply") and doc.scene.assets[1].kind == "file" and doc.scene.assets[1].mesh.face_count == 12
    assert not panel.import_mesh(tmp_path / "missing.ply")
    panel.asset_list.setCurrentRow(0)
    panel.asset_detail.setValue(1)
    assert doc.scene.assets[0].detail == 1 and doc.scene.assets[0].mesh.face_count == H.primitive("torus", 1).face_count
    # an instancer on the torus, tree mode, fixed colour, without the fractal
    panel._add_instancer()
    assert len(doc.scene.instancers) == 1 and panel.current_instancer().asset == "torus"
    panel.mode_box.setCurrentIndex(1)
    panel.depth.setValue(2)
    panel.color_box.setCurrentIndex(2)
    panel.show_fractal_check.setChecked(False)
    inst = doc.scene.instancers[0]
    assert inst.mode == "tree" and inst.depth == 2 and inst.color_mode == "fixed" and not doc.scene.solid.show_fractal
    assert len(doc.scene.visible_instancers()) == 1
    wait_until(lambda: editor.viewport.up_to_date, timeout_ms=120000)
    assert "20 instances" in editor.viewport.stats.notes and editor.viewport.image is not None
    # an own IFS edited through the table, sent to the main window
    panel.source_box.setCurrentIndex(1)
    assert inst.source == "own" and inst.flame is not None and panel.own_group.isVisibleTo(panel) and panel.table.rowCount() == 4
    panel.table.item(0, 7).setText("0.6")
    assert H.read_affine3d(inst.flame.xforms[0])["scale"] == pytest.approx(0.6) and doc.undo_label == "Edit transform"
    panel.table.item(1, 2).setText("0.25")
    assert H.read_affine3d(inst.flame.xforms[1])["position"][1] == pytest.approx(0.25)
    panel.add_xform_button.click()
    assert len(inst.flame.xforms) == 5 and panel.table.rowCount() == 5
    panel.table.setCurrentCell(4, 0)
    panel.remove_xform_button.click()
    assert len(inst.flame.xforms) == 4
    sent = []
    editor.flame_sent.connect(sent.append)
    panel.send_button.click()
    assert sent and len(sent[0].xforms) == 4 and sent[0] is not inst.flame
    doc.undo()
    assert len(doc.scene.instancers[0].flame.xforms) == 5 and doc.scene.assets[0].mesh is not None   # meshes survive undo
    doc.redo()
    # the Mesh tab's clean mesh as an asset
    doc.update_mesh_settings(None, points=30_000, resolution=24, target_faces=500, clean="aggressive")
    editor.mesh_panel.generate_button.click()
    wait_until(lambda: not editor.meshing, timeout_ms=120000)
    assert panel.asset_from_clean_mesh(tmp_path / "assets")
    assert doc.scene.assets[-1].kind == "fractal" and (tmp_path / "assets").exists() and doc.scene.assets[-1].mesh is not None
    # export the instances
    doc.update_export_settings(subject="instances", formats=["glb"], folder=str(tmp_path / "exp"), name="holon", blender=True)
    spin(50)
    assert editor.export_panel.subject_instances.isChecked() and editor.export_panel.export_button.isEnabled()
    editor.export_panel.export_button.click()
    wait_until(lambda: not editor.exporting, timeout_ms=120000)
    names = sorted(p.name for p in (tmp_path / "exp").iterdir())
    assert "holon.glb" in names and "holon_blender.py" in names and "holon_instances.json" in names
    assert len(read_gltf_instances(tmp_path / "exp" / "holon.glb")[0][0]) == 20
    # removing the asset detaches the instancer
    panel.asset_list.setCurrentRow(0)
    panel.remove_asset_button.click()
    assert doc.scene.instancers[0].asset == "" and doc.scene.visible_instancers() == []
    assert not editor.export_panel.export_button.isEnabled()

"""Meshing and export: capture, voxels, the isosurface, mesh operations, file formats, the pipeline and the Mesh / Export tabs."""

import numpy as np
import pytest

from fractalchemy.scene3d import format as fa3d
from fractalchemy.scene3d.model import ExportSettings, MeshSettings, Scene3D
from fractalchemy.solid import pipeline
from fractalchemy.solid.capture import PointCloud, capture_points
from fractalchemy.solid.io import EXPORT_FORMATS, export_format, read_mesh, write_mesh
from fractalchemy.solid.io.blender import blender_script
from fractalchemy.solid.io.usd import usda_text
from fractalchemy.solid.isosurface import resolve_ambiguities, surface_nets
from fractalchemy.solid.mesh import AGGRESSIVE_CLEAN, CleanSettings, Mesh, clean, quadric_decimate, remesh, thin_wall_estimate
from fractalchemy.solid.mesh_preview import fallback_palette, nearest_palette_index, render_mesh, sample_surface
from fractalchemy.solid.uv import bake_vertex_colors, box_uvs, cylindrical_uvs, spherical_uvs, with_uvs
from fractalchemy.solid.voxelize import dilate, erode, grid_bounds, log_histogram, smooth, suggest_threshold, voxelize
from tests.conftest import wait_until
from tests.test_solid import tetrahedron


# --- fixtures -------------------------------------------------------------------------------------------------------
def shell_cloud(n: int = 60_000, radius: float = 0.9, seed: int = 0) -> PointCloud:
    """Points on a sphere of `radius` with a hue ramp palette."""
    rng = np.random.default_rng(seed)
    v = rng.normal(size=(n, 3))
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    palette = np.stack([np.linspace(0, 1, 256), np.linspace(1, 0, 256), np.full(256, 0.5)], axis=1).astype(np.float32)
    return PointCloud((v * radius).astype(np.float32), (rng.random(n) * 255).astype(np.uint8), np.zeros(n, np.int16), palette)


def sphere_mesh(resolution: int = 40) -> Mesh:
    grid = smooth(voxelize(shell_cloud(), resolution), 1.0)
    normalized, _scale = grid.normalized()
    return surface_nets(grid, 0.2, normalized)


def tetra_mesh() -> Mesh:
    v = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float)
    return Mesh(v, np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]]))


# --- capture and voxels -----------------------------------------------------------------------------------------------
def test_capture_is_deterministic_and_keeps_world_points_with_colours():
    a = capture_points(tetrahedron(), 20_000, seed=3, threads=2)
    b = capture_points(tetrahedron(), 20_000, seed=3, threads=2)
    assert len(a) >= 20_000 and a.xyz.shape == (len(a), 3) and a.color.dtype == np.uint8 and a.xform.max() == 3
    assert np.array_equal(a.xyz, b.xyz) and np.array_equal(a.color, b.color)
    assert a.xyz.min() >= -0.01 and a.xyz[:, 2].max() <= 0.81 and a.rgb.shape == (len(a), 3)
    assert capture_points(tetrahedron(), 5000, cancelled=lambda: True) is None
    with pytest.raises(ValueError):
        flame = tetrahedron()
        for x in flame.xforms:
            x.weight = 0
        capture_points(flame, 100)


def test_voxelize_counts_points_and_filters_keep_mass_roughly():
    cloud = shell_cloud(20_000)
    lo, hi = grid_bounds(cloud.xyz)
    assert (lo < -0.85).all() and (hi > 0.85).all()
    grid = voxelize(cloud, 32)
    assert grid.shape == (34, 34, 34) and grid.density.sum() == pytest.approx(20_000, abs=60)   # a few trimmed by the percentile box
    assert grid.color.shape == (34, 34, 34, 3) and grid.mean_color().max() <= 1.0
    assert grid.density[0].sum() == 0 and grid.density[:, 0].sum() == 0                        # the padding stays empty
    blurred = smooth(grid, 1.0)
    assert blurred.density.sum() == pytest.approx(grid.density.sum(), rel=0.02) and blurred.occupied > grid.occupied
    assert dilate(grid, 1).occupied > grid.occupied and erode(grid, 1).occupied < grid.occupied
    normalized, scale = grid.normalized()
    assert scale > 0 and normalized.max() >= 1.0
    edges, counts = log_histogram(normalized)
    assert edges.shape == (65,) and counts.sum() == grid.occupied and edges[0] < edges[-1]
    assert 0.02 <= suggest_threshold(normalized) <= 0.5
    with pytest.raises(ValueError):
        voxelize(cloud, 4)
    assert voxelize(cloud, 16, with_color=False).color is None


# --- the isosurface -------------------------------------------------------------------------------------------------
def test_surface_nets_makes_a_watertight_oriented_shell_with_the_right_area():
    mesh = sphere_mesh(40)
    rep = mesh.report()
    assert rep.faces > 2000 and rep.watertight and rep.consistent and rep.nonmanifold_edges == 0
    assert rep.components == 2                                  # a shell has an outer and an inner surface
    assert rep.area == pytest.approx(2 * 4 * np.pi * 0.9 ** 2, rel=0.25)
    assert mesh.colors is not None and mesh.colors.shape == (mesh.vertex_count, 3) and mesh.normals is not None
    outer = mesh.keep_components(largest=1)[0]
    assert outer.signed_volume() > 0 and outer.signed_volume() == pytest.approx(4 / 3 * np.pi * 0.95 ** 3, rel=0.3)
    # nothing above the level: an empty mesh
    grid = voxelize(shell_cloud(5000), 16)
    assert surface_nets(grid, 1e9).face_count == 0


def test_ambiguous_voxel_faces_are_filled_so_edges_stay_manifold():
    inside = np.zeros((5, 5, 5), dtype=bool)
    inside[1, 1, 1] = inside[2, 2, 1] = True                 # two voxels touching along an edge: the diagonal pattern
    fixed = resolve_ambiguities(inside)
    assert fixed[1, 2, 1] and fixed[2, 1, 1] and fixed.sum() == 4
    assert not fixed[0].any() and not fixed[-1].any()
    grid_density = inside.astype(np.float32)
    from fractalchemy.solid.voxelize import VoxelGrid
    grid = VoxelGrid(grid_density, None, np.zeros(3), 1.0)
    mesh = surface_nets(grid, 0.5)
    assert mesh.report().nonmanifold_edges == 0 and mesh.report().watertight


# --- mesh operations ------------------------------------------------------------------------------------------------
def test_mesh_basics_weld_degenerate_components_and_orientation():
    t = tetra_mesh()
    assert t.signed_volume() == pytest.approx(1 / 6) and t.is_consistently_oriented() and t.report().watertight
    assert t.flipped().signed_volume() == pytest.approx(-1 / 6)
    # a duplicate vertex and a degenerate face
    v = np.vstack([t.vertices, t.vertices[3] + 1e-9])
    f = np.vstack([t.faces, [[0, 0, 1]], [[1, 2, 4]]])
    loose = Mesh(v, f)
    welded = loose.weld(1e-6)
    assert welded.vertex_count == 4 and welded.face_count == 4                 # the duplicate face folds onto an existing one
    # two pieces, keep the large one
    far = t.transformed(offset=(5, 5, 5))
    both = Mesh(np.vstack([t.vertices, far.vertices]), np.vstack([t.faces, far.faces + 4]))
    sub = both.subset(np.arange(4))
    assert sub.vertex_count == 4 and both.components()[0] == 2
    kept, dropped = both.keep_components(largest=1)
    assert dropped == 1 and kept.face_count == 4
    # scrambled winding, fixed
    scrambled = sphere_mesh(24).keep_components(largest=1)[0]
    flip = np.random.default_rng(1).random(scrambled.face_count) < 0.5
    scrambled.faces[flip] = scrambled.faces[flip][:, ::-1]
    assert not scrambled.is_consistently_oriented()
    fixed = scrambled.oriented()
    assert fixed.is_consistently_oriented() and fixed.signed_volume() > 0 and fixed.report().watertight
    assert t.scaled_to(10.0).extent().max() == pytest.approx(10.0)


def test_holes_fill_smoothing_keeps_volume_and_the_report_recommends():
    mesh = sphere_mesh(32).keep_components(largest=1)[0]
    holed = mesh.subset(np.arange(mesh.face_count) > 12)          # several small, touching holes
    assert holed.boundary_edges().shape[0] > 0 and not holed.report().watertight
    assert "open edges" in holed.report().recommendation()
    filled, count = holed.fill_holes(64)
    assert count >= 1 and filled.report().watertight and filled.is_consistently_oriented()
    smoothed = mesh.taubin_smoothed(10)
    assert smoothed.signed_volume() == pytest.approx(mesh.signed_volume(), rel=0.05) and smoothed.report().watertight
    rep = mesh.report()
    assert rep.printable and rep.recommendation().startswith("Ready to print") and rep.to_dict()["faces"] == mesh.face_count
    assert Mesh.empty().report().recommendation().startswith("The mesh is empty")


def test_quadric_decimation_hits_the_target_and_stays_watertight():
    mesh = sphere_mesh(40).keep_components(largest=1)[0]
    before = mesh.report()
    rounds = []
    small = quadric_decimate(mesh, 800, progress=lambda fraction, faces: rounds.append(faces))
    rep = small.report()
    assert small.face_count <= 820 and rep.watertight and rep.consistent and rep.components == 1
    assert rep.volume == pytest.approx(before.volume, rel=0.05) and len(rounds) >= 2
    assert small.colors is not None and small.colors.shape == (small.vertex_count, 3)
    assert mesh.decimated(mesh.face_count + 10) is mesh


def test_clean_pipeline_levels_and_remesh_and_thin_wall():
    mesh = sphere_mesh(32)
    out, rep = clean(mesh, CleanSettings(min_piece_faces=0, keep_largest=1, smooth_iterations=2, target_faces=1500))
    assert rep.components == 1 and rep.watertight and rep.faces <= 1520 and any("decimated" in n for n in rep.notes)
    out2, rep2 = clean(mesh, AGGRESSIVE_CLEAN)
    assert rep2.components == 1 and rep2.printable
    inside = np.zeros((12, 12, 12), dtype=bool)
    inside[2:10, 2:10, 2:10] = True
    inside[5, 5, 5] = False                                   # a cavity
    solid = remesh(inside, np.zeros(3), 1.0)
    assert solid[5, 5, 5] and solid.sum() == 8 ** 3
    slab = np.zeros((12, 12, 12), dtype=bool)
    slab[2:10, 2:10, 4:6] = True                                # two voxels thick
    assert thin_wall_estimate(slab, 0.5) == pytest.approx(2 * 0.5, rel=0.3)
    assert thin_wall_estimate(inside, 0.5) <= 0.5 * 8          # a lower bound: never more than the block itself


# --- UVs, textures, preview --------------------------------------------------------------------------------------------
def test_uv_projections_and_texture_bake():
    mesh = sphere_mesh(24).keep_components(largest=1)[0]
    boxed = box_uvs(mesh)
    assert boxed.vertex_count == 3 * boxed.face_count and boxed.uvs.shape == (boxed.vertex_count, 2)
    assert boxed.uvs.min() >= 0 and boxed.uvs.max() <= 1
    tiles = set(zip((boxed.uvs[:, 0] * 3).astype(int), (boxed.uvs[:, 1] * 2).astype(int)))
    assert len(tiles) == 6                                     # every face of the box is used by a sphere
    assert spherical_uvs(mesh).uvs.shape == (mesh.vertex_count, 2) and cylindrical_uvs(mesh).uvs.max() <= 1.0
    assert with_uvs(mesh, "atlas").uvs is not None          # falls back to box without xatlas
    texture = bake_vertex_colors(boxed, 128)
    assert texture.shape == (128, 128, 3) and texture.dtype == np.uint8 and texture.std() > 1
    with pytest.raises(ValueError):
        bake_vertex_colors(mesh, 32)                            # no UVs


def test_mesh_preview_renders_with_the_scene_lights_and_palette_colours():
    flame = tetrahedron()
    scene = Scene3D("p", flame)
    mesh = sphere_mesh(20).keep_components(largest=1)[0]
    points, normals, nearest, faces = sample_surface(mesh, 5000)
    assert points.shape == (5000, 3) and normals.shape == (5000, 3) and faces.max() < mesh.face_count
    assert np.linalg.norm(points, axis=1).mean() == pytest.approx(1.0, abs=0.12)      # on the blurred shell, radius ≈ 0.9 + a voxel
    palette = fallback_palette()
    assert palette.shape == (256, 3) and nearest_palette_index(np.array([[0.5, 0.5, 0.5]]), palette)[0] >= 216   # a grey entry
    image = render_mesh(mesh, flame.camera.at_size(80, 60), scene, 80, 60, 1, samples=60_000)
    assert image.shape == (60, 80, 4) and image[..., 3].min() == 255
    scene.environment.visible = False
    image = render_mesh(mesh, flame.camera.at_size(80, 60), scene, 80, 60, 1, samples=60_000)
    assert image[..., 3].max() == 255 and (image[..., 3] == 0).any()   # the object, on a transparent background


# --- file formats ---------------------------------------------------------------------------------------------------
def test_every_export_format_round_trips(tmp_path):
    mesh = sphere_mesh(20).keep_components(largest=1)[0]
    for fmt in EXPORT_FORMATS:
        if not fmt.available:
            continue
        files = write_mesh(mesh, tmp_path / f"m{fmt.extension}", fmt, name="round trip")
        assert files[0].suffix == fmt.extension and files[0].exists()
        back = read_mesh(files[0])
        assert back.face_count == mesh.face_count and back.vertex_count == mesh.vertex_count
        assert np.allclose(np.sort(back.vertices, axis=0), np.sort(mesh.vertices, axis=0), atol=1e-4), fmt.key
        assert back.normals is not None
        assert (back.colors is not None) == fmt.colors, fmt.key
        assert abs(back.signed_volume()) == pytest.approx(abs(mesh.signed_volume()), rel=1e-3)
    assert export_format("nope").key == "obj"
    with pytest.raises(ValueError):
        read_mesh(tmp_path / "x.xyz")
    (tmp_path / "bad.obj").write_text("# nothing\n")
    with pytest.raises(ValueError):
        read_mesh(tmp_path / "bad.obj")
    (tmp_path / "bad.stl").write_bytes(b"short")
    with pytest.raises(ValueError):
        read_mesh(tmp_path / "bad.stl")
    (tmp_path / "bad.glb").write_text("{}")
    with pytest.raises(ValueError):
        read_mesh(tmp_path / "bad.glb")


def test_textured_exports_carry_uvs_and_reference_the_texture(tmp_path):
    mesh = with_uvs(sphere_mesh(20).keep_components(largest=1)[0], "box")
    texture = tmp_path / "m_color.png"
    from PIL import Image
    Image.fromarray(bake_vertex_colors(mesh, 64)).save(texture)
    for key in ("obj", "glb", "usda"):
        files = write_mesh(mesh, tmp_path / f"t.{key}", key, texture=texture, name="tex")
        back = read_mesh(files[0])
        assert back.uvs is not None and back.uvs.shape == (back.vertex_count, 2), key
        assert np.allclose(np.sort(back.uvs, axis=0), np.sort(mesh.uvs, axis=0), atol=1e-4), key
    assert (tmp_path / "t.mtl").exists() and "map_Kd m_color.png" in (tmp_path / "t.mtl").read_text()
    text = usda_text(mesh, "tex", "m_color.png", 0.001)
    assert "metersPerUnit = 0.001" in text and "UsdUVTexture" in text and "@m_color.png@" in text and 'def Mesh "mesh"' in text
    plain = usda_text(sphere_mesh(16), "plain")
    assert "UsdPrimvarReader_float3" in plain and "displayColor" in plain
    # the ASCII USD parser (used without usd-core) reads the writer's layout
    from fractalchemy.solid.io.usd import _parse_usda
    parsed = _parse_usda(plain, "plain")
    assert parsed.face_count == sphere_mesh(16).face_count and parsed.colors is not None


def test_blender_script_is_valid_python_and_carries_the_scene():
    flame = tetrahedron()
    scene = Scene3D("b", flame)
    scene.lights[1].shadows = True
    text = blender_script(scene, "b.glb", (0.5, 0.5, 0.4), 1.0, "b", "b_color.png", "b_blender.py")
    compile(text, "b_blender.py", "exec")
    assert 'ASSET = os.path.join(HERE, \'b.glb\')' in text and "TEXTURE = 'b_color.png'" in text
    assert text.count("SUN") == 1 and "2, \"lights\"" in text.replace("'", '"') or "2," in text
    assert "camera_data.angle" in text and "film_transparent = False" in text
    scene.environment.visible = False
    assert "film_transparent = True" in blender_script(scene, "b.ply", (0, 0, 0), 1.0)


# --- the pipeline -----------------------------------------------------------------------------------------------------
def test_pipeline_stages_cache_capture_and_report_everything(tmp_path):
    flame = tetrahedron()
    settings = MeshSettings(points=60_000, resolution=40, threshold=0.15, clean="aggressive", target_faces=3000)
    messages = []
    stage = pipeline.capture_stage(flame, settings, progress=lambda f, m: messages.append((f, m)))
    assert stage is not None and stage.points >= 60_000 and stage.matches(settings) and messages[-1][0] == 1.0
    assert not stage.matches(MeshSettings(points=60_000, resolution=48))
    result = pipeline.build_mesh(stage, settings, progress=lambda f, m: messages.append((f, m)))
    assert result is not None and result.full_report.faces > 1000 and result.clean_report.faces <= 3000
    assert result.clean_report.printable and result.inside.any() and result.histogram[1].sum() > 0
    assert set(result.seconds) == {"capture", "filter", "isosurface", "clean"}
    assert result.mesh("full") is result.full and result.report("clean") is result.clean_report
    # cancelling mid-way
    calls = [0]

    def cancelled() -> bool:
        calls[0] += 1
        return calls[0] > 2
    assert pipeline.build_mesh(stage, settings, cancelled=cancelled) is None
    assert pipeline.capture_stage(flame, settings, cancelled=lambda: True) is None
    # the remesh level
    remeshed = pipeline.build_mesh(stage, MeshSettings(points=60_000, resolution=40, clean="remesh", target_faces=2000))
    assert remeshed.clean_report.components == 1 and remeshed.clean_report.watertight
    assert any("remeshed" in n for n in remeshed.clean_report.notes)
    # export
    scene = Scene3D("tetra", flame)
    export = ExportSettings(formats=["glb", "stl", "usda"], materials="texture", texture_size=128, units="mm", size_mm=50.0)
    outcome = pipeline.export_result(result, scene, export, tmp_path / "out", "tetra", progress=lambda f, m: None)
    names = sorted(p.name for p in outcome.files)
    assert names == ["tetra.glb", "tetra.stl", "tetra.usda", "tetra_blender.py", "tetra_color.png"]
    assert outcome.report == tmp_path / "out" / "tetra_report.md" and outcome.report.exists()
    report = outcome.report.read_text()
    assert "## Clean mesh" in report and "watertight | yes" in report and "50 mm" in report
    assert read_mesh(tmp_path / "out" / "tetra.stl").extent().max() == pytest.approx(50.0, rel=1e-3)
    assert "metersPerUnit = 0.001" in (tmp_path / "out" / "tetra.usda").read_text()
    with pytest.raises(ValueError):
        pipeline.export_result(result, scene, ExportSettings(formats=[]), tmp_path, "x")


def test_mesh_and_export_settings_live_in_the_scene_file():
    scene = Scene3D("s", tetrahedron())
    scene.mesh.resolution = 200
    scene.export.formats = ["stl", "usdz"]
    scene.export.units = "mm"
    copy = fa3d.scene_from_text(fa3d.scene_to_text(scene))
    assert copy.mesh.resolution == 200 and copy.export.formats == ["stl", "usdz"] and copy.export.units == "mm"
    assert copy.copy().export.formats is not copy.export.formats


# --- the window -------------------------------------------------------------------------------------------------------
@pytest.fixture
def main(main_window_factory):
    win = main_window_factory(cheap_renders=True)
    yield win
    if win._three_d is not None:
        win._three_d.wait_for_jobs()
        win._three_d.document._modified = False


def editor_with_mesh_settings(win):
    win.show_flame(tetrahedron())
    win.actionThreeDEditor.trigger()
    editor = win.three_d_editor
    editor.resize(900, 560)
    editor.viewport.set_quality("Draft")
    wait_until(lambda: editor.isVisible())
    editor.document.update_mesh_settings(None, points=50_000, resolution=32, target_faces=2000, clean="aggressive")
    return editor


def test_mesh_tab_generates_shows_and_regenerates_from_the_cached_capture(main):
    editor = editor_with_mesh_settings(main)
    panel = editor.mesh_panel
    assert [editor.tabs.tabText(i) for i in range(editor.tabs.count())][-2:] == ["Mesh", "Export"]
    assert panel.result_label.text() == "No mesh yet." and not panel.show_clean.isEnabled() and panel.generate_button.isEnabled()
    panel.generate_button.click()
    assert editor.meshing and not panel.generate_button.isEnabled() and panel.cancel_button.isEnabled()
    wait_until(lambda: not editor.meshing, timeout_ms=120000)
    result = editor.document.mesh_result
    assert result is not None and result.clean_report.faces <= 2000 and "Clean:" in panel.result_label.text()
    assert panel.histogram._counts is not None and panel.show_clean.isEnabled()
    stage = editor.document.voxel_stage
    # show the clean mesh in the viewport
    panel.show_clean.setChecked(True)
    assert editor.document.scene.solid.display == "mesh" and editor.viewport.showing_mesh
    assert editor.render_panel.display_box.currentData() == "mesh"
    wait_until(lambda: editor.viewport.up_to_date, timeout_ms=120000)
    assert editor.viewport.stats.engine.startswith("mesh preview") and "faces" in editor.viewport.stats.notes[0]
    assert editor.viewport.image is not None
    # a threshold change is an undo step; regenerating reuses the capture
    panel.histogram._move(panel.histogram.width() * 0.9)
    assert editor.document.scene.mesh.threshold > 0.15 and editor.document.undo_label == "Mesh settings"
    assert "Regenerate" in panel.generate_button.text()
    panel.generate_button.click()
    wait_until(lambda: not editor.meshing, timeout_ms=120000)
    assert editor.document.voxel_stage is stage and editor.document.mesh_result is not result
    # a different fractal drops the mesh and the display falls back to the solid render
    editor.document.set_fractal(tetrahedron())
    assert editor.document.mesh_result is None and editor.document.scene.solid.display == "solid" and panel.show_solid.isChecked()


def test_export_tab_writes_files_and_cancel_stops_meshing(main, tmp_path):
    editor = editor_with_mesh_settings(main)
    export = editor.export_panel
    assert not export.export_button.isEnabled()
    editor.mesh_panel.generate_button.click()
    editor.mesh_panel.cancel_button.click()
    wait_until(lambda: not editor.meshing, timeout_ms=60000)
    assert editor.document.mesh_result is None
    editor.mesh_panel.generate_button.click()
    wait_until(lambda: not editor.meshing, timeout_ms=120000)
    assert export.export_button.isEnabled()
    export.format_checks["glb"].setChecked(True)
    export.format_checks["stl"].setChecked(True)
    export.format_checks["ply"].setChecked(False)
    export.materials_box.setCurrentIndex(export.materials_box.findData("texture"))
    export.texture_box.setCurrentIndex(0)
    export.units_mm.setChecked(True)
    export.folder.setText(str(tmp_path / "exp"))
    export.folder.editingFinished.emit()
    export.name.setText("tetra")
    export.name.editingFinished.emit()
    e = editor.document.scene.export
    assert set(e.formats) >= {"glb", "stl"} and e.materials == "texture" and e.units == "mm" and e.folder.endswith("exp")
    assert editor.export_folder() == tmp_path / "exp" and editor.export_name() == "tetra"
    export.export_button.click()
    assert editor.exporting
    wait_until(lambda: not editor.exporting, timeout_ms=120000)
    names = sorted(p.name for p in (tmp_path / "exp").iterdir())
    assert "tetra.glb" in names and "tetra.stl" in names and "tetra_color.png" in names and "tetra_report.md" in names
    assert "tetra_blender.py" in names and "tetra.glb" in export.result_label.text()
    assert main._settings.value("three_d/export_folder") == str(tmp_path / "exp")

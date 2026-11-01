"""Mesh export from a fragment's distance estimator: the GPU probe, the meshing and the files."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from fractalchemy.fragments.batch import prepare
from fractalchemy.fragments.gl.engine import FragEngine
from fractalchemy.fragments.gl.mesh import Bounds, DistanceProbe, has_distance_estimator, probe_source, provides_color
from fractalchemy.fragments.mesh import DEExportSettings, DEMeshSettings, build_de_mesh, estimated_bytes, export_de_mesh

SPHERE = """#define providesColor
uniform float Radius; slider[0.1,1,2]
float DE(vec3 p) { return length(p) - Radius; }
vec3 baseColor(vec3 p, vec3 n) { return vec3(1.0, 0.0, 0.0); }
void main() { gl_FragColor = vec4(DE(vec3(0.0))); }
"""

NO_DE = """void main() { gl_FragColor = vec4(1.0); }"""


@pytest.fixture
def engine(gl_context):
    engine = FragEngine(gl_context)
    yield engine
    engine.close()


def _prepared(tmp_path: Path, engine: FragEngine, text: str = SPHERE):
    path = tmp_path / "sphere.frag"
    path.write_text(text)
    return prepare(path, engine)


def test_probe_source_renames_main_and_detects_features(tmp_path, engine):
    prepared = _prepared(tmp_path, engine)
    modern = prepared.request.modern
    assert has_distance_estimator(modern) and provides_color(modern)
    probe = probe_source(modern)
    assert "fractalchemy_original_main(" in probe.fragment and probe.fragment.count("void main(") == 1
    assert len(probe.fragment_map.origins) == probe.fragment.count("\n") + 1 or len(probe.fragment_map.origins) >= len(modern.fragment_map.origins)


def test_fragment_without_de_is_refused(tmp_path, engine):
    prepared = _prepared(tmp_path, engine, NO_DE)
    assert not has_distance_estimator(prepared.request.modern)
    with pytest.raises(ValueError, match="DE"):
        DistanceProbe(engine, prepared.request)


def test_probe_samples_the_distance_field(tmp_path, engine):
    prepared = _prepared(tmp_path, engine)
    probe = DistanceProbe(engine, prepared.request)
    result = probe.sample(Bounds((0.0, 0.0, 0.0), 4.0), 32, colors=True)
    probe.close()
    assert result.distance.shape == (32, 32, 32) and result.color.shape == (32, 32, 32, 3)
    centre = result.origin + (np.array([16, 16, 16]) + 0.5) * result.spacing     # voxel (16,16,16) centre, just past the origin
    assert abs(result.distance[16, 16, 16] - (np.linalg.norm(centre) - 1.0)) < 1e-4
    assert abs(result.distance[0, 0, 0] - (np.linalg.norm(result.origin + 0.5 * result.spacing) - 1.0)) < 1e-4
    assert np.allclose(result.color[16, 16, 16], (1.0, 0.0, 0.0))
    # the axes are not mixed up: moving along x changes only x
    x_step = result.origin + (np.array([20, 16, 16]) + 0.5) * result.spacing
    assert abs(result.distance[20, 16, 16] - (np.linalg.norm(x_step) - 1.0)) < 1e-4


def test_fit_bounds_shrinks_to_the_sphere(tmp_path, engine):
    prepared = _prepared(tmp_path, engine)
    probe = DistanceProbe(engine, prepared.request)
    fitted = probe.fit_bounds(Bounds((0.0, 0.0, 0.0), 10.0), 0.2)
    probe.close()
    assert 2.0 < fitted.size < 3.5 and max(abs(c) for c in fitted.center) < 0.3


def test_mesh_volume_and_colours_and_export(tmp_path, engine):
    prepared = _prepared(tmp_path, engine)
    probe = DistanceProbe(engine, prepared.request)
    settings = DEMeshSettings(resolution=48, bounds=Bounds((0.0, 0.0, 0.0), 3.0), fit=False, threshold_voxels=0.0, clean="simple")
    sampled = probe.sample(settings.bounds, settings.resolution, colors=True)
    probe.close()
    result = build_de_mesh(sampled, settings)
    rep = result.clean_report
    assert rep.watertight and rep.components == 1
    assert abs(rep.volume - 4.0 / 3.0 * math.pi) / (4.0 / 3.0 * math.pi) < 0.08
    assert result.clean.colors is not None and np.allclose(result.clean.colors.mean(axis=0), (1.0, 0.0, 0.0), atol=0.02)
    outcome = export_de_mesh(result, DEExportSettings(formats=["ply", "stl"]), tmp_path / "out", "sphere", "sphere.frag")
    assert [p.name for p in outcome.files] == ["sphere.ply", "sphere.stl"] and outcome.report.exists()
    assert "watertight | yes" in outcome.report.read_text()


def test_settings_checks():
    assert DEMeshSettings(resolution=4).check()
    assert DEMeshSettings(resolution=64, bounds=Bounds(size=0.0)).check()
    assert not DEMeshSettings().check()
    assert estimated_bytes(128, True) == 128 ** 3 * 4 * 6


def test_sparse_blocks_match_the_dense_mesh(tmp_path, engine):
    from fractalchemy.fragments.mesh import active_blocks, build_de_mesh_sparse

    prepared = _prepared(tmp_path, engine)
    probe = DistanceProbe(engine, prepared.request)
    dense_settings = DEMeshSettings(resolution=64, bounds=Bounds((0.0, 0.0, 0.0), 3.0), fit=False, threshold_voxels=0.0, clean="none")
    dense = build_de_mesh(probe.sample(dense_settings.bounds, 64, colors=True), dense_settings)
    sparse_settings = DEMeshSettings(resolution=64, bounds=Bounds((0.0, 0.0, 0.0), 3.0), fit=False, threshold_voxels=0.0, clean="none",
                                     sparse=True, block=32)
    sparse = build_de_mesh_sparse(probe, sparse_settings)
    coarse = probe.sample(sparse_settings.bounds, 16)
    probe.close()
    assert sparse.full.face_count == dense.full.face_count and sparse.full_report.watertight
    assert abs(sparse.full_report.volume - dense.full_report.volume) < 1e-6
    assert np.allclose(sparse.full.colors.mean(axis=0), (1.0, 0.0, 0.0), atol=0.02)
    blocks = active_blocks(coarse, sparse_settings.bounds, 64, 32, 0.0)
    assert 1 <= len(blocks) <= 8 and not DEMeshSettings(resolution=2048, sparse=True).check()
    assert DEMeshSettings(resolution=2048).check()

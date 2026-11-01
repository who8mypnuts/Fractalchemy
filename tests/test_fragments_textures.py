"""Textures for `uniform sampler2D tex; file[…]`: specs, decoding, `#TexParameter`, the GL cache and the task jobs."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from fractalchemy.fragments.files import FileManager
from fractalchemy.fragments.gl.engine import FragEngine
from fractalchemy.fragments.gl.job import FragRenderSettings, FragRequest
from fractalchemy.fragments.gl.tasks import FragTask, check_versions, clear_textures
from fractalchemy.fragments.glsl_compat import CompatOptions, modernise
from fractalchemy.fragments.preprocessor import Preprocessor
from fractalchemy.fragments.state import ParameterState
from fractalchemy.fragments.textures import (GL_LINEAR, GL_LINEAR_MIPMAP_LINEAR, GL_NEAREST, TextureError, TextureSpec, filter_pair,
                                             load_texture, split_cube_strip, texture_specs, wrap_pair)

TEXTURED = """#vertex
varying vec2 coord;
void main() { gl_Position = gl_Vertex; coord = gl_Vertex.xy * 0.5 + 0.5; }
#endvertex
varying vec2 coord;
uniform sampler2D tex; file[strip.png]
#TexParameter tex GL_TEXTURE_MIN_FILTER GL_NEAREST
#TexParameter tex GL_TEXTURE_MAG_FILTER GL_NEAREST
#TexParameter tex GL_TEXTURE_WRAP_S GL_CLAMP_TO_EDGE
void main() { gl_FragColor = vec4(texture2D(tex, coord).rgb, 1.0); }
"""


@pytest.fixture
def engine(gl_context):
    engine = FragEngine(gl_context)
    yield engine
    engine.close()


def _strip(path: Path, width: int = 4) -> Path:
    """A `width` × 1 strip: red, green, blue, white."""
    colors = np.array([[255, 0, 0, 255], [0, 255, 0, 255], [0, 0, 255, 255], [255, 255, 255, 255]], dtype=np.uint8)[:width]
    Image.fromarray(colors.reshape(1, width, 4), "RGBA").save(path)
    return path


def _request(engine: FragEngine, text: str, path: Path) -> FragRequest:
    files = FileManager(original=path)
    source = Preprocessor(files).parse(text, path)
    options = CompatOptions("modernise", engine.capabilities.glsl_version, engine.capabilities.has_fp64)
    state = ParameterState(source.all_params)
    return FragRequest(modernise(source, options), None, dict(state.values), source.buffer, textures=texture_specs(source, state, files))


def test_specs_resolve_files_and_parameters(tmp_path: Path):
    _strip(tmp_path / "strip.png")
    path = tmp_path / "t.frag"
    files = FileManager(original=path)
    source = Preprocessor(files).parse(TEXTURED, path)
    state = ParameterState(source.all_params)
    specs = texture_specs(source, state, files)
    spec = specs["tex"]
    assert spec.path == tmp_path / "strip.png" and not spec.cube and spec.integer == ""
    assert spec.params == {"GL_TEXTURE_MIN_FILTER": "GL_NEAREST", "GL_TEXTURE_MAG_FILTER": "GL_NEAREST", "GL_TEXTURE_WRAP_S": "GL_CLAMP_TO_EDGE"}
    assert filter_pair(spec.params) == (GL_NEAREST, GL_NEAREST, False) and wrap_pair(spec.params) == (False, True)
    assert filter_pair({"GL_TEXTURE_MIN_FILTER": "GL_LINEAR_MIPMAP_LINEAR"}) == (GL_LINEAR_MIPMAP_LINEAR, GL_LINEAR, True)
    assert spec.cache_key() is not None and TextureSpec("x", None).cache_key() is None


def test_missing_file_gives_no_path_and_loader_refuses(tmp_path: Path):
    path = tmp_path / "t.frag"
    files = FileManager(original=path)
    source = Preprocessor(files).parse(TEXTURED, path)
    spec = texture_specs(source, ParameterState(source.all_params), files)["tex"]
    assert spec.path is None
    with pytest.raises(TextureError):
        load_texture(spec)


def test_load_texture_flips_rows_and_splits_cube_strips(tmp_path: Path):
    image = np.zeros((2, 2, 4), dtype=np.uint8)
    image[0, :, 0] = 255   # top row red in the file
    Image.fromarray(image, "RGBA").save(tmp_path / "two.png")
    loaded = load_texture(TextureSpec("t", tmp_path / "two.png"))
    assert loaded.data.shape == (2, 2, 4) and loaded.data[1, 0, 0] == 255 and loaded.data[0, 0, 0] == 0   # GL rows start at the bottom
    faces = split_cube_strip(np.arange(6 * 3 * 3 * 4, dtype=np.uint8).reshape(3, 18, 4))
    assert len(faces) == 6 and all(f.shape == (3, 3, 4) for f in faces) and faces[1][0, 0, 0] == 3 * 4
    integer = load_texture(TextureSpec("t", tmp_path / "two.png", integer="u"))
    assert integer.data.dtype == np.uint32 and integer.dtype == "u4"


def test_engine_binds_and_samples_the_texture(tmp_path: Path, engine: FragEngine):
    _strip(tmp_path / "strip.png")
    request = _request(engine, TEXTURED, tmp_path / "t.frag")
    with engine.ctx:
        job = engine.start(request, FragRenderSettings(8, 2, subframe_max=1, surface_key="tex"))
        image = job.run_pass()
        job.close()
    assert image.shape == (2, 8, 4)
    assert tuple(image[0, 0, :3]) == (255, 0, 0) and tuple(image[0, 7, :3]) == (255, 255, 255)   # nearest filtering, clamped
    assert tuple(image[0, 3, :3]) == (0, 255, 0)
    assert len(engine.textures._textures) == 1 and not engine.textures.take_problems()


def test_cache_reloads_a_changed_file_and_clears(tmp_path: Path, engine: FragEngine):
    path = _strip(tmp_path / "strip.png")
    request = _request(engine, TEXTURED, tmp_path / "t.frag")
    with engine.ctx:
        job = engine.start(request, FragRenderSettings(4, 1, subframe_max=1, surface_key="tex2"))
        first = job.run_pass()
        job.close()
        image = np.full((1, 4, 4), 255, dtype=np.uint8)
        image[..., 0] = 0
        Image.fromarray(image, "RGBA").save(path)
        later = path.stat().st_mtime_ns + 1
        import os
        os.utime(path, ns=(later, later))
        request = _request(engine, TEXTURED, tmp_path / "t.frag")
        job = engine.start(request, FragRenderSettings(4, 1, subframe_max=1, surface_key="tex2"))
        second = job.run_pass()
        job.close()
        assert tuple(first[0, 0, :3]) == (255, 0, 0) and tuple(second[0, 0, :3]) == (0, 255, 255)
        assert len(engine.textures._textures) == 1           # the old upload was evicted
        task = engine.start(FragTask("clear", clear_textures), None)
        task.run_pass()
        assert task.stats.finished and task.stats.facts == "texture cache cleared" and not engine.textures._textures


def test_unreadable_texture_is_reported_not_fatal(tmp_path: Path, engine: FragEngine):
    (tmp_path / "strip.png").write_bytes(b"not an image")
    request = _request(engine, TEXTURED, tmp_path / "t.frag")
    with engine.ctx:
        job = engine.start(request, FragRenderSettings(4, 1, subframe_max=1, surface_key="tex3"))
        image = job.run_pass()
        job.close()
    assert image is not None and any("cannot read strip.png" in note for note in job.stats.facts.notes)


def test_version_check_task(tmp_path: Path, engine: FragEngine):
    path = tmp_path / "t.frag"
    source = Preprocessor(FileManager(original=path)).parse(TEXTURED, path)
    top = engine.capabilities.glsl_version
    versions = [v for v in (330, 400, 450, 460) if v <= top] + [top + 10]
    with engine.ctx:
        task = engine.start(FragTask("versions", check_versions(source, "modernise", versions, engine.capabilities.has_fp64)), None)
        task.run_pass()
    results = dict(task.stats.facts)
    assert all(results[v] == [] for v in versions[:-1])
    assert results[top + 10] and "GLSL" in results[top + 10][0]

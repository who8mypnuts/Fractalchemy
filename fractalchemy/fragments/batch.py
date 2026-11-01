"""Headless rendering of fragments — what FragM's `.fqs` scripts did, as a Python API for the CLI and the Batch dialog.

    result = render(Path("Mandelbulb.frag"), FragFinalSettings(output_path="out.png"), preset="Octobulb")
    check(Path("Mandelbulb.frag"))           # preprocess + compile only

`prepare()` builds a `FragRenderInput` from a file (the `Default` preset applied, then a named one), `render()`
drives a `FragFinalRenderer` on an engine the caller owns and writes every frame, `render_presets()` /
`render_keyframes()` do that for every preset / keyframe (`renderPresets.fqs` / `renderKeyframes.fqs`), `check()`
reports compile diagnostics (`testFrags.fqs`). No Qt: usable from scripts and from the test-suite.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .animation import AnimationSettings, camera_path, keyframe_blend
from .document_format import read_fragment, split_metadata
from .easing import parse_all
from .files import FileManager
from .gl.diagnostics import Diagnostic
from .gl.engine import FragEngine
from .gl.final import FragFinalRenderer, FragFinalResult, FrameImage, write_frame
from .gl.job import FragRequest
from .glsl_compat import CompatError, CompatOptions, modernise
from .preprocessor import Preprocessor
from .presets import is_keyframe
from .render_settings import FragFinalSettings, safe_stem
from .source import CRITICAL, FragmentSource, Message
from .state import ParameterState
from .textures import texture_specs


@dataclass
class Prepared:
    """A fragment ready to render.

    Attributes:
        source: The preprocessed fragment.
        request: The translated program and values.
        state: The parameter state after the presets.
        animation: The clock (from the `.fafrag` metadata or the defaults).
        messages: Preprocessor remarks.
    """
    source: FragmentSource
    request: FragRequest
    state: ParameterState
    animation: AnimationSettings
    messages: list[Message] = field(default_factory=list)


class BatchError(RuntimeError):
    """A fragment could not be prepared (preprocessor errors, an unknown preset, an unsupported GLSL version)."""


def prepare(path: Path, engine: FragEngine, preset: str | None = "Default", include_paths: list[Path] | None = None,
            settings_text: str = "", compat_mode: str = "modernise") -> Prepared:
    """Preprocess, translate and parameterise a fragment file for `engine`."""
    path = Path(path)
    try:
        text, metadata = read_fragment(path)
    except Exception:  # noqa: BLE001 - a broken metadata block: use the raw text
        text, metadata = split_metadata(path.read_text(encoding="utf-8", errors="replace"))[0], None
    source = Preprocessor(FileManager(include_paths or [], path)).parse(text, path)
    if not source.fragment or any(m.level == CRITICAL and "Could not resolve" in m.text for m in source.messages):
        critical = "; ".join(m.text for m in source.messages if m.level == CRITICAL)
        raise BatchError(f"{path.name}: {critical or 'nothing to compile'}")
    caps = engine.capabilities
    options = CompatOptions(compat_mode, caps.glsl_version, caps.has_fp64)
    try:
        modern = modernise(source, options)
        buffer_modern = modernise(source.buffer_shader, options) if source.buffer_shader else None
    except CompatError as exc:
        raise BatchError(f"{path.name}: {exc}") from exc
    state = ParameterState(source.all_params)
    if "Default" in source.presets:
        state.apply_settings(source.presets["Default"])
    if preset and preset != "Default":
        if preset not in source.presets:
            raise BatchError(f"{path.name}: no preset called {preset!r} (has: {', '.join(source.presets) or 'none'})")
        state.apply_settings(source.presets[preset])
    if settings_text:
        state.apply_settings(settings_text)
    request = FragRequest(modern, buffer_modern, dict(state.values), source.buffer, source.clear_on_change, source.subframes_between_redraws,
                          source.depth_to_alpha, dict(source.texture_params.get("backbuffer", {})),
                          texture_specs(source, state, FileManager(include_paths or [], path)))
    animation = AnimationSettings.from_dict(metadata.animation if metadata is not None else None)
    return Prepared(source, request, state, animation, list(source.messages))


def check(path: Path, engine: FragEngine, include_paths: list[Path] | None = None) -> list[Diagnostic]:
    """Compile a fragment (and its buffer shader); the diagnostics, empty when everything compiled."""
    prepared = prepare(path, engine, None, include_paths)
    diagnostics = engine.check(prepared.request.modern)
    if prepared.request.buffer_modern is not None:
        diagnostics += engine.check(prepared.request.buffer_modern)
    return diagnostics


def render(path: Path, settings: FragFinalSettings, engine: FragEngine, preset: str | None = "Default", include_paths: list[Path] | None = None,
           progress: Callable | None = None, frame_done: Callable[[FrameImage, Path], None] | None = None,
           animation: AnimationSettings | None = None) -> FragFinalResult:
    """Render a fragment with `settings` to its output path(s); returns the renderer's result (paths filled in)."""
    prepared = prepare(path, engine, preset, include_paths)
    clock = animation or prepared.animation
    curves = parse_all([line for line in prepared.source.presets.get("Default", "").splitlines() if line.count(":") == 11])
    keyframes = prepared.source.keyframe_names()
    path_model = camera_path(prepared.source.presets, clock) if keyframes else None
    renderer = FragFinalRenderer(engine, prepared.request, prepared.state, settings, clock, path_model, curves, prepared.source.auto_focus,
                                 blend=keyframe_blend(prepared.source.presets, prepared.state, clock))
    written: list[Path] = []
    settings_text = prepared.state.to_text(provenance=Path(path).name)

    def on_frame(image: FrameImage) -> None:
        target = settings.frame_path(image.frame, clock.frames)
        if settings.unique_name:
            target = settings.unique(target)
        write_frame(image, target, settings, settings_text)
        written.append(target)
        if frame_done is not None:
            frame_done(image, target)

    result = renderer.run(progress, on_frame)
    result.paths = written
    return result


def render_presets(path: Path, settings: FragFinalSettings, engine: FragEngine, folder: Path, include_paths: list[Path] | None = None,
                   keyframes_only: bool = False, progress: Callable | None = None) -> list[Path]:
    """One image per preset (or per keyframe) into `folder`, named `<fragment>-<preset>.<ext>`; returns the files."""
    path = Path(path)
    folder = Path(folder)
    probe = Preprocessor(FileManager(include_paths or [], path)).parse(read_fragment(path)[0], path)
    names = [n for n in probe.presets if is_keyframe(n)] if keyframes_only else list(probe.presets)
    written: list[Path] = []
    suffix = Path(settings.output_path).suffix or ".png"
    for name in names:
        target = folder / f"{safe_stem(path.stem)}-{safe_stem(name)}{suffix}"
        result = render(path, settings.with_(output_path=str(target), animation=False), engine, name, include_paths, progress)
        written += result.paths
    return written


__all__ = ["Prepared", "BatchError", "prepare", "check", "render", "render_presets", "safe_stem"]

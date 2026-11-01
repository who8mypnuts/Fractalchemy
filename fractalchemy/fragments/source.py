"""What the preprocessor produces: the program text with every line's origin, plus everything it lifted out of it.

A `FragmentSource` is FragM's `FragmentSource` struct: the fragment lines (and the `#vertex` lines), the parameters
found in annotated uniforms, the presets, the textures and their `#TexParameter`s, the camera kind, the buffer type,
the buffer shader (another `FragmentSource`) and the flags the `#define`s set. Every emitted line remembers the
file and line it came from (`LineMap`) so a driver error in an include points into the include — the job FragM's
`#line` directives did, done exactly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .parameters import GuiParameter

INFO, WARNING, CRITICAL, SCRIPT = "info", "warning", "critical", "script"


@dataclass(frozen=True)
class Message:
    """A preprocessor / compiler remark for the log.

    Attributes:
        level: `info`, `warning`, `critical` or `script` (FragM's `#info` lines).
        text: The message.
        file: The source file it refers to (None: none in particular).
        line: 1-based line in `file` (0: none).
    """
    level: str
    text: str
    file: Path | None = None
    line: int = 0


@dataclass
class LineMap:
    """Origin of every emitted line: `(file index, 1-based line)` or None for generated text.

    Attributes:
        files: The files by index (None for an unsaved tab's text).
        origins: One entry per emitted line.
    """
    files: list[Path | None] = field(default_factory=list)
    origins: list[tuple[int, int] | None] = field(default_factory=list)

    def file_index(self, path: Path | None) -> int:
        """Index of `path` in `files`, appended when new (identity for None)."""
        for i, known in enumerate(self.files):
            if known == path:
                return i
        self.files.append(path)
        return len(self.files) - 1

    def origin(self, emitted_line: int) -> tuple[Path | None, int] | None:
        """`(file, line)` of 1-based emitted line `emitted_line`, or None for generated lines."""
        index = emitted_line - 1
        if not 0 <= index < len(self.origins) or self.origins[index] is None:
            return None
        file_index, line = self.origins[index]
        return self.files[file_index], line

    def copy(self) -> "LineMap":
        return LineMap(list(self.files), list(self.origins))


@dataclass
class FragmentSource:
    """The preprocessed program (see the module docstring).

    Attributes:
        fragment: The fragment shader lines (directives already replaced by comments, annotations stripped).
        vertex: The lines between `#vertex` and `#endvertex` (empty when the fragment has none).
        line_map, vertex_line_map: Where each line came from.
        params: The annotated uniforms, in order of appearance (buffer-shader parameters are on `buffer_shader`).
        presets: `#preset` blocks by name, body text without the markers.
        preset_spans: For each preset, `(file, first line, last line)` of the block in its file (for *Select preset*).
        textures: Sampler uniform name → the resolved texture path (None when unresolved).
        texture_params: Sampler uniform name → {GL parameter: value} from `#TexParameter` lines.
        camera: `"2D"` or `"3D"` (`""` until `#camera` was seen; the engine defaults to 2D).
        buffer: `#buffer` type text (`""`, `NONE`, `RGBA8`, `RGBA16`, `RGBA16F`, `RGBA32F`).
        buffer_shader: The `#buffershader` program, or None.
        clear_on_change, subframes_between_redraws, subframe_max, depth_to_alpha, auto_focus, has_pixel_size: the flags.
        version_line: The user fragment's `#version` line (`""` when absent: GLSL 1.10).
        runnable: False when `#donotrun` appeared.
        dependencies: Every file included (for copying with autosaved fragments).
        messages: What the preprocessor had to say.
    """
    fragment: list[str] = field(default_factory=list)
    vertex: list[str] = field(default_factory=list)
    line_map: LineMap = field(default_factory=LineMap)
    vertex_line_map: LineMap = field(default_factory=LineMap)
    params: list[GuiParameter] = field(default_factory=list)
    presets: dict[str, str] = field(default_factory=dict)
    preset_spans: dict[str, tuple[Path | None, int, int]] = field(default_factory=dict)
    textures: dict[str, Path | None] = field(default_factory=dict)
    texture_params: dict[str, dict[str, str]] = field(default_factory=dict)
    camera: str = ""
    buffer: str = ""
    buffer_shader: "FragmentSource | None" = None
    clear_on_change: bool = True
    subframes_between_redraws: int = 0
    subframe_max: int = -1
    depth_to_alpha: bool = False
    auto_focus: bool = False
    has_pixel_size: bool = False
    version_line: str = ""
    runnable: bool = True
    dependencies: list[Path] = field(default_factory=list)
    messages: list[Message] = field(default_factory=list)

    def text(self) -> str:
        """The fragment shader source as one string."""
        return "\n".join(self.fragment)

    def vertex_text(self) -> str:
        return "\n".join(self.vertex)

    @property
    def camera_kind(self) -> str:
        """`"3D"` or `"2D"` (FragM treats an absent `#camera` as 2D)."""
        return "3D" if self.camera.strip().upper() == "3D" else "2D"

    @property
    def all_params(self) -> list[GuiParameter]:
        """The fragment's parameters followed by the buffer shader's that the fragment does not also declare."""
        names = {p.name for p in self.params}
        extra = [p for p in self.buffer_shader.params if p.name not in names] if self.buffer_shader else []
        return list(self.params) + extra

    def preset_names(self) -> list[str]:
        return list(self.presets)

    def is_own_param(self, param) -> bool:
        """True when `param` was declared in the fragment itself rather than in an included file."""
        origin = self.line_map.origin(param.line + 1)
        main = self.line_map.files[0] if self.line_map.files else None
        return origin is not None and origin[0] == main

    def own_param_names(self) -> list[str]:
        """The names of the parameters the fragment declares itself (what *Mutate* varies by default)."""
        return [p.name for p in self.params if self.is_own_param(p)]

    def keyframe_names(self) -> list[str]:
        """Presets named `KeyFrame.nnnn`, in numeric order."""
        from .presets import is_keyframe, keyframe_index
        return sorted((n for n in self.presets if is_keyframe(n)), key=keyframe_index)

    def log(self, level: str, text: str, file: Path | None = None, line: int = 0) -> None:
        self.messages.append(Message(level, text, file, line))


__all__ = ["FragmentSource", "LineMap", "Message", "INFO", "WARNING", "CRITICAL", "SCRIPT"]

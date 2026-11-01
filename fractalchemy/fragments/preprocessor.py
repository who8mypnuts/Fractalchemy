"""The `.frag` preprocessor — FragM's `Preprocessor::parse`, directive for directive.

Two passes, as in FragM. The first (`_parse_source`) splits the text into lines and resolves `#include "file"`
(matched at column 0 only, resolved beside the including file then on the include paths, included *textually every
time* — `Complex.frag` includes `ComplexBase.frag` twice on purpose) and `#buffershader "file"` (a separate parse).
The second (`parse`) walks the merged lines: `#preset … #endpreset` blocks are lifted out, `#replace "a" "b"` rules
apply to every later line, the host directives (`#camera`, `#buffer`, `#group`, `#vertex` / `#endvertex`, `#info`,
`#donotrun`, `#TexParameter`) are turned into comments so line numbers hold, annotated uniforms become parameters
and bare declarations, the `#define`s that steer the renderer are read, and with `move_main` the fragment's `main`
is renamed so a `void main() { fragmentariumMain(); }` can be the last definition.

The regular expressions are FragM's (`Preprocessor.h`), translated literally — Qt's `[float|double]{5,6}` and
`[true|false]{4,5}` character-class quirks are written as the alternations they meant, and a space before the
declaration's `;` is tolerated (three corpus fragments have one and FragM hands their annotation to the compiler). Every emitted line keeps
`(file, line)` in the `LineMap`, which replaces FragM's `#line` arithmetic.
"""

from __future__ import annotations

import re
from pathlib import Path

from .files import FileManager, IncludeNotFound
from .parameters import (BoolParameter, ColorParameter, FloatColorParameter, FloatParameter, GuiParameter, IntMenuParameter,
                         IntParameter, LockType, SamplerParameter, SliderType, VectorParameter)
from .source import CRITICAL, INFO, SCRIPT, WARNING, FragmentSource

MAX_INCLUDE_DEPTH = 32
MAIN_RENAMED = "fragmentariumMain"
DEFAULT_GROUP = "Default"

NUMF = r"\s*([-+]{0,1}\d{0,}(?:[.]\d{0,})?(?:[eE][+-]{0,1}\d{1,})?)\s*"
NUMI = r"\s*([-+]?\d{1,})\s*"
SLIDER_TYPE = r"\s*(Linear|Logarithmic)?"
LOCK_TYPE = r"\s*(Locked|NotLocked|NotLockable)?\s*.?$"


def _vec(n: int) -> str:
    return r"\s*\(" + ",".join([NUMF] * n) + r"\)\s*"


RE_INCLUDE = re.compile(r'^#include(.*)\s"([^"]+)"\s*$')
RE_BUFFERSHADER = re.compile(r'^#buffershader\s"([^"]+)"\s*$')
RE_FLOAT4 = re.compile(r"^\s*uniform\s+(d?vec4)\s+(\S+)\s*;\s*slider\s*\[" + _vec(4) + "," + _vec(4) + "," + _vec(4) + r"\]" + SLIDER_TYPE + LOCK_TYPE)
RE_FLOAT3 = re.compile(r"^\s*uniform\s+(d?vec3)\s+(\S+)\s*;\s*slider\s*\[" + _vec(3) + "," + _vec(3) + "," + _vec(3) + r"\]" + SLIDER_TYPE + LOCK_TYPE)
RE_FLOAT2 = re.compile(r"^\s*uniform\s+(d?vec2)\s+(\S+)\s*;\s*slider\s*\[" + _vec(2) + "," + _vec(2) + "," + _vec(2) + r"\]" + SLIDER_TYPE + LOCK_TYPE)
RE_FLOAT1 = re.compile(r"^\s*uniform\s+(float|double)\s+(\S+)\s*;\s*slider\[" + NUMF + "," + NUMF + "," + NUMF + r"\]" + SLIDER_TYPE + LOCK_TYPE)
RE_COLOR = re.compile(r"^\s*uniform\s+(d?vec3)\s+(\S+)\s*;\s*color\s*\[" + NUMF + "," + NUMF + "," + NUMF + r"\]" + LOCK_TYPE)
RE_FLOATCOLOR = re.compile(r"^\s*uniform\s+(d?vec4)\s+(\S+)\s*;\s*color\s*\[" + ",".join([NUMF] * 6) + r"\]" + LOCK_TYPE)
RE_INTMENU = re.compile(r"^\s*uniform\s+int\s+(\S+)\s*;\s*menu\[" + NUMI + r",(.*)\]" + LOCK_TYPE)
RE_INT = re.compile(r"^\s*uniform\s+int\s+(\S+)\s*;\s*slider\[" + NUMI + "," + NUMI + "," + NUMI + r"\]" + LOCK_TYPE)
RE_BOOL = re.compile(r"^\s*uniform\s+bool\s+(\S+)\s*;\s*checkbox\[\s*(true|false|True|False|TRUE|FALSE)\s*\]" + LOCK_TYPE)
RE_MAIN = re.compile(r"^\s*void\s+main\s*\(.*$")
RE_REPLACE = re.compile(r'^#replace\s+"([^"]+)"\s+"([^"]+)"\s*$')
RE_SAMPLER = re.compile(r"^\s*uniform\s+([iu]?sampler2D)\s+(\S+)\s*;\s*file\[(\S+)\].*$")
RE_SAMPLER_CHANNEL = re.compile(r"^\s*uniform\s+([iu]?sampler2D)\s+(\S+)\s*;\s*file\[(\S+),\s+(\S+)\].*$")
RE_SAMPLERCUBE = re.compile(r"^\s*uniform\s+(samplerCube)\s+(\S+)\s*;\s*file\[(.*)\].*$")
RE_DONTCLEAR = re.compile(r"^\s*#define\s+dontclearonchange$", re.IGNORECASE)
RE_ITERATIONS = re.compile(r"^\s*#define\s+iterationsbetweenredraws\s*(\d+)\s*$", re.IGNORECASE)
RE_SUBFRAMEMAX = re.compile(r"^\s*#define\s+subframemax\s*(\d+)\s*$", re.IGNORECASE)
RE_PIXELSIZE = re.compile(r"^\s*uniform\s+vec2\s+pixelSize.*$", re.IGNORECASE)
RE_DEPTHTOALPHA = re.compile(r"^\s*uniform\s+bool\s+depthtoalpha.*$", re.IGNORECASE)
RE_AUTOFOCUS = re.compile(r"^\s*uniform\s+bool\s+autofocus.*$", re.IGNORECASE)
RE_LINE_BREAK = re.compile(r"\r\n|\r|\n")
RE_PRESET_NAME = re.compile(r"^#preset\s*(.*)$", re.IGNORECASE)
ANNOTATION_REGEXES = (RE_FLOAT4, RE_FLOAT3, RE_FLOAT2, RE_FLOAT1, RE_COLOR, RE_FLOATCOLOR, RE_INTMENU, RE_INT, RE_BOOL)


def _num(text: str, warn, name: str) -> float:
    """FragM's `parseDouble`: an unreadable number is 0 with a warning."""
    try:
        return float(text) if text.strip() else 0.0
    except ValueError:
        warn(f"Could not parse double: {text} (uniform {name})")
        return 0.0


class Preprocessor:
    """Turns fragment text into a `FragmentSource` (see the module docstring).

    Args:
        files: Include-path resolution.
        move_main: Rename the fragment's `main` and append a trailing `main` that calls it (FragM's *Move main to
            end* preference, on by default).
    """

    def __init__(self, files: FileManager, move_main: bool = True):
        self.files = files
        self.move_main = move_main

    # --- entry points ----------------------------------------------------------------------------------------------
    def parse(self, text: str, path: Path | None, is_buffer_shader: bool = False, parent_version: str = "") -> FragmentSource:
        """Preprocess `text` (the contents of `path`, or an unsaved tab when None).

        Args:
            text: The fragment source.
            path: Its file (includes are resolved beside it first).
            is_buffer_shader: Parsing a `#buffershader` file (no `main` renaming; inherits `parent_version`).
            parent_version: The including fragment's `#version` line, inserted when the buffer shader has none.
        """
        source = FragmentSource()
        lines, origins = self._parse_source(source, text, path, depth=0, version_hint=parent_version if is_buffer_shader else "")
        source.fragment, source.line_map.origins = lines, origins
        self._second_pass(source, path, move_main=self.move_main and not is_buffer_shader)
        return source

    def create_autosave_fragment(self, text: str, path: Path | None) -> tuple[str, list[Path]]:
        """FragM's `createAutosaveFragment`: the text with every non-keyframe `#preset` block removed, plus the files it includes.

        The render window appends a `Default` preset with the current settings and writes the result beside the image;
        `#include` lines stay (the includes can be copied alongside).
        """
        kept: list[str] = []
        skipping = False
        for line in RE_LINE_BREAK.split(text):
            stripped = line.strip()
            if not skipping and stripped.lower().startswith("#preset"):
                name = stripped[len("#preset"):].strip()
                if not name.lower().startswith("keyframe"):
                    skipping = True
                    continue
            if skipping:
                if stripped.lower().startswith("#endpreset"):
                    skipping = False
                continue
            kept.append(line)
        probe = FragmentSource()
        self._parse_source(probe, text, path, depth=0, version_hint="")
        return "\n".join(kept), list(dict.fromkeys(probe.dependencies))

    # --- pass one: lines and includes ----------------------------------------------------------------------------------
    def _parse_source(self, source: FragmentSource, text: str, path: Path | None, depth: int, version_hint: str
                      ) -> tuple[list[str], list[tuple[int, int] | None]]:
        """Split `text`, pull in includes; returns the merged lines with their origins."""
        file_index = source.line_map.file_index(path)
        raw = RE_LINE_BREAK.split(text)
        if depth == 0:
            if raw and raw[0].startswith("#version"):
                source.version_line = raw[0].strip()
            elif version_hint:
                raw.insert(0, version_hint)      # a buffer shader takes the fragment's #version
                source.version_line = version_hint
        lines: list[str] = []
        origins: list[tuple[int, int] | None] = []
        for number, line in enumerate(raw, start=1):
            include = RE_INCLUDE.match(line)
            buffer = RE_BUFFERSHADER.match(line)
            if include:
                if include.group(1).strip():
                    source.log(CRITICAL, "'#include' expected", path, number)
                    continue
                self._include(source, include.group(2), path, number, depth, lines, origins)
            elif buffer:
                self._buffer_shader(source, buffer.group(1), path, number)
            else:
                lines.append(line)
                origins.append((file_index, number))
        if depth > 0 or self._has_includes(raw):
            lines.append("#group default")          # FragM: back to the default group after an included file
            origins.append(None)
        return lines, origins

    @staticmethod
    def _has_includes(raw: list[str]) -> bool:
        return any(RE_INCLUDE.match(line) for line in raw)

    def _include(self, source: FragmentSource, name: str, origin: Path | None, number: int, depth: int, lines, origins) -> None:
        if depth >= MAX_INCLUDE_DEPTH:
            source.log(CRITICAL, f"Include depth over {MAX_INCLUDE_DEPTH} at '{name}' — an include cycle?", origin, number)
            return
        try:
            resolved = self.files.resolve_name(name, origin)
        except IncludeNotFound as exc:
            for tried in exc.tried:
                source.log(INFO, f"Tried path: {tried}")
            source.log(CRITICAL, str(exc), origin, number)
            return
        try:
            text = resolved.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            source.log(CRITICAL, f"Unable to open: {resolved} ({exc})", origin, number)
            return
        source.log(INFO, f"Including file: {resolved}")
        source.dependencies.append(resolved)
        sub_lines, sub_origins = self._parse_source(source, text, resolved, depth + 1, "")
        lines += sub_lines
        origins += sub_origins

    def _buffer_shader(self, source: FragmentSource, name: str, origin: Path | None, number: int) -> None:
        try:
            resolved = self.files.resolve_name(name, origin)
            text = resolved.read_text(encoding="utf-8", errors="replace")
        except (IncludeNotFound, OSError) as exc:
            source.log(CRITICAL, f"Cannot include buffershader '{name}': {exc}", origin, number)
            return
        source.log(INFO, f"Including buffershader: {resolved}")
        source.dependencies.append(resolved)
        source.buffer_shader = self.parse(text, resolved, is_buffer_shader=True, parent_version=source.version_line)
        source.dependencies += source.buffer_shader.dependencies

    # --- pass two: directives, presets, annotations --------------------------------------------------------------------
    def _second_pass(self, source: FragmentSource, path: Path | None, move_main: bool) -> None:
        _Walker(source, path, move_main, self.files).run()
        source.has_pixel_size = any(RE_PIXELSIZE.match(s) for s in source.fragment)
        source.depth_to_alpha = any(RE_DEPTHTOALPHA.match(s) for s in source.fragment)
        source.auto_focus = any(RE_AUTOFOCUS.match(s) for s in source.fragment)
        if move_main:
            for text in ("", f"void main() {{ {MAIN_RENAMED}(); }}", ""):
                source.fragment.append(text)
                source.line_map.origins.append(None)
        self._check_versions(source)

    @staticmethod
    def _check_versions(source: FragmentSource) -> None:
        """The vertex part takes the fragment's `#version`; differing versions are a warning (FragM's check)."""
        if not source.vertex or not source.version_line:
            return
        if not source.vertex[0].startswith("#version"):
            source.vertex.insert(0, source.version_line)
            source.vertex_line_map.origins.insert(0, None)
        elif source.vertex[0].strip() != source.version_line:
            source.log(WARNING, f"Fragment and Vertex do not have the same #version: {source.vertex[0]} / {source.version_line}")


class _Walker:
    """The state of the second pass over one `FragmentSource` (current group, last comment, replace rules, vertex mode)."""

    def __init__(self, source: FragmentSource, path: Path | None, move_main: bool, files: FileManager):
        self.source = source
        self.path = path
        self.move_main = move_main
        self.files = files
        self.group = ""
        self.last_comment = ""
        self.replacements: dict[str, str] = {}
        self.in_vertex = False
        self.source.vertex_line_map.files = self.source.line_map.files   # shared file table

    def run(self) -> None:
        lines, origins = self.source.fragment, self.source.line_map.origins
        i = 0
        while i < len(lines):
            stripped = lines[i].strip()
            if stripped.lower().startswith("#preset"):
                self._lift_preset(i)
                continue                          # the lines moved up; re-examine index i
            line = lines[i]
            if not line.startswith("#replace"):
                line = self._apply_replacements(line)
                lines[i] = line
            self._special(i, line)
            self._annotation(i, lines[i])
            self.last_comment = stripped[2:].strip() if stripped.startswith("//") else ""
            if self.in_vertex and not stripped.lower().startswith("#vertex"):
                self.source.vertex.append(lines[i])
                self.source.vertex_line_map.origins.append(origins[i])
                lines[i] = "// " + lines[i]
            i += 1

    # --- presets ------------------------------------------------------------------------------------------------------
    def _lift_preset(self, i: int) -> None:
        lines, origins = self.source.fragment, self.source.line_map.origins
        name = RE_PRESET_NAME.match(lines[i].strip()).group(1).strip()
        start_origin = origins[i]
        del lines[i], origins[i]
        body: list[str] = []
        found_end = False
        end_origin = start_origin
        while i < len(lines):
            end_origin = origins[i] or end_origin
            if lines[i].strip().lower().startswith("#endpreset"):
                del lines[i], origins[i]
                found_end = True
                break
            body.append(lines[i])
            del lines[i], origins[i]
        if not found_end:
            self.source.log(WARNING, "Did not find #endpreset", self.path)
        self.source.presets[name] = "\n".join(body)
        if start_origin is not None and end_origin is not None:
            file = self.source.line_map.files[start_origin[0]]
            self.source.preset_spans[name] = (file, start_origin[1], end_origin[1])

    def _apply_replacements(self, line: str) -> str:
        for old, new in self.replacements.items():
            if old in line:
                line = line.replace(old, new)
        return line

    # --- host directives -----------------------------------------------------------------------------------------------
    def _special(self, i: int, line: str) -> None:
        lines = self.source.fragment
        stripped = line.strip()
        lowered = stripped.lower()
        if lowered.startswith("#camera"):
            lines[i] = "// " + stripped
            self.source.camera = stripped[len("#camera"):].strip()
        elif lowered.startswith("#texparameter"):
            lines[i] = "// " + stripped
            self._tex_parameter(stripped[len("#TexParameter"):].strip())
        elif stripped.split(" ")[0] == "#buffer":
            lines[i] = "// " + stripped
            self.source.buffer = stripped[len("#buffer"):].strip()
        elif lowered.startswith("#donotrun"):
            lines[i] = "// " + stripped
            origin = self.source.line_map.origins[i]
            if origin is not None and origin[0] == 0:          # only the user's own file decides (includes all say #donotrun)
                self.source.runnable = False
        elif lowered.startswith("#group"):
            lines[i] = "// " + stripped
            group = stripped[len("#group"):].strip()
            self.group = "" if group.lower() == "default" else group
        elif lowered.startswith("#vertex"):
            lines[i] = "// " + stripped
            self.in_vertex = True
        elif line.lower().startswith("#endvertex"):
            lines[i] = "// " + stripped
            self.in_vertex = False
        elif lowered.startswith("#info"):
            lines[i] = "// " + stripped
            self.source.log(SCRIPT, stripped[len("#info"):].strip())
        elif not self.in_vertex and self.move_main and RE_MAIN.match(line):
            lines[i] = line.replace(" main", " " + MAIN_RENAMED, 1)
        else:
            match = RE_REPLACE.match(line)
            if match:
                lines[i] = "//" + line
                self.replacements[match.group(1)] = match.group(2)

    def _tex_parameter(self, text: str) -> None:
        parts = text.split(" ")
        if len(parts) != 3:
            self.source.log(WARNING, f"#TexParameter expects three arguments! Found: {','.join(parts)}")
            return
        self.source.texture_params.setdefault(parts[0], {})[parts[1]] = parts[2]

    # --- annotated uniforms ---------------------------------------------------------------------------------------------
    def _annotation(self, i: int, line: str) -> None:
        sampler = RE_SAMPLER_CHANNEL.match(line) or RE_SAMPLER.match(line) or RE_SAMPLERCUBE.match(line)
        if sampler:
            self._sampler(i, sampler)
            return
        for regex in ANNOTATION_REGEXES:
            match = regex.match(line)
            if match:
                self._add(i, self._build(regex, match))
                return
        if RE_DONTCLEAR.match(line):
            self.source.clear_on_change = False
        elif RE_ITERATIONS.match(line):
            self.source.subframes_between_redraws = int(RE_ITERATIONS.match(line).group(1))
        elif RE_SUBFRAMEMAX.match(line):
            self.source.subframe_max = int(RE_SUBFRAMEMAX.match(line).group(1))

    def _warn(self, text: str) -> None:
        self.source.log(WARNING, text, self.path)

    def _add(self, i: int, param: GuiParameter | None) -> None:
        """Replace the annotated line by the bare declaration and record the parameter (None: a parse warning was logged)."""
        if param is None:
            return
        param.group, param.tooltip, param.line = self.group, self.last_comment, i
        self.source.fragment[i] = f"uniform {param.glsl_type} {param.name};"
        self.source.params.append(param)

    def _sampler(self, i: int, match: re.Match) -> None:
        glsl_type, name, file_name = match.group(1), match.group(2), match.group(3)
        channels = match.group(4) if match.re is RE_SAMPLER_CHANNEL else ""
        try:
            path: Path | None = self.files.resolve_name(file_name, self.path)
            self.source.log(INFO, f"Added texture: {name} -> {path}" + (f" using channels: {channels}" if channels else ""))
        except IncludeNotFound as exc:
            path = None
            self.source.log(CRITICAL, str(exc), self.path)
        self.source.textures[name] = path
        default = file_name if path is None else str(path)
        self._add(i, SamplerParameter(name, glsl_type, default=default, lock=LockType.ALWAYS_LOCKED, channels=channels))

    def _build(self, regex: re.Pattern, m: re.Match) -> GuiParameter | None:
        """A parameter from a matched annotation (FragM's `parse*Slider` / `parseColorChooser` / …)."""
        g = m.groups()
        if regex is RE_FLOAT1:
            return self._float(g)
        if regex in (RE_FLOAT2, RE_FLOAT3, RE_FLOAT4):
            return self._vector(g, {RE_FLOAT2: 2, RE_FLOAT3: 3, RE_FLOAT4: 4}[regex])
        if regex is RE_COLOR:
            rgb = tuple(_num(t, self._warn, g[1]) for t in g[2:5])
            return ColorParameter(g[1], g[0], default=rgb, lock=LockType.from_text(g[5] or ""))
        if regex is RE_FLOATCOLOR:
            return self._float_color(g)
        if regex is RE_INTMENU:
            return self._menu(g)
        if regex is RE_INT:
            return self._int(g)
        if regex is RE_BOOL:
            return BoolParameter(g[0], "bool", default=g[1].lower() == "true", lock=LockType.from_text(g[2] or ""))
        return None

    def _float(self, g) -> GuiParameter | None:
        glsl_type, name = g[0], g[1]
        try:
            from_, default, to = (float(t) for t in g[2:5])
        except ValueError:
            self._warn(f"Could not parse float value for uniform: {name}")
            return None
        return FloatParameter(name, glsl_type, default=default, from_=from_, to=to,
                              lock=LockType.from_text(g[6] or ""), slider=SliderType.from_text(g[5] or ""))

    def _vector(self, g, n: int) -> GuiParameter:
        glsl_type, name = g[0], g[1]
        numbers = [_num(t, self._warn, name) for t in g[2:2 + 3 * n]]
        from_, default, to = tuple(numbers[:n]), tuple(numbers[n:2 * n]), tuple(numbers[2 * n:3 * n])
        normalize = n >= 3 and from_ == to and name != "Up"
        if n >= 3 and from_ == to:
            from_, to = (-1.0,) * n, (1.0,) * n
        return VectorParameter(name, glsl_type, default=default, from_=from_, to=to, normalize=normalize,
                               lock=LockType.from_text(g[2 + 3 * n + 1] or ""), slider=SliderType.from_text(g[2 + 3 * n] or ""))

    def _float_color(self, g) -> GuiParameter | None:
        glsl_type, name = g[0], g[1]
        try:
            from_, default, to = (float(t) for t in g[2:5])
        except ValueError:
            self._warn(f"Could not parse color value for uniform: {name}")
            return None
        rgb = tuple(_num(t, self._warn, name) for t in g[5:8])
        return FloatColorParameter(name, glsl_type, default=(*rgb, default), from_=from_, to=to, lock=LockType.from_text(g[8] or ""))

    def _menu(self, g) -> GuiParameter | None:
        name = g[0]
        texts = tuple(t for t in g[2].split(";"))
        try:
            default = int(g[1])
        except ValueError:
            default = None
        if default is None or len(texts) < 2:
            self._warn(f"Could not parse integer value for uniform: {name}")
            return None
        return IntMenuParameter(name, "int", default=default, texts=texts, lock=LockType.from_text(g[3] or ""))

    def _int(self, g) -> GuiParameter | None:
        name = g[0]
        try:
            from_, default, to = (int(t) for t in g[1:4])
        except ValueError:
            self._warn(f"Could not parse integer value for uniform: {name}")
            return None
        return IntParameter(name, "int", default=default, from_=from_, to=to, lock=LockType.from_text(g[4] or ""))


__all__ = ["Preprocessor", "MAIN_RENAMED", "MAX_INCLUDE_DEPTH", "DEFAULT_GROUP"]

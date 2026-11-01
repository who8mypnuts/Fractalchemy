"""The compatibility layer: legacy Fragmentarium GLSL (1.10 / 1.20) made to compile on a core-profile context.

The fragment corpus writes `gl_FragColor`, `varying`, `gl_Vertex`, `gl_ProjectionMatrix` and `texture2D` — GLSL
1.20, which core-profile contexts (what moderngl creates everywhere, the only kind macOS has, what AMD enforces)
reject. FragM injects a macro patch and asks for a compatibility profile where it can; this module finishes the
idea so fragments run unchanged:

* the target version is `max(330, requested)` (a `compatibility` profile word is dropped; as in FragM, doubles
  need an explicit `#version 400` or higher);
* a vertex prelude declares `vertex_position` / `projectionMatrix` and maps the legacy names onto them; a fragment
  prelude declares `fragColor` for `gl_FragColor` and turns `varying` into `in`;
* `texture2D` / `textureCube` / `texture2DLod` / `shadow2D` become **wrapper functions** — not macros, because a
  fragment may define its own `texture()` (one in the corpus does) — emitted only for the sampler types in use;
* duplicate `varying` / `uniform` declarations that two includes both carry are dropped (1.20 tolerated them, 3.30
  does not), `attribute` becomes `in`, misplaced `#version` lines go;
* the `LineMap` is carried through, so a driver error still points at the original file and line; prelude lines
  map to None and are reported as such.

Mode `patch` keeps FragM's macro patch only (for compatibility contexts); `off` passes the text through unchanged.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace

from .const_fold import fold_const_initializers
from .source import FragmentSource, LineMap

MIN_VERSION = 330
FP64_VERSION = 400
MODES = ("modernise", "patch", "off")

RE_VERSION = re.compile(r"^\s*#version\s+(\d+)\s*(\w+)?")
RE_DECL = re.compile(r"^\s*(varying|uniform|attribute)\s+(?:(?:lowp|mediump|highp)\s+)?[\w\[\]]+\s+\w+\s*(?:\[\s*\w*\s*\])?\s*;\s*$")
RE_FP64 = re.compile(r"\b(double|dvec[234]|dmat[234](?:x[234])?)\b")
RE_FRAGDATA = re.compile(r"\bgl_FragData\s*\[\s*(\d+)\s*\]")
RE_NOISE = re.compile(r"\bnoise([1-4])\s*\(")
RE_TEXTURE_FUNC = re.compile(r"\b(?:vec4|float)\s+texture\s*\(")
RE_EXTENSION = re.compile(r"^\s*#extension\b")
RE_LEFTOVER_INCLUDE = re.compile(r"#include\b")   # only in comments by now; moderngl's own include resolver would still trip over it
LEGACY_SAMPLERS = {                       # legacy call → (wrapper source)
    "texture2D": "vec4 texture2D(sampler2D s, vec2 c) { return texture(s, c); }\n"
                 "vec4 texture2D(sampler2D s, vec2 c, float b) { return texture(s, c, b); }",
    "texture2DLod": "vec4 texture2DLod(sampler2D s, vec2 c, float l) { return textureLod(s, c, l); }",
    "textureCube": "vec4 textureCube(samplerCube s, vec3 c) { return texture(s, c); }",
    "textureCubeLod": "vec4 textureCubeLod(samplerCube s, vec3 c, float l) { return textureLod(s, c, l); }",
    "shadow2D": "vec4 shadow2D(sampler2DShadow s, vec3 c) { return vec4(texture(s, c)); }",
    "texture2DProj": "vec4 texture2DProj(sampler2D s, vec3 c) { return textureProj(s, c); }\n"
                     "vec4 texture2DProj(sampler2D s, vec4 c) { return textureProj(s, c); }",
}
NOISE_SHIM = """// legacy noiseN(): no driver implements them; a hash noise stands in
float fragm_hash(vec3 p) { p = fract(p * 0.3183099 + vec3(0.1, 0.2, 0.3)); p *= 17.0; return fract(p.x * p.y * p.z * (p.x + p.y + p.z)); }
float noise1(float x) { return fragm_hash(vec3(x, 0.0, 0.0)) * 2.0 - 1.0; }
float noise1(vec2 x) { return fragm_hash(vec3(x, 0.0)) * 2.0 - 1.0; }
float noise1(vec3 x) { return fragm_hash(x) * 2.0 - 1.0; }
vec2 noise2(vec2 x) { return vec2(noise1(x), noise1(x + 31.7)); }
vec3 noise3(vec3 x) { return vec3(noise1(x), noise1(x + 31.7), noise1(x + 71.3)); }
vec4 noise4(vec4 x) { return vec4(noise3(x.xyz), noise1(x.w)); }"""
DEFAULT_VERTEX = ["void main(void) {", "    gl_Position = gl_Vertex;", "}"]

VERTEX_PRELUDE = """layout(location = 0) in vec4 vertex_position;
#define gl_Vertex vertex_position
uniform mat4 projectionMatrix;
#define gl_ProjectionMatrix projectionMatrix
#define varying out
#define attribute in"""
FRAGMENT_PRELUDE = """#define varying in
out vec4 fragColor;
#define gl_FragColor fragColor"""
# FragM's own "compatibility patch" (DisplayWidget.h), used in `patch` mode on drivers offering a compatibility context
FRAGM_VERTEX_PATCH = """// compatibility patch
#define FRAGMPATCHED 1
#if __VERSION__ >= 330
layout(location = 0) in vec4 vertex_position;
#else
#if (__VERSION__ > 120 && __VERSION__ < 330)
in vec4 vertex_position;
#else
#if  __VERSION__ <= 120
attribute vec4 vertex_position;
#endif
#endif
#endif
#if __VERSION__ == 100 || __VERSION__ > 120
#define gl_Vertex vertex_position
#endif
uniform mat4 projectionMatrix;
#define gl_ProjectionMatrix projectionMatrix
#if __VERSION__ > 120
#define varying out
#endif
// end compatibility patch"""
FRAGM_FRAGMENT_PATCH = """// compatibility patch
#define FRAGMPATCHED 1
#if __VERSION__ > 120
#define varying in
#define texture2D texture
out vec4 fragColor;
#define gl_FragColor fragColor
#endif
// end compatibility patch"""


@dataclass(frozen=True)
class CompatOptions:
    """How to translate.

    Attributes:
        mode: `modernise` (default), `patch` (FragM's macros only) or `off`.
        context_glsl: The GLSL version the context offers (330, 400, 450, …).
        has_fp64: Whether `double` types are available (GL ≥ 4.0 or `GL_ARB_gpu_shader_fp64`).
        force_version: Compile at exactly this version regardless of the fragment's `#version` (*Test GLSL versions*).
    """
    mode: str = "modernise"
    context_glsl: int = 330
    has_fp64: bool = False
    force_version: int | None = None


class CompatError(ValueError):
    """The fragment asks for more than the context offers (a GLSL version, doubles)."""


@dataclass
class ModernSource:
    """The translated program.

    Attributes:
        vertex, fragment: The shader sources handed to the driver.
        vertex_map, fragment_map: Line maps of the emitted text (prelude lines → None).
        version: The `#version` number used.
        notes: What the layer changed (for the log and the preprocessed-source viewer).
    """
    vertex: str
    fragment: str
    vertex_map: LineMap
    fragment_map: LineMap
    version: int
    notes: list[str] = field(default_factory=list)


def requested_version(version_line: str) -> tuple[int, str]:
    """`(number, profile)` of a `#version` line; `(110, "")` when absent (FragM's rule)."""
    match = RE_VERSION.match(version_line or "")
    if not match:
        return 110, ""
    return int(match.group(1)), (match.group(2) or "")


def needs_fp64(lines: list[str]) -> bool:
    """Whether the source uses double-precision types outside comments."""
    return any(RE_FP64.search(_strip_comment(line)) for line in lines)


def target_version(source: FragmentSource, options: CompatOptions) -> int:
    """The version to compile at: `max(330, requested)`; raises `CompatError` when the context cannot provide it.

    Double precision is not inferred from the text: the includes wrap their `double` code in `#if __VERSION__ >= 400`
    (and some of it does not compile), so — as in FragM — only a fragment that asks for `#version 400` or higher
    gets doubles.
    """
    requested, _profile = requested_version(source.version_line)
    target = max(MIN_VERSION, requested) if options.force_version is None else max(MIN_VERSION, options.force_version)
    if target > options.context_glsl:
        raise CompatError(f"This fragment needs GLSL {target}; the driver offers GLSL {options.context_glsl}")
    if target >= FP64_VERSION and not options.has_fp64:
        raise CompatError("This fragment asks for GLSL 4.00 or later (double precision), which this OpenGL driver does not offer")
    return target


def modernise(source: FragmentSource, options: CompatOptions = CompatOptions()) -> ModernSource:
    """Translate a preprocessed fragment for the context described by `options`."""
    if options.mode not in MODES:
        raise ValueError(f"unknown compatibility mode {options.mode!r}")
    version = target_version(source, options) if options.mode != "off" else requested_version(source.version_line)[0]
    notes: list[str] = []
    source = _with_default_vertex(source, notes)
    if options.mode != "off":
        source = _with_folded_consts(source, notes)
    if options.mode == "off":
        vertex, vmap = _plain(source.vertex, source.vertex_line_map)
        fragment, fmap = _plain(source.fragment, source.line_map)
    elif options.mode == "patch":
        vertex, vmap = _patched(source.vertex, source.vertex_line_map, version, FRAGM_VERTEX_PATCH)
        fragment, fmap = _patched(source.fragment, source.line_map, version, FRAGM_FRAGMENT_PATCH)
        notes.append("FragM compatibility patch applied")
    else:
        vertex, vmap = _modern(source.vertex, source.vertex_line_map, version, vertex_stage=True, notes=notes)
        fragment, fmap = _modern(source.fragment, source.line_map, version, vertex_stage=False, notes=notes)
    return ModernSource(vertex, fragment, vmap, fmap, version, notes)


def _note(notes: list[str], text: str) -> None:
    """Record a remark once (several `#extension` lines would otherwise repeat it)."""
    if text not in notes:
        notes.append(text)


def _with_folded_consts(source: FragmentSource, notes: list[str]) -> FragmentSource:
    """`const` initializers that call functions (`sqrt` after Math.frag redefined it) become literals (`const_fold.py`)."""
    fragment, folded = fold_const_initializers(source.fragment)
    if not folded:
        return source
    _note(notes, "const initializer evaluated at build time (a redefined function made it non-constant): " + ", ".join(folded))
    return replace(source, fragment=fragment)


def _with_default_vertex(source: FragmentSource, notes: list[str]) -> FragmentSource:
    """A fragment without a `#vertex` block gets the pass-through vertex shader (FragM refuses such fragments)."""
    if source.vertex:
        return source
    lines = [source.version_line] if source.version_line else []
    lines += DEFAULT_VERTEX
    notes.append("no #vertex block: default pass-through vertex shader used")
    return replace(source, vertex=lines, vertex_line_map=LineMap(list(source.line_map.files), [None] * len(lines)))


# --- the three modes -------------------------------------------------------------------------------------------------
def _plain(lines: list[str], line_map: LineMap) -> tuple[str, LineMap]:
    return "\n".join(lines), line_map.copy()


def _patched(lines: list[str], line_map: LineMap, version: int, patch: str) -> tuple[str, LineMap]:
    """FragM's `applyShaderPatch`: the version line first, the patch, then the source without its `#version`."""
    out = _Emitter(line_map)
    out.generated(f"#version {version}")
    out.generated(patch)
    for text, origin in zip(lines, line_map.origins):
        if RE_VERSION.match(text):
            continue
        out.add(text, origin)
    return out.result()


def _modern(lines: list[str], line_map: LineMap, version: int, vertex_stage: bool, notes: list[str]) -> tuple[str, LineMap]:
    out = _Emitter(line_map)
    out.generated(f"#version {version}" + (" core" if version >= 150 else ""))
    body = [_strip_comment(text) for text in lines]
    for text, code, origin in zip(lines, body, line_map.origins):
        if RE_EXTENSION.match(code):
            out.add(text, origin)        # #extension must precede everything but #version: hoisted above the prelude
    out.generated(VERTEX_PRELUDE if vertex_stage else FRAGMENT_PRELUDE)
    if not vertex_stage:
        _fragment_shims(out, body, notes)
    seen: set[str] = set()
    for text, code, origin in zip(lines, body, line_map.origins):
        if RE_VERSION.match(text) or RE_EXTENSION.match(code):
            _note(notes, ("#version" if RE_VERSION.match(text) else "#extension") + " line moved to the top")
            out.add("// " + text, origin)
            continue
        if RE_DECL.match(code):
            key = re.sub(r"\s+", " ", code.strip())
            if key in seen:
                out.add("// duplicate declaration removed: " + text.strip(), origin)
                continue
            seen.add(key)
        out.add(_rewrite_line(text, code), origin)
    return out.result()


def _fragment_shims(out: "_Emitter", body: list[str], notes: list[str]) -> None:
    """Wrapper functions for the legacy texture calls in use, `gl_FragData` outputs, the noise shim."""
    joined = "\n".join(body)
    for legacy, wrapper in LEGACY_SAMPLERS.items():
        if re.search(rf"\b{legacy}\s*\(", joined):
            out.generated(wrapper)       # emitted before any user function called `texture`, so the built-in is still visible
    if RE_TEXTURE_FUNC.search(joined):
        notes.append("the fragment defines its own texture() function; the texture2D wrappers precede it")
    indices = sorted({int(m) for m in RE_FRAGDATA.findall(joined)})
    for index in indices:
        out.generated(f"layout(location = {index}) out vec4 fragData_{index};")
    if indices:
        notes.append("gl_FragData outputs declared")
    if RE_NOISE.search(joined):
        out.generated(NOISE_SHIM)
        notes.append("legacy noise functions replaced by a hash noise")


def _rewrite_line(text: str, code: str) -> str:
    """Per-line rewrites that cannot be macros: `gl_FragData[n]`, `attribute`."""
    if "gl_FragData" in code:
        text = RE_FRAGDATA.sub(lambda m: f"fragData_{m.group(1)}", text)
    if code.lstrip().startswith("attribute "):
        text = text.replace("attribute ", "in ", 1)
    return text


def _strip_comment(line: str) -> str:
    """The line without a trailing `//` comment (string literals do not occur in GLSL)."""
    index = line.find("//")
    return line if index < 0 else line[:index]


class _Emitter:
    """Collects output lines with their origins."""

    def __init__(self, line_map: LineMap):
        self.files = list(line_map.files)
        self.lines: list[str] = []
        self.origins: list[tuple[int, int] | None] = []

    def add(self, text: str, origin: tuple[int, int] | None) -> None:
        self.lines.append(RE_LEFTOVER_INCLUDE.sub("#_include", text))
        self.origins.append(origin)

    def generated(self, text: str) -> None:
        for line in text.split("\n"):
            self.add(line, None)

    def result(self) -> tuple[str, LineMap]:
        return "\n".join(self.lines), LineMap(self.files, self.origins)


__all__ = ["CompatOptions", "CompatError", "ModernSource", "modernise", "target_version", "requested_version", "needs_fp64",
           "MODES", "MIN_VERSION", "FP64_VERSION"]

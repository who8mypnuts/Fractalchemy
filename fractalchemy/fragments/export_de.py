"""*Export DE…*: a fragment's distance estimator as stand-alone code — GLSL, a Shadertoy, a Unity shader or an Unreal
include — with the slider values baked in as constants.

The preprocessed fragment (includes expanded, locks substituted) is scanned for its functions; the closure of `DE`
(every function it calls, transitively, every overload of those names) is kept together with the `#define`s, the
global declarations and the uniforms they mention — each uniform becoming `const <type> <name> = <value>;` from the
current parameter values, so the exported code is exactly what the viewport shows. The GLSL target is that text; the
Shadertoy target adds a small raymarcher `mainImage` with the fragment's camera; the HLSL targets (Unity's ShaderLab
file, Unreal's `.ush` include plus a Custom-node snippet) translate the GLSL mechanically — types, built-in names,
single-scalar vector constructors, `mod` — and list in `notes` what a human must still check (matrix products need
`mul`, textures are not carried over).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

TARGETS = ("glsl", "shadertoy", "unity", "unreal")
TARGET_LABELS = {"glsl": "GLSL (baked DE)", "shadertoy": "Shadertoy (DE + raymarcher)", "unity": "Unity ShaderLab (HLSL)",
                 "unreal": "Unreal .ush include (HLSL)"}
TARGET_SUFFIXES = {"glsl": ".glsl", "shadertoy": ".glsl", "unity": ".shader", "unreal": ".ush"}
TYPES = r"(?:void|float|int|bool|uint|double|[biud]?vec[234]|d?mat[234](?:x[234])?)"
RE_FUNCTION_HEAD = re.compile(rf"^[ \t]*({TYPES})\s+([A-Za-z_]\w*)\s*\(([^)]*)\)\s*\{{", re.MULTILINE)
RE_UNIFORM = re.compile(rf"^[ \t]*uniform\s+({TYPES})\s+([A-Za-z_]\w*)\s*;.*$", re.MULTILINE)
RE_DEFINE = re.compile(r"^[ \t]*#define\s+([A-Za-z_]\w*)(.*)$", re.MULTILINE)
RE_GLOBAL = re.compile(rf"^[ \t]*((?:const\s+)?{TYPES}\s+([A-Za-z_]\w*)\s*(?:=[^;]*)?;)", re.MULTILINE)
RE_STRUCT = re.compile(r"^[ \t]*struct\s+([A-Za-z_]\w*)\s*\{[^}]*\}\s*;", re.MULTILINE | re.DOTALL)
WORD = re.compile(r"\b[A-Za-z_]\w*\b")
CAMERA = ("Eye", "Target", "Up", "FOV")


@dataclass
class Function:
    name: str
    return_type: str
    text: str
    start: int
    calls: set[str] = field(default_factory=set)


@dataclass
class Extraction:
    """What the scan found (see the module docstring)."""
    functions: list[Function]
    defines: list[str]
    globals: list[str]
    structs: list[str]
    uniforms: list[tuple[str, str]]           # (type, name) the closure mentions
    notes: list[str] = field(default_factory=list)


@dataclass
class DEExport:
    target: str
    code: str
    suffix: str
    notes: list[str] = field(default_factory=list)


# --- scanning -------------------------------------------------------------------------------------------------------
def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", text)


def _function_end(text: str, open_brace: int) -> int:
    depth = 0
    for i in range(open_brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i + 1
    return len(text)


def parse_functions(text: str) -> list[Function]:
    """Every function definition in `text` (comments stripped), in order."""
    out = []
    for match in RE_FUNCTION_HEAD.finditer(text):
        end = _function_end(text, match.end() - 1)
        body = text[match.start():end]
        function = Function(match.group(2), match.group(1), body.strip("\n"), match.start())
        function.calls = set(WORD.findall(body[len(match.group(0)):])) | set(WORD.findall(match.group(3)))
        out.append(function)
    return out


def extract_de(fragment_text: str, root: str = "DE") -> Extraction:
    """The closure of `root` and everything it needs (`ValueError` when `root` is not defined)."""
    text = strip_comments(fragment_text)
    functions = parse_functions(text)
    if not any(f.name == root for f in functions):
        raise ValueError(f"the fragment does not define {root}")
    extraction = _closure(text, functions, [root])
    init = _needed_init(extraction, functions, text)
    if init:
        extraction = _closure(text, functions, [root, "init"], keep_init=init)
        extraction.notes.append("the fragment sets globals in init(): call init() once before DE()")
    return extraction


def _closure(text: str, functions: list[Function], roots: list[str], keep_init: list[Function] | None = None) -> Extraction:
    by_name: dict[str, list[Function]] = {}
    for function in functions:
        if function.name == "init" and keep_init is not None and function not in keep_init:
            continue                                   # the include's empty `void init() {}` stub, not the user's
        by_name.setdefault(function.name, []).append(function)
    wanted, queue = set(), list(roots)
    while queue:
        name = queue.pop()
        if name in wanted or name not in by_name:
            continue
        wanted.add(name)
        for function in by_name[name]:
            queue += [n for n in function.calls if n in by_name and n not in wanted]
    kept = [f for f in functions if f.name in wanted and (f.name != "init" or keep_init is None or f in keep_init)]
    words = set()
    for function in kept:
        words |= function.calls | set(WORD.findall(function.text))
    inside = [(f.start, f.start + len(f.text)) for f in functions]

    def outside(position: int) -> bool:
        return not any(s <= position < e for s, e in inside)

    defines = [m.group(0).strip() for m in RE_DEFINE.finditer(text) if m.group(1) in words and outside(m.start())]
    structs = [m.group(0).strip() for m in RE_STRUCT.finditer(text) if m.group(1) in words]
    uniforms = [(m.group(1), m.group(2)) for m in RE_UNIFORM.finditer(text) if m.group(2) in words]
    uniform_names = {name for _t, name in uniforms}
    globals_ = [m.group(1).strip() for m in RE_GLOBAL.finditer(text)
                if m.group(2) in words and m.group(2) not in uniform_names and outside(m.start()) and "uniform" not in m.group(1)]
    return Extraction(kept, defines, globals_, structs, uniforms)


def _needed_init(extraction: Extraction, functions: list[Function], text: str) -> list[Function]:
    """FragM fragments set globals in `init()` (`providesInit`): the `init` definitions touching a global the closure reads."""
    if any(f.name == "init" for f in extraction.functions):
        return []
    used = {WORD.findall(g)[-1] for g in extraction.globals if WORD.findall(g)}
    return [f for f in functions if f.name == "init" and f.calls & used]


# --- baking --------------------------------------------------------------------------------------------------------
def glsl_literal(glsl_type: str, value: Any) -> str:
    """A GLSL constant expression of `value` as `glsl_type` (`vec3(1.0, 2.0, 3.0)`, `true`, `3`, `1.5`)."""
    if glsl_type == "bool":
        return "true" if value else "false"
    if glsl_type in ("int", "uint"):
        return str(int(value))
    if glsl_type in ("float", "double"):
        return _float(value)
    if glsl_type.startswith(("vec", "dvec")):
        n = int(glsl_type[-1])
        parts = list(value)[:n] if isinstance(value, (tuple, list)) else [value] * n
        while len(parts) < n:
            parts.append(0.0)
        return f"vec{n}({', '.join(_float(v) for v in parts)})"
    if glsl_type.startswith(("ivec", "bvec")):
        n = int(glsl_type[-1])
        parts = list(value)[:n] if isinstance(value, (tuple, list)) else [value] * n
        return f"{glsl_type}({', '.join(str(int(v)) if glsl_type[0] == 'i' else ('true' if v else 'false') for v in parts)})"
    raise ValueError(f"cannot bake a {glsl_type}")


def _float(value: Any) -> str:
    text = f"{float(value):.9g}"
    if "e" in text or "." in text or "inf" in text or "nan" in text:
        return text
    return text + ".0"


def baked_glsl(extraction: Extraction, values: dict[str, Any], name: str = "fragment") -> tuple[str, list[str]]:
    """The extraction as GLSL with the uniforms baked from `values`; returns the text and notes (uniforms without a value)."""
    notes: list[str] = []
    lines = [f"// {name}: distance estimator exported by Fractalchemy (the slider values baked in as constants)", ""]
    lines += extraction.defines
    for glsl_type, uniform in extraction.uniforms:
        if uniform in values:
            try:
                lines.append(f"const {glsl_type} {uniform} = {glsl_literal(glsl_type, values[uniform])};")
                continue
            except (ValueError, TypeError):
                pass
        if glsl_type.startswith("sampler"):
            notes.append(f"{uniform} is a texture: bind it yourself (textures are not exported)")
            lines.append(f"uniform {glsl_type} {uniform};")
        else:
            notes.append(f"{uniform} has no value: left as a uniform")
            lines.append(f"uniform {glsl_type} {uniform};")
    lines += extraction.structs + extraction.globals
    lines.append("")
    for function in extraction.functions:
        lines.append(function.text)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n", notes


# --- targets ---------------------------------------------------------------------------------------------------------
SHADERTOY_MAIN = """
// --- a small raymarcher around DE (camera from the fragment's settings) -----------------------------------------
const vec3 camEye = {eye};
const vec3 camTarget = {target};
const vec3 camUp = {up};
const float camFov = {fov};

vec3 calcNormal(vec3 p) {{
    vec2 e = vec2(1e-4, 0.0);
    return normalize(vec3(DE(p + e.xyy) - DE(p - e.xyy), DE(p + e.yxy) - DE(p - e.yxy), DE(p + e.yyx) - DE(p - e.yyx)));
}}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {{
    {init_call}vec2 uv = (fragCoord - 0.5 * iResolution.xy) / iResolution.y;
    vec3 dir = normalize(camTarget - camEye);
    vec3 right = normalize(cross(dir, camUp));
    vec3 up = cross(right, dir);
    vec3 rd = normalize(dir + camFov * (uv.x * right + uv.y * up));
    float t = 0.0;
    float d = 1.0;
    int steps = 0;
    for (int i = 0; i < 256; i++) {{
        d = DE(camEye + rd * t);
        if (d < 1e-4 * t || t > 50.0) break;
        t += d * 0.9;
        steps = i;
    }}
    vec3 col = vec3(0.05, 0.06, 0.09);
    if (d < 1e-4 * t) {{
        vec3 p = camEye + rd * t;
        vec3 n = calcNormal(p);
        float diff = max(dot(n, normalize(vec3(0.6, 0.8, -0.4))), 0.0);
        float ao = 1.0 - float(steps) / 256.0;
        col = (0.15 + 0.85 * diff) * ao * (0.5 + 0.5 * n);
    }}
    fragColor = vec4(pow(col, vec3(0.4545)), 1.0);
}}
"""

HLSL_PRELUDE = """// GLSL helpers the translation relies on
float glsl_mod(float x, float y) { return x - y * floor(x / y); }
float2 glsl_mod(float2 x, float2 y) { return x - y * floor(x / y); }
float3 glsl_mod(float3 x, float3 y) { return x - y * floor(x / y); }
float4 glsl_mod(float4 x, float4 y) { return x - y * floor(x / y); }
float2 glsl_mod(float2 x, float y) { return x - y * floor(x / y); }
float3 glsl_mod(float3 x, float y) { return x - y * floor(x / y); }
float4 glsl_mod(float4 x, float y) { return x - y * floor(x / y); }
"""

UNITY_TEMPLATE = """Shader "Fractalchemy/{name}"
{{
    Properties
    {{
        _MaxSteps ("Max steps", Int) = 256
        _Epsilon ("Surface epsilon", Float) = 0.0002
    }}
    SubShader
    {{
        Tags {{ "RenderType" = "Opaque" }}
        Pass
        {{
            Cull Front
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "UnityCG.cginc"

{code}

            struct appdata {{ float4 vertex : POSITION; }};
            struct v2f {{ float4 pos : SV_POSITION; float3 world : TEXCOORD0; }};
            int _MaxSteps;
            float _Epsilon;

            v2f vert(appdata v)
            {{
                v2f o;
                o.pos = UnityObjectToClipPos(v.vertex);
                o.world = mul(unity_ObjectToWorld, v.vertex).xyz;
                return o;
            }}

            float3 calcNormal(float3 p)
            {{
                float2 e = float2(1e-4, 0.0);
                return normalize(float3(DE(p + e.xyy) - DE(p - e.xyy), DE(p + e.yxy) - DE(p - e.yxy), DE(p + e.yyx) - DE(p - e.yyx)));
            }}

            float4 frag(v2f i) : SV_Target
            {{
                {init_call}// march in object space from the camera through this fragment's position on the proxy cube
                float3 ro = mul(unity_WorldToObject, float4(_WorldSpaceCameraPos, 1.0)).xyz;
                float3 rd = normalize(mul(unity_WorldToObject, float4(i.world, 1.0)).xyz - ro);
                float t = 0.0;
                float d = 1.0;
                for (int s = 0; s < _MaxSteps; s++)
                {{
                    d = DE(ro + rd * t);
                    if (d < _Epsilon * max(t, 1.0) || t > 100.0) break;
                    t += d * 0.9;
                }}
                if (d > _Epsilon * max(t, 1.0)) discard;
                float3 n = calcNormal(ro + rd * t);
                float diff = max(dot(n, normalize(float3(0.6, 0.8, -0.4))), 0.0);
                return float4((0.15 + 0.85 * diff) * (0.5 + 0.5 * n), 1.0);
            }}
            ENDHLSL
        }}
    }}
}}
"""

UNREAL_TEMPLATE = """// {name}.ush — the distance estimator for Unreal's Custom material node (HLSL).
// Put this file under <Project>/Shaders/ (and register the folder with AddShaderSourceDirectoryMapping in a module's
// StartupModule), then in a Custom node use:
//     #include "/Project/{name}.ush"
//     return RaymarchDE(CameraPosition, normalize(WorldPosition - CameraPosition));
// The Custom node must have "Include File Paths" set to the .ush and an output type of CMOT Float3.
#pragma once

{code}

float3 CalcNormalDE(float3 p)
{{
    float2 e = float2(1e-4, 0.0);
    return normalize(float3(DE(p + e.xyy) - DE(p - e.xyy), DE(p + e.yxy) - DE(p - e.yxy), DE(p + e.yyx) - DE(p - e.yyx)));
}}

float3 RaymarchDE(float3 ro, float3 rd)
{{
    {init_call}float t = 0.0;
    float d = 1.0;
    for (int i = 0; i < 256; i++)
    {{
        d = DE(ro + rd * t);
        if (d < 2e-4 * max(t, 1.0) || t > 100.0) break;
        t += d * 0.9;
    }}
    if (d > 2e-4 * max(t, 1.0)) return float3(0.0, 0.0, 0.0);
    float3 n = CalcNormalDE(ro + rd * t);
    float diff = max(dot(n, normalize(float3(0.6, 0.8, -0.4))), 0.0);
    return (0.15 + 0.85 * diff) * (0.5 + 0.5 * n);
}}
"""

HLSL_TYPES = {"vec2": "float2", "vec3": "float3", "vec4": "float4", "ivec2": "int2", "ivec3": "int3", "ivec4": "int4", "bvec2": "bool2",
              "bvec3": "bool3", "bvec4": "bool4", "mat2": "float2x2", "mat3": "float3x3", "mat4": "float4x4", "dvec2": "double2",
              "dvec3": "double3", "dvec4": "double4", "uvec2": "uint2", "uvec3": "uint3", "uvec4": "uint4"}
HLSL_FUNCTIONS = {"mix": "lerp", "fract": "frac", "inversesqrt": "rsqrt", "dFdx": "ddx", "dFdy": "ddy", "mod": "glsl_mod"}


def to_hlsl(glsl: str) -> tuple[str, list[str]]:
    """A mechanical GLSL → HLSL translation and the things it could not settle."""
    notes: list[str] = []
    text = glsl
    for glsl_type, hlsl_type in HLSL_TYPES.items():
        text = re.sub(rf"\b{glsl_type}\b", hlsl_type, text)
    for glsl_fn, hlsl_fn in HLSL_FUNCTIONS.items():
        text = re.sub(rf"\b{glsl_fn}\s*\(", f"{hlsl_fn}(", text)
    text = _rewrite_calls(text, "atan", _atan_to_atan2, notes)
    for n in (2, 3, 4):
        text = _rewrite_calls(text, f"float{n}", lambda args, n=n: _splat(f"float{n}", args), notes)
    if re.search(r"\bfloat[234]x[234]\b", text):
        notes.append("matrices: HLSL multiplies with mul(m, v) and stores row-major — check every matrix product and constructor")
    if "texture(" in text or "sampler" in text:
        notes.append("textures are not translated: declare a Texture2D + SamplerState and replace texture() calls")
    if "gl_FragCoord" in text or "gl_" in text:
        notes.append("gl_* built-ins have no HLSL equivalent; pass the values in")
    return HLSL_PRELUDE + "\n" + text, notes


def _split_args(inner: str) -> list[str]:
    args, depth, current = [], 0, []
    for ch in inner:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == "," and depth == 0:
            args.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if current or args:
        args.append("".join(current).strip())
    return args


def _rewrite_calls(text: str, name: str, rewrite, notes: list[str]) -> str:
    """Apply `rewrite(args) -> str | None` to every call of `name` (None keeps the call)."""
    out, position = [], 0
    pattern = re.compile(rf"\b{name}\s*\(")
    while True:
        match = pattern.search(text, position)
        if match is None:
            out.append(text[position:])
            break
        depth, i = 1, match.end()
        while i < len(text) and depth:
            depth += 1 if text[i] == "(" else -1 if text[i] == ")" else 0
            i += 1
        inner = text[match.end():i - 1]
        replaced = rewrite(_split_args(_rewrite_calls(inner, name, rewrite, notes)))
        out.append(text[position:match.start()])
        out.append(replaced if replaced is not None else f"{name}({_rewrite_calls(inner, name, rewrite, notes)})")
        position = i
    return "".join(out)


def _atan_to_atan2(args: list[str]) -> str | None:
    return f"atan2({args[0]}, {args[1]})" if len(args) == 2 else None


def _splat(hlsl_type: str, args: list[str]) -> str | None:
    return f"(({hlsl_type})({args[0]}))" if len(args) == 1 else None


def export_de(fragment_text: str, values: dict[str, Any], target: str, name: str = "fragment") -> DEExport:
    """The distance estimator of a preprocessed fragment as `target` code (see `TARGETS`).

    Raises:
        ValueError: No `DE`, or an unknown target.
    """
    if target not in TARGETS:
        raise ValueError(f"unknown target {target!r}")
    extraction = extract_de(fragment_text)
    glsl, notes = baked_glsl(extraction, values, name)
    notes = extraction.notes + notes
    safe = re.sub(r"\W+", "_", name).strip("_") or "fragment"
    init_call = "init();\n    " if any(f.name == "init" for f in extraction.functions) else ""
    if target == "glsl":
        return DEExport(target, glsl, TARGET_SUFFIXES[target], notes)
    if target == "shadertoy":
        camera = {key: values.get(key) for key in CAMERA}
        main = SHADERTOY_MAIN.format(eye=glsl_literal("vec3", camera["Eye"] or (0.0, 0.0, -4.0)), target=glsl_literal("vec3", camera["Target"] or (0.0, 0.0, 0.0)),
                                     up=glsl_literal("vec3", camera["Up"] or (0.0, 1.0, 0.0)), fov=_float(camera["FOV"] if camera["FOV"] is not None else 0.6),
                                     init_call=init_call)
        notes.append("Shadertoy: paste into the Image tab; a #version line must not be present (none is)")
        return DEExport(target, glsl + main, TARGET_SUFFIXES[target], notes)
    hlsl, hlsl_notes = to_hlsl(glsl)
    notes += hlsl_notes
    if target == "unity":
        return DEExport(target, UNITY_TEMPLATE.format(name=safe, code=_indent(hlsl, 12), init_call=init_call), TARGET_SUFFIXES[target], notes)
    return DEExport(target, UNREAL_TEMPLATE.format(name=safe, code=hlsl, init_call=init_call), TARGET_SUFFIXES[target], notes)


def _indent(text: str, spaces: int) -> str:
    pad = " " * spaces
    return "\n".join(pad + line if line.strip() else line for line in text.splitlines())


__all__ = ["TARGETS", "TARGET_LABELS", "TARGET_SUFFIXES", "DEExport", "Extraction", "extract_de", "baked_glsl", "glsl_literal", "to_hlsl", "export_de"]

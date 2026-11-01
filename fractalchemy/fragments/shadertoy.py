"""Shadertoy → fragment: wrap `mainImage` with Shadertoy's uniforms, map channels to `file[…]` textures or buffers.

An *Image* shader becomes one fragment: the Shadertoy uniforms (`iResolution`, `iTime` / `iGlobalTime`, `iTimeDelta`,
`iFrame`, `iMouse`, `iDate`, `iChannelResolution`) are declared on top of the host's `pixelSize` / `time` /
`subframe`, every `iChannelN` that is given a file becomes a `uniform sampler2D iChannelN; file[…]`, and a `main`
calls `mainImage(gl_FragColor, gl_FragCoord.xy)`. An *Image + Buffer A* pair becomes two files: Buffer A is the
main program whose self-reading channel is the `backbuffer` (Shadertoy's feedback), and Image is its
`#buffershader`, reading Buffer A through `frontbuffer`. Shadertoy's multi-buffer graphs beyond that (B, C, D,
cubemaps, sound, keyboard, video) are not mapped — the converter says so in its notes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

RE_MAIN_IMAGE = re.compile(r"\bvoid\s+mainImage\s*\(")
RE_CHANNEL_USE = re.compile(r"\biChannel([0-3])\b")
RE_KEYBOARD = re.compile(r"\b(iKeyboard|iSampleRate|iChannelTime|iSound)\b")
CHANNELS = 4

PRELUDE = """#info Imported from Shadertoy: {name}
#include "Shadertoy.frag"
#group Shadertoy
// Mouse position as Shadertoy's iMouse.xy (pixels); the zw pair is left at zero
uniform vec2 MousePixel; slider[(0,0),(0,0),(8192,8192)]
uniform float Speed; slider[0,1,10]
uniform int subframe;
float iTime = iGlobalTime * Speed;
float iTimeDelta = 1.0 / 60.0;
int iFrame = subframe;
float iFrameRate = 60.0;
vec4 iMouse = vec4(MousePixel, 0.0, 0.0);
vec4 iDate = vec4(2024.0, 1.0, 1.0, mod(iTime, 86400.0));
vec3 iChannelResolution[4] = vec3[4](iResolution, iResolution, iResolution, iResolution);
"""

BUFFER_PRELUDE = """#buffer RGBA32F
#buffershader "{image_file}"
#define DontClearOnChange
uniform sampler2D backbuffer;
"""

IMAGE_SHADER_PRELUDE = """#donotrun
// Shadertoy Image pass of {name}: reads Buffer A (the accumulation) through frontbuffer
#vertex
varying vec2 coord;
void main(void) {{ gl_Position = gl_Vertex; coord = (gl_ProjectionMatrix * gl_Vertex).xy; }}
#endvertex
varying vec2 coord;
uniform sampler2D frontbuffer;
uniform vec2 pixelSize;
uniform float time;
uniform int subframe;
vec3 iResolution = vec3(1.0 / pixelSize.x, 1.0 / pixelSize.y, 1.0);
float iTime = time;
float iGlobalTime = time;
float iTimeDelta = 1.0 / 60.0;
int iFrame = subframe;
vec4 iMouse = vec4(0.0);
vec4 iDate = vec4(2024.0, 1.0, 1.0, mod(time, 86400.0));
vec3 iChannelResolution[4] = vec3[4](iResolution, iResolution, iResolution, iResolution);
"""


@dataclass
class Conversion:
    """What the converter produced.

    Attributes:
        main: The fragment text (Buffer A when there is one, else Image).
        image: The `#buffershader` file text (Image) when Buffer A is used, else None.
        image_file: The file name the main fragment expects the image shader under.
        notes: What was mapped and what could not be.
    """
    main: str
    image: str | None = None
    image_file: str = ""
    notes: list[str] = field(default_factory=list)


def convert(name: str, image_code: str, buffer_a_code: str = "", channels: list[str | None] | None = None,
            buffer_channels: list[str | None] | None = None, feedback_channel: int = 0) -> Conversion:
    """Turn Shadertoy code into fragment text (see the module docstring).

    Args:
        name: The shader's name (for `#info` and file names).
        image_code: The Image tab (must define `mainImage`).
        buffer_a_code: The Buffer A tab, or empty.
        channels: Image's iChannel0..3: a texture file name, `"bufferA"` (when Buffer A exists) or None.
        buffer_channels: Buffer A's iChannel0..3 (`"self"` for its own previous frame, a file name, or None).
        feedback_channel: Which of Buffer A's channels is its own previous frame (Shadertoy usually uses 0).

    Raises:
        ValueError: When a pass has no `mainImage`.
    """
    channels = list(channels or [None] * CHANNELS) + [None] * CHANNELS
    buffer_channels = list(buffer_channels or [None] * CHANNELS) + [None] * CHANNELS
    notes: list[str] = []
    if not RE_MAIN_IMAGE.search(image_code):
        raise ValueError("the Image code has no `void mainImage(out vec4 fragColor, in vec2 fragCoord)`")
    for code in (image_code, buffer_a_code):
        if RE_KEYBOARD.search(code):
            notes.append("keyboard / sound / channel-time inputs are not available; they read as zero")
    if not buffer_a_code.strip():
        return Conversion(_image_only(name, image_code, channels, notes), notes=notes)
    if not RE_MAIN_IMAGE.search(buffer_a_code):
        raise ValueError("the Buffer A code has no `mainImage`")
    safe = _safe(name)
    image_file = f"{safe}-image.frag"
    main = PRELUDE.format(name=name) + BUFFER_PRELUDE.format(image_file=image_file)
    main += _channel_declarations(buffer_channels, "self", "backbuffer", notes, feedback_channel, used_channels(buffer_a_code))
    main += _keyboard_stub() + "\n" + _strip_version(buffer_a_code) + _main_call("gl_FragColor")
    image = IMAGE_SHADER_PRELUDE.format(name=name) + _channel_declarations(channels, "bufferA", "frontbuffer", notes, -1, used_channels(image_code))
    image += _keyboard_stub() + "\n" + _strip_version(image_code) + _main_call("gl_FragColor")
    notes.append(f"Buffer A is the main program (its channel {feedback_channel} reads the previous frame); Image is {image_file}")
    return Conversion(main, image, image_file, notes)


def _image_only(name: str, code: str, channels: list, notes: list[str]) -> str:
    text = PRELUDE.format(name=name) + _channel_declarations(channels, None, None, notes, -1, used_channels(code))
    return text + _keyboard_stub() + "\n" + _strip_version(code) + _main_call("gl_FragColor")


def _channel_declarations(channels: list, special: str | None, special_uniform: str | None, notes: list[str], feedback: int = -1,
                          used: list[int] | None = None) -> str:
    lines = []
    for index in range(CHANNELS):
        if used is not None and index not in used:
            continue
        source = channels[index]
        if source is None:
            if index == feedback and special_uniform:
                lines.append(f"#define iChannel{index} {special_uniform}")
            else:
                lines.append(f"uniform sampler2D iChannel{index}; file[checker.png]")
                notes.append(f"iChannel{index} has no input: a placeholder texture name was written (change the file[…] line)")
        elif special and source == special:
            lines.append(f"#define iChannel{index} {special_uniform}")
        else:
            lines.append(f"uniform sampler2D iChannel{index}; file[{source}]")
    return "\n".join(lines) + "\n"


def _keyboard_stub() -> str:
    return "vec4 shadertoyTexelFetch(sampler2D s, ivec2 p) { return texelFetch(s, p, 0); }\n"


def _strip_version(code: str) -> str:
    return re.sub(r"^\s*#version[^\n]*\n", "", code, count=1)


def _main_call(out: str) -> str:
    return f"\nvoid main(void) {{\n\tvec4 shadertoyColor = vec4(0.0);\n\tmainImage(shadertoyColor, gl_FragCoord.xy);\n\t{out} = shadertoyColor;\n}}\n"


def _safe(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in name.strip()) or "shadertoy"


def used_channels(code: str) -> list[int]:
    """The iChannel indices the code reads."""
    return sorted({int(m.group(1)) for m in RE_CHANNEL_USE.finditer(code)})


__all__ = ["Conversion", "convert", "used_channels"]

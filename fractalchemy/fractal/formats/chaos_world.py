"""Chaotica `.chaos` worlds → Flame objects (read only).

Chaotica stores each IFS as iterators with angle/length affines, a list of
transforms with `type_name` + params (flam3-compatible names), per-iterator
selection weights (xaos) and a flam3 palette. Two camera styles exist: the
older `scale` camera and the `flam3 camera` with `sensor_width`, whose
"Viewing transform" is the final xform.
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from pathlib import Path

from ..scene import Affine, Camera, Coloring, Flame, XForm
from ..variations import normalize

IFS_TAGS = ("flam3_IFS", "IFS")
# Chaotica's brightness scale differs from Apophysis's; this factor makes the bundled
# samples look comparable. It is a heuristic — adjust in one place if renders look off.
BRIGHTNESS_SCALE = 0.2


class ChaosParseError(ValueError):
    """The XML was not a Chaotica world we can read."""


def parse_file(path: Path) -> list[Flame]:
    """Every IFS in the world that has at least one iterator."""
    return [f for f in (_flame_from_ifs(ifs) for ifs in _ifs_elements(path)) if f.xforms]


def flame_names(path: Path) -> list[str]:
    """IFS names, cheaply."""
    return [ifs.get("name", "IFS") for ifs in _ifs_elements(path) if ifs.find("node[@name='iterators']/iterator") is not None]


def _ifs_elements(path: Path) -> list[ET.Element]:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise ChaosParseError(f"{path.name} is not valid Chaotica XML: {exc}") from exc
    return [el for tag in IFS_TAGS for el in root.iter(tag)]


# --- conversion ---------------------------------------------------------------
def _flame_from_ifs(ifs: ET.Element) -> Flame:
    flame = Flame(name=ifs.get("name", "IFS"), source_version="Chaotica")
    unsupported: set[str] = set()
    imaging = ifs.find("imaging")
    width = _int(imaging, "image_width", 800)
    height = _int(imaging, "image_height", 600)
    flame.camera = _camera(ifs.find("camera"), width, height)
    flame.coloring = _coloring(imaging)
    iterators = ifs.findall("node[@name='iterators']/iterator")
    flame.xforms = [_xform_from_iterator(it, unsupported) for it in iterators]
    _apply_xaos(flame.xforms, iterators)
    camera = ifs.find("camera")
    viewing = camera.find("flam3_transform") if camera is not None else None
    if viewing is not None:
        flame.final = _xform_from_transform(viewing, unsupported)
        flame.final.weight = 0.0
        flame.final.color_speed = 0.0   # a viewing transform has no shader: it never recolours
    palette = ifs.find("colouring/table[@name='flam3_palette']/values")
    if palette is not None and palette.text:
        floats = [float(v) for v in palette.text.split()]
        flame.palette = [tuple(max(0, min(255, round(c * 255))) for c in floats[i:i + 3]) for i in range(0, len(floats) - 2, 3)]
    flame.unsupported = sorted(unsupported)
    return flame


def _camera(camera: ET.Element | None, width: int, height: int) -> Camera:
    if camera is None:
        return Camera(width=width, height=height)
    pos = _vec(camera, "pos", (0.0, 0.0))
    if camera.find("real[@name='sensor_width']") is not None:
        sensor = _real(camera, "sensor_width", 1.0)
        scale = width / sensor if sensor else 200.0
        rotate = _real(camera, "rotate", 0.0)
    else:
        scale = _real(camera, "scale", 200.0)
        rotate = _vec(camera, "rotate", (0.0, 0.0))[0]
    return Camera((pos[0], pos[1]), scale, 0.0, rotate, width, height)


def _coloring(imaging: ET.Element | None) -> Coloring:
    if imaging is None:
        return Coloring()
    bg = _vec(imaging, "background_colour", (0.0, 0.0, 0.0, 1.0))
    return Coloring(
        brightness=_real(imaging, "brightness", 20.0) * BRIGHTNESS_SCALE,
        gamma=_real(imaging, "flam3_gamma", 4.0),
        gamma_threshold=_real(imaging, "flam3_gamma_linear_threshold", 0.01),
        vibrancy=_real(imaging, "flam3_vibrancy", 1.0),
        background=tuple(max(0, min(255, round(c * 255))) for c in bg[:3]),
    )


def _xform_from_iterator(it: ET.Element, unsupported: set[str]) -> XForm:
    xform = _xform_from_transform(it.find("flam3_transform"), unsupported)
    shader = it.find("flam3_shader")
    if shader is not None:
        xform.color = _real(shader, "palette_index", 0.0)
        xform.color_speed = _real(shader, "blend_speed", 0.5)
        xform.opacity = _real(shader, "opacity", 1.0)
    weights = it.find("weights_selector")
    xform.weight = _real(weights, "base_weight", 0.5) if weights is not None else 0.5
    xform.name = it.get("name", "")
    return xform


def _xform_from_transform(tr: ET.Element | None, unsupported: set[str]) -> XForm:
    xform = XForm(variations={})
    if tr is None:
        return xform
    for affine in tr.findall("affine2"):
        name = (affine.get("name") or "").lower()
        target = "post" if "post" in name else "coefs"
        setattr(xform, target, _affine(affine))
    variations: dict[str, float] = {}
    params: dict[str, float] = {}
    for t in tr.findall("node[@name='transforms']/transform"):
        type_name = (t.findtext("string[@name='type_name']") or "").strip()
        if not type_name:
            continue
        weight = 1.0
        for real in t.findall("params/real"):
            key, value = real.get("name", ""), float(real.text or 0)
            if key == type_name:
                weight = value
            else:  # Chaotica writes some parameters bare ("Re_A"), others prefixed ("bipolar_shift")
                params[key if key.startswith(type_name + "_") else f"{type_name}_{key}"] = value
        variations[type_name] = variations.get(type_name, 0.0) + weight
    xform.variations, xform.params, unknown = normalize(variations, params)
    unsupported.update(unknown)
    return xform


def _apply_xaos(xforms: list[XForm], iterators: list[ET.Element]) -> None:
    """Chaotica lists, per iterator i, the weight of reaching i *from* each other iterator (a column of flam3's matrix)."""
    n = len(xforms)
    columns = []
    for it in iterators:
        node = it.find("weights_selector/node[@name='per_iterator_weights']")
        column = [1.0] * n
        if node is not None:
            for j, real in enumerate(node.findall("real")[:n]):
                column[j] = float(real.text or 1)
        columns.append(column)
    if all(all(v == 1.0 for v in col) for col in columns):
        return
    for i, xform in enumerate(xforms):
        xform.chaos = [columns[j][i] for j in range(n)]


def _affine(affine: ET.Element) -> Affine:
    xa, xl = math.radians(_real(affine, "x_axis_angle", 0.0)), _real(affine, "x_axis_length", 1.0)
    ya, yl = math.radians(_real(affine, "y_axis_angle", 90.0)), _real(affine, "y_axis_length", 1.0)
    ox, oy = _vec(affine, "offset", (0.0, 0.0))[:2]
    return tuple(_tidy(v) for v in (math.cos(xa) * xl, math.sin(xa) * xl, math.cos(ya) * yl, math.sin(ya) * yl, ox, oy))


def _tidy(value: float) -> float:
    """Kill the 6e-17 left by cos(90°) so axis-aligned affines stay exact."""
    return 0.0 if abs(value) < 1e-12 else value


def _real(el: ET.Element | None, name: str, default: float) -> float:
    if el is None:
        return default
    text = el.findtext(f"real[@name='{name}']")
    try:
        return float(text) if text is not None else default
    except ValueError:
        return default


def _int(el: ET.Element | None, name: str, default: int) -> int:
    if el is None:
        return default
    text = el.findtext(f"int[@name='{name}']")
    try:
        return int(text) if text is not None else default
    except ValueError:
        return default


def _vec(el: ET.Element, name: str, default: tuple) -> tuple:
    for tag in ("vec2", "vec3", "vec4"):
        text = el.findtext(f"{tag}[@name='{name}']")
        if text is not None:
            try:
                values = tuple(float(v) for v in text.split())
                return values + default[len(values):] if len(values) < len(default) else values
            except ValueError:
                return default
    return default


__all__ = ["parse_file", "parse_text", "flame_names", "flame_to_ifs", "flames_to_world", "ChaosParseError"]


# --- writing ------------------------------------------------------------------
def flame_to_ifs(flame: Flame, indent: str = "\t") -> str:
    """An `<IFS>` element for `flame` in Chaotica's format (flam3 camera, iterators, palette)."""
    cam, col = flame.camera, flame.coloring
    ppu = cam.scale * (2.0 ** cam.zoom)
    lines = [f'{indent}<IFS name="{_attr(flame.name)}">', f'{indent}\t<camera name="flam3 camera">',
             f'{indent}\t\t<vec2 name="pos">{_g(cam.center[0])} {_g(cam.center[1])}</vec2>',
             f'{indent}\t\t<real name="rotate">{_g(cam.rotate)}</real>',
             f'{indent}\t\t<real name="sensor_width">{_g(cam.width / ppu if ppu else 1.0)}</real>']
    if flame.final is not None:
        lines.append(f'{indent}\t\t<flam3_transform name="Viewing transform">')
        lines += _transform_body(flame.final, indent + "\t\t\t", include_post=True)
        lines.append(f"{indent}\t\t</flam3_transform>")
    lines += [f"{indent}\t</camera>", f'{indent}\t<imaging name="img">',
              f'{indent}\t\t<int name="image_width">{cam.width}</int>', f'{indent}\t\t<int name="image_height">{cam.height}</int>',
              f'{indent}\t\t<int name="image_aa_level">2</int>', f'{indent}\t\t<int name="image_layers">1</int>',
              f'{indent}\t\t<int name="image_quality">0</int>', f'{indent}\t\t<string name="antialiasing_mode">fine</string>',
              f'{indent}\t\t<real name="brightness">{_g(col.brightness / BRIGHTNESS_SCALE)}</real>',
              f'{indent}\t\t<vec4 name="background_colour">{_g(col.background[0] / 255)} {_g(col.background[1] / 255)} {_g(col.background[2] / 255)} 1</vec4>',
              f'{indent}\t\t<real name="flam3_gamma">{_g(col.gamma)}</real>', f'{indent}\t\t<real name="flam3_vibrancy">{_g(col.vibrancy)}</real>',
              f'{indent}\t\t<bool name="flam3_use_highlight_power">false</bool>', f'{indent}\t\t<real name="flam3_highlight_power">0.01</real>',
              f'{indent}\t\t<real name="flam3_gamma_linear_threshold">{_g(col.gamma_threshold)}</real>',
              f"{indent}\t</imaging>", f"{indent}\t<colouring>", f'{indent}\t\t<table name="flam3_palette">',
              f"{indent}\t\t\t<values>" + " ".join(_g(c / 255.0) for rgb in flame.palette for c in rgb) + "</values>",
              f"{indent}\t\t</table>", f"{indent}\t</colouring>", f'{indent}\t<node name="iterators">']
    for i, xform in enumerate(flame.xforms):
        lines.append(f'{indent}\t\t<iterator name="Iterator {i}">')
        lines.append(f'{indent}\t\t\t<flam3_transform name="flam3_xform {i}">')
        lines += _transform_body(xform, indent + "\t\t\t\t", include_post=True)
        lines += [f"{indent}\t\t\t</flam3_transform>", f'{indent}\t\t\t<flam3_shader name="flam3 shader">',
                  f'{indent}\t\t\t\t<real name="palette_index">{_g(xform.color)}</real>',
                  f'{indent}\t\t\t\t<real name="blend_speed">{_g(xform.color_speed)}</real>',
                  f'{indent}\t\t\t\t<real name="opacity">{_g(xform.opacity)}</real>',
                  f'{indent}\t\t\t\t<table name="layer_weights">', f"{indent}\t\t\t\t\t<values>1 1 1 1</values>",
                  f"{indent}\t\t\t\t</table>", f"{indent}\t\t\t</flam3_shader>",
                  f'{indent}\t\t\t<weights_selector name="Iterator selection weights">',
                  f'{indent}\t\t\t\t<real name="base_weight">{_g(xform.weight)}</real>',
                  f'{indent}\t\t\t\t<node name="per_iterator_weights">']
        for j, other in enumerate(flame.xforms):   # Chaotica lists the weight *into* this iterator from each other one
            weight = 1.0 if other.chaos is None or i >= len(other.chaos) else other.chaos[i]
            lines.append(f'{indent}\t\t\t\t\t<real name="iter {j} weight">{_g(weight)}</real>')
        lines += [f"{indent}\t\t\t\t</node>", f"{indent}\t\t\t</weights_selector>", f"{indent}\t\t</iterator>"]
    lines += [f"{indent}\t</node>", f"{indent}</IFS>"]
    return "\n".join(lines) + "\n"


def flames_to_world(flames: list[Flame], name: str = "World") -> str:
    """A complete `.chaos` document."""
    body = "".join(flame_to_ifs(f) for f in flames)
    return f'<?xml version="1.0" encoding="utf-8"?>\n<world name="{_attr(name)}">\n\t<int name="format_version">1</int>\n{body}</world>\n'


def _transform_body(xform: XForm, indent: str, include_post: bool) -> list[str]:
    lines = _affine_lines("Pre affine", xform.coefs, indent)
    if include_post and xform.has_post():
        lines += _affine_lines("Post affine", xform.post, indent)
    lines.append(f'{indent}<node name="transforms">')
    variations = dict(xform.variations)
    for k, name in enumerate(variations):
        lines.append(f'{indent}\t<transform name="Transform {k}">')
        lines.append(f'{indent}\t\t<string name="type_name">{name}</string>')
        lines.append(f"{indent}\t\t<params>")
        lines.append(f'{indent}\t\t\t<real name="{name}">{_g(variations[name])}</real>')
        for key, value in xform.params.items():
            if key.startswith(name + "_"):
                lines.append(f'{indent}\t\t\t<real name="{key}">{_g(value)}</real>')
        lines += [f"{indent}\t\t</params>", f"{indent}\t</transform>"]
    lines.append(f"{indent}</node>")
    return lines


def _affine_lines(name: str, coefs, indent: str) -> list[str]:
    a, b, c, d, e, f = coefs
    return [f'{indent}<affine2 name="{name}">',
            f'{indent}\t<real name="x_axis_angle">{_g(math.degrees(math.atan2(b, a)))}</real>',
            f'{indent}\t<real name="x_axis_length">{_g(math.hypot(a, b))}</real>',
            f'{indent}\t<real name="y_axis_angle">{_g(math.degrees(math.atan2(d, c)))}</real>',
            f'{indent}\t<real name="y_axis_length">{_g(math.hypot(c, d))}</real>',
            f'{indent}\t<vec2 name="offset">{_g(e)} {_g(f)}</vec2>', f"{indent}</affine2>"]


def parse_text(text: str) -> list[Flame]:
    """Flames from Chaotica XML text (clipboard)."""
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise ChaosParseError(f"not valid Chaotica XML: {exc}") from exc
    elements = [root] if root.tag in IFS_TAGS else [el for tag in IFS_TAGS for el in root.iter(tag)]
    return [f for f in (_flame_from_ifs(e) for e in elements) if f.xforms]


def _g(value: float) -> str:
    text = repr(float(value))
    return text[:-2] if text.endswith(".0") else text


def _attr(text: str) -> str:
    return text.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")

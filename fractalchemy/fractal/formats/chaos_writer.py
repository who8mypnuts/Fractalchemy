"""Flame → Chaotica `.chaos` world text (the inverse of `chaos_world`'s reader).

Chaotica has no `zoom`, so it is folded into `sensor_width`; the final xform becomes the
camera's viewing transform; xaos rows become per-iterator "weights into this iterator".
"""

from __future__ import annotations

import math

from ..scene import Flame, XForm
from .chaos_world import BRIGHTNESS_SCALE
from .xml_text import attr_text, number_text


def flame_to_ifs(flame: Flame, indent: str = "\t") -> str:
    """An `<IFS>` element for `flame` in Chaotica's format (flam3 camera, imaging, palette, iterators)."""
    lines = [f'{indent}<IFS name="{attr_text(flame.name)}">']
    lines += _camera_lines(flame, indent + "\t")
    lines += _imaging_lines(flame, indent + "\t")
    lines += _palette_lines(flame, indent + "\t")
    lines.append(f'{indent}\t<node name="iterators">')
    for i, xform in enumerate(flame.xforms):
        lines += _iterator_lines(flame, i, xform, indent + "\t\t")
    lines += [f"{indent}\t</node>", f"{indent}</IFS>"]
    return "\n".join(lines) + "\n"


def _camera_lines(flame: Flame, indent: str) -> list[str]:
    """The flam3-style camera; the final xform becomes Chaotica's viewing transform."""
    cam = flame.camera
    ppu = cam.scale * (2.0 ** cam.zoom)
    lines = [f'{indent}<camera name="flam3 camera">',
             f'{indent}\t<vec2 name="pos">{number_text(cam.center[0])} {number_text(cam.center[1])}</vec2>',
             f'{indent}\t<real name="rotate">{number_text(cam.rotate)}</real>',
             f'{indent}\t<real name="sensor_width">{number_text(cam.width / ppu if ppu else 1.0)}</real>']
    if flame.final is not None:
        lines.append(f'{indent}\t<flam3_transform name="Viewing transform">')
        lines += _transform_body(flame.final, indent + "\t\t")
        lines.append(f"{indent}\t</flam3_transform>")
    lines.append(f"{indent}</camera>")
    return lines


def _imaging_lines(flame: Flame, indent: str) -> list[str]:
    cam, col = flame.camera, flame.coloring
    bg = " ".join(number_text(c / 255) for c in col.background)
    return [f'{indent}<imaging name="img">',
            f'{indent}\t<int name="image_width">{cam.width}</int>', f'{indent}\t<int name="image_height">{cam.height}</int>',
            f'{indent}\t<int name="image_aa_level">2</int>', f'{indent}\t<int name="image_layers">1</int>',
            f'{indent}\t<int name="image_quality">0</int>', f'{indent}\t<string name="antialiasing_mode">fine</string>',
            f'{indent}\t<real name="brightness">{number_text(col.brightness / BRIGHTNESS_SCALE)}</real>',
            f'{indent}\t<vec4 name="background_colour">{bg} 1</vec4>',
            f'{indent}\t<real name="flam3_gamma">{number_text(col.gamma)}</real>',
            f'{indent}\t<real name="flam3_vibrancy">{number_text(col.vibrancy)}</real>',
            f'{indent}\t<bool name="flam3_use_highlight_power">false</bool>',
            f'{indent}\t<real name="flam3_highlight_power">0.01</real>',
            f'{indent}\t<real name="flam3_gamma_linear_threshold">{number_text(col.gamma_threshold)}</real>',
            f"{indent}</imaging>"]


def _palette_lines(flame: Flame, indent: str) -> list[str]:
    values = " ".join(number_text(c / 255.0) for rgb in flame.palette for c in rgb)
    return [f"{indent}<colouring>", f'{indent}\t<table name="flam3_palette">', f"{indent}\t\t<values>{values}</values>",
            f"{indent}\t</table>", f"{indent}</colouring>"]


def _iterator_lines(flame: Flame, index: int, xform: XForm, indent: str) -> list[str]:
    """One iterator: transform, shader and selection weights (xaos as weights *into* this iterator)."""
    lines = [f'{indent}<iterator name="Iterator {index}">', f'{indent}\t<flam3_transform name="flam3_xform {index}">']
    lines += _transform_body(xform, indent + "\t\t")
    lines += [f"{indent}\t</flam3_transform>", f'{indent}\t<flam3_shader name="flam3 shader">',
              f'{indent}\t\t<real name="palette_index">{number_text(xform.color)}</real>',
              f'{indent}\t\t<real name="blend_speed">{number_text(xform.color_speed)}</real>',
              f'{indent}\t\t<real name="opacity">{number_text(xform.opacity)}</real>',
              f'{indent}\t\t<table name="layer_weights">', f"{indent}\t\t\t<values>1 1 1 1</values>", f"{indent}\t\t</table>",
              f"{indent}\t</flam3_shader>", f'{indent}\t<weights_selector name="Iterator selection weights">',
              f'{indent}\t\t<real name="base_weight">{number_text(xform.weight)}</real>',
              f'{indent}\t\t<node name="per_iterator_weights">']
    for j, other in enumerate(flame.xforms):
        weight = 1.0 if other.chaos is None or index >= len(other.chaos) else other.chaos[index]
        lines.append(f'{indent}\t\t\t<real name="iter {j} weight">{number_text(weight)}</real>')
    lines += [f"{indent}\t\t</node>", f"{indent}\t</weights_selector>", f"{indent}</iterator>"]
    return lines


def flames_to_world(flames: list[Flame], name: str = "World") -> str:
    """A complete `.chaos` document."""
    body = "".join(flame_to_ifs(f) for f in flames)
    return f'<?xml version="1.0" encoding="utf-8"?>\n<world name="{attr_text(name)}">\n\t<int name="format_version">1</int>\n{body}</world>\n'


def _transform_body(xform: XForm, indent: str) -> list[str]:
    """Affines plus one `<transform>` per variation (with that variation's parameters)."""
    lines = _affine_lines("Pre affine", xform.combined_coefs(), indent)   # Chaotica has one affine before the variations
    if xform.has_post():
        lines += _affine_lines("Post affine", xform.post, indent)
    lines.append(f'{indent}<node name="transforms">')
    variations = dict(xform.variations)
    for k, name in enumerate(variations):
        lines.append(f'{indent}\t<transform name="Transform {k}">')
        lines.append(f'{indent}\t\t<string name="type_name">{name}</string>')
        lines.append(f"{indent}\t\t<params>")
        lines.append(f'{indent}\t\t\t<real name="{name}">{number_text(variations[name])}</real>')
        for key, value in xform.params.items():
            if key.startswith(name + "_"):
                lines.append(f'{indent}\t\t\t<real name="{key}">{number_text(value)}</real>')
        lines += [f"{indent}\t\t</params>", f"{indent}\t</transform>"]
    lines.append(f"{indent}</node>")
    return lines


def _affine_lines(name: str, coefs, indent: str) -> list[str]:
    a, b, c, d, e, f = coefs
    return [f'{indent}<affine2 name="{name}">',
            f'{indent}\t<real name="x_axis_angle">{number_text(math.degrees(math.atan2(b, a)))}</real>',
            f'{indent}\t<real name="x_axis_length">{number_text(math.hypot(a, b))}</real>',
            f'{indent}\t<real name="y_axis_angle">{number_text(math.degrees(math.atan2(d, c)))}</real>',
            f'{indent}\t<real name="y_axis_length">{number_text(math.hypot(c, d))}</real>',
            f'{indent}\t<vec2 name="offset">{number_text(e)} {number_text(f)}</vec2>', f"{indent}</affine2>"]

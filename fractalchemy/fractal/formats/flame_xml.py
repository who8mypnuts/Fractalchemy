"""Apophysis / flam3 `<flame>` XML ⇄ Flame objects.

Reading is tolerant: unknown variation attributes are recorded in `Flame.unsupported`
rather than rejected, so legacy and plugin-heavy files still load and render with
the variations we do know.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from ... import config
from ..scene import Affine, Camera, Coloring, Flame, XForm, identity_affine
from ..variations import REGISTRY, canonical_name, normalize

# xform attributes that are not variations
XFORM_ATTRS = {
    "weight", "color", "symmetry", "color_speed", "opacity", "coefs", "post", "chaos", "name", "animate",
    "plotmode", "var_color", "modulus", "modulus_x", "modulus_y", "enabled", "var", "var1", "vars",
    "motion_frequency", "motion_function", "motion_offset",
}
_HEX_TRIPLET = re.compile(r"[0-9A-Fa-f]{6}")


class FlameParseError(ValueError):
    """The XML was not a flame file we can read."""


# --- reading ----------------------------------------------------------------
def parse_file(path: Path) -> list[Flame]:
    """Every renderable <flame> in `path` (those with at least one xform)."""
    return [f for f in (flame_from_element(e) for e in flame_elements(path)) if f.xforms]


def flame_names(path: Path) -> list[str]:
    """Names of the renderable flames, cheaply."""
    return [e.get("name", "flame") for e in flame_elements(path) if e.find("xform") is not None]


def flame_elements(path: Path) -> list[ET.Element]:
    """The <flame> elements of a file (a bare <flame> root counts as one)."""
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise FlameParseError(f"{path.name} is not valid flame XML: {exc}") from exc
    return [root] if root.tag == "flame" else root.findall("flame")


def parse_text(text: str) -> list[Flame]:
    """Flames from XML text (clipboard / tests)."""
    root = ET.fromstring(text)
    elements = [root] if root.tag == "flame" else root.findall("flame")
    return [f for f in (flame_from_element(e) for e in elements) if f.xforms]


def flame_from_element(el: ET.Element) -> Flame:
    """Build a Flame from one <flame> element."""
    width, height = _ints(el.get("size", "800 600"), 2, (800, 600))
    cx, cy = _floats(el.get("center", "0 0"), 2, (0.0, 0.0))
    rotate = _float(el.get("rotate"), None)
    if rotate is None:
        rotate = -_float(el.get("angle"), 0.0) * 180.0 / 3.141592653589793
    flame = Flame(
        name=el.get("name", "flame"),
        camera=Camera((cx, cy), _float(el.get("scale"), 200.0), _float(el.get("zoom"), 0.0), rotate, width, height),
        coloring=Coloring(
            brightness=_float(el.get("brightness"), 4.0), gamma=_float(el.get("gamma"), 4.0),
            gamma_threshold=_float(el.get("gamma_threshold"), 0.01), vibrancy=_float(el.get("vibrancy"), 1.0),
            contrast=_float(el.get("contrast"), 1.0), background=_background(el.get("background", "0 0 0")),
        ),
        source_version=el.get("version", ""),
    )
    unsupported: set[str] = set()
    flame.xforms = [_xform_from_element(x, unsupported) for x in el.findall("xform")]
    final = el.find("finalxform")
    if final is not None and final.get("enabled", "1") != "0":
        flame.final = _xform_from_element(final, unsupported)
    flame.palette = _palette(el) or flame.palette
    flame.unsupported = sorted(unsupported)
    return flame


def _xform_from_element(el: ET.Element, unsupported: set[str]) -> XForm:
    attrs = dict(el.attrib)
    xform = XForm(
        weight=_float(attrs.get("weight"), 0.5),
        color=_float(attrs.get("color"), 0.0),
        opacity=_float(attrs.get("opacity"), 1.0),
        coefs=_affine(attrs.get("coefs")),
        post=_affine(attrs.get("post")),
        name=attrs.get("name", ""),
    )
    if "color_speed" in attrs:
        xform.color_speed = _float(attrs["color_speed"], 0.5)
    else:
        xform.color_speed = XForm.speed_from_symmetry(_float(attrs.get("symmetry"), 0.0))
    if "chaos" in attrs:
        xform.chaos = [float(v) for v in attrs["chaos"].split()] or None
    variations, params = _split_variations(attrs)
    xform.variations, xform.params, unknown = normalize(variations, params)
    unsupported.update(unknown)
    return xform


def _split_variations(attrs: dict[str, str]) -> tuple[dict[str, float], dict[str, float]]:
    """Separate variation weights from their parameters among an xform's attributes."""
    candidates = {k: v for k, v in attrs.items() if k not in XFORM_ATTRS}
    variations: dict[str, float] = {}
    params: dict[str, float] = {}
    # Variation names: known ones, or any attribute that is a prefix of an `x_y` attribute, or unknown non-param attrs.
    names = {k for k in candidates if canonical_name(k) in REGISTRY}
    for k in candidates:
        if k in names:
            continue
        if any(k.startswith(n + "_") for n in names | set(candidates) - {k}):
            continue  # looks like a parameter of another attribute
        names.add(k)
    for k, v in candidates.items():
        value = _float(v, 0.0)
        if k in names:
            variations[k] = value
        else:
            params[k] = value
    return variations, params


def _palette(el: ET.Element) -> list[tuple[int, int, int]]:
    palette = el.find("palette")
    if palette is not None and palette.text:
        return [tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) for h in _HEX_TRIPLET.findall(palette.text)]
    colors = el.findall("color")   # flam3's older per-entry form
    if colors:
        out = []
        for c in sorted(colors, key=lambda c: int(c.get("index", "0"))):
            r, g, b = _ints(c.get("rgb", "0 0 0"), 3, (0, 0, 0))
            out.append((r, g, b))
        return out
    return []


# --- writing ----------------------------------------------------------------
def flame_to_xml(flame: Flame, indent: str = "") -> str:
    """A <flame> element (Apophysis 7x style) for `flame`."""
    cam, col = flame.camera, flame.coloring
    head = (
        f'<flame name="{_attr(flame.name)}" version="{config.APP_NAME} {config.APP_VERSION}" '
        f'size="{cam.width} {cam.height}" center="{_g(cam.center[0])} {_g(cam.center[1])}" scale="{_g(cam.scale)}" '
        f'zoom="{_g(cam.zoom)}" rotate="{_g(cam.rotate)}" oversample="1" filter="0.2" quality="5" '
        f'background="{_g(col.background[0] / 255)} {_g(col.background[1] / 255)} {_g(col.background[2] / 255)}" '
        f'brightness="{_g(col.brightness)}" gamma="{_g(col.gamma)}" gamma_threshold="{_g(col.gamma_threshold)}" '
        f'vibrancy="{_g(col.vibrancy)}" contrast="{_g(col.contrast)}">'
    )
    lines = [indent + head]
    for x in flame.xforms:
        lines.append(f"{indent}   <xform {_xform_attrs(x, final=False)} />")
    if flame.final is not None:
        lines.append(f"{indent}   <finalxform {_xform_attrs(flame.final, final=True)} />")
    lines.append(f'{indent}   <palette count="{len(flame.palette)}" format="RGB">')
    hexes = ["%02x%02x%02x" % tuple(c) for c in flame.palette]
    per_line = config.FLAME_COLORS_PER_LINE
    for i in range(0, len(hexes), per_line):
        lines.append(f"{indent}      " + "".join(hexes[i:i + per_line]))
    lines.append(f"{indent}   </palette>")
    lines.append(f"{indent}</flame>")
    return "\n".join(lines) + "\n"


def flames_to_xml(flames: list[Flame], name: str = "Fractalchemy") -> str:
    """A whole <Flames> document."""
    body = "".join(flame_to_xml(f, "") for f in flames)
    return f'<Flames name="{_attr(name)}">\n{body}</Flames>\n'


def _xform_attrs(x: XForm, final: bool) -> str:
    parts = [] if final else [f'weight="{_g(x.weight)}"']
    parts.append(f'color="{_g(x.color)}"')
    parts.append(f'symmetry="{_g(x.symmetry)}"')
    if x.opacity != 1.0:
        parts.append(f'opacity="{_g(x.opacity)}"')
    if x.name:
        parts.append(f'name="{_attr(x.name)}"')
    for name, weight in x.variations.items():
        parts.append(f'{name}="{_g(weight)}"')
    parts.append('coefs="' + " ".join(_g(v) for v in x.coefs) + '"')
    if x.has_post():
        parts.append('post="' + " ".join(_g(v) for v in x.post) + '"')
    for key, value in x.params.items():
        parts.append(f'{key}="{_g(value)}"')
    if x.chaos is not None and not final:
        parts.append('chaos="' + " ".join(_g(v) for v in x.chaos) + '"')
    return " ".join(parts)


# --- small helpers ----------------------------------------------------------
def _float(text: str | None, default):
    if text is None:
        return default
    try:
        return float(text)
    except ValueError:
        return default


def _floats(text: str, count: int, default):
    try:
        values = [float(v) for v in text.split()]
    except ValueError:
        return default
    return tuple(values[:count]) if len(values) >= count else default


def _ints(text: str, count: int, default):
    values = _floats(text, count, None)
    return tuple(int(v) for v in values) if values else default


def _affine(text: str | None) -> Affine:
    values = _floats(text, 6, None) if text else None
    return tuple(values) if values else identity_affine()


def _background(text: str) -> tuple[int, int, int]:
    r, g, b = _floats(text, 3, (0.0, 0.0, 0.0))
    return tuple(max(0, min(255, round(v * 255))) for v in (r, g, b))


def _g(value: float) -> str:
    """Shortest text that reads back to the same float (`1.0` → `1`)."""
    text = repr(float(value))
    return text[:-2] if text.endswith(".0") else text


def _attr(text: str) -> str:
    return text.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")

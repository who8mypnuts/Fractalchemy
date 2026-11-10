"""The statements that turn one flame into another: what the Script Editor's recorder writes (Qt-free).

    lines = flame_diff(before, after)                     # ['coloring.gamma = 3.5', 'camera.zoom = 1.25', …]
    lines = flame_diff(before, after, style="relative")   # ['coloring.gamma += 0.5', 'camera.zoom += 0.25', …]

**Sections**, in this order (later statements rely on the structure earlier ones settle):

1. *Structure* — one transform appended (`add_transform(...)`), one removed (`remove_transform(k)`), the final transform
   switched on or off; anything else (a paste, an adopted mutant) rebuilds the transforms (`clear_transforms()` plus the
   blocks Flame → Script writes).
2. *Transforms* — per transform, computed against the flame as the structure statements leave it (they are executed,
   so side effects such as the xaos column `add_transform` appends are accounted for): weights, colours, names, the
   three affines, variations, parameters, then xaos (`xaos.set(i, j, w)` for one link, the whole row otherwise).
3. *Camera*, *colouring* (curves included), the flame's *oversample* / *filter radius*, and the *palette* — the most
   readable exact form: `gradient.rotate(n)` / `reverse()` / `invert()` when that is what happened, else the Gradient
   Library's nodes (`gradient`, the hint) or the simplified nodes when they reproduce the palette exactly, else all 256
   colours.

**Generate, verify, fall back.** The statements are executed on a copy of `before` and compared with `after`
(`codegen.flame_differences`). A section that does not reproduce its part — the API clamps a value the file held out of
range, a relative change that cannot be expressed — is replaced by exact assignments to the raw model
(`flame.coloring.vibrancy = 1.5`, `flame.xforms[2] = XForm(...)`, `gradient.colors = [...]`). A recording is therefore
correct by construction; readability never costs correctness.

**Relative style** (the recorder's *Changes*): numbers become changes (`+= d`), the camera pans (`camera.pan(dx, dy)`),
a triangle whose 2×2 part turned or scaled becomes `rotate(θ)` / `scale(s)` (else `multiply(...)`) plus `translate`, and
the Gradient Library's own operations, when `hints` name them, become `gradient.adjust_stops(...)` / `reverse()` / …
Colours, curves, xaos, structure and anything a change cannot express stay as values.

Not recorded: the flame's name, `unsupported`, `source_version`.
"""

from __future__ import annotations

import math
import threading

from ..fractal import variations as V
from ..fractal.curves import CHANNELS
from ..fractal.scene import Flame, XForm
from ..model import Gradient, simplify
from ..model.stop import ColorStop
from . import codegen as G
from .codegen import affine, coord, curve_call, num, palette_lines, stops_call, xform_lines

PALETTE_SIZE = 256
XFORM_FIELDS = ("weight", "color", "color_speed", "opacity", "var_color")
CAMERA_FIELDS = ("scale", "zoom", "rotate", "perspective", "zpos", "dof")
ANGLES = ("pitch", "yaw", "pitch_y")
COLORING_FIELDS = ("brightness", "gamma", "gamma_threshold", "vibrancy", "contrast")
BIND_AFTER = 3                      # statements about one transform before it gets a name of its own (`t3 = transforms[2]`)
SECTIONS = ("transforms", "final", "camera", "coloring", "flame", "palette")


def _run(lines: list[str], flame: Flame) -> Flame | None:
    from .runner import run_script
    if not lines:
        return flame.copy()
    result = run_script("\n".join(lines), flame, None, threading.Event(), seed=0)
    return result.flame if result.ok and not result.stopped else None


def _close(a: float, b: float) -> bool:
    return math.isclose(float(a), float(b), rel_tol=G.DEFAULT_TOLERANCE, abs_tol=G.DEFAULT_TOLERANCE)


def _affine_close(a, b) -> bool:
    return all(_close(x, y) for x, y in zip(a, b))


def _xform_same(a: XForm, b: XForm) -> bool:
    """Equivalent apart from xaos."""
    da, db = G._xform_dict(a, 0), G._xform_dict(b, 0)
    da.pop("chaos"), db.pop("chaos")
    out: list[str] = []
    G._compare(da, db, "x", G.DEFAULT_TOLERANCE, out)
    return not out


# --- structure ------------------------------------------------------------------------------------------------------------
def _structure(before: Flame, after: Flame) -> tuple[list[str], bool]:
    """Statements for added / removed transforms and the final transform; (lines, rebuilt everything)."""
    b, a = before.xforms, after.xforms
    lines: list[str] = []
    if len(a) == len(b) + 1 and all(_xform_same(x, y) for x, y in zip(b, a)):
        lines += xform_lines(a[-1], f"t{len(a)}", final=False)
    elif len(a) == len(b) - 1 and b:
        removed = next((k for k in range(len(b)) if all(_xform_same(x, y) for x, y in zip(b[:k] + b[k + 1:], a))), None)
        if removed is None:
            return _rebuild(after), True
        lines.append(f"remove_transform({removed})")
    elif len(a) != len(b):
        return _rebuild(after), True
    if (before.final is None) != (after.final is None):
        if after.final is None:
            lines.append("remove_final_transform()")
        else:
            lines += xform_lines(after.final, "final", final=True)
    return lines, False


def _rebuild(after: Flame) -> list[str]:
    lines = ["# transforms rebuilt (the structure changed)", "clear_transforms()"]
    for i, x in enumerate(after.xforms):
        lines += xform_lines(x, f"t{i + 1}", final=False)
    if after.final is not None:
        lines += xform_lines(after.final, "final", final=True)
    return lines


# --- one transform ---------------------------------------------------------------------------------------------------------
def _rotation_scale(m0, m1) -> tuple[str, float, float] | None:
    """How the 2×2 part went from m0 to m1, as the API's `rotate` / `scale` would do it: ("rotate", degrees, 1),
    ("scale", 1, factor), ("both", degrees, factor) or None (anything else)."""
    a0, b0, c0, d0 = m0
    a1, b1, c1, d1 = m1
    det = a0 * d0 - b0 * c0
    if abs(det) < 1e-12:
        return None
    # R maps the old axes onto the new ones: [a1 c1; b1 d1] = R · [a0 c0; b0 d0]
    inv = (d0 / det, -b0 / det, -c0 / det, a0 / det)             # inverse of [[a0, c0], [b0, d0]] in (p, q, r, s) order
    r00 = a1 * inv[0] + c1 * inv[1]
    r01 = a1 * inv[2] + c1 * inv[3]
    r10 = b1 * inv[0] + d1 * inv[1]
    r11 = b1 * inv[2] + d1 * inv[3]
    scale = math.hypot(r00, r10)
    if not (_close(r00, r11) and _close(r01, -r10)) or scale < 1e-12:
        return None
    degrees = -math.degrees(math.atan2(r10, r00))                 # the API turns counter-clockwise on screen (y down)
    rotated, scaled = not _close(degrees, 0.0), not _close(scale, 1.0)
    if rotated and scaled:
        return ("both", degrees, scale)
    if rotated:
        return ("rotate", degrees, 1.0)
    return ("scale", 0.0, scale) if scaled else None


def _affine_lines(var: str, which: str, old, new, style: str) -> list[str]:
    target = {"coefs": var, "pre": f"{var}.pre", "post": f"{var}.post"}[which]
    if style == "relative" and which == "coefs":
        change = _rotation_scale(old[:4], new[:4])
        if change is not None:
            kind, degrees, scale = change
            lines = []
            if kind in ("rotate", "both"):
                lines.append(f"{var}.rotate({num(degrees)})")
            if kind in ("scale", "both"):
                lines.append(f"{var}.scale({num(scale)})")
            if not (_close(old[4], new[4]) and _close(old[5], new[5])):
                lines.append(f"{var}.translate({num(new[4] - old[4])}, {num(new[5] - old[5])})")
            return lines
    return [f"{target}.coefs = ({affine(new)})"]


def _field(value) -> str:
    return repr(value) if isinstance(value, str) else num(value)


def _xform_changes(a: XForm, b: XForm, var: str, final: bool, style: str) -> list[str]:
    """Statements about one transform (`a` as it is, `b` as it should be), with `var` standing for it."""
    lines: list[str] = []
    for name in XFORM_FIELDS:
        if final and name == "weight":
            continue
        old, new = getattr(a, name), getattr(b, name)
        if not _close(old, new):
            lines.append(f"{var}.{name} += {num(new - old)}" if style == "relative" else f"{var}.{name} = {num(new)}")
    if a.name != b.name:
        lines.append(f"{var}.name = {b.name!r}")
    for which in ("coefs", "pre", "post"):
        old, new = tuple(getattr(a, which)), tuple(getattr(b, which))
        if not _affine_close(old, new):
            lines += _affine_lines(var, which, old, new, style)
    for name in list(a.variations):
        if name not in b.variations:
            lines.append(f"del {var}.variations[{name!r}]")
    for name, weight in b.variations.items():
        if name not in a.variations or not _close(a.variations[name], weight):
            if name in V.REGISTRY:
                lines.append(f"{var}.variations[{name!r}] = {num(weight)}")
            else:
                lines.append(f"# {var}: variation '{name}' is not available here (not recorded)")
    filled = _with_variations(a, b).params                   # what the API's variation assignments leave behind
    for key, value in b.params.items():
        current = filled.get(key)
        if current is None or not _close(current, value):
            lines.append(f"{var}.params[{key!r}] = {num(value)}")
    return lines


def _with_variations(a: XForm, b: XForm) -> XForm:
    """`a` with `b`'s variations added the API's way (a new variation brings its parameter defaults)."""
    probe = a.copy()
    for name in b.variations:
        probe.variations.setdefault(name, 1.0)
        var = V.REGISTRY.get(name)
        if var is not None:
            for key, default in var.params.items():
                probe.params.setdefault(key, float(default))
    return probe


def _chaos_row(x: XForm, n: int) -> list[float]:
    row = [float(v) for v in (x.chaos or [])][:n]
    return row + [1.0] * (n - len(row))


def _xaos_lines(current: Flame, after: Flame) -> list[str]:
    n = len(after.xforms)
    lines = []
    for i, (a, b) in enumerate(zip(current.xforms, after.xforms)):
        old, new = _chaos_row(a, n), _chaos_row(b, n)
        changed = [j for j in range(n) if not _close(old[j], new[j])]
        if not changed:
            continue
        if all(v == 1.0 for v in new):
            lines.append(f"transforms[{i}].xaos = None")
        elif len(changed) == 1:
            lines.append(f"xaos.set({i}, {changed[0]}, {num(new[changed[0]])})")
        else:
            lines.append(f"transforms[{i}].xaos = [{', '.join(num(v) for v in new)}]")
    return lines


def _transform_section(current: Flame, after: Flame, style: str) -> list[str]:
    lines: list[str] = []
    for i, (a, b) in enumerate(zip(current.xforms, after.xforms)):
        body = _xform_changes(a, b, "@", False, style)
        lines += _bind(body, f"transforms[{i}]", f"t{i + 1}")
    return lines + _xaos_lines(current, after)


def _final_section(current: Flame, after: Flame, style: str) -> list[str]:
    if current.final is None or after.final is None:
        return []
    return _bind(_xform_changes(current.final, after.final, "@", True, style), "final_transform()", "final")


def _bind(body: list[str], expression: str, name: str) -> list[str]:
    """Write `body` (statements about "@") with `expression`, or bind it to `name` first when it is used often."""
    if len(body) >= BIND_AFTER:
        return [f"{name} = {expression}"] + [line.replace("@", name) for line in body]
    return [line.replace("@", expression) for line in body]


# --- camera, colouring, flame ---------------------------------------------------------------------------------------------
def _camera_section(before: Flame, after: Flame, style: str) -> list[str]:
    c0, c1 = before.camera, after.camera
    lines = []
    if (c0.width, c0.height) != (c1.width, c1.height):
        lines.append(f"camera.set_size({c1.width}, {c1.height})")
    if not (_close(c0.center[0], c1.center[0]) and _close(c0.center[1], c1.center[1])):
        if style == "relative":
            lines.append(f"camera.pan({num(c1.center[0] - c0.center[0])}, {num(c1.center[1] - c0.center[1])})")
        else:
            pixel = 1.0 / max(1e-12, c1.pixels_per_unit(c1.width, c1.height))
            lines.append(f"camera.center = ({coord(c1.center[0], pixel)}, {coord(c1.center[1], pixel)})")
    for name in CAMERA_FIELDS:
        old, new = getattr(c0, name), getattr(c1, name)
        if _close(old, new):
            continue
        if style == "relative" and name == "rotate":
            lines.append(f"camera.rotate_by({num(new - old)})")
        elif style == "relative" and name in ("zoom", "perspective", "zpos", "dof"):
            lines.append(f"camera.{name} += {num(new - old)}")
        elif style == "relative" and name == "scale":
            lines.append(f"camera.scale *= {num(new / old) if old else num(new)}")
        else:
            lines.append(f"camera.{name} = {num(new)}")
    for name in ANGLES:
        old, new = getattr(c0, name), getattr(c1, name)
        if not _close(old, new):
            lines.append(f"camera.{name} += {num(math.degrees(new - old))}" if style == "relative"
                         else f"camera.{name} = {num(math.degrees(new))}")
    return lines


def _coloring_section(before: Flame, after: Flame, style: str) -> list[str]:
    c0, c1 = before.coloring, after.coloring
    lines = []
    for name in COLORING_FIELDS:
        old, new = getattr(c0, name), getattr(c1, name)
        if not _close(old, new):
            lines.append(f"coloring.{name} += {num(new - old)}" if style == "relative" else f"coloring.{name} = {num(new)}")
    if tuple(int(c) for c in c0.background) != tuple(int(c) for c in c1.background):
        lines.append(f"coloring.background = '{G.color_hex(c1.background)}'")
    for channel in CHANNELS:
        old, new = c0.curves.points[channel], c1.curves.points[channel]
        if old != new:
            lines.append(f"coloring.reset_curves({channel!r})" if c1.curves.is_default(channel) else curve_call(channel, new))
    return lines


def _flame_section(before: Flame, after: Flame) -> list[str]:
    lines = []
    if before.oversample != after.oversample:
        lines.append(f"flame.oversample = {int(after.oversample)}")
    if not _close(before.filter_radius, after.filter_radius):
        lines.append(f"flame.filter_radius = {num(after.filter_radius)}")
    return lines


# --- the palette ----------------------------------------------------------------------------------------------------------
def _palette(colors) -> list[tuple[int, int, int]]:
    return [tuple(int(c) for c in rgb) for rgb in colors]


def _sampled(stops: list[ColorStop], exact: bool = False) -> list[tuple[int, int, int]]:
    """The palette `stops_call(stops, exact)` produces."""
    return _palette(Gradient("x", [ColorStop(float(s.position) if exact else float(num(s.position)), tuple(s.color))
                                   for s in stops]).sample(PALETTE_SIZE))


def _stops_lines(stops: list[ColorStop], new: list) -> list[str] | None:
    """`gradient.set_stops(...)` for `stops` when it reproduces `new` (readable positions first, exact ones otherwise)."""
    for exact in (False, True):
        if _sampled(stops, exact) == new:
            return stops_call(stops, exact)
    return None


def _palette_section(before: Flame, after: Flame, gradient: Gradient | None, hints: dict | None, style: str) -> list[str]:
    old, new = _palette(before.palette), _palette(after.palette)
    if old == new:
        return []
    for n in range(1, PALETTE_SIZE):
        if new == old[-n:] + old[:-n]:
            return [f"gradient.rotate({n})"]
    if new == old[::-1]:
        return ["gradient.reverse()"]
    if new == [(255 - r, 255 - g, 255 - b) for r, g, b in old]:
        return ["gradient.invert()"]
    if style == "relative" and hints:
        hinted = _hinted_gradient(hints)
        if hinted:
            return hinted
    if gradient is not None and gradient.stops:
        lines = _stops_lines(gradient.stops, new)
        if lines:
            return lines
    simplified = simplify(Gradient.from_colors("x", new).stops, 0)
    if simplified and len(simplified) <= 32:
        lines = _stops_lines(simplified, new)
        if lines:
            return lines
    return palette_lines(new)


def _hinted_gradient(hints: dict) -> list[str]:
    """The Gradient Library's own operation as a change: adjustments (`hue`, `saturation`, `luminance`, `rotation`) or
    a named operation."""
    operation = hints.get("operation")
    if operation in ("reverse", "invert", "smooth", "add_nodes", "remove_nodes"):
        return [f"gradient.{operation}()"]
    adjustments = hints.get("adjustments")
    if adjustments:
        parts = [f"{name}={num(value)}" for name, value in adjustments.items() if name != "rotation" and value]
        lines = [f"gradient.adjust_stops({', '.join(parts)})"] if parts else []
        if adjustments.get("rotation"):
            lines.append(f"gradient.rotate_stops({num(adjustments['rotation'] / 400.0)})")
        return lines
    return []


# --- exact fallbacks ------------------------------------------------------------------------------------------------------
def _raw_xform(x: XForm) -> str:
    chaos = None if x.chaos is None else [float(v) for v in x.chaos]
    return (f"XForm(weight={num(x.weight)}, color={num(x.color)}, color_speed={num(x.color_speed)}, opacity={num(x.opacity)}, "
            f"coefs=({affine(x.coefs)}), post=({affine(x.post)}), variations={G.mapping(x.variations)}, params={G.mapping(x.params)}, "
            f"chaos={'None' if chaos is None else '[' + ', '.join(num(v) for v in chaos) + ']'}, name={x.name!r}, "
            f"var_color={num(x.var_color)}, pre=({affine(x.pre)}))")


def _raw(section: str, after: Flame) -> list[str]:
    """Exact assignments to the raw model for one section."""
    if section == "transforms":
        return ["# recorded as values: the change could not be expressed with the API's helpers",
                "flame.xforms = [", *[f"    {_raw_xform(x)}," for x in after.xforms], "]"]
    if section == "final":
        return [f"flame.final = {_raw_xform(after.final) if after.final is not None else 'None'}"]
    if section == "camera":
        c = after.camera
        lines = [f"flame.camera.center = ({num(c.center[0])}, {num(c.center[1])})", f"flame.camera.width = {c.width}",
                 f"flame.camera.height = {c.height}"]
        return lines + [f"flame.camera.{name} = {num(getattr(c, name))}" for name in CAMERA_FIELDS + ANGLES]
    if section == "coloring":
        c = after.coloring
        lines = [f"flame.coloring.{name} = {num(getattr(c, name))}" for name in COLORING_FIELDS]
        lines.append(f"flame.coloring.background = {tuple(int(v) for v in c.background)}")
        return lines + [f"flame.coloring.curves.set_points({ch!r}, [{', '.join(f'({num(x)}, {num(y)})' for x, y in c.curves.points[ch])}])"
                        for ch in CHANNELS]
    if section == "palette":
        return palette_lines(after.palette)
    return [f"flame.oversample = {int(after.oversample)}", f"flame.filter_radius = {num(after.filter_radius)}"]


def _centre_close(result: Flame, after: Flame) -> bool:
    """The camera centre is within half a pixel (the readable centre `coord` writes)."""
    camera = after.camera
    pixel = 1.0 / max(1e-12, camera.pixels_per_unit(camera.width, camera.height))
    return all(abs(float(x) - float(y)) <= pixel / 2 for x, y in zip(result.camera.center, camera.center))


def _section_of(path: str) -> str:
    for section, prefix in (("transforms", "flame.xforms"), ("final", "flame.final"), ("camera", "flame.camera"),
                            ("coloring", "flame.coloring"), ("palette", "flame.palette")):
        if path.startswith(prefix):
            return section
    return "flame"


# --- the diff --------------------------------------------------------------------------------------------------------------
def diff_sections(before: Flame, after: Flame, gradient: Gradient | None = None, style: str = "absolute",
                  hints: dict | None = None) -> dict[str, list[str]]:
    """`flame_diff`, section by section (verified; see the module docstring)."""
    structure, _rebuilt = _structure(before, after)
    current = _run(structure, before) if structure else before
    sections: dict[str, list[str]] = {name: [] for name in SECTIONS}
    if current is None:
        structure = _rebuild(after)
        current = _run(structure, before)
    sections["transforms"] = structure + (_transform_section(current, after, style) if current is not None else [])
    sections["final"] = _final_section(current, after, style) if current is not None else []
    sections["camera"] = _camera_section(before, after, style)
    sections["coloring"] = _coloring_section(before, after, style)
    sections["flame"] = _flame_section(before, after)
    sections["palette"] = _palette_section(before, after, gradient, hints, style)
    for _attempt in range(2):
        result = _run([line for name in SECTIONS for line in sections[name]], before)
        if result is None:
            failing = set(SECTIONS) - {"palette", "flame"} if _attempt == 0 else set(SECTIONS)
        else:
            failing = {_section_of(path) for path in G.flame_differences(result, after)
                       if not (path.startswith("flame.camera.center") and _centre_close(result, after))}
        if not failing:
            break
        for name in failing:
            sections[name] = _raw(name, after)
    return sections


def flame_diff(before: Flame, after: Flame, gradient: Gradient | None = None, style: str = "absolute",
               hints: dict | None = None) -> list[str]:
    """API statements that turn `before` into `after` (empty when nothing differs); see the module docstring.

    Args:
        before, after: The flames.
        gradient: The Gradient Library's gradient, when it shows the `after` palette (its nodes are recorded).
        style: `absolute` (values) or `relative` (changes).
        hints: What the Gradient Library did (`operation`, `adjustments`) — relative style only.
    """
    sections = diff_sections(before, after, gradient, style, hints)
    return [line for name in SECTIONS for line in sections[name]]


__all__ = ["flame_diff", "diff_sections", "SECTIONS"]

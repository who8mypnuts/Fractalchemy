"""Writing flames as scripting-API code, and comparing flames: what Flame → Script, the recorder's diff generator and
their tests share.

* **Numbers** (`num`): the shortest text that reads back within 1e-9 (relative) — `3.5`, not `3.5000000000` — and
  integers stay integers; `coord` gives camera centres as many decimals as the zoom needs for sub-pixel accuracy.
* **Blocks**: `xform_lines` (an `add_transform(...)` / `set_final_transform(...)` block with its affines and
  parameters), `palette_lines` (all 256 colours), `stops_call` (`gradient.set_stops([...])`).
* **Equivalence** (`flame_differences` / `flames_equivalent`): two flames render the same — numbers within a tolerance,
  a missing variation parameter equal to its formula's default, xaos rows padded with 1s (and `None` ≡ all ones), the
  name and the bookkeeping fields (`unsupported`, `source_version`) ignored.

Qt-free.
"""

from __future__ import annotations

import math

from ..fractal import variations as V
from ..fractal.scene import Flame, XForm, identity_affine

DEFAULT_TOLERANCE = 1e-7
COLORS_PER_LINE = 8
IGNORED_FIELDS = ("name", "unsupported", "source_version")


# --- numbers ---------------------------------------------------------------------------------------------------------------
def num(value) -> str:
    """A number as short, exact-enough Python text (`3.5`, `0.3`, `12`, `1e-12`)."""
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, int):
        return str(value)
    v = float(value)
    if not math.isfinite(v):
        return f"float('{v}')"
    shortest = repr(v)
    short = f"{v:.9g}"
    text = short if len(short) < len(shortest) and abs(float(short) - v) <= 1e-9 * abs(v) else shortest
    return text if ("." in text or "e" in text or "n" in text) else text + ".0"


def coord(value: float, pixel: float) -> str:
    """A coordinate with enough decimals to place it within a quarter of `pixel` (fractal units per pixel), at least 4."""
    decimals = 4 if pixel <= 0 or not math.isfinite(pixel) else max(4, min(15, math.ceil(-math.log10(pixel / 4.0))))
    text = f"{float(value):.{decimals}f}".rstrip("0")
    return text + "0" if text.endswith(".") else text


def affine(coefs) -> str:
    """`a, b, c, d, e, f`."""
    return ", ".join(num(c) for c in coefs)


def mapping(values: dict) -> str:
    """`{'key': number, …}`."""
    return "{" + ", ".join(f"{k!r}: {num(v)}" for k, v in values.items()) + "}"


def color_hex(rgb) -> str:
    r, g, b = (int(c) for c in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


# --- blocks ---------------------------------------------------------------------------------------------------------------
def xform_lines(x: XForm, var: str, final: bool) -> list[str]:
    """A transform as an `add_transform(...)` (or `set_final_transform(...)`) call bound to `var`, plus its affines and
    parameters."""
    fields = [f"variations={mapping(x.variations) if x.variations else '{}'}"]
    if not final:
        fields.insert(0, f"weight={num(x.weight)}")
    fields += [f"color={num(x.color)}", f"color_speed={num(x.color_speed)}"]
    if x.opacity != 1.0:
        fields.append(f"opacity={num(x.opacity)}")
    if x.var_color != 1.0:
        fields.append(f"var_color={num(x.var_color)}")
    if x.name:
        fields.append(f"name={x.name!r}")
    call = "set_final_transform" if final else "add_transform"
    lines = [f"{var} = {call}({', '.join(fields)})", f"{var}.set_affine({affine(x.coefs)})"]
    if tuple(x.pre) != identity_affine():
        lines.append(f"{var}.pre.coefs = ({affine(x.pre)})")
    if tuple(x.post) != identity_affine():
        lines.append(f"{var}.post.coefs = ({affine(x.post)})")
    if x.params:
        lines.append(f"{var}.params.update({mapping(x.params)})")
    return lines


def palette_lines(palette, target: str = "gradient.colors") -> list[str]:
    """`gradient.colors = [...]` with every colour, eight per line."""
    colors = [tuple(int(c) for c in rgb) for rgb in palette]
    lines = [f"{target} = ["]
    for start in range(0, len(colors), COLORS_PER_LINE):
        lines.append("    " + ", ".join(str(c) for c in colors[start:start + COLORS_PER_LINE]) + ",")
    return lines + ["]"]


def stops_call(stops, exact: bool = False) -> list[str]:
    """`gradient.set_stops([(position, '#rrggbb'), …])` (one stop per line when there are more than four); `exact` writes
    positions with every digit (a node on a colour boundary can tip the sampled palette by one)."""
    items = [f"({repr(float(s.position)) if exact else num(s.position)}, '{color_hex(s.color)}')" for s in stops]
    if len(items) <= 4:
        return [f"gradient.set_stops([{', '.join(items)}])"]
    return ["gradient.set_stops(["] + [f"    {item}," for item in items] + ["])"]


def curve_call(channel: str, points) -> str:
    return f"coloring.set_curve({channel!r}, [{', '.join(f'({num(x)}, {num(y)})' for x, y in points)}])"


# --- equivalence -----------------------------------------------------------------------------------------------------------
def _effective_params(x: XForm) -> dict[str, float]:
    """The parameters that matter for rendering: those of the transform's variations, defaults filled in."""
    params: dict[str, float] = {}
    for name in x.variations:
        var = V.REGISTRY.get(name)
        if var is not None:
            for key, default in var.params.items():
                params[key] = float(x.params.get(key, default))
        for key, value in x.params.items():
            if key.startswith(name + "_") or V.parameter_owner(key) == name:
                params[key] = float(value)
    return params


def _chaos(x: XForm, n: int) -> list[float] | None:
    row = [float(v) for v in (x.chaos or [])][:n]
    row += [1.0] * (n - len(row))
    return None if all(v == 1.0 for v in row) else row


def _close(a, b, tol: float) -> bool:
    return math.isclose(float(a), float(b), rel_tol=tol, abs_tol=tol)


def _compare(a, b, path: str, tol: float, out: list[str]) -> None:
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b), key=str):
            if key not in a or key not in b:
                out.append(f"{path}.{key}")
            else:
                _compare(a[key], b[key], f"{path}.{key}", tol, out)
    elif isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        if len(a) != len(b):
            out.append(f"{path} (length {len(a)} ≠ {len(b)})")
            return
        for i, (x, y) in enumerate(zip(a, b)):
            _compare(x, y, f"{path}[{i}]", tol, out)
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        if not _close(a, b, tol):
            out.append(f"{path} ({a!r} ≠ {b!r})")
    elif a != b:
        out.append(f"{path} ({a!r} ≠ {b!r})")


def _normalised(flame: Flame, ignore: tuple[str, ...]) -> dict:
    data = flame.to_dict()
    for key in ignore:
        data.pop(key, None)
    n = len(flame.xforms)
    data["xforms"] = [_xform_dict(x, n) for x in flame.xforms]
    if flame.final is not None:
        final = _xform_dict(flame.final, n)
        final.pop("weight", None)      # no engine uses the final transform's weight
        final.pop("chaos", None)
        data["final"] = final
    return data


def _xform_dict(x: XForm, n: int) -> dict:
    return {"weight": x.weight, "color": x.color, "color_speed": x.color_speed, "opacity": x.opacity, "var_color": x.var_color,
            "name": x.name, "coefs": [float(c) for c in x.coefs], "pre": [float(c) for c in x.pre],
            "post": [float(c) for c in x.post], "variations": {k: float(v) for k, v in x.variations.items()},
            "params": _effective_params(x), "chaos": _chaos(x, n)}


def flame_differences(a: Flame, b: Flame, tol: float = DEFAULT_TOLERANCE, ignore: tuple[str, ...] = IGNORED_FIELDS) -> list[str]:
    """Where `a` and `b` differ in anything that changes the render (empty list: equivalent); see the module docstring."""
    out: list[str] = []
    _compare(_normalised(a, ignore), _normalised(b, ignore), "flame", tol, out)
    return out


def flames_equivalent(a: Flame, b: Flame, tol: float = DEFAULT_TOLERANCE, ignore: tuple[str, ...] = IGNORED_FIELDS) -> bool:
    """True when `a` and `b` render the same (see `flame_differences`)."""
    return not flame_differences(a, b, tol, ignore)


__all__ = ["num", "coord", "affine", "mapping", "color_hex", "xform_lines", "palette_lines", "stops_call", "curve_call",
           "flame_differences", "flames_equivalent", "DEFAULT_TOLERANCE"]

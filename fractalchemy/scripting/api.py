"""The scripting API: what a script sees as its global names.

A script is plain Python. `ScriptContext.namespace()` builds its globals: the flame being edited plus helper
objects (`transforms`, `transform`, `camera`, `gradient`, `xaos`, `coloring`) and functions covering everything
the main window, the settings panel and the Gradient Library can edit — transforms and their variations,
parameters, colours, the chaos (xaos) matrix, the camera, the tone mapping — and a few conveniences
(random numbers, prompts, `update()` to re-render while the script runs).

Affine conventions are the model's (flam3 / Apophysis script order): `coefs = (a, b, c, d, e, f)` maps
`(x, y)` to `(a·x + c·y + e, b·x + d·y + f)`, so X = (a, b), Y = (c, d) and O = (e, f) are the triangle's
vectors; fractal-space y points down on screen.

The API talks to the application only through a `ScriptHost` (output, prompts, re-rendering), so it is
Qt-free and runs in tests with a fake host.
"""

from __future__ import annotations

import math
import random as _random
import time
from pathlib import Path
from typing import Callable, Iterable, Iterator, MutableMapping

from .. import config
from ..fractal import variations as V
from ..fractal.random_flame import RandomOptions, frame_camera, random_flame as _random_flame, random_gradient
from ..fractal.scene import Affine, Camera, Coloring, Flame, XForm, identity_affine
from ..model import Gradient, hex_to_rgb, rgb_to_hex, simplify
from ..model import operations as gradient_ops
from ..model.adjust import shift_hsl
from ..model.stop import ColorStop

PALETTE_SIZE = 256
DEFAULT_TRANSFORM_COUNT = (2, 5)
SLEEP_SLICE = 0.05


class ScriptError(Exception):
    """A mistake in the script's use of the API (bad name, index out of range, …); reported with its line."""


class ScriptStopped(BaseException):
    """Raised inside the script when it is stopped (Stop button or `stop()`); not an Exception, so a script's
    `except Exception:` cannot swallow it."""

    def __init__(self, reason: str = ""):
        super().__init__(reason or "Script stopped")
        self.reason = reason


class ScriptHost:
    """What the application provides to a running script. The default does nothing (tests subclass it)."""

    def print(self, text: str) -> None:
        pass

    def clear(self) -> None:
        pass

    def message(self, text: str) -> None:
        pass

    def input_text(self, prompt: str, default: str) -> str | None:
        return default

    def confirm(self, text: str) -> bool:
        return True

    def update(self, flame: Flame, wait: bool) -> None:
        pass

    def progress(self, fraction: float) -> None:
        pass

    def check_stop(self) -> None:
        """Raise ScriptStopped if the user pressed Stop (called from long waits)."""


# =====================================================================================================
# helpers
# =====================================================================================================
def _color(value) -> tuple[int, int, int]:
    """An RGB triple from `(r, g, b)` (0..255), `"#rrggbb"` or a ColorStop."""
    if isinstance(value, ColorStop):
        return tuple(value.color)
    if isinstance(value, str):
        try:
            return hex_to_rgb(value)
        except ValueError as exc:
            raise ScriptError(f"'{value}' is not a colour (use '#rrggbb' or (r, g, b))") from exc
    try:
        r, g, b = value
    except (TypeError, ValueError) as exc:
        raise ScriptError(f"{value!r} is not a colour (use '#rrggbb' or (r, g, b))") from exc
    return tuple(max(0, min(255, int(round(c)))) for c in (r, g, b))


def _variation_name(name: str) -> str:
    """The canonical registry name, or a ScriptError naming the problem."""
    if not isinstance(name, str):
        raise ScriptError(f"variation name must be a string, not {type(name).__name__}")
    canonical = V.canonical_name(name)
    if canonical not in V.REGISTRY:
        close = [n for n in V.catalogue() if name.lower() in n.lower()][:6]
        hint = f" Did you mean: {', '.join(close)}?" if close else " list_variations() shows every name."
        raise ScriptError(f"unknown variation '{name}'.{hint}")
    return canonical


def _fill_defaults(xform: XForm, name: str) -> None:
    """Give a freshly added variation its parameter defaults (as Apophysis does)."""
    var = V.REGISTRY.get(name)
    if var is not None:
        for key, default in var.params.items():
            xform.params.setdefault(key, float(default))


def _assign_flame(target: Flame, source: Flame) -> None:
    """Copy every field of `source` into `target` (the script's `flame` object keeps its identity)."""
    copy = source.copy()
    target.name = copy.name
    target.xforms = copy.xforms
    target.final = copy.final
    target.camera = copy.camera
    target.coloring = copy.coloring
    target.palette = copy.palette
    target.unsupported = copy.unsupported
    target.source_version = copy.source_version
    target.oversample = copy.oversample
    target.filter_radius = copy.filter_radius


def _fmt(value) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


# =====================================================================================================
# Transform
# =====================================================================================================
class VariationMap(MutableMapping):
    """Live view of a transform's variations: `t.variations['julian'] = 1` adds it (with parameter defaults),
    assigning 0 or `del` removes it. Names are checked against the loaded formulas."""

    def __init__(self, xform: XForm):
        self._x = xform

    def __getitem__(self, name: str) -> float:
        key = V.canonical_name(name) if isinstance(name, str) else name
        if key in self._x.variations:
            return self._x.variations[key]
        if name in self._x.variations:
            return self._x.variations[name]
        raise KeyError(name)

    def __setitem__(self, name: str, weight: float) -> None:
        key = name if name in self._x.variations else _variation_name(name)
        if not weight:
            self._x.variations.pop(key, None)
            return
        self._x.variations[key] = float(weight)
        _fill_defaults(self._x, key)

    def __delitem__(self, name: str) -> None:
        key = V.canonical_name(name) if isinstance(name, str) else name
        if key in self._x.variations:
            del self._x.variations[key]
        elif name in self._x.variations:
            del self._x.variations[name]
        else:
            raise KeyError(name)

    def __iter__(self) -> Iterator[str]:
        return iter(list(self._x.variations))

    def __len__(self) -> int:
        return len(self._x.variations)

    def __contains__(self, name) -> bool:
        return name in self._x.variations or (isinstance(name, str) and V.canonical_name(name) in self._x.variations)

    def __repr__(self) -> str:
        return "{" + ", ".join(f"{k!r}: {_fmt(v)}" for k, v in self._x.variations.items()) + "}"


class Affine6:
    """a..f access to an affine tuple held by a transform (`t.post.a = 1.2`)."""

    def __init__(self, get: Callable[[], Affine], set_: Callable[[Affine], None]):
        self._get, self._set = get, set_

    def _coef(self, index: int) -> float:
        return self._get()[index]

    def _set_coef(self, index: int, value: float) -> None:
        coefs = list(self._get())
        coefs[index] = float(value)
        self._set(tuple(coefs))

    a = property(lambda s: s._coef(0), lambda s, v: s._set_coef(0, v))
    b = property(lambda s: s._coef(1), lambda s, v: s._set_coef(1, v))
    c = property(lambda s: s._coef(2), lambda s, v: s._set_coef(2, v))
    d = property(lambda s: s._coef(3), lambda s, v: s._set_coef(3, v))
    e = property(lambda s: s._coef(4), lambda s, v: s._set_coef(4, v))
    f = property(lambda s: s._coef(5), lambda s, v: s._set_coef(5, v))

    @property
    def coefs(self) -> tuple:
        return tuple(self._get())

    @coefs.setter
    def coefs(self, value) -> None:
        self._set(_affine(value))

    def reset(self) -> "Affine6":
        """Back to the identity."""
        self._set(identity_affine())
        return self

    def __iter__(self):
        return iter(self._get())

    def __repr__(self) -> str:
        return "(" + ", ".join(_fmt(c) for c in self._get()) + ")"


def _affine(value) -> Affine:
    try:
        coefs = tuple(float(c) for c in value)
    except (TypeError, ValueError) as exc:
        raise ScriptError("an affine needs six numbers (a, b, c, d, e, f)") from exc
    if len(coefs) != 6:
        raise ScriptError("an affine needs six numbers (a, b, c, d, e, f)")
    return coefs


def _rotated(coefs: Affine, degrees: float) -> Affine:
    """The X and Y vectors turned by `degrees` counter-clockwise on screen (y points down in fractal space)."""
    a, b, c, d, e, f = coefs
    angle = math.radians(-degrees)
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    return (a * cos_a - b * sin_a, a * sin_a + b * cos_a, c * cos_a - d * sin_a, c * sin_a + d * cos_a, e, f)


class Transform:
    """A transform of the flame — a live view of one `XForm` (or of the *active* one for the global `transform`).

    Attributes are read and written directly: `t.weight = 0.5`, `t.a = 0.7`, `t.variations['spherical'] = 1`,
    `t.params['julian_power'] = 4`. Editing methods return the transform, so calls chain:
    `t.rotate(30).scale(0.8).translate(0.2, 0)`.
    """

    def __init__(self, context: "ScriptContext", xform: XForm | None = None):
        self._ctx = context
        self._xform = xform      # None: follow the active transform

    # --- identity -----------------------------------------------------------------------------------
    @property
    def _x(self) -> XForm:
        if self._xform is not None:
            return self._xform
        return self._ctx.active_xform()

    @property
    def index(self) -> int:
        """Position in `transforms` (0-based); -1 for the final transform or a detached copy."""
        x = self._x
        for i, candidate in enumerate(self._ctx.flame.xforms):
            if candidate is x:
                return i
        return -1

    @property
    def is_final(self) -> bool:
        return self._ctx.flame.final is self._x

    @property
    def xform(self) -> XForm:
        """The underlying model object (for anything the wrapper does not cover)."""
        return self._x

    def __eq__(self, other) -> bool:
        return isinstance(other, Transform) and other._x is self._x

    def __hash__(self) -> int:
        return id(self._x)

    def __repr__(self) -> str:
        x = self._x
        label = "final" if self.is_final else f"#{self.index + 1}"
        return f"<Transform {label}: {' + '.join(x.variations) or 'no variations'}, weight {_fmt(x.weight)}>"

    # --- plain attributes -----------------------------------------------------------------------------
    def _get(self, name):
        return getattr(self._x, name)

    def _set(self, name, value) -> None:
        setattr(self._x, name, value)

    weight = property(lambda s: s._get("weight"), lambda s, v: s._set("weight", max(0.0, float(v))))
    color = property(lambda s: s._get("color"), lambda s, v: s._set("color", min(1.0, max(0.0, float(v)))))
    color_speed = property(lambda s: s._get("color_speed"), lambda s, v: s._set("color_speed", min(1.0, max(0.0, float(v)))))
    opacity = property(lambda s: s._get("opacity"), lambda s, v: s._set("opacity", min(1.0, max(0.0, float(v)))))
    var_color = property(lambda s: s._get("var_color"), lambda s, v: s._set("var_color", float(v)))
    name = property(lambda s: s._get("name"), lambda s, v: s._set("name", str(v)))

    @property
    def symmetry(self) -> float:
        """Apophysis's `symmetry` (= 1 − 2·color_speed)."""
        return self._x.symmetry

    @symmetry.setter
    def symmetry(self, value: float) -> None:
        self._x.color_speed = XForm.speed_from_symmetry(float(value))

    # --- affine ------------------------------------------------------------------------------------------
    def _coef(self, index: int) -> float:
        return self._x.coefs[index]

    def _set_coef(self, index: int, value: float) -> None:
        coefs = list(self._x.coefs)
        coefs[index] = float(value)
        self._x.coefs = tuple(coefs)

    a = property(lambda s: s._coef(0), lambda s, v: s._set_coef(0, v))
    b = property(lambda s: s._coef(1), lambda s, v: s._set_coef(1, v))
    c = property(lambda s: s._coef(2), lambda s, v: s._set_coef(2, v))
    d = property(lambda s: s._coef(3), lambda s, v: s._set_coef(3, v))
    e = property(lambda s: s._coef(4), lambda s, v: s._set_coef(4, v))
    f = property(lambda s: s._coef(5), lambda s, v: s._set_coef(5, v))

    @property
    def coefs(self) -> tuple:
        """All six coefficients (a, b, c, d, e, f)."""
        return tuple(self._x.coefs)

    @coefs.setter
    def coefs(self, value) -> None:
        self._x.coefs = _affine(value)

    @property
    def post(self) -> Affine6:
        """The post-variation affine (a..f, `coefs`, `reset()`)."""
        x = self._x
        return Affine6(lambda: x.post, lambda v: setattr(x, "post", v))

    @post.setter
    def post(self, value) -> None:
        self._x.post = _affine(value)

    def set_affine(self, a: float, b: float, c: float, d: float, e: float, f: float) -> "Transform":
        """Set all six coefficients: x′ = a·x + c·y + e, y′ = b·x + d·y + f."""
        self._x.coefs = _affine((a, b, c, d, e, f))
        return self

    def reset_affine(self) -> "Transform":
        """Identity affine (and keep everything else)."""
        self._x.coefs = identity_affine()
        return self

    def reset_post(self) -> "Transform":
        self._x.post = identity_affine()
        return self

    def rotate(self, degrees: float) -> "Transform":
        """Turn the triangle about its own origin O (positive = counter-clockwise on screen)."""
        self._x.coefs = _rotated(self._x.coefs, float(degrees))
        return self

    def rotate_around(self, degrees: float, x: float = 0.0, y: float = 0.0) -> "Transform":
        """Turn the whole triangle, origin included, about the point (x, y)."""
        a, b, c, d, e, f = _rotated(self._x.coefs, float(degrees))
        angle = math.radians(-float(degrees))
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        dx, dy = e - x, f - y
        self._x.coefs = (a, b, c, d, x + dx * cos_a - dy * sin_a, y + dx * sin_a + dy * cos_a)
        return self

    def scale(self, sx: float, sy: float | None = None) -> "Transform":
        """Scale the X and Y vectors about the origin (one factor, or separate x / y factors)."""
        sy = sx if sy is None else sy
        a, b, c, d, e, f = self._x.coefs
        self._x.coefs = (a * sx, b * sx, c * sy, d * sy, e, f)
        return self

    def translate(self, dx: float, dy: float) -> "Transform":
        """Move the origin by (dx, dy) fractal units (y down on screen)."""
        a, b, c, d, e, f = self._x.coefs
        self._x.coefs = (a, b, c, d, e + float(dx), f + float(dy))
        return self

    def move_to(self, x: float, y: float) -> "Transform":
        """Put the origin at (x, y)."""
        a, b, c, d, _e, _f = self._x.coefs
        self._x.coefs = (a, b, c, d, float(x), float(y))
        return self

    def multiply(self, a: float, b: float, c: float, d: float) -> "Transform":
        """Apophysis `Multiply`: compose the 2×2 part with [[a, b], [c, d]] (the new matrix acts first)."""
        xa, xb, xc, xd, e, f = self._x.coefs
        self._x.coefs = (xa * a + xc * b, xb * a + xd * b, xa * c + xc * d, xb * c + xd * d, e, f)
        return self

    def flip_horizontal(self) -> "Transform":
        """Mirror the triangle in the vertical axis through the origin (0, 0)."""
        a, b, c, d, e, f = self._x.coefs
        self._x.coefs = (-a, b, -c, d, -e, f)
        return self

    def flip_vertical(self) -> "Transform":
        a, b, c, d, e, f = self._x.coefs
        self._x.coefs = (a, -b, c, -d, e, -f)
        return self

    @property
    def origin(self) -> tuple[float, float]:
        """(e, f): where the triangle's O point sits."""
        return (self._x.coefs[4], self._x.coefs[5])

    @origin.setter
    def origin(self, value) -> None:
        x, y = value
        self.move_to(x, y)

    @property
    def determinant(self) -> float:
        a, b, c, d, _e, _f = self._x.coefs
        return a * d - b * c

    # --- variations ---------------------------------------------------------------------------------------
    @property
    def variations(self) -> VariationMap:
        """Variation name → weight (live; assign 0 to remove)."""
        return VariationMap(self._x)

    @variations.setter
    def variations(self, value) -> None:
        if not isinstance(value, dict):
            raise ScriptError("variations must be a dict, e.g. {'linear': 1, 'spherical': 0.5}")
        self._x.variations = {}
        for name, weight in value.items():
            VariationMap(self._x)[name] = weight

    @property
    def variation_names(self) -> list[str]:
        return list(self._x.variations)

    def set_variation(self, name: str, weight: float) -> "Transform":
        """Set a variation's weight (0 removes it); parameters get their defaults."""
        VariationMap(self._x)[name] = weight
        return self

    def get_variation(self, name: str) -> float:
        """A variation's weight (0 if it is not used)."""
        return self._x.variations.get(V.canonical_name(name), self._x.variations.get(name, 0.0))

    def has_variation(self, name: str) -> bool:
        return name in VariationMap(self._x)

    def remove_variation(self, name: str) -> "Transform":
        VariationMap(self._x).pop(V.canonical_name(name), None)
        return self

    def clear_variations(self) -> "Transform":
        """Remove every variation (the transform contributes nothing until one is added)."""
        self._x.variations = {}
        return self

    def total_variation_weight(self) -> float:
        return float(sum(self._x.variations.values()))

    def normalize_variations(self) -> "Transform":
        """Scale the variation weights so they add up to 1."""
        total = self.total_variation_weight()
        if total:
            self._x.variations = {k: v / total for k, v in self._x.variations.items()}
        return self

    @property
    def params(self) -> dict:
        """Variation parameters keyed as in flame files (`julian_power`); live dict."""
        return self._x.params

    @params.setter
    def params(self, value) -> None:
        self._x.params = {str(k): float(v) for k, v in dict(value).items()}

    def set_param(self, name: str, value: float) -> "Transform":
        """Set a parameter; the name is checked against the loaded formulas."""
        if V.parameter_owner(name) is None and name not in self._x.params:
            owner = name.split("_")[0]
            options = list(V.REGISTRY[owner].params) if owner in V.REGISTRY else []
            raise ScriptError(f"unknown parameter '{name}'." + (f" Parameters of {owner}: {', '.join(options)}" if options else ""))
        self._x.params[name] = float(value)
        return self

    def get_param(self, name: str, default: float | None = None) -> float:
        """A parameter's value, else its formula default, else `default`."""
        if name in self._x.params:
            return self._x.params[name]
        owner = V.parameter_owner(name)
        if owner is not None:
            return V.REGISTRY[owner].params[name]
        if default is None:
            raise ScriptError(f"unknown parameter '{name}'")
        return default

    # --- xaos row -------------------------------------------------------------------------------------------
    @property
    def xaos(self) -> list[float]:
        """This transform's chaos row: the relative weight of every transform following it (1 = normal)."""
        n = len(self._ctx.flame.xforms)
        row = self._x.chaos
        if row is None:
            return [1.0] * n
        return [float(row[i]) if i < len(row) else 1.0 for i in range(n)]

    @xaos.setter
    def xaos(self, value) -> None:
        if value is None:
            self._x.chaos = None
        else:
            self._x.chaos = [max(0.0, float(v)) for v in value]

    # --- copies ------------------------------------------------------------------------------------------------
    def copy(self) -> "Transform":
        """A detached copy (add it with `add_transform(copy)`)."""
        return Transform(self._ctx, self._x.copy())

    def to_dict(self) -> dict:
        x = self._x
        return {"weight": x.weight, "color": x.color, "color_speed": x.color_speed, "opacity": x.opacity, "coefs": list(x.coefs),
                "post": list(x.post), "variations": dict(x.variations), "params": dict(x.params), "chaos": x.chaos, "name": x.name}


class TransformList:
    """`transforms`: the flame's transforms as `Transform` objects (live; supports `len`, indexing, slicing, iteration)."""

    def __init__(self, context: "ScriptContext"):
        self._ctx = context

    def _xforms(self) -> list[XForm]:
        return self._ctx.flame.xforms

    def __len__(self) -> int:
        return len(self._xforms())

    def __iter__(self) -> Iterator[Transform]:
        return iter([Transform(self._ctx, x) for x in self._xforms()])

    def __getitem__(self, index):
        xforms = self._xforms()
        if isinstance(index, slice):
            return [Transform(self._ctx, x) for x in xforms[index]]
        try:
            return Transform(self._ctx, xforms[index])
        except IndexError:
            raise ScriptError(f"transform index {index} is out of range (the flame has {len(xforms)} transforms)") from None
        except TypeError:
            raise ScriptError(f"transforms[...] needs an integer index, not {type(index).__name__}") from None

    def __bool__(self) -> bool:
        return bool(self._xforms())

    def __contains__(self, item) -> bool:
        return any(isinstance(item, Transform) and item._x is x for x in self._xforms())

    def index(self, item: Transform) -> int:
        for i, x in enumerate(self._xforms()):
            if item._x is x:
                return i
        raise ScriptError("that transform is not in the flame")

    def __repr__(self) -> str:
        return "[" + ", ".join(repr(t) for t in self) + "]"


# =====================================================================================================
# Camera, colouring, gradient, xaos helpers
# =====================================================================================================
class CameraHelper:
    """`camera`: the view. Angles are degrees; `zoom` is Apophysis's log2 zoom (each +1 doubles the magnification)."""

    def __init__(self, context: "ScriptContext"):
        self._ctx = context

    @property
    def _cam(self) -> Camera:
        return self._ctx.flame.camera

    x = property(lambda s: s._cam.center[0], lambda s, v: setattr(s._cam, "center", (float(v), s._cam.center[1])))
    y = property(lambda s: s._cam.center[1], lambda s, v: setattr(s._cam, "center", (s._cam.center[0], float(v))))
    scale = property(lambda s: s._cam.scale, lambda s, v: setattr(s._cam, "scale", max(1e-6, float(v))))
    zoom = property(lambda s: s._cam.zoom, lambda s, v: setattr(s._cam, "zoom", float(v)))
    rotate = property(lambda s: s._cam.rotate, lambda s, v: setattr(s._cam, "rotate", float(v)))
    width = property(lambda s: s._cam.width, lambda s, v: setattr(s._cam, "width", max(1, int(v))))
    height = property(lambda s: s._cam.height, lambda s, v: setattr(s._cam, "height", max(1, int(v))))
    pitch = property(lambda s: math.degrees(s._cam.pitch), lambda s, v: setattr(s._cam, "pitch", math.radians(float(v))))
    pitch_y = property(lambda s: math.degrees(s._cam.pitch_y), lambda s, v: setattr(s._cam, "pitch_y", math.radians(float(v))))
    yaw = property(lambda s: math.degrees(s._cam.yaw), lambda s, v: setattr(s._cam, "yaw", math.radians(float(v))))
    perspective = property(lambda s: s._cam.perspective, lambda s, v: setattr(s._cam, "perspective", float(v)))
    zpos = property(lambda s: s._cam.zpos, lambda s, v: setattr(s._cam, "zpos", float(v)))
    dof = property(lambda s: s._cam.dof, lambda s, v: setattr(s._cam, "dof", float(v)))

    @property
    def center(self) -> tuple[float, float]:
        return tuple(self._cam.center)

    @center.setter
    def center(self, value) -> None:
        x, y = value
        self._cam.center = (float(x), float(y))

    @property
    def size(self) -> tuple[int, int]:
        return (self._cam.width, self._cam.height)

    def set_size(self, width: int, height: int) -> "CameraHelper":
        """The flame's own image size in pixels (framing follows the width)."""
        self._cam.width, self._cam.height = max(1, int(width)), max(1, int(height))
        return self

    def reset(self) -> "CameraHelper":
        """Centre (0, 0), scale 200 at the flame's size, no zoom / rotation / 3D."""
        cam = self._cam
        self._ctx.flame.camera = Camera(width=cam.width, height=cam.height)
        return self

    def reset_3d(self) -> "CameraHelper":
        """Flat again: pitch, yaw, perspective, z position and depth blur back to 0."""
        cam = self._cam
        cam.pitch = cam.pitch_y = cam.yaw = cam.perspective = cam.zpos = cam.dof = 0.0
        return self

    def pan(self, dx: float, dy: float) -> "CameraHelper":
        """Move the centre by (dx, dy) fractal units (y down)."""
        self._cam.center = (self._cam.center[0] + float(dx), self._cam.center[1] + float(dy))
        return self

    def zoom_by(self, factor: float) -> "CameraHelper":
        """Multiply the magnification (2 = twice as close)."""
        if factor <= 0:
            raise ScriptError("zoom_by needs a positive factor")
        self._cam.zoom += math.log2(float(factor))
        return self

    def rotate_by(self, degrees: float) -> "CameraHelper":
        self._cam.rotate = (self._cam.rotate + float(degrees)) % 360.0
        return self

    def fit(self, margin: float = 1.15) -> bool:
        """Frame the attractor (as the Random Batch does); False if the system blows up or collapses."""
        return frame_camera(self._ctx.flame, float(margin))

    def to_dict(self) -> dict:
        return self._ctx.flame.to_dict()["camera"]

    def __repr__(self) -> str:
        c = self._cam
        return f"<camera center ({_fmt(c.center[0])}, {_fmt(c.center[1])}) scale {_fmt(c.scale)} zoom {_fmt(c.zoom)} rotate {_fmt(c.rotate)} {c.width}×{c.height}>"


class ColoringHelper:
    """`coloring`: the tone mapping (brightness, gamma, gamma_threshold, vibrancy, contrast, background)."""

    def __init__(self, context: "ScriptContext"):
        self._ctx = context

    @property
    def _col(self) -> Coloring:
        return self._ctx.flame.coloring

    brightness = property(lambda s: s._col.brightness, lambda s, v: setattr(s._col, "brightness", max(0.0, float(v))))
    gamma = property(lambda s: s._col.gamma, lambda s, v: setattr(s._col, "gamma", max(0.01, float(v))))
    gamma_threshold = property(lambda s: s._col.gamma_threshold, lambda s, v: setattr(s._col, "gamma_threshold", max(0.0, float(v))))
    vibrancy = property(lambda s: s._col.vibrancy, lambda s, v: setattr(s._col, "vibrancy", min(1.0, max(0.0, float(v)))))
    contrast = property(lambda s: s._col.contrast, lambda s, v: setattr(s._col, "contrast", max(0.01, float(v))))

    @property
    def background(self) -> tuple[int, int, int]:
        return tuple(self._col.background)

    @background.setter
    def background(self, value) -> None:
        self._col.background = _color(value)

    @property
    def background_hex(self) -> str:
        return "#" + rgb_to_hex(self._col.background).lstrip("#")

    def reset(self) -> "ColoringHelper":
        """Apophysis defaults: brightness 4, gamma 4, threshold 0.01, vibrancy 1, contrast 1, black background."""
        self._ctx.flame.coloring = Coloring()
        return self

    def reset_curves(self, channel: str | None = None) -> "ColoringHelper":
        """Straighten the tone curves (one channel — overall / red / green / blue / alpha — or all)."""
        self._col.curves.reset(channel)
        return self

    def __repr__(self) -> str:
        c = self._col
        return f"<coloring brightness {_fmt(c.brightness)} gamma {_fmt(c.gamma)} threshold {_fmt(c.gamma_threshold)} vibrancy {_fmt(c.vibrancy)} contrast {_fmt(c.contrast)} background {self.background_hex}>"


class GradientHelper:
    """`gradient`: the flame's palette (256 colours) and node-based edits like the Gradient Library's.

    Colours are `(r, g, b)` 0..255 or `'#rrggbb'`. Node operations work on a simplified stop list (as the
    Gradient Library shows) and re-sample it into the palette.
    """

    def __init__(self, context: "ScriptContext"):
        self._ctx = context

    @property
    def _flame(self) -> Flame:
        return self._ctx.flame

    # --- palette --------------------------------------------------------------------------------------------
    @property
    def colors(self) -> list[tuple[int, int, int]]:
        """All 256 palette entries (a copy; assign a list of 256 colours to replace them)."""
        return [tuple(c) for c in self._flame.palette]

    @colors.setter
    def colors(self, value) -> None:
        colors = [_color(c) for c in value]
        if len(colors) != PALETTE_SIZE:
            colors = Gradient.from_colors("palette", colors).sample(PALETTE_SIZE) if colors else Flame().palette
        self._flame.palette = [tuple(c) for c in colors]

    def get_color(self, index: int) -> tuple[int, int, int]:
        return tuple(self._flame.palette[max(0, min(PALETTE_SIZE - 1, int(index)))])

    def set_color(self, index: int, color) -> "GradientHelper":
        """Set one palette entry (index 0..255)."""
        self._flame.palette[max(0, min(PALETTE_SIZE - 1, int(index)))] = _color(color)
        return self

    def color_at(self, position: float) -> tuple[int, int, int]:
        """The colour at position 0..1 (the colour a transform with `color = position` paints with)."""
        return self.get_color(round(max(0.0, min(1.0, float(position))) * (PALETTE_SIZE - 1)))

    def hex_colors(self) -> list[str]:
        return ["#" + rgb_to_hex(c).lstrip("#") for c in self._flame.palette]

    # --- stops ---------------------------------------------------------------------------------------------------
    @property
    def stops(self) -> Gradient:
        """The palette as a node gradient (simplified, like the Gradient Library shows it) — a copy."""
        return Gradient(self._flame.name, simplify(self._flame.gradient.stops, config.IMPORT_SIMPLIFY_TOLERANCE))

    def set_stops(self, stops) -> "GradientHelper":
        """Replace the palette from a node gradient: a `Gradient`, or a list of `(position, color)` pairs."""
        if isinstance(stops, Gradient):
            gradient = stops
        else:
            try:
                gradient = Gradient("script", [ColorStop(float(p), _color(c)) for p, c in stops])
            except (TypeError, ValueError) as exc:
                raise ScriptError("set_stops needs a Gradient or a list of (position, color) pairs") from exc
        if not gradient.stops:
            raise ScriptError("a gradient needs at least one stop")
        self._flame.set_gradient(gradient)
        return self

    def from_colors(self, colors) -> "GradientHelper":
        """Spread the given colours evenly over the palette (e.g. `['#000', '#f80', '#fff']`)."""
        colors = [_color(c) for c in colors]
        if not colors:
            raise ScriptError("from_colors needs at least one colour")
        self._flame.set_gradient(Gradient.from_colors("script", colors))
        return self

    def _apply_stop_op(self, op: Callable[[Gradient, _random.Random], list[ColorStop]]) -> "GradientHelper":
        base = self.stops
        self._flame.set_gradient(Gradient(base.name, op(base, self._ctx.rng)))
        return self

    def random(self) -> "GradientHelper":
        """A whole new random gradient (the Gradient Library's *Reroll*)."""
        self._flame.set_gradient(random_gradient(self._ctx.rng))
        return self

    def randomize_colors(self) -> "GradientHelper":
        """Keep the nodes, draw new harmonising colours."""
        return self._apply_stop_op(gradient_ops.randomize_colors)

    def randomize_positions(self) -> "GradientHelper":
        """Keep the colours, scatter the nodes."""
        return self._apply_stop_op(gradient_ops.randomize_positions)

    def add_nodes(self) -> "GradientHelper":
        return self._apply_stop_op(gradient_ops.add_nodes)

    def remove_nodes(self) -> "GradientHelper":
        return self._apply_stop_op(gradient_ops.remove_nodes)

    def smooth(self) -> "GradientHelper":
        """Blur the colour curve (the Gradient Library's *Smooth gradient*)."""
        return self._apply_stop_op(lambda g, _rng: gradient_ops.smooth(g))

    # --- whole-palette adjustments --------------------------------------------------------------------------------
    def rotate(self, amount: float) -> "GradientHelper":
        """Cycle the palette by `amount` of its length (0.5 = half a turn) or, if |amount| ≥ 1, by that many entries."""
        n = int(round(amount * PALETTE_SIZE)) if abs(amount) < 1 else int(amount)
        n %= PALETTE_SIZE
        palette = self._flame.palette
        self._flame.palette = palette[-n:] + palette[:-n] if n else list(palette)
        return self

    def reverse(self) -> "GradientHelper":
        self._flame.palette = list(reversed(self._flame.palette))
        return self

    def invert(self) -> "GradientHelper":
        self._flame.palette = [(255 - r, 255 - g, 255 - b) for r, g, b in self._flame.palette]
        return self

    def hue_shift(self, degrees: float) -> "GradientHelper":
        return self.adjust(hue=degrees)

    def adjust(self, hue: float = 0.0, saturation: float = 0.0, luminance: float = 0.0) -> "GradientHelper":
        """The Gradient Library's sliders: hue in degrees, saturation / luminance in percent (−100 .. 100)."""
        self._flame.palette = [shift_hsl(tuple(c), float(hue), float(saturation), float(luminance)) for c in self._flame.palette]
        return self

    def blend(self, other, amount: float = 0.5) -> "GradientHelper":
        """Mix with another palette (a list of colours, a `Gradient` or another flame's gradient helper)."""
        if isinstance(other, GradientHelper):
            colors = other.colors
        elif isinstance(other, Gradient):
            colors = other.sample(PALETTE_SIZE)
        else:
            colors = [_color(c) for c in other]
            if len(colors) != PALETTE_SIZE:
                colors = Gradient.from_colors("b", colors).sample(PALETTE_SIZE)
        t = min(1.0, max(0.0, float(amount)))
        self._flame.palette = [tuple(int(round(a + (b - a) * t)) for a, b in zip(ca, cb)) for ca, cb in zip(self._flame.palette, colors)]
        return self

    def load(self, path, index: int = 0) -> "GradientHelper":
        """Load a gradient from any file the Gradient Library reads (.ugr, .map, .flame, .chaos, .fa, images …)."""
        from ..formats.registry import load_gradient
        try:
            gradient = load_gradient(Path(path).expanduser(), int(index))
        except Exception as exc:  # noqa: BLE001 - any reader error becomes a script error
            raise ScriptError(f"cannot load gradient from {path}: {exc}") from exc
        self._flame.set_gradient(gradient)
        return self

    def __repr__(self) -> str:
        return f"<gradient {len(self.stops)} nodes, {PALETTE_SIZE} colours>"


class XaosHelper:
    """`xaos`: the chaos matrix. `matrix[from][to]` is the relative weight of transform `to` following
    transform `from` (1 = normal, 0 = never)."""

    def __init__(self, context: "ScriptContext"):
        self._ctx = context

    def _index(self, which) -> int:
        n = len(self._ctx.flame.xforms)
        i = which.index if isinstance(which, Transform) else which
        if not isinstance(i, int) or not 0 <= i < n:
            raise ScriptError(f"transform index {which} is out of range (the flame has {n} transforms)")
        return i

    def _row(self, i: int) -> list[float]:
        x = self._ctx.flame.xforms[i]
        n = len(self._ctx.flame.xforms)
        if x.chaos is None:
            x.chaos = [1.0] * n
        while len(x.chaos) < n:
            x.chaos.append(1.0)
        return x.chaos

    def get(self, from_, to) -> float:
        i, j = self._index(from_), self._index(to)
        row = self._ctx.flame.xforms[i].chaos
        return 1.0 if row is None or j >= len(row) else float(row[j])

    def set(self, from_, to, weight: float) -> "XaosHelper":
        i, j = self._index(from_), self._index(to)
        self._row(i)[j] = max(0.0, float(weight))
        return self

    @property
    def matrix(self) -> list[list[float]]:
        n = len(self._ctx.flame.xforms)
        return [[self.get(i, j) for j in range(n)] for i in range(n)]

    def set_matrix(self, matrix) -> "XaosHelper":
        for i, row in enumerate(matrix):
            for j, value in enumerate(row):
                self.set(i, j, value)
        return self

    def set_row(self, from_, weights) -> "XaosHelper":
        for j, value in enumerate(weights):
            self.set(from_, j, value)
        return self

    def set_column(self, to, weights) -> "XaosHelper":
        for i, value in enumerate(weights):
            self.set(i, to, value)
        return self

    def reset(self) -> "XaosHelper":
        """No xaos: every transform may follow every other."""
        for x in self._ctx.flame.xforms:
            x.chaos = None
        return self

    def chain(self, allow_self: bool = False) -> "XaosHelper":
        """A ring: transform i may only be followed by i + 1 (and itself if `allow_self`)."""
        n = len(self._ctx.flame.xforms)
        return self.from_function(lambda i, j: 1.0 if j == (i + 1) % n or (allow_self and i == j) else 0.0)

    def isolate(self, which) -> "XaosHelper":
        """Transform `which` only follows itself and nothing else leads to it."""
        k = self._index(which)
        return self.from_function(lambda i, j: 0.0 if (i == k) != (j == k) else 1.0)

    def from_function(self, fn: Callable[[int, int], float]) -> "XaosHelper":
        """Fill the matrix from `fn(from_index, to_index) -> weight`."""
        n = len(self._ctx.flame.xforms)
        for i in range(n):
            for j in range(n):
                self.set(i, j, fn(i, j))
        return self

    def randomize(self, probability: float = 0.5) -> "XaosHelper":
        """Random on / off links (every transform keeps at least one way out)."""
        n = len(self._ctx.flame.xforms)
        rng = self._ctx.rng
        for i in range(n):
            row = [1.0 if rng.random() < probability else 0.0 for _ in range(n)]
            if n and not any(row):
                row[rng.randrange(n)] = 1.0
            self.set_row(i, row)
        return self

    @property
    def is_default(self) -> bool:
        return all(x.chaos is None or all(v == 1.0 for v in x.chaos) for x in self._ctx.flame.xforms)

    def __repr__(self) -> str:
        return "\n".join("  ".join(_fmt(v) for v in row) for row in self.matrix) or "<xaos: no transforms>"

    __str__ = __repr__


# =====================================================================================================
# The context: state + the functions
# =====================================================================================================
class ScriptContext:
    """Builds the global namespace for one script run and holds its state (the flame, the active transform)."""

    def __init__(self, flame: Flame | None, host: ScriptHost | None = None, active: int = 0, seed: int | None = None):
        self.flame = flame.copy() if flame is not None else Flame("untitled", [])
        self.host = host or ScriptHost()
        self.active = max(0, min(active, max(0, len(self.flame.xforms) - 1)))
        self.rng = _random.Random(seed)
        self.snapshots: dict[str, Flame] = {}
        self.output_lines = 0
        self.transforms = TransformList(self)
        self.transform = Transform(self)
        self.camera = CameraHelper(self)
        self.gradient = GradientHelper(self)
        self.xaos = XaosHelper(self)
        self.coloring = ColoringHelper(self)

    # --- state ---------------------------------------------------------------------------------------------
    def active_xform(self) -> XForm:
        xforms = self.flame.xforms
        if not xforms:
            raise ScriptError("the flame has no transforms — add one with add_transform() first")
        self.active = max(0, min(self.active, len(xforms) - 1))
        return xforms[self.active]

    def _index(self, which, default_active: bool = True) -> int:
        if which is None:
            if not default_active:
                raise ScriptError("a transform index is required")
            self.active_xform()   # raises when there is nothing to act on
            return self.active
        if isinstance(which, Transform):
            i = which.index
            if i < 0:
                raise ScriptError("that transform is not in the flame")
            return i
        if isinstance(which, XForm):
            for i, x in enumerate(self.flame.xforms):
                if x is which:
                    return i
            raise ScriptError("that transform is not in the flame")
        n = len(self.flame.xforms)
        if not isinstance(which, int) or isinstance(which, bool) or not -n <= which < n:
            raise ScriptError(f"transform index {which!r} is out of range (the flame has {n} transforms)")
        return which % n

    def _new_xform(self, spec, **fields) -> XForm:
        if isinstance(spec, Transform):
            xform = spec._x.copy()
        elif isinstance(spec, XForm):
            xform = spec.copy()
        elif isinstance(spec, dict):
            fields = {**spec, **fields}
            xform = XForm(variations={})
        elif spec is None:
            xform = XForm(variations={})
        else:
            raise ScriptError("add_transform takes a Transform, a dict of attributes or keyword arguments")
        wrapper = Transform(self, xform)
        if not isinstance(spec, (Transform, XForm)) and "variations" not in fields:
            xform.variations = {"linear": 1.0}
        for key, value in fields.items():
            if key in ("a", "b", "c", "d", "e", "f", "weight", "color", "color_speed", "symmetry", "opacity", "var_color", "name",
                       "coefs", "post", "variations", "params", "xaos"):
                setattr(wrapper, key, value)
            else:
                raise ScriptError(f"unknown transform attribute '{key}'")
        return xform

    # --- transforms ------------------------------------------------------------------------------------------
    def add_transform(self, spec=None, **fields) -> Transform:
        """Append a transform (it becomes the active one). Defaults: linear 1, weight 0.5, colour 0."""
        xform = self._new_xform(spec, **fields)
        self.flame.xforms.append(xform)
        for x in self.flame.xforms:
            if x.chaos is not None:
                x.chaos.append(1.0)
        self.active = len(self.flame.xforms) - 1
        return Transform(self, xform)

    def add_random_transform(self, variations: Iterable[str] | None = None) -> Transform:
        """Append a transform with one of Apophysis's random affines and random variations."""
        from ..fractal.random_flame import _random_xform   # the Random Batch recipe
        names = [_variation_name(n) for n in variations] if variations else [n for n in V.catalogue() if n != "pre_blur"]
        n = len(self.flame.xforms) + 1
        xform = _random_xform(self.rng, n - 1, n, names)
        xform.weight = 1.0 / n
        xform.color = self.rng.random()
        return self.add_transform(xform)

    def insert_transform(self, index: int, spec=None, **fields) -> Transform:
        xform = self._new_xform(spec, **fields)
        index = max(0, min(int(index), len(self.flame.xforms)))
        self.flame.xforms.insert(index, xform)
        for x in self.flame.xforms:
            if x.chaos is not None:
                x.chaos.insert(index, 1.0)
        self.active = index
        return Transform(self, xform)

    def remove_transform(self, which=None) -> Transform:
        """Delete a transform (by index or object; default: the active one); returns the detached transform."""
        i = self._index(which)
        xform = self.flame.xforms.pop(i)
        for x in self.flame.xforms:
            if x.chaos is not None and i < len(x.chaos):
                del x.chaos[i]
        self.active = max(0, min(self.active, len(self.flame.xforms) - 1))
        return Transform(self, xform)

    def copy_transform(self, which=None) -> Transform:
        """Duplicate a transform (default: the active one); the copy is appended and becomes active."""
        i = self._index(which)
        return self.add_transform(self.flame.xforms[i].copy())

    def clear_transforms(self) -> None:
        """Remove every transform (and the final transform)."""
        self.flame.xforms = []
        self.flame.final = None
        self.active = 0

    def get_transform(self, which) -> Transform:
        return Transform(self, self.flame.xforms[self._index(which, default_active=False)])

    def set_active_transform(self, which) -> Transform:
        """Choose which transform `transform` refers to."""
        self.active = self._index(which, default_active=False)
        return Transform(self)

    def move_transform(self, which, to: int) -> None:
        i = self._index(which, default_active=False)
        j = self._index(to, default_active=False)
        xforms = self.flame.xforms
        xforms.insert(j, xforms.pop(i))
        for x in xforms:
            if x.chaos is not None and len(x.chaos) > max(i, j):
                x.chaos.insert(j, x.chaos.pop(i))
        self.active = j

    def swap_transforms(self, first, second) -> None:
        i, j = self._index(first, default_active=False), self._index(second, default_active=False)
        xforms = self.flame.xforms
        xforms[i], xforms[j] = xforms[j], xforms[i]
        for x in xforms:
            if x.chaos is not None and len(x.chaos) > max(i, j):
                x.chaos[i], x.chaos[j] = x.chaos[j], x.chaos[i]

    def for_each_transform(self, fn: Callable) -> None:
        """Call `fn(transform, index)` (or `fn(transform)`) for every transform."""
        for i, x in enumerate(list(self.flame.xforms)):
            t = Transform(self, x)
            try:
                fn(t, i)
            except TypeError as exc:
                if "positional argument" not in str(exc):
                    raise
                fn(t)

    def normalize_weights(self) -> None:
        """Scale the weights so they add up to 1."""
        total = sum(x.weight for x in self.flame.xforms)
        if total > 0:
            for x in self.flame.xforms:
                x.weight /= total

    def total_weight(self) -> float:
        return float(sum(x.weight for x in self.flame.xforms))

    def final_transform(self) -> Transform | None:
        """The final transform as a `Transform`, or None if the flame has none."""
        return Transform(self, self.flame.final) if self.flame.final is not None else None

    def set_final_transform(self, spec=None, **fields) -> Transform:
        """Create (or replace) the final transform; `set_final_transform(None)` with no fields removes it."""
        if spec is None and not fields:
            self.flame.final = None
            return None
        xform = self._new_xform(spec, **fields)
        if "color_speed" not in fields and not isinstance(spec, (Transform, XForm)):
            xform.color_speed = 0.0
        self.flame.final = xform
        return Transform(self, xform)

    def remove_final_transform(self) -> None:
        self.flame.final = None

    def new_transform(self, spec=None, **fields) -> Transform:
        """A detached transform (not in the flame) to prepare and add later."""
        return Transform(self, self._new_xform(spec, **fields))

    # --- flame ----------------------------------------------------------------------------------------------
    def new_flame(self, name: str | None = None, keep_gradient: bool = True) -> Flame:
        """Start from scratch: no transforms, default camera (same size) and colouring; the palette is kept."""
        old = self.flame
        fresh = Flame(name or "untitled", [], camera=Camera(width=old.camera.width, height=old.camera.height))
        if keep_gradient:
            fresh.palette = list(old.palette)
        _assign_flame(self.flame, fresh)
        self.active = 0
        return self.flame

    def random_flame(self, variations: Iterable[str] | None = None, transforms=DEFAULT_TRANSFORM_COUNT, seed: int | None = None) -> Flame:
        """Replace the flame with a random one, as the Random Batch window makes them."""
        names = [_variation_name(n) for n in variations] if variations else [n for n in V.catalogue() if n != "pre_blur"]
        lo, hi = (transforms, transforms) if isinstance(transforms, int) else tuple(transforms)
        options = RandomOptions(names, int(lo), int(hi), self.flame.camera.width, self.flame.camera.height)
        rng = _random.Random(seed) if seed is not None else self.rng
        fresh = _random_flame(rng, options)
        fresh.name = self.flame.name if self.flame.name != "untitled" else "random"
        _assign_flame(self.flame, fresh)
        self.active = 0
        return self.flame

    def load_flame(self, path, index: int = 0) -> Flame:
        """Replace the flame with entry `index` of a .flame / .chaos / .fa file."""
        from ..fractal.formats import load_flame as _load
        try:
            fresh = _load(Path(path).expanduser(), int(index))
        except Exception as exc:  # noqa: BLE001
            raise ScriptError(f"cannot load {path}: {exc}") from exc
        _assign_flame(self.flame, fresh)
        self.active = 0
        return self.flame

    def save_flame(self, path, name: str | None = None) -> int:
        """Append the flame to a .flame or .fa file (created if missing); returns its entry index."""
        from ..fractal.formats import fractal_format_for
        target = Path(path).expanduser()
        try:
            fmt = fractal_format_for(target)
        except Exception as exc:  # noqa: BLE001
            raise ScriptError(str(exc)) from exc
        if not fmt.can_append:
            raise ScriptError(f"{fmt.name} files cannot be written")
        flame = self.flame.copy()
        if name:
            flame.name = str(name)
        try:
            return fmt.append(flame, target)
        except Exception as exc:  # noqa: BLE001
            raise ScriptError(f"cannot save to {target}: {exc}") from exc

    def set_flame(self, flame: Flame) -> Flame:
        """Replace the flame with a `Flame` object (e.g. one from `copy_flame()` / `from_text()`)."""
        if not isinstance(flame, Flame):
            raise ScriptError("set_flame needs a Flame object")
        _assign_flame(self.flame, flame)
        self.active = 0
        return self.flame

    def copy_flame(self) -> Flame:
        return self.flame.copy()

    def flame_text(self) -> str:
        """The flame as Fractalchemy (.fa) parameters text — what *Copy Parameters* puts on the clipboard."""
        from ..fractal.formats import flame_to_text
        return flame_to_text(self.flame)

    def flame_xml(self) -> str:
        """The flame as Apophysis `<flame>` XML."""
        from ..fractal.formats.flame_xml import flame_to_xml
        return flame_to_xml(self.flame)

    def from_text(self, text: str) -> Flame:
        """Replace the flame from parameters text: .fa JSON, Apophysis `<flame>` XML or a Chaotica world."""
        from ..fractal.formats import flame_from_text
        try:
            fresh = flame_from_text(str(text))
        except Exception as exc:  # noqa: BLE001
            raise ScriptError(f"cannot read parameters: {exc}") from exc
        return self.set_flame(fresh)

    def snapshot(self, key: str = "default") -> None:
        """Remember the flame as it is now (script-local; see `restore`)."""
        self.snapshots[str(key)] = self.flame.copy()

    def restore(self, key: str = "default") -> Flame:
        if str(key) not in self.snapshots:
            raise ScriptError(f"no snapshot named '{key}'")
        return self.set_flame(self.snapshots[str(key)])

    def validate(self) -> list[str]:
        """Problems that would stop the flame rendering (empty list = fine)."""
        problems = []
        if not self.flame.renderable():
            problems.append("no transform with a positive weight")
        for i, x in enumerate(self.flame.xforms):
            for name in x.variations:
                if V.resolve(name) is None:
                    problems.append(f"transform {i + 1}: unknown variation '{name}'")
        return problems

    # --- variations ------------------------------------------------------------------------------------------
    @staticmethod
    def list_variations(filter: str = "") -> list[str]:
        """Names of every loaded formula (optionally only those containing `filter`)."""
        return [n for n in sorted(V.catalogue()) if filter.lower() in n.lower()]

    @staticmethod
    def variation_info(name: str) -> dict:
        """Facts about a formula: kind, parameters with defaults, origin, notes."""
        var = V.REGISTRY[_variation_name(name)]
        return {"name": var.name, "kind": var.kind, "params": dict(var.params), "random": var.random, "direct_color": var.dc,
                "depth": var.z, "origin": var.origin, "note": var.note}

    @staticmethod
    def variation_params(name: str) -> list[str]:
        return list(V.REGISTRY[_variation_name(name)].params)

    def random_variation(self, exclude: Iterable[str] = ("pre_blur",)) -> str:
        """A random formula name."""
        names = [n for n in V.REGISTRY if n not in set(exclude)]
        return self.rng.choice(names)

    # --- randomness --------------------------------------------------------------------------------------------
    def random(self, a: float | None = None, b: float | None = None) -> float:
        """random() → 0..1, random(n) → 0..n, random(a, b) → a..b."""
        if a is None:
            return self.rng.random()
        if b is None:
            return self.rng.random() * a
        return self.rng.uniform(a, b)

    def random_int(self, a: int, b: int | None = None) -> int:
        """A random integer in a..b (both included), or 0..a."""
        if b is None:
            a, b = 0, a
        return self.rng.randint(int(a), int(b))

    def random_choice(self, items):
        items = list(items)
        if not items:
            raise ScriptError("random_choice needs a non-empty list")
        return self.rng.choice(items)

    def random_gauss(self, mean: float = 0.0, sigma: float = 1.0) -> float:
        return self.rng.gauss(mean, sigma)

    def random_bool(self, probability: float = 0.5) -> bool:
        return self.rng.random() < probability

    def random_color(self) -> tuple[int, int, int]:
        return (self.rng.randrange(256), self.rng.randrange(256), self.rng.randrange(256))

    def seed(self, value) -> None:
        """Seed the random generator so the script repeats exactly."""
        self.rng.seed(value)

    # --- output and interaction --------------------------------------------------------------------------------------
    def print(self, *values, sep: str = " ", end: str = "\n") -> None:
        """Write to the output panel (works like Python's print)."""
        self.output_lines += 1
        self.host.print(sep.join(str(v) for v in values) + end)

    def clear(self) -> None:
        self.host.clear()

    def message(self, text) -> None:
        """Show a message box (the script continues)."""
        self.host.message(str(text))

    def input_text(self, prompt: str = "Enter a value", default="") -> str | None:
        """Ask for text; None if cancelled."""
        return self.host.input_text(str(prompt), "" if default is None else str(default))

    def input_number(self, prompt: str = "Enter a number", default: float = 0.0) -> float | None:
        """Ask for a number (asks again while the answer is not a number); None if cancelled."""
        text = "" if default is None else f"{default:g}" if isinstance(default, (int, float)) else str(default)
        for _attempt in range(5):
            answer = self.host.input_text(str(prompt), text)
            if answer is None:
                return None
            try:
                return int(answer) if answer.strip().lstrip("-").isdigit() else float(answer)
            except ValueError:
                text = answer
                self.host.message(f"'{answer}' is not a number")
        return None

    def confirm(self, text: str = "Continue?") -> bool:
        return bool(self.host.confirm(str(text)))

    def update(self, wait: bool = True) -> None:
        """Show the flame in the main window now and re-render (`wait=True` waits for the first pass)."""
        self.host.check_stop()
        self.host.update(self.flame.copy(), bool(wait))

    def sleep(self, seconds: float) -> None:
        """Pause (the Stop button still works)."""
        end = time.monotonic() + max(0.0, float(seconds))
        while True:
            self.host.check_stop()
            remaining = end - time.monotonic()
            if remaining <= 0:
                return
            time.sleep(min(SLEEP_SLICE, remaining))

    def progress(self, fraction: float) -> None:
        """Show progress 0..1 in the Script Editor's status bar."""
        self.host.progress(max(0.0, min(1.0, float(fraction))))

    @staticmethod
    def stop(reason: str = "") -> None:
        """End the script here; what it changed so far is kept."""
        raise ScriptStopped(reason)

    # --- namespace --------------------------------------------------------------------------------------------------
    def namespace(self) -> dict:
        """The globals a script runs with."""
        ns = {
            "__name__": "__fractalchemy_script__", "__builtins__": __builtins__,
            "flame": self.flame, "transforms": self.transforms, "transform": self.transform, "camera": self.camera,
            "gradient": self.gradient, "xaos": self.xaos, "coloring": self.coloring,
            "Flame": Flame, "XForm": XForm, "Gradient": Gradient, "ColorStop": ColorStop, "math": math, "PI": math.pi, "TAU": math.tau,
            "hex_to_rgb": lambda text: hex_to_rgb(text), "rgb_to_hex": lambda rgb: "#" + rgb_to_hex(tuple(rgb)).lstrip("#"),
            "clamp": lambda v, lo, hi: max(lo, min(hi, v)), "lerp": lambda a, b, t: a + (b - a) * t,
            "deg2rad": math.radians, "rad2deg": math.degrees, "dist": lambda x1, y1, x2, y2: math.hypot(x2 - x1, y2 - y1),
        }
        for name in FUNCTION_NAMES:
            ns[name] = getattr(self, name)
        ns.update(self.apophysis_aliases())
        return ns

    def apophysis_aliases(self) -> dict:
        """Apophysis-style names (`AddTransform`, `Rotate`, `Print`, …) for users of its scripts."""
        return {
            "Transform": self.transform,
            "AddTransform": lambda: self.add_transform(), "DeleteTransform": lambda: self.remove_transform(),
            "CopyTransform": lambda: self.copy_transform(), "SetActiveTransform": self.set_active_transform,
            "Rotate": lambda deg: self.transform.rotate(deg), "Scale": lambda s: self.transform.scale(s),
            "Translate": lambda dx, dy: self.transform.translate(dx, dy), "Multiply": lambda a, b, c, d: self.transform.multiply(a, b, c, d),
            "RotateFlame": lambda deg: self.camera.rotate_by(deg), "NormalizeWeights": self.normalize_weights,
            "RandomGradient": lambda: self.gradient.random(), "UpdateFlame": lambda: self.update(),
            "ShowMessage": self.message, "Print": self.print, "Clear": self.clear,
            "Random": lambda n=None: self.rng.random() if n is None else self.rng.randrange(int(n)),
            "Trunc": math.trunc, "Round": round, "Sqr": lambda v: v * v,
        }


FUNCTION_NAMES = (
    "add_transform", "add_random_transform", "insert_transform", "remove_transform", "copy_transform", "clear_transforms",
    "get_transform", "set_active_transform", "move_transform", "swap_transforms", "for_each_transform", "normalize_weights",
    "total_weight", "final_transform", "set_final_transform", "remove_final_transform", "new_transform",
    "new_flame", "random_flame", "load_flame", "save_flame", "set_flame", "copy_flame", "flame_text", "flame_xml", "from_text",
    "snapshot", "restore", "validate",
    "list_variations", "variation_info", "variation_params", "random_variation",
    "random", "random_int", "random_choice", "random_gauss", "random_bool", "random_color", "seed",
    "print", "clear", "message", "input_text", "input_number", "confirm", "update", "sleep", "progress", "stop",
)

__all__ = ["ScriptContext", "ScriptHost", "ScriptError", "ScriptStopped", "Transform", "TransformList", "VariationMap", "Affine6",
           "CameraHelper", "ColoringHelper", "GradientHelper", "XaosHelper", "FUNCTION_NAMES"]

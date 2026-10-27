"""The variation registry: the model of a *formula* and the catalogue both engines read.

A `Variation` is one formula (flam3 "variation", Apophysis "plugin") defined for *both*
engines: a numpy implementation (CPU engine, float64) and a GLSL snippet (GPU preview)
written from the same maths, so the two engines agree on what a flame looks like.
`tests/test_variations.py` evaluates both forms on the same points and checks they match.

The formulas themselves live in `fractalchemy/formulas/`:

* Python modules using the `@variation` decorator (the flam3 classics and anything
  that needs numpy tricks) — "legacy" style: `fn(point) -> (dx, dy[, dz])`, inline GLSL.
* `.c` files in the Apophysis plugin dialect, compiled by `formulas/lang` — "formula"
  style: the numpy function maps the whole point state, the GLSL is a function body.

`formulas.load_all()` fills `REGISTRY`; it runs on first import of this module's users.

GLSL conventions (inside a generated per-xform function):
    t        vec2   the point after the pre-affine (FTx, FTy);  tz: its depth
    w        float  the variation weight
    v        vec2   accumulator — add the weighted result to it;  vz: its depth
    col      float  the point colour (direct-colour variations write it)
    r2 r theta phi  precomputed: |t|², |t|, atan(t.x, t.y), atan(t.y, t.x)   (legacy snippets)
    c00..c21        the xform's affine coefficients
    P_<param>       the variation's parameters (full flame-file names, e.g. P_julian_power)
    rnd(s)          uniform random in [0, 1)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

EPS = 1e-10
PI = math.pi

NORMAL, PRE, POST = "normal", "pre", "post"          # Variation.kind
Z_NONE, Z_PASS, Z_FORMULA = "none", "pass", "formula"   # Variation.z
LEGACY, FORMULA = "legacy", "formula"                 # Variation.style


class Point:
    """A batch of points for the numpy implementations (lazy helpers mirror the GLSL names).

    Attributes:
        x, y, z: The input point (after the pre-affine) — `FTx`, `FTy`, `FTz`.
        px, py, pz: The accumulator — `FPx`, `FPy`, `FPz`.
        c: The point colour (`TC`).
        w: The variation weight.
        coefs: The xform's affine coefficients (a, b, c, d, e, f).
        params: Parameters and prepared values, keyed by full name.
        rng: Random generator for `rnd()`.
    """
    __slots__ = ("x", "y", "z", "px", "py", "pz", "c", "w", "coefs", "params", "rng", "_r2", "_r", "_theta", "_phi")

    def __init__(self, x: np.ndarray, y: np.ndarray, w: float, coefs, params: dict[str, float], rng: np.random.Generator,
                 z: np.ndarray | None = None, px=None, py=None, pz=None, c=None):
        self.x, self.y, self.w, self.coefs, self.params, self.rng = x, y, w, coefs, params, rng
        self.z = z if z is not None else np.zeros_like(x)
        self.px = px if px is not None else np.zeros_like(x)
        self.py = py if py is not None else np.zeros_like(x)
        self.pz = pz if pz is not None else np.zeros_like(x)
        self.c = c if c is not None else np.zeros_like(x)
        self._r2 = self._r = self._theta = self._phi = None

    @property
    def r2(self) -> np.ndarray:
        if self._r2 is None:
            self._r2 = self.x * self.x + self.y * self.y
        return self._r2

    @property
    def r(self) -> np.ndarray:
        if self._r is None:
            self._r = np.sqrt(self.r2)
        return self._r

    @property
    def theta(self) -> np.ndarray:
        if self._theta is None:
            self._theta = np.arctan2(self.x, self.y)
        return self._theta

    @property
    def phi(self) -> np.ndarray:
        if self._phi is None:
            self._phi = np.arctan2(self.y, self.x)
        return self._phi

    @property
    def n(self) -> int:
        return self.x.shape[0]

    def p(self, name: str) -> float:
        return self.params[name]

    def rnd(self) -> np.ndarray:
        return self.rng.random(self.x.shape[0])


NumpyFn = Callable[[Point], tuple]
State = tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]


@dataclass(frozen=True)
class ParamInfo:
    """What the editor needs to know about one parameter."""
    name: str
    type: str = "float"          # float | int
    default: float = 0.0
    min: float | None = None
    max: float | None = None
    cyclic: bool = False
    nonzero: bool = False


@dataclass(frozen=True)
class Variation:
    """One variation, defined for both engines.

    Attributes:
        name: Flame-file attribute name.
        numpy: Legacy style: `fn(point) -> (dx, dy)` or `(dx, dy, dz)` with the *weighted* contribution.
            Formula style: `fn(point) -> (tx, ty, tz, px, py, pz, c)`, the whole state after the formula.
        glsl: Legacy: snippet adding the weighted contribution to `v`. Formula: a function body (see module doc).
        params: Parameter name → default, keyed by the full flame-file name (`julian_power`).
        random: Uses random numbers (engines can't be compared point-for-point).
        uses_affine: Reads the xform's affine coefficients (waves, popcorn, rings, fan).
        note: Caveat shown to the user.
        kind: `normal` (adds to the accumulator), `pre` (rewrites the input point before the others),
            `post` (rewrites the accumulator after the others) — Apophysis's `pre_` / `post_` rule.
        z: `none` (leaves depth alone), `pass` (adds `w·tz`, as Apophysis built-ins do), `formula` (sets it itself).
        dc: Writes the point colour (direct colour).
        style: `legacy` or `formula` calling convention (see `numpy` / `glsl`).
        glsl_decls: Helper functions / lookup tables for the GLSL body, `@`-prefixed (formula style).
        prepare: `fn(params, weight, coefs, rng) -> dict` of per-transform constants added to the parameters.
        param_info: Parameter metadata for the editor.
        origin: Where the formula came from (file name, author, licence).
        tables: Constant lookup tables (name → flat list) the GLSL reads through the parameter texture.
    """
    name: str
    numpy: NumpyFn
    glsl: str
    params: dict[str, float] = field(default_factory=dict)
    random: bool = False
    uses_affine: bool = False
    note: str = ""
    kind: str = NORMAL
    z: str = Z_NONE
    dc: bool = False
    style: str = LEGACY
    glsl_decls: str = ""
    prepare: Callable | None = None
    param_info: dict[str, ParamInfo] = field(default_factory=dict)
    origin: str = ""
    tables: dict[str, list[float]] = field(default_factory=dict)

    def param_keys(self) -> list[str]:
        """Parameter names as they appear in flame files."""
        return list(self.params)

    def apply(self, p: Point) -> State:
        """Run the formula on a batch; returns the new `(x, y, z, px, py, pz, c)` state."""
        if self.style == FORMULA:
            x, y, z, px, py, pz, c = self.numpy(p)
            if self.z == Z_PASS:   # Apophysis built-in behaviour: the depth follows the weight
                if self.kind == PRE:
                    z = z * p.w
                elif self.kind == POST:
                    pz = pz * p.w
                else:
                    pz = pz + p.w * p.z
            return x, y, z, px, py, pz, c
        out = self.numpy(p)
        if len(out) == 3:
            dx, dy, dz = out
        else:
            dx, dy = out
            dz = self.w_times_z(p) if self.z == Z_PASS else 0.0
        if self.kind == PRE:
            return p.x + dx, p.y + dy, p.z + dz, p.px, p.py, p.pz, p.c
        return p.x, p.y, p.z, p.px + dx, p.py + dy, p.pz + dz, p.c

    @staticmethod
    def w_times_z(p: Point) -> np.ndarray:
        return p.w * p.z

    def summary(self) -> str:
        """One line for listings: name, kind, parameters."""
        extras = [self.kind] if self.kind != NORMAL else []
        if self.z != Z_NONE:
            extras.append("3D" if self.z == Z_FORMULA else "z-pass")
        if self.dc:
            extras.append("direct colour")
        return f"{self.name}" + (f" [{', '.join(extras)}]" if extras else "") + (f" ({', '.join(self.params)})" if self.params else "")


class _Registry(dict):
    """The catalogue; fills itself from `fractalchemy.formulas` on first read."""
    _loading = False

    def ensure_loaded(self) -> None:
        if self._loading or dict.__len__(self):
            return
        _Registry._loading = True
        try:
            from ..formulas import load_all   # imported here: formulas depends on this module
            load_all()
        finally:
            _Registry._loading = False

    def __getitem__(self, key):
        self.ensure_loaded()
        return dict.__getitem__(self, key)

    def __contains__(self, key):
        self.ensure_loaded()
        return dict.__contains__(self, key)

    def __iter__(self):
        self.ensure_loaded()
        return dict.__iter__(self)

    def __len__(self):
        self.ensure_loaded()
        return dict.__len__(self)

    def get(self, key, default=None):
        self.ensure_loaded()
        return dict.get(self, key, default)

    def keys(self):
        self.ensure_loaded()
        return dict.keys(self)

    def values(self):
        self.ensure_loaded()
        return dict.values(self)

    def items(self):
        self.ensure_loaded()
        return dict.items(self)


REGISTRY: dict[str, Variation] = _Registry()
ALIASES: dict[str, str] = {}   # e.g. "linear3D" -> "linear"


def register(var: Variation, aliases: tuple[str, ...] = (), replace: bool = True) -> Variation:
    """Add a variation to the registry (later registrations win, so user formulas can override)."""
    if not replace and dict.__contains__(REGISTRY, var.name):
        return dict.__getitem__(REGISTRY, var.name)
    dict.__setitem__(REGISTRY, var.name, var)
    for alias in aliases:
        ALIASES[alias] = var.name
    return var


def variation(name: str, glsl: str, params: dict[str, float] | None = None, *, random: bool = False,
              uses_affine: bool = False, note: str = "", aliases: tuple[str, ...] = (), kind: str = NORMAL,
              z: str = Z_NONE, dc: bool = False, param_info: dict[str, ParamInfo] | None = None, origin: str = ""):
    """Decorator registering a numpy implementation together with its GLSL twin (legacy style).

    `params` may use short names (`power`) — they are prefixed with the variation name — or full names.
    """
    def register_fn(fn: NumpyFn) -> NumpyFn:
        full = {(k if k.startswith(name + "_") else f"{name}_{k}"): float(v) for k, v in (params or {}).items()}
        info = dict(param_info or {})
        for key, default in full.items():
            info.setdefault(key, ParamInfo(key, "float", default))
        register(Variation(name, fn, glsl.strip(), full, random, uses_affine, note, kind, z, dc, LEGACY, "", None,
                           info, origin), aliases)
        return fn
    return register_fn


def resolve(name: str) -> Variation | None:
    """The Variation for a flame-file name, following aliases; None if unknown."""
    REGISTRY.ensure_loaded()
    return REGISTRY.get(ALIASES.get(name, name))


def canonical_name(name: str) -> str:
    """Alias-resolved name (unknown names pass through unchanged)."""
    REGISTRY.ensure_loaded()
    return ALIASES.get(name, name)


def pre_blur_glsl() -> str:
    """GLSL for the pre_blur jitter applied to `t` before the other variations (weight in `pb`)."""
    return "{ float a = rnd(s) * 2.0 * PI; float k = pb * (rnd(s) + rnd(s) + rnd(s) + rnd(s) - 2.0); t += k * vec2(cos(a), sin(a)); }"


def classify(names) -> tuple[list[str], list[str]]:
    """Split variation names into (supported, unsupported)."""
    supported, unsupported = [], []
    for name in names:
        (supported if resolve(name) is not None else unsupported).append(name)
    return supported, unsupported


def normalize(variations: dict[str, float], params: dict[str, float]) -> tuple[dict[str, float], dict[str, float], list[str]]:
    """Resolve aliases (`linear3D` → `linear`, parameters renamed to match) and drop zero weights.

    Returns:
        (variations, params, unsupported names) with canonical names.
    """
    out_vars: dict[str, float] = {}
    out_params = dict(params)
    unsupported = []
    for name, weight in variations.items():
        if weight == 0:
            continue
        canonical = canonical_name(name)
        if canonical not in REGISTRY:
            unsupported.append(name)
            for key in list(out_params):   # parameters of a variation we can't run are meaningless alone
                if key.startswith(name + "_"):
                    del out_params[key]
            continue
        out_vars[canonical] = out_vars.get(canonical, 0.0) + weight
        if canonical != name:
            for key in list(out_params):
                if key.startswith(name + "_"):
                    out_params[canonical + key[len(name):]] = out_params.pop(key)
    return out_vars, out_params, unsupported


def params_for(name: str, params: dict[str, float]) -> dict[str, float]:
    """The full parameter set of variation `name` (defaults filled in, full keys)."""
    var = REGISTRY[name]
    return {key: params.get(key, default) for key, default in var.params.items()}


_param_index: tuple[int, dict[str, str]] = (0, {})


def parameter_owner(key: str) -> str | None:
    """The variation a parameter name belongs to, if any registered variation declares it."""
    global _param_index
    if _param_index[0] != len(REGISTRY):
        index: dict[str, str] = {}
        for var in REGISTRY.values():
            for p in var.params:
                index.setdefault(p, var.name)
        _param_index = (len(REGISTRY), index)
    return _param_index[1].get(key)

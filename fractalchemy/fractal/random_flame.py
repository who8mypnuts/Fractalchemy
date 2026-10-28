"""Random flames, after Apophysis's `RandomFlame` (RndFlame.pas / ControlPoint.RandomCP).

For every flame: a transform count in `[min_transforms, max_transforms]`; one of Apophysis's three
affine recipes (7/10: identity translated, rotated, scaled and sometimes sheared; 2/10: the "Chaos: The
Software" formula; 1/10: fully random coefficients); per transform two of the enabled variations with
complementary weights (`RandomVariation`); weights from the transforms' areas or all equal; colours spread
over the palette; a random gradient. Flames that blow up or collapse are rejected and rolled again, and the
camera is framed from a short iteration of the system (Apophysis's `CalcBoundbox`).
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field

import numpy as np

from ..model import Gradient
from ..model.operations import reroll
from . import variations as V
from .scene import Camera, Flame, XForm

MAX_ATTEMPTS = 25
FRAME_POINTS = 3000
FRAME_STEPS = 60
FRAME_FUSE = 15
FRAME_MARGIN = 1.15          # the bounding box fills 1 / this of the image
MIN_EXTENT = 1e-4
MAX_EXTENT = 60.0


@dataclass
class RandomOptions:
    """What the random batch may use.

    Attributes:
        variations: Names the generator may pick from (empty = linear only).
        min_transforms, max_transforms: Transform count range (Apophysis: 2..5).
        width, height: Image size of the generated flames.
        name_prefix: Flame names are `prefix-<n>`.
    """
    variations: list[str] = field(default_factory=lambda: ["linear"])
    min_transforms: int = 2
    max_transforms: int = 5
    width: int = 1024
    height: int = 768
    name_prefix: str = ""


def random_batch(count: int, options: RandomOptions, seed: int | None = None, progress=None) -> list[Flame]:
    """`count` random flames (framed and renderable); `progress(done, total)` is called after each."""
    rng = random.Random(seed)
    prefix = options.name_prefix or time.strftime("Random-%Y%m%d-%H%M%S")
    flames = []
    for i in range(max(0, int(count))):
        flame = random_flame(rng, options)
        flame.name = f"{prefix}-{i + 1}"
        flames.append(flame)
        if progress is not None:
            progress(i + 1, count)
    return flames


def random_flame(rng: random.Random, options: RandomOptions) -> Flame:
    """One random flame; rolls again while the system blows up or collapses (Apophysis `BlowsUp`)."""
    names = [n for n in options.variations if n in V.REGISTRY] or ["linear"]
    lo, hi = max(1, int(options.min_transforms)), max(1, int(options.max_transforms))
    if hi < lo:
        lo, hi = hi, lo
    last: Flame | None = None
    for _attempt in range(MAX_ATTEMPTS):
        count = rng.randint(lo, hi)
        flame = Flame("random", [_random_xform(rng, i, count, names) for i in range(count)])
        flame.camera = Camera(width=int(options.width), height=int(options.height))
        _assign_weights(flame, rng)
        last = flame
        if frame_camera(flame):
            break
    flame = last
    flame.set_gradient(random_gradient(rng))
    return flame


# --- transforms ------------------------------------------------------------------------------------------
def _random_xform(rng: random.Random, i: int, count: int, names: list[str]) -> XForm:
    recipe = rng.randrange(10)
    if recipe <= 6:
        coefs = _recipe_identity(rng, i)
    elif recipe <= 8:
        coefs = _recipe_chaos(rng)
    else:
        coefs = (rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-2, 2), rng.uniform(-2, 2))
    xform = XForm(weight=1.0 / count, color=i / (count - 1) if count > 1 else 0.0, color_speed=0.5, coefs=coefs)
    xform.variations = random_variations(rng, names)
    xform.params = {}
    for name in xform.variations:
        xform.params.update(V.REGISTRY[name].params)   # defaults, as Apophysis keeps them
    return xform


def _recipe_identity(rng: random.Random, i: int) -> tuple:
    """Apophysis recipe 0..6: identity (mirrored 1 in 10), translated, rotated, scaled, sometimes sheared."""
    a, b, c, d = (1.0 if rng.randrange(10) < 9 else -1.0), 0.0, 0.0, 1.0
    e, f = rng.uniform(-1, 1), rng.uniform(-1, 1)
    angle = math.radians(rng.uniform(0, 360))
    ca, sa = math.cos(angle), math.sin(angle)
    a, b, c, d = a * ca - b * sa, a * sa + b * ca, c * ca - d * sa, c * sa + d * ca   # rotate
    s = rng.uniform(0.2, 1.0) if i > 0 else rng.uniform(0.6, 1.0)
    a, b, c, d = a * s, b * s, c * s, d * s
    if rng.randrange(2) == 0:   # Multiply(1, r - 0.5, r - 0.5, 1)
        p, q = rng.random() - 0.5, rng.random() - 0.5
        a, b, c, d = a + c * p, b + d * p, a * q + c, b * q + d
    return (a, b, c, d, e, f)


def _recipe_chaos(rng: random.Random) -> tuple:
    """Apophysis recipe 7..8, 'from the source to Chaos: The Software'."""
    r = rng.uniform(-1, 1)
    r = r + 0.2 if 0 <= r < 0.2 else r - 0.2 if -0.2 < r <= 0 else r
    s = rng.uniform(-1, 1)
    s = s + 0.2 if 0 <= s < 0.2 else s + 0.2 if -0.2 < s <= 0 else s
    theta = math.pi * rng.random()
    phi = (2 + rng.random()) * math.pi / 4
    a = r * math.cos(theta)
    c = s * (math.cos(theta) * math.cos(phi) - math.sin(theta))
    b = r * math.sin(theta)
    d = s * (math.sin(theta) * math.cos(phi) + math.cos(theta))
    return (a, b, c, d, rng.uniform(-1, 1), rng.uniform(-1, 1))


def random_variations(rng: random.Random, names: list[str]) -> dict[str, float]:
    """Apophysis `RandomVariation`: two enabled variations, weights w and 1 − w (or one with weight 1)."""
    a, b = rng.choice(names), rng.choice(names)
    if a == b:
        return {a: 1.0}
    w = rng.random()
    return {a: w, b: 1.0 - w}


def _assign_weights(flame: Flame, rng: random.Random) -> None:
    """Apophysis: half the time weights follow the transforms' areas (ComputeWeights), else they are equal."""
    n = len(flame.xforms)
    if rng.randrange(2) == 0 or n == 1:
        for x in flame.xforms:
            x.weight = 1.0 / n
        return
    areas = [abs(x.coefs[0] * x.coefs[3] - x.coefs[1] * x.coefs[2]) + 1e-3 for x in flame.xforms]
    total = sum(areas)
    for x, area in zip(flame.xforms, areas):
        x.weight = area / total


# --- gradient and framing --------------------------------------------------------------------------------
def random_gradient(rng: random.Random) -> Gradient:
    """A whole new random gradient (the Gradient Library's 'reroll')."""
    return Gradient("random", reroll(Gradient("seed", []), rng))


def sample_points(flame: Flame, points: int = FRAME_POINTS, steps: int = FRAME_STEPS, seed: int = 7) -> tuple[np.ndarray, np.ndarray]:
    """(x, y) of `points` orbits after `steps` plotted iterations (the camera projection included)."""
    from ..render.compiled import CompiledFlame
    from ..render.cpu_engine import PointPopulation
    from ..render.projection import project

    compiled = CompiledFlame.build(flame)
    worker = PointPopulation(compiled, points, seed, (1.0, 0.0, 0.0, 1.0, 0.0, 0.0), 1, 1, flame.camera)
    worker.fuse(FRAME_FUSE)
    xs, ys = [], []
    rng = np.random.default_rng(seed)
    for _ in range(steps):
        worker._step()
        x, y, z = worker.x, worker.y, worker.z
        if compiled.final is not None:
            from ..render.cpu_engine import apply_xform
            x, y, z, _c = apply_xform(compiled.final, x, y, z, worker.c, worker.rng)
        x, y = project(flame.camera, x, y, z, rng)
        xs.append(x.copy())
        ys.append(y.copy())
    return np.concatenate(xs), np.concatenate(ys)


def frame_camera(flame: Flame, margin: float = FRAME_MARGIN) -> bool:
    """Centre and scale the camera on the attractor; False if the system blows up or collapses."""
    try:
        x, y = sample_points(flame)
    except Exception:  # noqa: BLE001 - a formula that cannot run: treat as a bad roll
        return False
    finite = np.isfinite(x) & np.isfinite(y)
    if finite.mean() < 0.9:
        return False
    x, y = x[finite], y[finite]
    x0, x1 = np.percentile(x, [0.5, 99.5])
    y0, y1 = np.percentile(y, [0.5, 99.5])
    w, h = float(x1 - x0), float(y1 - y0)
    if not (MIN_EXTENT < w < MAX_EXTENT and MIN_EXTENT < h < MAX_EXTENT):
        return False
    cam = flame.camera
    cam.center = (float((x0 + x1) / 2), float((y0 + y1) / 2))
    cam.zoom = 0.0
    cam.scale = min(cam.width / (w * margin), cam.height / (h * margin))
    return True


__all__ = ["RandomOptions", "random_batch", "random_flame", "random_variations", "random_gradient", "frame_camera", "sample_points"]

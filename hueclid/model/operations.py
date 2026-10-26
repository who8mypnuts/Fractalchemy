"""Whole-gradient node operations: randomise, recolour, reroll, grow, thin and smooth.

Each takes a Gradient and returns a new list of stops. `rng` is injectable so
tests are deterministic.
"""

from __future__ import annotations

import math
import random
from typing import Sequence

from .adjust import shift_hsl
from .color import RGB, hsl_to_rgb
from .gradient import Gradient
from .simplify import simplify
from .stop import ColorStop

MIN_NODES = 2
MAX_NODES = 128
GROW_RANGE = (2, 6)          # "auto increase" adds this many nodes
THIN_FRACTION = (0.25, 0.5)  # "decrease" removes this share of nodes
SMOOTH_SAMPLES = 256
SMOOTH_RADIUS = 6            # blur radius in samples (~2% of the gradient)
SMOOTH_TOLERANCE = 10        # per-channel tolerance when thinning the blurred curve
REROLL_NODES = (3, 24)       # node count range for a freshly rerolled gradient

# Hue offsets (degrees) of classic colour harmonies; random colours are drawn from one of these.
HARMONIES = {
    "analogous": (0, 30, -30, 60),
    "complementary": (0, 180, 30, 210),
    "triadic": (0, 120, 240),
    "split": (0, 150, 210),
}


def randomize_positions(gradient: Gradient, rng: random.Random | None = None) -> list[ColorStop]:
    """Keep every colour but scatter the nodes to entirely new positions."""
    rng = rng or random.Random()
    return sorted((ColorStop(rng.random(), s.color) for s in gradient.stops), key=lambda s: s.position)


def randomize_colors(gradient: Gradient, rng: random.Random | None = None) -> list[ColorStop]:
    """Keep every node where it is but give each a new colour from a random harmony."""
    rng = rng or random.Random()
    palette = _random_palette(rng)
    return [ColorStop(s.position, _pick(palette, rng)) for s in gradient.stops]


def reroll(gradient: Gradient, rng: random.Random | None = None) -> list[ColorStop]:
    """A whole new gradient: random node count, positions and colours."""
    rng = rng or random.Random()
    palette = _random_palette(rng)
    count = rng.randint(*REROLL_NODES)
    return sorted((ColorStop(rng.random(), _pick(palette, rng)) for _ in range(count)), key=lambda s: s.position)


def add_nodes(gradient: Gradient, rng: random.Random | None = None) -> list[ColorStop]:
    """Insert a few nodes whose colours harmonise with what is already there."""
    rng = rng or random.Random()
    if not gradient.stops:
        return []
    room = MAX_NODES - len(gradient.stops)
    count = min(room, rng.randint(*GROW_RANGE))
    new = [ColorStop(pos, _harmonious_color(gradient.color_at(pos), rng)) for pos in (rng.random() for _ in range(count))]
    return sorted([s.copy() for s in gradient.stops] + new, key=lambda s: s.position)


def remove_nodes(gradient: Gradient, rng: random.Random | None = None) -> list[ColorStop]:
    """Randomly drop a share of the nodes, never going below MIN_NODES."""
    rng = rng or random.Random()
    stops = gradient.stops
    removable = max(0, len(stops) - MIN_NODES)
    count = min(removable, round(len(stops) * rng.uniform(*THIN_FRACTION)))
    doomed = set(rng.sample(range(len(stops)), count)) if count else set()
    return [s.copy() for i, s in enumerate(stops) if i not in doomed]


def smooth(gradient: Gradient) -> list[ColorStop]:
    """Blur the colour curve, then keep only the nodes needed to reproduce it."""
    if len(gradient.stops) < 2:
        return [s.copy() for s in gradient.stops]
    samples = gradient.sample(SMOOTH_SAMPLES)
    blurred = _blur(samples, SMOOTH_RADIUS)
    dense = Gradient.from_colors(gradient.name, blurred).stops
    return simplify(dense, SMOOTH_TOLERANCE)


# --- helpers ----------------------------------------------------------------
def _random_palette(rng: random.Random) -> list[RGB]:
    """A handful of colours sharing a harmony: random base hue, varied saturation/lightness."""
    base_hue = rng.uniform(0, 360)
    offsets = HARMONIES[rng.choice(sorted(HARMONIES))]
    palette = []
    for offset in offsets:
        for _ in range(2):
            hue = (base_hue + offset + rng.uniform(-8, 8)) % 360
            palette.append(hsl_to_rgb(hue / 360.0, rng.uniform(0.45, 1.0), rng.uniform(0.15, 0.85)))
    palette.append(hsl_to_rgb(base_hue / 360.0, rng.uniform(0.0, 0.3), rng.choice((0.05, 0.95))))  # near-black / near-white accent
    return palette


def _pick(palette: list[RGB], rng: random.Random) -> RGB:
    """A palette colour with a touch of jitter so repeated picks aren't identical."""
    return shift_hsl(rng.choice(palette), rng.uniform(-6, 6), rng.uniform(-8, 8), rng.uniform(-8, 8))


def _harmonious_color(color: RGB, rng: random.Random) -> RGB:
    hue = rng.choice((-1, 1)) * rng.uniform(12, 35)         # analogous hue, clearly visible
    return shift_hsl(color, hue, rng.uniform(-15, 15), rng.uniform(-12, 12))


def _blur(colors: Sequence[RGB], radius: int) -> list[RGB]:
    weights = [math.exp(-(i * i) / (2 * (radius / 2) ** 2)) for i in range(-radius, radius + 1)]
    total = sum(weights)
    out = []
    for i in range(len(colors)):
        acc = [0.0, 0.0, 0.0]
        for k, w in zip(range(i - radius, i + radius + 1), weights):
            c = colors[min(max(k, 0), len(colors) - 1)]  # clamp at the ends (not cyclic)
            for ch in range(3):
                acc[ch] += c[ch] * w
        out.append(tuple(int(round(v / total)) for v in acc))  # type: ignore[arg-type]
    return out

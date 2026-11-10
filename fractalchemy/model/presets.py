"""A few bright named gradients, shared by the Formula Editor's gradient menu and the scripting API
(`list_gradient_presets()`, `gradient.preset(name)`)."""

from __future__ import annotations

from .gradient import Gradient

GRADIENT_PRESETS: dict[str, tuple[tuple[int, int, int], ...]] = {
    "Yellow · cyan · magenta": ((255, 210, 48), (41, 217, 255), (255, 63, 181)),
    "Fire": ((255, 240, 120), (255, 120, 20), (140, 10, 60)),
    "Ocean": ((200, 255, 240), (30, 170, 220), (20, 40, 120)),
    "Forest": ((240, 255, 170), (80, 200, 90), (20, 80, 50)),
    "Candy": ((255, 150, 220), (150, 220, 255), (255, 250, 150)),
    "Greyscale": ((255, 255, 255), (128, 128, 128), (20, 20, 20)),
}


def preset_gradient(name: str) -> Gradient:
    """One of `GRADIENT_PRESETS` as a gradient (the first for an unknown name)."""
    colors = GRADIENT_PRESETS.get(name, next(iter(GRADIENT_PRESETS.values())))
    return Gradient.from_colors(name, list(colors))


__all__ = ["GRADIENT_PRESETS", "preset_gradient"]

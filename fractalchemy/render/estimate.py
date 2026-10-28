"""Before a render starts: how much work it is and roughly how long it will take.

The estimate uses the best rate available for the engine kind that will run: the last final
render's measured speed on that kind, else the preview engine's measured speed (same hardware,
comparable code path), else nothing — then only the sample count is stated. Qt-free so the
Render window's wording can be tested directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .final_settings import ENGINE_CPU, FinalRenderSettings
from .units import format_rate, format_seconds


RateHint = Callable[[], "tuple[str, float] | None"]   # returns (preview engine name, samples / s), or None


@dataclass
class RenderEstimate:
    """Tracks measured sample rates per engine kind and phrases the estimate.

    Attributes:
        measured: Engine kind ("gpu" / "cpu") → samples per second from a finished final render.
    """
    measured: dict[str, float] = field(default_factory=dict)

    def record(self, kind: str, rate: float) -> None:
        """Remember a finished render's speed for its engine kind."""
        if rate > 0:
            self.measured[kind] = rate

    def rate_for(self, kind: str, preview_hint: tuple[str, float] | None) -> tuple[str, float] | None:
        """(source description, samples/s) for `kind`, or None when nothing has been measured.

        Args:
            kind: "gpu" or "cpu".
            preview_hint: (preview engine name, samples/s) of the viewport's last render, if any.
        """
        if kind in self.measured:
            return f"the last {kind.upper()} render's measured speed", self.measured[kind]
        if preview_hint and preview_hint[1] > 0 and preview_hint[0].lower().startswith(kind):
            return "the preview's measured speed", preview_hint[1]
        return None

    def describe(self, settings: FinalRenderSettings, tiles: int, kind: str, preview_hint: tuple[str, float] | None) -> str:
        """The sentence under the plan: samples to run and, when a rate is known, the rough time."""
        total = settings.samples_per_tile * tiles
        rate = self.rate_for(kind, preview_hint)
        if rate is None:
            return f"{total / 1e9:.2f} G samples to run. Time unknown until an engine has measured its speed."
        return (f"{total / 1e9:.2f} G samples to run — roughly {format_seconds(total / rate[1])} at {rate[0]} "
                f"({format_rate(rate[1])}), plus filtering.")

    def short(self, settings: FinalRenderSettings, tiles: int, kind: str, preview_hint: tuple[str, float] | None) -> str:
        """'≈ 3 min 07 s' for the progress panel's Remaining field, or '' without a rate."""
        rate = self.rate_for(kind, preview_hint)
        return f"≈ {format_seconds(settings.samples_per_tile * tiles / rate[1])}" if rate else ""


def engine_kind(settings: FinalRenderSettings, gpu_available: bool) -> str:
    """Which kind of sampler these settings will get: "gpu" unless the CPU is chosen or there is no OpenGL."""
    return "gpu" if settings.engine != ENGINE_CPU and gpu_available else "cpu"


__all__ = ["RenderEstimate", "RateHint", "engine_kind"]

"""What a render job is asked to do, and what it reports back."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from .. import config


@dataclass(frozen=True)
class RenderSettings:
    """Size and effort of one render.

    Attributes:
        width, height: Output size in pixels.
        passes: Progressive passes; the image is delivered after each one.
        quality: Total samples per pixel over all passes (Apophysis's "quality").
        points: Size of the point population iterated in parallel.
        fuse: Warm-up iterations that are not plotted after (re)seeding.
        seed: Random seed, so a render is repeatable.
    """
    width: int = 800
    height: int = 600
    passes: int = config.PREVIEW_PASSES
    quality: float = config.PREVIEW_QUALITY
    points: int = config.PREVIEW_POINTS
    fuse: int = config.PREVIEW_FUSE
    seed: int = 1

    @property
    def samples_total(self) -> int:
        """Samples (plotted iterations) over the whole render."""
        return max(1, int(self.width * self.height * self.quality))

    @property
    def samples_per_pass(self) -> int:
        """Samples per progressive pass."""
        return max(1, self.samples_total // max(1, self.passes))

    def scaled(self, factor: float) -> "RenderSettings":
        """Same render at another resolution (e.g. 0.5 while dragging)."""
        return replace(self, width=max(1, int(self.width * factor)), height=max(1, int(self.height * factor)))

    def with_size(self, width: int, height: int) -> "RenderSettings":
        """Same render at another output size."""
        return replace(self, width=max(1, width), height=max(1, height))

    def with_effort(self, passes: int, quality: float) -> "RenderSettings":
        """Same render with another pass count / quality (clamped to sane minimums)."""
        return replace(self, passes=max(1, int(passes)), quality=max(0.01, float(quality)))


@dataclass
class RenderStats:
    """Progress facts for the status bar.

    Attributes:
        engine: Engine name ("GPU (OpenGL)" / "CPU (numpy, n threads)").
        passes_done, passes_total: Progressive pass counter.
        samples: Iterations plotted so far.
        hits: Points that landed inside the image so far (an estimate for GPU renders is 'samples').
        seconds: Wall time spent rendering so far.
        width, height: Size of the delivered image.
        notes: Engine remarks (e.g. unsupported variations that were ignored).
    """
    engine: str = ""
    passes_done: int = 0
    passes_total: int = 0
    samples: int = 0
    hits: int = 0
    seconds: float = 0.0
    width: int = 0
    height: int = 0
    notes: list[str] = field(default_factory=list)

    @property
    def samples_per_second(self) -> float:
        """Throughput so far (0 before any time was spent)."""
        return self.samples / self.seconds if self.seconds > 0 else 0.0

    @property
    def finished(self) -> bool:
        """True once every pass has been delivered."""
        return self.passes_total > 0 and self.passes_done >= self.passes_total

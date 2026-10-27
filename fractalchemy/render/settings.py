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
        oversample: Supersampling factor: the histogram has `oversample`² buckets per output pixel
            (Apophysis / flam3 `oversample`; 1 = plot straight into pixels).
        filter_radius: Radius of the Gaussian spatial filter that sums buckets into pixels, in output
            pixels (Apophysis / flam3 `filter`; with oversample 1 anything below ~0.3 is no filter).
        refine_to: After the `passes`, keep adding passes (each doubling the samples) until this quality
            is reached; 0 = stop at `quality`. Refining passes yield to any other pending render.
        density_scale: Multiplier on the samples (Apophysis renders quality · 4^zoom per pixel, so a
            zoomed-in view is not starved); the viewport sets it from the camera zoom.
    """
    width: int = 800
    height: int = 600
    passes: int = config.PREVIEW_PASSES
    quality: float = config.PREVIEW_QUALITY
    points: int = config.PREVIEW_POINTS
    fuse: int = config.PREVIEW_FUSE
    seed: int = 1
    oversample: int = config.PREVIEW_OVERSAMPLE
    filter_radius: float = config.PREVIEW_FILTER
    refine_to: float = 0.0
    density_scale: float = 1.0

    @property
    def samples_total(self) -> int:
        """Samples (plotted iterations) over the configured passes."""
        return max(1, int(self.width * self.height * self.quality * self.density_scale))

    @property
    def samples_per_pass(self) -> int:
        return max(1, self.samples_total // max(1, self.passes))

    @property
    def samples_target(self) -> int:
        """Samples at which refinement stops (0 = no refining: the job ends with the configured passes)."""
        if self.refine_to > self.quality:
            return max(1, int(self.width * self.height * self.refine_to * self.density_scale))
        return 0

    def next_pass_samples(self, passes_done: int, samples_done: int) -> int:
        """How many samples the next pass should add: a configured pass, or a doubling refinement pass."""
        if passes_done < self.passes:
            return self.samples_per_pass
        return max(1, min(max(self.samples_per_pass, samples_done), self.samples_target - samples_done))

    def scaled(self, factor: float) -> "RenderSettings":
        """Same render at another resolution (e.g. 0.5 while dragging)."""
        return replace(self, width=max(1, int(self.width * factor)), height=max(1, int(self.height * factor)))

    def with_size(self, width: int, height: int) -> "RenderSettings":
        return replace(self, width=max(1, width), height=max(1, height))

    def with_effort(self, passes: int, quality: float) -> "RenderSettings":
        return replace(self, passes=max(1, int(passes)), quality=max(0.01, float(quality)))

    def with_filter(self, oversample: int, filter_radius: float) -> "RenderSettings":
        return replace(self, oversample=max(1, min(config.MAX_OVERSAMPLE, int(oversample))),
                       filter_radius=max(0.0, min(config.MAX_FILTER_RADIUS, float(filter_radius))))

    def with_refine(self, refine_to: float) -> "RenderSettings":
        return replace(self, refine_to=max(0.0, min(config.MAX_REFINE_QUALITY, float(refine_to))))

    def within_bucket_limit(self, max_buckets: int = config.MAX_BUCKETS) -> "RenderSettings":
        """Lower the oversample until the histogram fits `max_buckets` (memory safety for large viewports)."""
        settings = self
        while settings.oversample > 1 and settings.bucket_size[0] * settings.bucket_size[1] > max_buckets:
            settings = replace(settings, oversample=settings.oversample - 1)
        return settings

    def for_zoom(self, zoom: float) -> "RenderSettings":
        """Apophysis's rule: a view zoomed in by `zoom` (log2) gets 4^zoom times the samples (never fewer, capped)."""
        return replace(self, density_scale=max(1.0, min(config.ZOOM_DENSITY_MAX, 4.0 ** float(zoom))))

    @property
    def filter_width(self) -> int:
        """Side of the spatial filter kernel in buckets (1 = no filtering)."""
        from .filtering import filter_width
        return filter_width(self.oversample, self.filter_radius)

    @property
    def gutter(self) -> int:
        """Extra buckets on every side of the image so the kernel can reach past its edge."""
        return (self.filter_width - self.oversample) // 2

    @property
    def bucket_size(self) -> tuple[int, int]:
        """(width, height) of the supersampled histogram including the gutter."""
        g = 2 * self.gutter
        return (self.width * self.oversample + g, self.height * self.oversample + g)


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
        samples_target: Samples after which the job is done (0 = after `passes_total` passes).
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
    samples_target: int = 0

    @property
    def samples_per_second(self) -> float:
        return self.samples / self.seconds if self.seconds > 0 else 0.0

    @property
    def quality(self) -> float:
        """Samples per pixel so far."""
        return self.samples / (self.width * self.height) if self.width and self.height else 0.0

    @property
    def passes_finished(self) -> bool:
        """The configured passes are done (the picture may still be refining)."""
        return self.passes_total > 0 and self.passes_done >= self.passes_total

    @property
    def refining(self) -> bool:
        """Past the configured passes, adding samples towards `samples_target`."""
        return self.passes_finished and self.samples < self.samples_target

    @property
    def finished(self) -> bool:
        return self.passes_finished and self.samples >= self.samples_target

"""What a final render is asked to do: size, quality, filtering, denoising, engine, output.

`FinalRenderSettings` is a plain, serialisable description (the Render window persists it in
QSettings via `to_dict` / `from_dict`). Everything derived from it — how many buckets, how the
image is split into tiles to respect the memory limit, how much work that is — lives here too,
so the UI can show the plan before the render starts and the engine follows the same plan.

Tiles: the histogram of a large image does not fit in memory (16 bytes per bucket on the GPU,
32 on the CPU, times oversample²). Like Apophysis's "slices", the image is then rendered as
several tiles, each running the full chaos game and keeping only the points that land inside it —
so a 3-tile render costs three times the iterations. A `gutter` of extra buckets around every
tile lets the spatial filter and density estimation see real neighbours across tile seams.
"""

from __future__ import annotations

import math
import os
from dataclasses import asdict, dataclass, field, replace
from typing import Any

from .denoise import denoiser_kind
from .filters import DensityEstimation, filter_kind, make_taps

ENGINE_AUTO, ENGINE_GPU, ENGINE_CPU = "auto", "gpu", "cpu"
ENGINES = ((ENGINE_AUTO, "Automatic (GPU when available)"), (ENGINE_GPU, "GPU — OpenGL, single precision"),
           (ENGINE_CPU, "CPU — all cores, double precision"))
DENSITY_PRESETS = (100, 250, 500, 1000, 2000, 4000, 8000, 16000)
MAX_OVERSAMPLE = 8
MAX_DIMENSION = 1 << 20           # 1,048,576 px per side; memory and disk are the real limits
CPU_BYTES_PER_BUCKET = 32 + 16    # float64 RGBA histogram + float32 log-scaled copy for filtering
GPU_BYTES_PER_BUCKET = 32 + 16 + 16   # master + readback copy + filter copy (the texture lives on the GPU)
GPU_TEXTURE_BYTES_PER_BUCKET = 16
DEFAULT_GPU_MEMORY_MB = 1024      # RGBA32F tile texture budget when none is set: fine on any discrete GPU
DEFAULT_MEMORY_FRACTION = 0.5     # of physical RAM, when no limit is set


@dataclass(frozen=True)
class FinalRenderSettings:
    """A complete description of one final render (see the module docstring).

    Attributes:
        width, height: Output size in pixels.
        quality: Samples per output pixel (Apophysis "density").
        oversample: Buckets per pixel along each axis (Apophysis "oversample").
        filter_kind: Reconstruction filter key (`filters.FILTERS`).
        filter_radius: Filter radius in output pixels.
        denoiser: Denoiser key (`denoise.DENOISERS`; "density" = flam3 density estimation).
        denoise_strength: 0..100 for image-space denoisers.
        de_max_radius, de_min_radius, de_curve: flam3 density-estimation parameters.
        engine: "auto" / "gpu" / "cpu".
        cpu_threads: Worker threads for the CPU engine (0 = every core).
        memory_limit_mb: Histogram memory budget deciding the tile split (0 = half of physical RAM).
        gpu_memory_mb: Largest tile texture on the GPU (0 = 1 GB); raise it on big cards to render in fewer tiles.
        transparent: Render the background as transparency (alpha-capable formats only).
        depth: Bits per channel in the file: 8 or 16 (PNG / TIFF).
        output_path: Destination file ("" = not chosen yet).
        output_format: Output format key (`output.FORMATS`).
        lossy_quality: 1..100 for JPEG / WebP / AVIF / HEIF / JPEG XL.
        lossless: Prefer lossless encoding where the format offers it (WebP / JPEG XL / AVIF).
        save_parameters: Write a `.flame` with the parameters next to the image.
        embed_parameters: Store the parameters in the image's metadata.
        save_incomplete: Keep what was rendered when the render is stopped early.
        save_details: Write a fractal + render report beside the image.
        details_format: Report format key: "md", "txt" or "html" (`report.REPORT_FORMATS`).
        fuse: Warm-up iterations per point before plotting.
        seed: Random seed.
    """
    width: int = 1920
    height: int = 1080
    quality: float = 2000.0
    oversample: int = 2
    filter_kind: str = "gaussian"
    filter_radius: float = 0.5
    denoiser: str = "none"
    denoise_strength: float = 50.0
    de_max_radius: float = 9.0
    de_min_radius: float = 0.0
    de_curve: float = 0.4
    engine: str = ENGINE_AUTO
    cpu_threads: int = 0
    memory_limit_mb: int = 0
    gpu_memory_mb: int = 0
    transparent: bool = False
    depth: int = 8
    output_path: str = ""
    output_format: str = "png"
    lossy_quality: int = 95
    lossless: bool = False
    save_parameters: bool = False
    embed_parameters: bool = True
    save_incomplete: bool = True
    save_details: bool = False
    details_format: str = "md"
    fuse: int = 30
    seed: int = 1

    # --- derived --------------------------------------------------------------------------
    @property
    def samples_per_tile(self) -> int:
        """Iterations every tile runs: quality × output pixels (each tile sees the whole chaos game)."""
        return max(1, int(self.width * self.height * self.quality))

    @property
    def bucket_size(self) -> tuple[int, int]:
        """(width, height) of the full histogram in buckets."""
        return self.width * self.oversample, self.height * self.oversample

    @property
    def density_estimation(self) -> DensityEstimation | None:
        """The DE parameters when the density denoiser is chosen, else None."""
        if self.denoiser != "density":
            return None
        return DensityEstimation(max(0.0, self.de_max_radius), max(0.0, self.de_min_radius), max(0.01, self.de_curve))

    def gutter(self) -> int:
        """Extra buckets around a tile so filtering sees real neighbours across seams."""
        reach = make_taps(filter_kind(self.filter_kind), self.filter_radius, self.oversample).reach
        de = self.density_estimation
        if de is not None:
            reach = max(reach, de.reach(self.oversample))
        return reach

    def with_size(self, width: int, height: int) -> "FinalRenderSettings":
        """Same settings at another size."""
        return replace(self, width=max(1, int(width)), height=max(1, int(height)))

    def to_dict(self) -> dict[str, Any]:
        """Plain data for persistence."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FinalRenderSettings":
        """Inverse of `to_dict`; unknown keys are ignored, bad values fall back to the defaults."""
        defaults = cls()
        values = {}
        for name, default in asdict(defaults).items():
            if name not in data:
                continue
            try:
                values[name] = type(default)(data[name]) if not isinstance(default, bool) else bool(data[name])
            except (TypeError, ValueError):
                pass
        return cls(**values)

    def problems(self) -> list[str]:
        """Reasons this render cannot start (empty when it can)."""
        issues = []
        if not (1 <= self.width <= MAX_DIMENSION and 1 <= self.height <= MAX_DIMENSION):
            issues.append(f"Size must be between 1 and {MAX_DIMENSION:,} pixels per side")
        if self.quality <= 0:
            issues.append("Density must be positive")
        if not (1 <= self.oversample <= MAX_OVERSAMPLE):
            issues.append(f"Oversample must be 1 to {MAX_OVERSAMPLE}")
        if self.depth not in (8, 16):
            issues.append("Depth must be 8 or 16 bits")
        if not denoiser_kind(self.denoiser).available:
            issues.append(f"The {denoiser_kind(self.denoiser).label} denoiser is not installed")
        if not self.output_path.strip():
            issues.append("Choose an output file")
        return issues


# --- memory and tiles -------------------------------------------------------------------------
def physical_memory_bytes() -> int:
    """Installed RAM, or 8 GB if the platform does not say."""
    try:
        pages, page_size = os.sysconf("SC_PHYS_PAGES"), os.sysconf("SC_PAGE_SIZE")
        if pages > 0 and page_size > 0:
            return int(pages) * int(page_size)
    except (AttributeError, ValueError, OSError):
        pass
    try:
        import ctypes

        class _Status(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong), ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong), ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        status = _Status()
        status.dwLength = ctypes.sizeof(_Status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):   # type: ignore[attr-defined]
            return int(status.ullTotalPhys)
    except Exception:  # noqa: BLE001 - not Windows, or the call failed
        pass
    return 8 << 30


def memory_budget_bytes(settings: FinalRenderSettings) -> int:
    """The histogram memory a render may use: the explicit limit, else half of physical RAM (no fixed ceiling)."""
    if settings.memory_limit_mb > 0:
        return int(settings.memory_limit_mb) << 20
    return int(physical_memory_bytes() * DEFAULT_MEMORY_FRACTION)


def gpu_budget_bytes(settings: FinalRenderSettings) -> int:
    """Texture memory one GPU tile may use."""
    return int(settings.gpu_memory_mb or DEFAULT_GPU_MEMORY_MB) << 20


@dataclass(frozen=True)
class Tile:
    """One tile of the bucket grid.

    Attributes:
        x0, y0, x1, y1: Interior bucket rectangle (multiples of the oversample; x1 / y1 exclusive).
        gutter: Extra buckets rendered on every side.
    """
    x0: int
    y0: int
    x1: int
    y1: int
    gutter: int

    @property
    def width(self) -> int:
        """Interior width in buckets."""
        return self.x1 - self.x0

    @property
    def height(self) -> int:
        """Interior height in buckets."""
        return self.y1 - self.y0

    @property
    def padded_size(self) -> tuple[int, int]:
        """(width, height) in buckets including the gutter — the histogram actually accumulated."""
        return self.width + 2 * self.gutter, self.height + 2 * self.gutter

    @property
    def buckets(self) -> int:
        """Number of buckets accumulated (gutter included)."""
        w, h = self.padded_size
        return w * h

    def pixel_rect(self, oversample: int) -> tuple[int, int, int, int]:
        """(x, y, width, height) of the output pixels this tile produces."""
        return self.x0 // oversample, self.y0 // oversample, self.width // oversample, self.height // oversample


@dataclass(frozen=True)
class TilePlan:
    """How the histogram is split, and what it costs.

    Attributes:
        tiles: Row-major list of tiles.
        bytes_per_bucket: Host memory per accumulated bucket for the engine in use.
        max_dimension: Longest tile side allowed (texture size on the GPU).
    """
    tiles: tuple[Tile, ...] = field(default_factory=tuple)
    bytes_per_bucket: int = CPU_BYTES_PER_BUCKET
    max_dimension: int = 1 << 30

    @property
    def count(self) -> int:
        """Number of tiles."""
        return len(self.tiles)

    @property
    def peak_bytes(self) -> int:
        """Host memory of the largest tile's histogram and filter copies."""
        return max((t.buckets for t in self.tiles), default=0) * self.bytes_per_bucket


def plan_tiles(settings: FinalRenderSettings, gpu: bool = False, max_texture: int = 1 << 30,
               budget_bytes: int | None = None) -> TilePlan:
    """Split the bucket grid into the fewest tiles that fit the memory budget (and texture limits).

    Tiles are full-width strips when the width fits; wider images get columns too. Interior
    edges fall on pixel boundaries (multiples of the oversample), so tiles map to whole pixels.
    """
    os_ = settings.oversample
    gutter = settings.gutter()
    bucket_w, bucket_h = settings.bucket_size
    bytes_per_bucket = GPU_BYTES_PER_BUCKET if gpu else CPU_BYTES_PER_BUCKET
    budget = memory_budget_bytes(settings) if budget_bytes is None else budget_bytes
    max_buckets = max(os_ * os_, budget // bytes_per_bucket)
    if gpu:
        max_buckets = min(max_buckets, max(os_ * os_, gpu_budget_bytes(settings) // GPU_TEXTURE_BYTES_PER_BUCKET))
    max_side = max(os_, (max_texture if gpu else 1 << 30) - 2 * gutter)
    columns = _split(bucket_w, os_, max_side)
    padded_w = max(w for _, w in columns) + 2 * gutter
    rows_limit = max(os_, min(max_side, (max_buckets // padded_w - 2 * gutter) // os_ * os_))
    rows = _split(bucket_h, os_, rows_limit)
    tiles = tuple(Tile(x, y, x + w, y + h, gutter) for y, h in rows for x, w in columns)
    return TilePlan(tiles, bytes_per_bucket, max_side)


def _split(length: int, os_: int, max_len: int) -> list[tuple[int, int]]:
    """Cut `length` buckets into ≤ `max_len` pieces whose edges are multiples of `os_`: [(start, size)]."""
    pixels = length // os_
    max_pixels = max(1, max_len // os_)
    pieces = max(1, math.ceil(pixels / max_pixels))
    per = math.ceil(pixels / pieces)
    out = []
    start = 0
    while start < pixels:
        size = min(per, pixels - start)
        out.append((start * os_, size * os_))
        start += size
    return out


def describe_plan(settings: FinalRenderSettings, plan: TilePlan) -> str:
    """A sentence for the Render window about memory and tiling."""
    peak = _mb_text(plan.peak_bytes)
    output = _mb_text(settings.width * settings.height * 8)
    if plan.count == 1:
        return f"One tile: {peak} for the histogram + {output} for the image."
    limit = "GPU memory or the memory limit" if plan.bytes_per_bucket == GPU_BYTES_PER_BUCKET else "memory limit"
    return (f"{plan.count} tiles (≤ {peak} each, + {output} for the image): every tile runs the full "
            f"chaos game, so this render costs {plan.count}× the iterations of a single tile. Raise the {limit} "
            f"to use fewer tiles.")


def _mb_text(n: int) -> str:
    return f"{n / (1 << 30):,.1f} GB" if n >= (1 << 30) else f"{n / (1 << 20):,.0f} MB"


__all__ = ["FinalRenderSettings", "ENGINES", "ENGINE_AUTO", "ENGINE_GPU", "ENGINE_CPU", "DENSITY_PRESETS", "MAX_OVERSAMPLE",
           "MAX_DIMENSION", "Tile", "TilePlan", "plan_tiles", "describe_plan", "memory_budget_bytes", "gpu_budget_bytes",
           "physical_memory_bytes"]

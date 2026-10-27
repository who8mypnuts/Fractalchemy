"""Worker processes for the final renderer's CPU sampler.

numpy releases the GIL inside its kernels, but a chaos-game step is many short kernels and
temporaries, and threads end up serialised on the interpreter and the allocator (measured:
1.5× on four cores). Processes scale. Each worker owns a point population and writes its hits
straight into a *shared-memory* histogram, so nothing large ever crosses a queue; bands of rows
are protected by locks so no hit is lost to a race (see `samplers.CpuSampler`).

Only this module and the Qt-free parts of the package are imported in a worker; the start
method is always "spawn" so forking a Qt process with live threads is never attempted.
"""

from __future__ import annotations

import multiprocessing as mp
import time
from multiprocessing import shared_memory

import numpy as np

from ..fractal.scene import Flame
from .compiled import CompiledFlame
from .cpu_engine import _Worker

BAND_LOCKS = 64                 # fixed pool: locks must be inherited at process start, tiles come later
PARTITION_ABOVE = 1 << 21       # buckets; smaller histograms are cache-resident, so plain adds under one lock win
POINTS_PER_WORKER = 1 << 16     # population per process; keeps the step's temporaries cache-resident
FLUSH_SAMPLES = 1 << 21         # hits gathered before they are added to the shared histogram
PAUSE_POLL_SECONDS = 0.1

FLAG_CANCEL, FLAG_PAUSE = 0, 1


class TilePopulation(_Worker):
    """A preview-engine worker re-targeted at a tile: same iteration, hits are returned instead of binned."""

    def __init__(self, compiled: CompiledFlame, points: int, seed: int):
        super().__init__(compiled, points, seed, (1.0, 0.0, 0.0, 1.0, 0.0, 0.0), 1, 1)

    def retarget(self, affine, width: int, height: int) -> None:
        """Point the projection at a new tile."""
        self.pixel_transform = tuple(affine)
        self.width, self.height = int(width), int(height)

    def hits(self, iterations: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Run `iterations` steps; returns (bucket index, plot weight, palette index) of the points that hit the tile."""
        idx_parts, weight_parts, color_parts = [], [], []
        for _ in range(iterations):
            xi = self._step()
            idx, op, ci = self._project(xi)
            idx_parts.append(idx)
            weight_parts.append(op)
            color_parts.append(ci)
        return np.concatenate(idx_parts), np.concatenate(weight_parts), np.concatenate(color_parts)


class SharedHistogram:
    """A (4, rows, cols) float64 histogram in shared memory, plus the band → lock mapping."""

    def __init__(self, width: int, height: int, name: str | None = None, create: bool = False):
        self.width, self.height = width, height
        size = 4 * width * height * 8
        if create:
            self.shm = shared_memory.SharedMemory(create=True, size=size)
        else:
            try:   # attach without registering with this process's resource tracker (the owner unlinks)
                self.shm = shared_memory.SharedMemory(name=name, track=False)
            except TypeError:   # Python < 3.13 without the `track` argument
                self.shm = shared_memory.SharedMemory(name=name)
        self.planes = np.ndarray((4, height * width), dtype=np.float64, buffer=self.shm.buf)
        if create:
            self.planes.fill(0.0)
        self.band_rows = max(1, -(-height // BAND_LOCKS))

    @property
    def name(self) -> str:
        """Shared-memory block name for attaching from another process."""
        return self.shm.name

    def array(self) -> np.ndarray:
        """The histogram as (4, rows, cols)."""
        return self.planes.reshape(4, self.height, self.width)

    def add(self, idx: np.ndarray, op: np.ndarray, ci: np.ndarray, palette: np.ndarray, locks) -> None:
        """Add a batch of hits: partition by band (radix sort on a 16-bit key), add each band under its lock.

        Small histograms skip the partitioning: it only pays once random access misses the caches.
        """
        if idx.shape[0] == 0:
            return
        if self.width * self.height <= PARTITION_ABOVE:
            colours = palette[ci] * op[:, None]
            with locks[0]:
                for ch in range(3):
                    np.add.at(self.planes[ch], idx, colours[:, ch])
                np.add.at(self.planes[3], idx, op)
            return
        band = (idx // (self.band_rows * self.width)).astype(np.uint16)
        bounds = np.concatenate(([0], np.cumsum(np.bincount(band, minlength=BAND_LOCKS))))
        order = np.argsort(band, kind="stable")
        idx, op, ci = idx[order], op[order], ci[order]
        for b in range(BAND_LOCKS):
            lo, hi = int(bounds[b]), int(bounds[b + 1])
            if hi <= lo:
                continue
            sel = slice(lo, hi)
            weights = op[sel]
            colours = palette[ci[sel]] * weights[:, None]
            with locks[b]:
                for ch in range(3):
                    np.add.at(self.planes[ch], idx[sel], colours[:, ch])
                np.add.at(self.planes[3], idx[sel], weights)

    def close(self, unlink: bool = False) -> None:
        """Detach (and, for the owner, delete) the block."""
        self.planes = None
        self.shm.close()
        if unlink:
            try:
                self.shm.unlink()
            except FileNotFoundError:
                pass


def worker_main(flame_data: dict, seed: int, fuse: int, commands: mp.Queue, results: mp.Queue, flags, locks) -> None:
    """Entry point of a worker process: serve "tile" / "run" / "stop" commands until told to stop."""
    compiled = CompiledFlame.build(Flame.from_dict(flame_data))
    population = TilePopulation(compiled, POINTS_PER_WORKER, seed)
    population.fuse(fuse)
    histogram: SharedHistogram | None = None
    try:
        while True:
            command, *args = commands.get()
            if command == "stop":
                break
            if command == "tile":
                if histogram is not None:
                    histogram.close()
                name, width, height, affine = args
                histogram = SharedHistogram(width, height, name=name)
                population.retarget(affine, width, height)
                results.put(("ready", seed))
            elif command == "run":
                done = _run(population, histogram, int(args[0]), flags, locks, results, compiled.palette)
                results.put(("done", seed, done))
    except (KeyboardInterrupt, EOFError, BrokenPipeError):
        pass
    finally:
        if histogram is not None:
            histogram.close()


def _run(population: TilePopulation, histogram: SharedHistogram, samples: int, flags, locks, results, palette) -> int:
    n = population.x.shape[0]
    iterations = max(1, -(-samples // n))
    per_flush = max(1, FLUSH_SAMPLES // n)
    done = 0
    while done < iterations:
        while flags[FLAG_PAUSE] and not flags[FLAG_CANCEL]:
            time.sleep(PAUSE_POLL_SECONDS)
        if flags[FLAG_CANCEL]:
            break
        chunk = min(per_flush, iterations - done)
        idx, op, ci = population.hits(chunk)
        histogram.add(idx, op, ci, palette, locks)
        done += chunk
        results.put(("progress", chunk * n))
    return done * n


__all__ = ["TilePopulation", "SharedHistogram", "worker_main", "BAND_LOCKS", "FLAG_CANCEL", "FLAG_PAUSE"]

"""The solid renderer on the CPU engine: the chaos game splatted into a G-buffer and shadow maps, then shaded.

`SolidCpuJob` has the same shape as `CpuRenderJob` (`run_pass()` until `stats.finished`, `image()`, `close()`)
so the `RenderService` runs it like any render; `CpuEngine.start()` makes one when the settings carry a
scene. Every worker thread iterates its own `PointPopulation` (the same iteration as the 2D engine) into its
own G-buffer; after a pass the buffers are merged by depth and the merged buffer is shaded.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

import numpy as np

from ..fractal.scene import Flame
from ..render.compiled import CompiledFlame
from ..render.cpu_engine import ITERATIONS_PER_CHUNK, PointPopulation, apply_xform
from ..render.settings import RenderSettings, RenderStats
from ..scene3d.model import Scene3D
from .gbuffer import GBuffer, ShadowMap
from .shading import MAX_LIGHTS, shade
from .view import View

SHADOW_MAP_SIZE = 1024
RANGE_SAMPLES = 4          # iterations of the population used to size the depth range and the shadow maps


class SolidCpuJob:
    """One progressive solid render on the CPU; call `run_pass()` repeatedly until `stats.finished`."""

    def __init__(self, flame: Flame, settings: RenderSettings, scene: Scene3D, threads: int):
        self.flame = flame
        self.settings = settings
        self.scene = scene
        self.compiled = CompiledFlame.build(flame)
        self.threads = max(1, min(threads, settings.points // 256 or 1))
        self.view = View(flame.camera, settings.width, settings.height, settings.oversample)
        self.stats = RenderStats(engine=f"CPU solid (numpy, {self.threads} threads)", passes_total=settings.passes,
                                 width=settings.width, height=settings.height, notes=list(self.compiled.notes),
                                 samples_target=settings.samples_target)
        per_thread = max(64, settings.points // self.threads)
        self._workers = [SolidPopulation(self.compiled, per_thread, settings.seed * 7919 + i, self.view, flame)
                         for i in range(self.threads)]
        self._pool = ThreadPoolExecutor(max_workers=self.threads, thread_name_prefix="render-solid")
        self.gbuffer = GBuffer(*self.view.size)
        self.depth_range: tuple[float, float] = (-1.0, 1.0)
        self.bounds = np.array([[-1.0, -1.0, -1.0], [1.0, 1.0, 1.0]])
        self.shadow_maps: dict[int, ShadowMap] = {}
        self._elapsed = 0.0
        self._fused = False

    # --- setup --------------------------------------------------------------------------------------------------
    def _prepare(self) -> None:
        """Warm the populations up and size the depth range / shadow maps from where the points are."""
        list(self._pool.map(lambda w: w.fuse(self.settings.fuse), self._workers))
        samples = [w.sample_view(RANGE_SAMPLES) for w in self._workers]
        vx = np.concatenate([s[0] for s in samples])
        vy = np.concatenate([s[1] for s in samples])
        vz = np.concatenate([s[2] for s in samples])
        self.depth_range = self.view.depth_range(vz)
        self.bounds = self.view.bounds(vx, vy, vz)
        for index, light in enumerate(self.scene.lights[:MAX_LIGHTS]):
            if light.shadows and self.scene.solid.display != "points":
                self.shadow_maps[index] = ShadowMap(light.altitude, light.azimuth, self.bounds, SHADOW_MAP_SIZE)
        for w in self._workers:
            w.set_targets(self.shadow_maps)
        self._fused = True

    # --- rendering ----------------------------------------------------------------------------------------------
    def run_pass(self, cancelled: Callable[[], bool] = lambda: False) -> np.ndarray | None:
        """Iterate one pass on all threads, merge the buffers, shade. Returns None if cancelled."""
        started = time.perf_counter()
        if not self._fused:
            self._prepare()
        wanted = self.settings.next_pass_samples(self.stats.passes_done, self.stats.samples)
        per_worker = max(1, -(-wanted // self.threads))
        results = list(self._pool.map(lambda w: w.run(per_worker, cancelled), self._workers))
        if cancelled():
            return None
        for samples, hits, gbuffer, maps in results:
            self.stats.samples += samples
            self.stats.hits += hits
            self.gbuffer.merge(gbuffer)
            for index, shadow in maps.items():
                self.shadow_maps[index].merge(shadow)
        self.stats.passes_done += 1
        image = self.image()
        self._elapsed += time.perf_counter() - started
        self.stats.seconds = self._elapsed
        return image

    def image(self) -> np.ndarray:
        """The merged G-buffer shaded to RGBA8."""
        return shade(self.view, self.gbuffer, self.scene, self.flame, self.shadow_maps, self.depth_range)

    def close(self) -> None:
        """Stop the worker threads."""
        self._pool.shutdown(wait=False)


class SolidPopulation(PointPopulation):
    """A point population whose plot is a depth-tested splat into its own G-buffer (and the lights' shadow maps)."""

    def __init__(self, compiled: CompiledFlame, points: int, seed: int, view: View, flame: Flame):
        super().__init__(compiled, points, seed, view.pixel_transform, *view.size, flame.camera)
        self.view = view
        self.gbuffer = GBuffer(*view.size)
        self.shadow_maps: dict[int, ShadowMap] = {}
        self._xform_count = len(compiled.xforms)

    def set_targets(self, shadow_maps: dict[int, ShadowMap]) -> None:
        """Give the population its own copy of each shadow map to splat into (merged by the job)."""
        self.shadow_maps = {i: m.empty_copy() for i, m in shadow_maps.items()}

    def _view_points(self) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """View-space positions, palette indices and materials of the current points (after the final transform)."""
        x, y, z, c = self.x, self.y, self.z, self.c
        if self.compiled.final is not None:
            x, y, z, c = apply_xform(self.compiled.final, x, y, z, c, self.rng)
        vx, vy, vz = self.view.to_view(x, y, z)
        color = np.clip(c * 255.0 + 0.5, 0, 255).astype(np.int16)
        return vx, vy, vz, color, self.prev.astype(np.int16)

    def sample_view(self, iterations: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """View-space positions of the population over a few iterations (to size the depth range)."""
        xs, ys, zs = [], [], []
        for _ in range(iterations):
            self._step()
            vx, vy, vz, _c, _m = self._view_points()
            xs.append(vx)
            ys.append(vy)
            zs.append(vz)
        return np.concatenate(xs), np.concatenate(ys), np.concatenate(zs)

    def run(self, samples: int, cancelled: Callable[[], bool]) -> tuple[int, int, GBuffer, dict[int, ShadowMap]]:
        """Splat about `samples` iterations; returns (samples done, hits, the G-buffer, the shadow maps)."""
        n = self.x.shape[0]
        done = hits = 0
        iterations = max(1, -(-samples // n))
        while done < iterations * n and not cancelled():
            chunk = min(ITERATIONS_PER_CHUNK, iterations - done // n)
            for _ in range(chunk):
                self._step()
                vx, vy, vz, color, material = self._view_points()
                visible = self.opacities[self.prev] > 0
                px, py = self.view.project(vx, vy, vz, self.rng)
                hits += self.gbuffer.splat(px[visible], py[visible], vx[visible], vy[visible], vz[visible], color[visible], material[visible])
                for shadow in self.shadow_maps.values():
                    shadow.splat(vx[visible], vy[visible], vz[visible])
            done += chunk * n
        return done, hits, self.gbuffer, self.shadow_maps



__all__ = ["SolidCpuJob", "SolidPopulation", "SHADOW_MAP_SIZE"]

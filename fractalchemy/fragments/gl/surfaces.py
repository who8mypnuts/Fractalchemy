"""The accumulation buffers — FragM's `backBuffer` / `previewBuffer` pair, kept alive across render jobs.

A `Surface` is two framebuffers of the fragment's `#buffer` type (RGBA8, or a float format — FragM creates RGBA32F
for `NONE`) each with a depth texture (the raytracers write `gl_FragDepth`; it is read for the 3D point under the
mouse and for EXR depth output), and the `subframe` counter. Every subframe reads the *back* texture and draws
into the *front* one, then they swap. The `SurfaceCache` keeps one surface per render key so that a new job can
continue an accumulation (`DontClearOnChange` fragments keep their state through parameter edits, a Post-group
change only re-runs the display pass) unless it asks for a clear or the size / format changed.
"""

from __future__ import annotations

import numpy as np

BUFFER_FORMATS = {"": "f4", "NONE": "f4", "RGBA8": "f1", "RGBA16": "f2", "RGBA16F": "f2", "RGBA32F": "f4"}
DEFAULT_FORMAT = "RGBA32F"
GL_NEAREST, GL_LINEAR = 0x2600, 0x2601
FILTERS = {"GL_NEAREST": GL_NEAREST, "GL_LINEAR": GL_LINEAR}   # the mipmap filters are not meaningful for a render target


def buffer_dtype(buffer: str) -> tuple[str, str]:
    """`(moderngl dtype, normalised format name)` for a `#buffer` directive's text (unknown → RGBA8, as FragM warns and does)."""
    name = buffer.strip().upper()
    if name in BUFFER_FORMATS:
        return BUFFER_FORMATS[name], (DEFAULT_FORMAT if name in ("", "NONE") else name)
    return "f1", "RGBA8"


class Surface:
    """Two colour + depth framebuffers of one size and format, plus the subframe counter (see the module docstring)."""

    def __init__(self, ctx, width: int, height: int, buffer: str):
        self.ctx = ctx
        self.width, self.height = max(1, int(width)), max(1, int(height))
        self.dtype, self.format = buffer_dtype(buffer)
        self.textures = [ctx.texture((self.width, self.height), 4, dtype=self.dtype) for _ in range(2)]
        self.depths = [ctx.depth_texture((self.width, self.height)) for _ in range(2)]
        for texture in self.textures:
            texture.filter = (ctx.LINEAR, ctx.LINEAR)
            texture.repeat_x = texture.repeat_y = False
        self.fbos = [ctx.framebuffer([t], d) for t, d in zip(self.textures, self.depths)]
        self.front = 0             # index of the buffer last drawn into (FragM's previewBuffer)
        self.subframe = 0
        self.clear()

    def apply_params(self, params: dict[str, str]) -> None:
        """`#TexParameter backbuffer …`: filtering and wrapping of the accumulation textures (a Game of Life needs GL_NEAREST)."""
        mag = FILTERS.get(params.get("GL_TEXTURE_MAG_FILTER", ""), GL_LINEAR)
        min_ = FILTERS.get(params.get("GL_TEXTURE_MIN_FILTER", "").replace("_MIPMAP_LINEAR", "").replace("_MIPMAP_NEAREST", ""), GL_LINEAR)
        repeat_x = params.get("GL_TEXTURE_WRAP_S", "") == "GL_REPEAT"
        repeat_y = params.get("GL_TEXTURE_WRAP_T", "") == "GL_REPEAT"
        for texture in self.textures:
            texture.filter = (min_, mag)
            texture.repeat_x, texture.repeat_y = repeat_x, repeat_y

    def matches(self, width: int, height: int, buffer: str) -> bool:
        return (self.width, self.height, self.dtype) == (max(1, int(width)), max(1, int(height)), buffer_dtype(buffer)[0])

    def clear(self) -> None:
        """Transparent black, depth 1.0, subframe 0 (FragM's `initPreviewBuffer` + `doClearBackBuffer`)."""
        for fbo in self.fbos:
            fbo.clear(0.0, 0.0, 0.0, 0.0, depth=1.0)
        self.subframe = 0

    def swap(self) -> None:
        """The front buffer becomes the back buffer; the next draw targets the other one."""
        self.front = 1 - self.front

    @property
    def back_texture(self):
        """What the next subframe reads (`backbuffer`)."""
        return self.textures[1 - self.front]

    @property
    def front_texture(self):
        """What was drawn last (`frontbuffer` for the display pass)."""
        return self.textures[self.front]

    @property
    def front_fbo(self):
        return self.fbos[self.front]

    def depth_at(self, x: int, y: int) -> float:
        """The depth value at pixel `(x, y)` (GL rows: y = 0 at the bottom) of the front buffer."""
        x, y = min(max(int(x), 0), self.width - 1), min(max(int(y), 0), self.height - 1)
        data = self.front_fbo.read(viewport=(x, y, 1, 1), components=1, attachment=-1, dtype="f4")
        return float(np.frombuffer(data, dtype=np.float32)[0])

    def read_float(self) -> np.ndarray:
        """The front buffer as `(H, W, 4)` float32, row 0 at the top."""
        data = self.front_fbo.read(components=4, dtype="f4")
        return np.frombuffer(data, dtype=np.float32).reshape(self.height, self.width, 4)[::-1].copy()

    def read_depth(self) -> np.ndarray:
        """The front depth buffer as `(H, W)` float32, row 0 at the top."""
        data = self.front_fbo.read(components=1, attachment=-1, dtype="f4")
        return np.frombuffer(data, dtype=np.float32).reshape(self.height, self.width)[::-1].copy()

    def release(self) -> None:
        for obj in self.fbos + self.textures + self.depths:
            obj.release()


class SurfaceCache:
    """Surfaces by render key, so a job can pick up where the last one for that key stopped."""

    def __init__(self, ctx, limit: int = 8):
        self.ctx = ctx
        self.limit = limit
        self._surfaces: dict[object, Surface] = {}

    def get(self, key: object, width: int, height: int, buffer: str, clear: bool) -> Surface:
        """The surface for `key` at this size / format — reused (and cleared when asked) or newly made."""
        surface = self._surfaces.get(key)
        if surface is not None and not surface.matches(width, height, buffer):
            surface.release()
            surface = None
        if surface is None:
            self._evict()
            surface = self._surfaces[key] = Surface(self.ctx, width, height, buffer)
        elif clear:
            surface.clear()
        self._surfaces[key] = self._surfaces.pop(key)       # most recently used last
        return surface

    def peek(self, key: object) -> Surface | None:
        return self._surfaces.get(key)

    def drop(self, key: object) -> None:
        surface = self._surfaces.pop(key, None)
        if surface is not None:
            surface.release()

    def _evict(self) -> None:
        while len(self._surfaces) >= self.limit:
            self._surfaces.pop(next(iter(self._surfaces))).release()

    def release(self) -> None:
        for surface in self._surfaces.values():
            surface.release()
        self._surfaces.clear()


__all__ = ["Surface", "SurfaceCache", "buffer_dtype", "BUFFER_FORMATS"]

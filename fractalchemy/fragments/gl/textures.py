"""GL textures for the sampler uniforms — FragM's `initFragmentTextures` with its cache.

Unit 0 is the back / front buffer; user samplers take units 1…  The cache keys textures by file, modification
time, channels and sampler kind, so a texture survives rebuilds and parameter edits and is re-read when the file
changes; textures no longer referenced are released after a bind (FragM's `clearTextureCache`). `#TexParameter`
filters / wrapping / anisotropy apply on upload, mipmaps are generated when a mipmap filter asks for them.
"""

from __future__ import annotations

from ..textures import TextureError, TextureImage, TextureSpec, anisotropy, filter_pair, load_texture, wrap_pair
from .program import Program


class TextureCache:
    """Uploads and binds a request's textures (see the module docstring).

    Attributes:
        problems: Messages about textures that could not be loaded since the last `take_problems()`.
    """

    def __init__(self, ctx):
        self.ctx = ctx
        self._textures: dict[tuple, object] = {}
        self._failed: set[tuple] = set()
        self.problems: list[str] = []

    def bind(self, program: Program, request) -> None:
        """Bind every sampler uniform of `program` that the request names a file for; unit 0 stays the buffers."""
        specs: dict[str, TextureSpec] = getattr(request, "textures", {}) or {}
        unit = 1
        used: set[tuple] = set()
        for name, info in program.uniforms.items():
            if not info.sampler or name in ("backbuffer", "frontbuffer"):
                continue
            spec = specs.get(name)
            key = spec.cache_key() if spec is not None else None
            if key is None:
                continue
            texture = self._textures.get(key)
            if texture is None and key not in self._failed:
                texture = self._upload(spec)
                if texture is None:
                    self._failed.add(key)
            if texture is None:
                continue
            used.add(key)
            texture.use(unit)
            program.set(name, unit)
            unit += 1
        self._evict(used, specs)

    def _upload(self, spec: TextureSpec):
        try:
            image = load_texture(spec)
        except TextureError as exc:
            self.problems.append(str(exc))
            return None
        texture = self._make(spec, image)
        self._textures[spec.cache_key()] = texture
        return texture

    def _make(self, spec: TextureSpec, image: TextureImage):
        min_filter, mag_filter, mipmaps = filter_pair(spec.params)
        repeat_x, repeat_y = wrap_pair(spec.params)
        if spec.cube and image.faces:
            side = image.faces[0].shape[0]
            texture = self.ctx.texture_cube((side, side), 4, b"".join(face.tobytes() for face in image.faces), dtype=image.dtype)
        else:
            height, width = image.data.shape[:2]
            texture = self.ctx.texture((width, height), 4, image.data.tobytes(), dtype=image.dtype)
            texture.repeat_x, texture.repeat_y = repeat_x, repeat_y
        if mipmaps and not spec.integer:
            texture.build_mipmaps()
        elif min_filter not in (0x2600, 0x2601):
            min_filter = 0x2601
        texture.filter = (min_filter, mag_filter)
        if not spec.integer and hasattr(texture, "anisotropy"):
            try:
                texture.anisotropy = anisotropy(spec.params)
            except Exception:  # noqa: BLE001 - the extension may be missing
                pass
        return texture

    def _evict(self, used: set[tuple], specs: dict[str, TextureSpec]) -> None:
        """Release textures no request names any more (a changed file or a removed uniform)."""
        wanted = {s.cache_key() for s in specs.values()} | used
        for key in [k for k in self._textures if k not in wanted]:
            self._textures.pop(key).release()
        self._failed = {k for k in self._failed if k in wanted}

    def take_problems(self) -> list[str]:
        problems, self.problems = self.problems, []
        return problems

    def clear(self) -> None:
        """FragM's *Clear texture cache*."""
        for texture in self._textures.values():
            texture.release()
        self._textures.clear()
        self._failed.clear()

    def release(self) -> None:
        self.clear()


__all__ = ["TextureCache"]

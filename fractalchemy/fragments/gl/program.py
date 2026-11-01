"""A linked fragment program with its uniform table — what the engine caches per source text."""

from __future__ import annotations

from dataclasses import dataclass

GL_BOOL_TYPES = {0x8B56, 0x8B57, 0x8B58, 0x8B59}
GL_SAMPLER_TYPES = {0x8B5E: "sampler2D", 0x8B60: "samplerCube", 0x8DCA: "isampler2D", 0x8DD2: "usampler2D", 0x8B62: "sampler2DShadow",
                    0x8B5F: "sampler3D", 0x8DCC: "isamplerCube", 0x8DD4: "usamplerCube"}
SPECIAL_UNIFORMS = ("pixelSize", "globalPixelSize", "subframe", "time", "backbuffer", "frontbuffer", "projectionMatrix")


@dataclass(frozen=True)
class UniformInfo:
    """One active uniform.

    Attributes:
        name: As declared.
        fmt: moderngl's format (`1f`, `3f`, `1i`, `2d`, `16f`, …).
        dimension: Components per element.
        array_length: Elements (1 unless an array).
        is_bool: Declared `bool` / `bvecN` (uploaded as ints).
        sampler: The sampler type name, or `""` for a value uniform.
    """
    name: str
    fmt: str
    dimension: int
    array_length: int
    is_bool: bool
    sampler: str

    @property
    def scalar_kind(self) -> str:
        """`f`, `d`, `i` or `I` — the element type."""
        return self.fmt[-1]


class Program:
    """A moderngl program plus the fullscreen-triangle VAO and the active-uniform table.

    Args:
        ctx: The context.
        program: The linked moderngl program.
        triangle: The engine's vertex buffer of the fullscreen triangle.
    """

    def __init__(self, ctx, program, triangle, compile_ms: float = 0.0):
        self.ctx = ctx
        self.program = program
        self.compile_ms = compile_ms          # how long the build took (FragM reports the last build's time for a cached program too)
        self.vao = ctx.vertex_array(program, [(triangle, "4f", "vertex_position")]) if "vertex_position" in program else \
            ctx.vertex_array(program, [])
        self.uniforms: dict[str, UniformInfo] = {}
        for name in program:
            member = program[name]
            if hasattr(member, "fmt"):
                gl_type = getattr(member, "gl_type", 0)
                self.uniforms[name] = UniformInfo(name, member.fmt, member.dimension, member.array_length,
                                                  gl_type in GL_BOOL_TYPES, GL_SAMPLER_TYPES.get(gl_type, ""))

    def __contains__(self, name: str) -> bool:
        return name in self.uniforms

    def set(self, name: str, value) -> bool:
        """Set a uniform when the program has it; False when the compiler optimised it away."""
        if name not in self.uniforms:
            return False
        self.program[name].value = value
        return True

    def user_uniform_names(self) -> list[str]:
        """Active uniforms that are the fragment's own (the engine's special uniforms excluded)."""
        return [n for n in self.uniforms if n not in SPECIAL_UNIFORMS]

    def render(self) -> None:
        """Draw the fullscreen triangle."""
        self.vao.render(mode=self.ctx.TRIANGLES, vertices=3)

    def release(self) -> None:
        self.vao.release()
        self.program.release()


__all__ = ["Program", "UniformInfo", "SPECIAL_UNIFORMS"]

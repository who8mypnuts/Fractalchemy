"""The solid renderer on the GPU: the numpy pipeline of `fractalchemy/solid/` as OpenGL passes.

Per pass: the population iterates (the same transform-feedback shader as the flame render), is drawn as
depth-tested points into the **G-buffer** (RGBA32F: view position, packed palette colour + material) and, for
each shadow-casting light, into a **shadow map** (R32F, `MIN` blending — the nearest distance along the light).
Then a **normals** pass (neighbour cross products, as `shading.normals_from_positions`), the **shade** pass
(normal smoothing, ambient occlusion, lights, shadows, fog, exposure, sRGB — `shading.shade`) at the
supersampled size, and a **downsample** pass to the output. `tests/test_solid.py` feeds both engines the same
points and checks the images agree.
"""

from __future__ import annotations

import time
from typing import Callable

import numpy as np

from ..fractal.scene import Flame
from ..scene3d.model import Scene3D
from ..solid.gbuffer import ShadowMap
from ..solid.shading import DISCONTINUITY, MAX_LIGHTS, ao_kernel
from ..solid.view import View, light_direction
from .codegen import generate_solid
from .compiled import CompiledFlame
from .projection import glsl_uniforms
from .settings import RenderSettings, RenderStats
from .tonemap import FULLSCREEN_VERTEX_GLSL

SHADOW_MAP_SIZE = 1024
RANGE_SAMPLES = 4
MAX_AO_SAMPLES = 64

SOLID_FRAGMENT = """
#version 330
in vec4 v_data;
out vec4 f_data;
void main() { f_data = v_data; }
"""

NORMALS_GLSL = """
#version 330
uniform sampler2D u_gbuffer;
uniform sampler2D u_count;       // samples per pixel (the density threshold)
uniform float u_min_hits;
uniform float u_limit;           // a neighbour further away in depth than this belongs to another surface
out vec4 f_normal;
vec4 fetch(ivec2 p) {
    ivec2 size = textureSize(u_gbuffer, 0);
    p = clamp(p, ivec2(0), size - 1);
    vec4 g = texelFetch(u_gbuffer, p, 0);
    if (texelFetch(u_count, p, 0).r < u_min_hits) g.w = -1.0;
    return g;
}
void main() {
    ivec2 p = ivec2(gl_FragCoord.xy);
    vec4 centre = fetch(p);
    if (centre.w < 0.0) { f_normal = vec4(0.0); return; }
    float depth = -centre.z;
    vec3 n = vec3(0.0);
    const ivec2 offsets[8] = ivec2[8](ivec2(1, 0), ivec2(0, 1), ivec2(-1, 0), ivec2(0, -1), ivec2(1, -1), ivec2(1, 1), ivec2(-1, 1), ivec2(-1, -1));
    // pairs (dy, dx): (0,1)-(1,0), (1,0)-(0,-1), (0,-1)-(-1,0), (-1,0)-(0,1), (-1,1)-(1,1), (1,1)-(1,-1), (1,-1)-(-1,-1), (-1,-1)-(-1,1)
    const ivec2 pa[8] = ivec2[8](ivec2(1, 0), ivec2(0, 1), ivec2(-1, 0), ivec2(0, -1), ivec2(1, -1), ivec2(1, 1), ivec2(-1, 1), ivec2(-1, -1));
    const ivec2 pb[8] = ivec2[8](ivec2(0, 1), ivec2(-1, 0), ivec2(0, -1), ivec2(1, 0), ivec2(1, 1), ivec2(-1, 1), ivec2(-1, -1), ivec2(1, -1));
    for (int i = 0; i < 8; i++) {
        vec4 a = fetch(p + pa[i]);          // (dx, dy) as pixel offsets
        vec4 b = fetch(p + pb[i]);
        bool oka = a.w >= 0.0 && abs(-a.z - depth) < u_limit;
        bool okb = b.w >= 0.0 && abs(-b.z - depth) < u_limit;
        if (oka && okb) n += cross(a.xyz - centre.xyz, b.xyz - centre.xyz);
    }
    f_normal = vec4(n, 1.0);
}
"""

SHADE_GLSL = """
#version 330
#define PI 3.14159265358979323846
uniform sampler2D u_gbuffer;
uniform sampler2D u_count;
uniform float u_min_hits;
uniform sampler2D u_normals;
uniform sampler2D u_palette;
uniform sampler2D u_materials;    // 3 texels per material: (diffuse, ambient, specular, shininess), (spec rgb, wrap), (colour rgb, fixed)
uniform sampler2D u_shadow[8];
uniform int u_material_count;
uniform int u_smooth_radius;
uniform vec3 u_eye;
uniform vec3 u_cam_x;             // view-plane → G-buffer pixel mapping (for the AO projection)
uniform vec3 u_cam_y;
uniform float u_perspective;
uniform int u_display_points;
uniform int u_ao;
uniform float u_ao_radius;
uniform int u_ao_samples;
uniform float u_ao_falloff;
uniform float u_ao_intensity;
uniform vec3 u_ao_kernel[64];
uniform int u_light_count;
uniform vec3 u_light_dir[8];
uniform vec3 u_light_color[8];    // colour × intensity
uniform float u_light_shadow[8];  // shadow intensity (0: no shadow map)
uniform int u_light_taps[8];
uniform mat3 u_light_basis[8];
uniform vec2 u_light_origin[8];
uniform vec2 u_light_scale[8];
uniform float u_light_bias[8];
uniform float u_light_size;
uniform vec3 u_env_color;
uniform float u_env_ambient;
uniform float u_exposure;
uniform int u_env_visible;
uniform int u_fog;
uniform vec2 u_fog_range;         // (start depth, end depth)
uniform vec3 u_fog_color;
out vec4 f_color;

vec4 fetch(sampler2D t, ivec2 p) { ivec2 size = textureSize(t, 0); return texelFetch(t, clamp(p, ivec2(0), size - 1), 0); }
vec4 surface(ivec2 p) {
    vec4 g = texelFetch(u_gbuffer, p, 0);
    if (texelFetch(u_count, p, 0).r < u_min_hits) g.w = -1.0;     // too few samples: dust, not surface
    return g;
}

vec3 smoothed_normal(ivec2 p) {
    vec3 total = vec3(0.0);
    float count = 0.0;
    for (int dy = -u_smooth_radius; dy <= u_smooth_radius; dy++)
        for (int dx = -u_smooth_radius; dx <= u_smooth_radius; dx++) {
            vec4 n = fetch(u_normals, p + ivec2(dx, dy));
            total += n.xyz * n.w;
            count += n.w;
        }
    vec3 n = count > 0.0 ? total / count : fetch(u_normals, p).xyz;
    float len = length(n);
    n = len > 1e-20 ? n / len : vec3(0.0);
    return n.z < 0.0 ? -n : n;
}

vec2 project(vec3 q) {
    vec2 f = q.xy / (1.0 - u_perspective * q.z);
    return vec2(dot(u_cam_x, vec3(f, 1.0)), dot(u_cam_y, vec3(f, 1.0)));
}

float occlusion(vec3 pos, vec3 n) {
    vec3 helper = abs(n.y) < 0.9 ? vec3(0.0, 1.0, 0.0) : vec3(1.0, 0.0, 0.0);
    vec3 t = cross(helper, n);
    float tl = length(t);
    t = tl > 1e-12 ? t / tl : vec3(0.0);
    vec3 b = cross(n, t);
    ivec2 size = textureSize(u_gbuffer, 0);
    float occluded = 0.0;
    for (int i = 0; i < u_ao_samples; i++) {
        vec3 k = u_ao_kernel[i];
        vec3 sample_pos = pos + u_ao_radius * (k.x * t + k.y * b + k.z * n);
        vec2 px = project(sample_pos);
        ivec2 pi = clamp(ivec2(floor(px + 0.5)), ivec2(0), size - 1);
        vec4 g = surface(pi);
        if (g.w < 0.0) continue;
        float diff = (-sample_pos.z) - (-g.z);
        if (diff > 0.02 * u_ao_radius && diff < u_ao_radius)
            occluded += 1.0 - pow(clamp(diff / u_ao_radius, 0.0, 1.0), max(u_ao_falloff, 1e-3));
    }
    return 1.0 - u_ao_intensity * occluded / float(max(u_ao_samples, 1));
}

float shadow_depth(int i, ivec2 c) {
    // GLSL 3.30 indexes sampler arrays with constants only
    switch (i) {
        case 0: return texelFetch(u_shadow[0], c, 0).r;
        case 1: return texelFetch(u_shadow[1], c, 0).r;
        case 2: return texelFetch(u_shadow[2], c, 0).r;
        case 3: return texelFetch(u_shadow[3], c, 0).r;
        case 4: return texelFetch(u_shadow[4], c, 0).r;
        case 5: return texelFetch(u_shadow[5], c, 0).r;
        case 6: return texelFetch(u_shadow[6], c, 0).r;
        default: return texelFetch(u_shadow[7], c, 0).r;
    }
}

float shadow(int i, vec3 pos) {
    vec3 l = u_light_basis[i] * pos;
    vec2 cell = (l.xy - u_light_origin[i]) * u_light_scale[i];
    int taps = u_light_taps[i];
    float total = 0.0;
    for (int du = -taps; du <= taps; du++)
        for (int dv = -taps; dv <= taps; dv++) {
            ivec2 c = clamp(ivec2(floor(cell)) + ivec2(du, dv), ivec2(0), ivec2(int(u_light_size) - 1));
            float nearest = shadow_depth(i, c);
            total += (nearest + u_light_bias[i] < l.z) ? 1.0 : 0.0;
        }
    float n = float(2 * taps + 1);
    return total / (n * n);
}

void main() {
    ivec2 p = ivec2(gl_FragCoord.xy);
    vec4 g = surface(p);
    if (g.w < 0.0) {
        f_color = u_env_visible == 1 ? vec4(clamp(u_env_color * u_exposure, 0.0, 1.0), 1.0) : vec4(0.0);
        return;
    }
    int code = int(g.w + 0.5);
    int colour = code & 255;
    int material = min(code >> 8, u_material_count - 1);
    vec4 m0 = texelFetch(u_materials, ivec2(material * 3, 0), 0);
    vec4 m1 = texelFetch(u_materials, ivec2(material * 3 + 1, 0), 0);
    vec4 m2 = texelFetch(u_materials, ivec2(material * 3 + 2, 0), 0);
    vec3 base = mix(texelFetch(u_palette, ivec2(colour, 0), 0).rgb, m2.rgb, m2.w);
    vec3 rgb;
    if (u_display_points == 1) {
        rgb = base;
    } else {
        vec3 n = smoothed_normal(p);
        vec3 pos = g.xyz;
        float ao = u_ao == 1 ? occlusion(pos, n) : 1.0;
        vec3 v = normalize(u_eye - pos);
        rgb = base * (m0.y * u_env_ambient * u_env_color) * ao;
        for (int i = 0; i < u_light_count; i++) {
            vec3 L = u_light_dir[i];
            float ndl = dot(n, L);
            float lambert = clamp((ndl + m1.w) / (1.0 + m1.w), 0.0, 1.0);
            vec3 h = normalize(v + L);
            float spec = ndl > 0.0 ? pow(clamp(dot(n, h), 0.0, 1.0), max(m0.w, 1.0)) : 0.0;
            float lit = u_light_shadow[i] > 0.0 ? 1.0 - u_light_shadow[i] * shadow(i, pos) : 1.0;
            rgb += base * (m0.x * lambert) * u_light_color[i] * (lit * ao);
            rgb += m1.rgb * (m0.z * spec) * u_light_color[i] * lit;
        }
        if (u_fog == 1) {
            float t = clamp((-pos.z - u_fog_range.x) / max(u_fog_range.y - u_fog_range.x, 1e-6), 0.0, 1.0);
            rgb = mix(rgb, u_fog_color, t);
        }
    }
    f_color = vec4(clamp(rgb * u_exposure, 0.0, 1.0), 1.0);
}
"""

DOWNSAMPLE_GLSL = """
#version 330
uniform sampler2D u_image;
uniform int u_factor;
out vec4 f_color;
vec3 encode(vec3 c) {
    vec3 lo = c * 12.92;
    vec3 hi = 1.055 * pow(max(c, vec3(1e-9)), vec3(1.0 / 2.4)) - 0.055;
    return mix(hi, lo, step(c, vec3(0.0031308)));
}
void main() {
    ivec2 p = ivec2(gl_FragCoord.xy) * u_factor;
    vec4 total = vec4(0.0);
    for (int dy = 0; dy < u_factor; dy++)
        for (int dx = 0; dx < u_factor; dx++)
            total += texelFetch(u_image, p + ivec2(dx, dy), 0);
    vec4 c = total / float(u_factor * u_factor);
    f_color = vec4(encode(c.rgb), c.a);
}
"""


def _set_array(program, name: str, values, dtype: str = "f4", width: int = 1) -> None:
    """Write a uniform array (`width` components per element), trimmed to the length the compiler kept."""
    uniform = program.get(name, None)
    if uniform is None:
        return
    data = np.asarray(values, dtype=dtype).reshape(-1, width)[:uniform.array_length]
    uniform.write(np.ascontiguousarray(data).tobytes())


class SolidGpuJob:
    """One progressive solid render on the GPU; call `run_pass()` until `stats.finished`."""

    def __init__(self, engine, flame: Flame, settings: RenderSettings, scene: Scene3D):
        from .gpu_engine import GpuPopulation
        self.engine = engine
        self.ctx = engine.ctx
        self.gl = engine.gl
        self.flame = flame
        self.settings = settings
        self.scene = scene
        self.compiled = CompiledFlame.build(flame)
        self.view = View(flame.camera, settings.width, settings.height, settings.oversample)
        self.generated = generate_solid(self.compiled)
        self.population = GpuPopulation(engine, self.compiled, settings.points, settings.seed, flame.camera, self.generated, SOLID_FRAGMENT)
        self.stats = RenderStats(engine=f"GPU solid ({engine.renderer})", passes_total=settings.passes,
                                 width=settings.width, height=settings.height, notes=list(self.compiled.notes),
                                 samples_target=settings.samples_target)
        self.depth_range = (-1.0, 1.0)
        self.bounds = np.array([[-1.0, -1.0, -1.0], [1.0, 1.0, 1.0]])
        self.shadow_maps: dict[int, ShadowMap] = {}
        self.shadow_textures: dict[int, tuple] = {}
        self._programs()
        self._create_targets()
        self._elapsed = 0.0
        self._fused = False
        self._closed = False

    # --- setup --------------------------------------------------------------------------------------------------
    def _programs(self) -> None:
        engine = self.engine
        if not hasattr(engine, "_solid_programs"):
            engine._solid_programs = {
                "normals": self.ctx.program(vertex_shader=FULLSCREEN_VERTEX_GLSL, fragment_shader=NORMALS_GLSL),
                "shade": self.ctx.program(vertex_shader=FULLSCREEN_VERTEX_GLSL, fragment_shader=SHADE_GLSL),
                "down": self.ctx.program(vertex_shader=FULLSCREEN_VERTEX_GLSL, fragment_shader=DOWNSAMPLE_GLSL),
            }
            engine._solid_vaos = {name: self.ctx.vertex_array(prog, []) for name, prog in engine._solid_programs.items()}
        self.programs = engine._solid_programs
        self.vaos = engine._solid_vaos

    def _create_targets(self) -> None:
        w, h = self.view.size
        gl = self.gl
        self.gbuffer_tex = self.ctx.texture((w, h), 4, dtype="f4")
        self.gbuffer_tex.filter = (gl.NEAREST, gl.NEAREST)
        self.gbuffer_depth = self.ctx.depth_renderbuffer((w, h))
        self.gbuffer_fbo = self.ctx.framebuffer([self.gbuffer_tex], self.gbuffer_depth)
        self.gbuffer_fbo.clear(0.0, 0.0, 0.0, -1.0, depth=1.0)
        self.count_tex = self.ctx.texture((w, h), 1, dtype="f4")
        self.count_tex.filter = (gl.NEAREST, gl.NEAREST)
        self.count_fbo = self.ctx.framebuffer([self.count_tex])
        self.count_fbo.clear(0.0, 0.0, 0.0, 0.0)
        self.normals_tex = self.ctx.texture((w, h), 4, dtype="f4")
        self.normals_tex.filter = (gl.NEAREST, gl.NEAREST)
        self.normals_fbo = self.ctx.framebuffer([self.normals_tex])
        self.shaded_tex = self.ctx.texture((w, h), 4, dtype="f4")
        self.shaded_tex.filter = (gl.NEAREST, gl.NEAREST)
        self.shaded_fbo = self.ctx.framebuffer([self.shaded_tex])
        self.out_tex = self.ctx.texture((self.settings.width, self.settings.height), 4)
        self.out_fbo = self.ctx.framebuffer([self.out_tex])
        palette = self.compiled.palette.astype(np.float32)
        self.palette_tex = self.ctx.texture((256, 1), 3, palette.tobytes(), dtype="f4")
        self.palette_tex.filter = (gl.NEAREST, gl.NEAREST)
        mats = [self.scene.material_for(i) for i in range(max(1, len(self.scene.materials)))]
        table = np.zeros((len(mats) * 3, 4), dtype=np.float32)
        for i, m in enumerate(mats):
            table[i * 3] = (m.diffuse, m.ambient, m.specular, m.shininess)
            table[i * 3 + 1] = (*(c / 255.0 for c in m.specular_color), m.wrap)
            table[i * 3 + 2] = (*(c / 255.0 for c in m.color), 1.0 if m.color_mode == "fixed" else 0.0)
        self.materials_tex = self.ctx.texture((len(mats) * 3, 1), 4, table.tobytes(), dtype="f4")
        self.materials_tex.filter = (gl.NEAREST, gl.NEAREST)
        self.material_count = len(mats)

    def _prepare(self) -> None:
        """Warm up, then size the depth range and the shadow maps from where the points are (read back once)."""
        self.population.bind()
        self.population.iterate(self.settings.fuse)
        xs, ys, zs = [], [], []
        for _ in range(RANGE_SAMPLES):
            self.population.iterate(1)
            state = np.frombuffer(self.population.buffers[self.population.current].read(), dtype=np.float32).reshape(-1, 6)[:, :3]
            x, y, z = state[:, 0].astype(np.float64), state[:, 1].astype(np.float64), state[:, 2].astype(np.float64)
            if self.compiled.final is not None:
                from .cpu_engine import apply_xform
                x, y, z, _c = apply_xform(self.compiled.final, x, y, z, np.zeros_like(x), np.random.default_rng(0))
            vx, vy, vz = self.view.to_view(x, y, z)
            xs.append(vx)
            ys.append(vy)
            zs.append(vz)
        vx, vy, vz = np.concatenate(xs), np.concatenate(ys), np.concatenate(zs)
        self.depth_range = self.view.depth_range(vz)
        self.bounds = self.view.bounds(vx, vy, vz)
        for index, light in enumerate(self.scene.lights[:MAX_LIGHTS]):
            if light.shadows and self.scene.solid.display != "points":
                shadow = ShadowMap(light.altitude, light.azimuth, self.bounds, SHADOW_MAP_SIZE)
                self.shadow_maps[index] = shadow
                tex = self.ctx.texture((SHADOW_MAP_SIZE, SHADOW_MAP_SIZE), 1, dtype="f4")
                tex.filter = (self.gl.NEAREST, self.gl.NEAREST)
                fbo = self.ctx.framebuffer([tex])
                fbo.clear(1e30, 0.0, 0.0, 0.0)
                self.shadow_textures[index] = (tex, fbo)
        self._set_plot_uniforms()
        self._fused = True

    def _set_plot_uniforms(self) -> None:
        from .gpu_engine import _set
        prog = self.population.plot_prog
        a, b, c, d, e, f = self.view.pixel_transform
        w, h = self.view.size
        _set(prog, "u_cam_x", (a, c, e))
        _set(prog, "u_cam_y", (b, d, f))
        _set(prog, "u_target", (float(w), float(h)))
        _set(prog, "u_depth_range", (float(self.depth_range[0]), float(self.depth_range[1])))
        for name, value in glsl_uniforms(self.flame.camera).items():
            _set(prog, name, value)
        _set(prog, "u_light_size", float(SHADOW_MAP_SIZE))

    # --- rendering ----------------------------------------------------------------------------------------------
    def run_pass(self, cancelled: Callable[[], bool] = lambda: False) -> np.ndarray | None:
        """Iterate and splat enough draws for one pass, then shade and read back."""
        if self._closed:
            return None
        from .gpu_engine import _set
        started = time.perf_counter()
        gl = self.gl
        self.population.bind()
        if not self._fused:
            self._prepare()
        prog = self.population.plot_prog
        wanted = self.settings.next_pass_samples(self.stats.passes_done, self.stats.samples)
        draws = max(1, -(-wanted // self.settings.points))
        w, h = self.view.size
        for _ in range(draws):
            if cancelled():
                return None
            self.population.iterate(1)
            # the camera's G-buffer: depth-tested points
            self.gbuffer_fbo.use()
            self.ctx.viewport = (0, 0, w, h)
            self.ctx.enable(gl.DEPTH_TEST)
            self.ctx.disable(gl.BLEND)
            _set(prog, "u_mode", 0)
            self.population.plot()
            self.ctx.disable(gl.DEPTH_TEST)
            if self.scene.solid.min_hits > 1:
                # the hit count per pixel: the same points, added up
                self.count_fbo.use()
                self.ctx.viewport = (0, 0, w, h)
                self.ctx.enable(gl.BLEND)
                self.ctx.blend_func = gl.ONE, gl.ONE
                _set(prog, "u_mode", 2)
                self.population.plot()
                self.ctx.disable(gl.BLEND)
            # the lights' shadow maps: nearest distance along the light (MIN blending)
            for index, shadow in self.shadow_maps.items():
                tex, fbo = self.shadow_textures[index]
                fbo.use()
                self.ctx.viewport = (0, 0, SHADOW_MAP_SIZE, SHADOW_MAP_SIZE)
                self.ctx.enable(gl.BLEND)
                self.ctx.blend_func = gl.ONE, gl.ONE
                self.ctx.blend_equation = gl.MIN
                _set(prog, "u_mode", 1)
                _set(prog, "u_light_basis", tuple(float(v) for v in shadow.basis.T.reshape(-1)))
                _set(prog, "u_light_origin", (float(shadow.origin[0]), float(shadow.origin[1])))
                _set(prog, "u_light_scale", (float(shadow.scale[0]), float(shadow.scale[1])))
                self.population.plot()
                self.ctx.blend_equation = gl.FUNC_ADD
                self.ctx.disable(gl.BLEND)
            self.stats.samples += self.settings.points
        image = self.image()
        self.stats.passes_done += 1
        self._elapsed += time.perf_counter() - started
        self.stats.seconds = self._elapsed
        self.stats.hits = self.stats.samples
        return image

    def image(self) -> np.ndarray:
        """Shade the G-buffer and read the output back as RGBA8."""
        from .gpu_engine import _set
        gl = self.gl
        w, h = self.view.size
        solid, env = self.scene.solid, self.scene.environment
        near, far = self.depth_range
        span = max(far - near, 1e-6)
        # normals
        min_hits = float(solid.min_hits) if solid.min_hits > 1 else 0.0
        self.normals_fbo.use()
        self.ctx.viewport = (0, 0, w, h)
        self.gbuffer_tex.use(0)
        self.count_tex.use(12)
        prog = self.programs["normals"]
        _set(prog, "u_gbuffer", 0)
        _set(prog, "u_count", 12)
        _set(prog, "u_min_hits", min_hits)
        _set(prog, "u_limit", float(DISCONTINUITY * span))
        self.vaos["normals"].render(mode=gl.TRIANGLES, vertices=3)
        # shading
        self.shaded_fbo.use()
        self.ctx.viewport = (0, 0, w, h)
        prog = self.programs["shade"]
        self.gbuffer_tex.use(0)
        self.normals_tex.use(1)
        self.palette_tex.use(2)
        self.materials_tex.use(3)
        self.count_tex.use(12)
        _set(prog, "u_gbuffer", 0)
        _set(prog, "u_count", 12)
        _set(prog, "u_min_hits", min_hits)
        _set(prog, "u_normals", 1)
        _set(prog, "u_palette", 2)
        _set(prog, "u_materials", 3)
        _set(prog, "u_material_count", self.material_count)
        _set(prog, "u_smooth_radius", int(round(solid.normal_smoothing)))
        _set(prog, "u_eye", tuple(float(v) for v in self.view.eye))
        a, b, c, d, e, f = self.view.pixel_transform
        _set(prog, "u_cam_x", (a, c, e))
        _set(prog, "u_cam_y", (b, d, f))
        _set(prog, "u_perspective", float(self.flame.camera.perspective))
        _set(prog, "u_display_points", 1 if solid.display == "points" else 0)
        _set(prog, "u_ao", 1 if solid.ao else 0)
        _set(prog, "u_ao_radius", float(solid.ao_radius * span * 4.0))
        samples = min(MAX_AO_SAMPLES, max(1, int(solid.ao_samples)))
        _set(prog, "u_ao_samples", samples)
        _set(prog, "u_ao_falloff", float(solid.ao_falloff))
        _set(prog, "u_ao_intensity", float(solid.ao_intensity))
        kernel = np.zeros((MAX_AO_SAMPLES, 3), dtype=np.float32)
        kernel[:samples] = ao_kernel(samples)
        _set_array(prog, "u_ao_kernel", kernel, "f4", 3)
        lights = self.scene.lights[:MAX_LIGHTS]
        _set(prog, "u_light_count", len(lights))
        dirs, colors, shadows, taps, bases, origins, scales, biases = [], [], [], [], [], [], [], []
        unit = 4
        units = []
        for index in range(MAX_LIGHTS):
            light = lights[index] if index < len(lights) else None
            shadow = self.shadow_maps.get(index) if light is not None and light.shadows and solid.display != "points" else None
            d = light_direction(light.altitude, light.azimuth) if light is not None else np.array([0.0, 0.0, 1.0])
            dirs += [float(v) for v in d]
            colors += [float(c) / 255.0 * light.intensity for c in light.color] if light is not None else [0.0, 0.0, 0.0]
            shadows.append(float(light.shadow_intensity) if shadow is not None else 0.0)
            taps.append(max(1, int(round(light.shadow_softness))) if light is not None else 1)
            if shadow is not None:
                bases += [float(v) for v in shadow.basis.T.reshape(-1)]
                origins += [float(shadow.origin[0]), float(shadow.origin[1])]
                scales += [float(shadow.scale[0]), float(shadow.scale[1])]
                biases.append(float(shadow.extent * 0.004))
                self.shadow_textures[index][0].use(unit)
            else:
                bases += [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
                origins += [0.0, 0.0]
                scales += [1.0, 1.0]
                biases.append(0.0)
                self.palette_tex.use(unit)       # any bound texture: the light has no map and never samples it
            units.append(unit)
            unit += 1
        _set_array(prog, "u_shadow", units, "i4", 1)
        _set_array(prog, "u_light_dir", dirs, "f4", 3)
        _set_array(prog, "u_light_color", colors, "f4", 3)
        _set_array(prog, "u_light_shadow", shadows, "f4", 1)
        _set_array(prog, "u_light_taps", taps, "i4", 1)
        _set_array(prog, "u_light_basis", bases, "f4", 9)
        _set_array(prog, "u_light_origin", origins, "f4", 2)
        _set_array(prog, "u_light_scale", scales, "f4", 2)
        _set_array(prog, "u_light_bias", biases, "f4", 1)
        _set(prog, "u_light_size", float(SHADOW_MAP_SIZE))
        _set(prog, "u_env_color", tuple(c / 255.0 for c in env.color))
        _set(prog, "u_env_ambient", float(env.ambient))
        _set(prog, "u_exposure", float(env.exposure))
        _set(prog, "u_env_visible", 1 if env.visible else 0)
        _set(prog, "u_fog", 1 if solid.fog else 0)
        _set(prog, "u_fog_range", (float(near + solid.fog_start * span), float(near + solid.fog_end * span)))
        _set(prog, "u_fog_color", tuple(c / 255.0 for c in solid.fog_color))
        self.vaos["shade"].render(mode=gl.TRIANGLES, vertices=3)
        # downsample + sRGB
        self.out_fbo.use()
        self.ctx.viewport = (0, 0, self.settings.width, self.settings.height)
        self.shaded_tex.use(0)
        prog = self.programs["down"]
        _set(prog, "u_image", 0)
        _set(prog, "u_factor", int(self.view.oversample))
        self.vaos["down"].render(mode=gl.TRIANGLES, vertices=3)
        data = self.out_fbo.read(components=4, dtype="f1")
        return np.frombuffer(data, dtype=np.uint8).reshape(self.settings.height, self.settings.width, 4).copy()

    def close(self) -> None:
        """Free the GPU objects (idempotent)."""
        if self._closed:
            return
        self._closed = True
        self.population.release()
        for obj in (self.gbuffer_fbo, self.gbuffer_tex, self.gbuffer_depth, self.count_fbo, self.count_tex, self.normals_fbo,
                    self.normals_tex, self.shaded_fbo, self.shaded_tex, self.out_fbo, self.out_tex, self.palette_tex, self.materials_tex):
            obj.release()
        for tex, fbo in self.shadow_textures.values():
            fbo.release()
            tex.release()


__all__ = ["SolidGpuJob", "SOLID_FRAGMENT", "NORMALS_GLSL", "SHADE_GLSL", "DOWNSAMPLE_GLSL", "SHADOW_MAP_SIZE"]

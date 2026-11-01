"""Spike (evidence for plans/fragments-plan.md, appendix C): preprocess a FragM .frag, modernise its legacy GLSL to
330 core, render 8 subframes with moderngl (ping-pong RGBA32F surfaces + the buffershader display pass) to /tmp/spike/out.png.

Run from samples/fragmentarium/Fragmentarium_Examples_Folder:
    python3 plans/spikes/frag_modernise_spike.py "Historical 3D Fractals/Mandelbulb.frag"
Not production code: a throw-away prototype kept so the plan's claims can be re-checked."""
import re, sys
from pathlib import Path
import numpy as np
import moderngl

EX = Path("/workspace/Fractalchemy/samples/fragmentarium/Fragmentarium_Examples_Folder")
INCLUDE = EX / "Include"

UNIFORM_ANNOT = re.compile(r"^(\s*uniform\s+(\w+)\s+(\w+)\s*;)\s*(slider|color|checkbox|menu|file)\s*\[(.*)\].*$")
NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"
def annot_default(typ, kind, body):
    nums = [float(x) for x in re.findall(NUM, body)]
    if kind == "checkbox": return body.strip().lower() == "true"
    if kind == "slider":
        n = {"float": 1, "double": 1, "int": 1, "vec2": 2, "vec3": 3, "vec4": 4, "dvec2": 2, "dvec3": 3, "dvec4": 4}[typ]
        d = nums[n:2 * n]
        return int(d[0]) if typ == "int" else (d[0] if n == 1 else tuple(d))
    if kind == "color":
        return tuple(nums[-3:]) if typ.endswith("vec3") else (nums[1], *nums[3:6])
    if kind == "menu": return int(nums[0])
    return None

def resolve(name, origin):
    for base in (origin.parent, INCLUDE):
        p = base / name
        if p.is_file():
            return p
    raise FileNotFoundError(name)

def preprocess(path, text=None, depth=0):
    """Returns dict(vertex=[...], fragment=[...], buffershader=dict|None, presets={}, camera, buffer)."""
    text = path.read_text(errors="replace") if text is None else text
    out = dict(vertex=[], fragment=[], buffershader=None, presets={}, camera="", buffer="", params=[])
    in_vertex = False
    preset = None
    for line in text.splitlines():
        s = line.strip()
        if preset is not None:
            if s.lower().startswith("#endpreset"):
                preset = None
            else:
                out["presets"][pname].append(line)
            continue
        m = re.match(r'^#include\s+"([^"]+)"', s)
        if m:
            sub = preprocess(resolve(m.group(1), path), depth=depth + 1)
            for k in ("vertex", "fragment"):
                out[k] += sub[k]
            out["presets"].update(sub["presets"])
            out["params"] += sub["params"]
            if sub["buffershader"]: out["buffershader"] = sub["buffershader"]
            if sub["camera"]: out["camera"] = sub["camera"]
            if sub["buffer"]: out["buffer"] = sub["buffer"]
            continue
        m = re.match(r'^#buffershader\s+"([^"]+)"', s)
        if m:
            out["buffershader"] = preprocess(resolve(m.group(1), path), depth=depth + 1)
            continue
        if s.lower().startswith("#preset"):
            pname = s.split(None, 1)[1] if " " in s else "Default"
            out["presets"][pname] = []
            preset = pname
            continue
        if s.lower().startswith("#vertex"):
            in_vertex = True; continue
        if s.lower().startswith("#endvertex"):
            in_vertex = False; continue
        if s.lower().startswith("#camera"):
            out["camera"] = s.split(None, 1)[1]; continue
        if s.lower().startswith("#buffer "):
            out["buffer"] = s.split(None, 1)[1]; continue
        if s.startswith(("#donotrun", "#info", "#group", "#TexParameter")):
            continue
        m = UNIFORM_ANNOT.match(line)
        if m:
            line = m.group(1)
            out["params"].append((m.group(3), annot_default(m.group(2), m.group(4), m.group(5))))
        (out["vertex"] if in_vertex else out["fragment"]).append(line)
    return out

VS_PATCH = """#version 330 core
layout(location = 0) in vec4 vertex_position;
#define gl_Vertex vertex_position
uniform mat4 projectionMatrix;
#define gl_ProjectionMatrix projectionMatrix
#define varying out
"""
FS_PATCH = """#version 330 core
#define varying in
#define texture2D texture
#define textureCube texture
#define texture2DLod textureLod
out vec4 fragColor;
#define gl_FragColor fragColor
"""

def modernise(lines, patch):
    body = [l for l in lines if not l.strip().startswith("#version")]
    return patch + "\n".join(body)

def dedupe_decls(src):
    """Legacy GLSL tolerated duplicate `varying`/`uniform` declarations across includes; 330 does not."""
    seen = set(); out = []
    for l in src.splitlines():
        key = re.sub(r"\s+", " ", l.strip())
        if re.match(r"^(varying|uniform)\s", key):
            if key in seen: continue
            seen.add(key)
        out.append(l)
    return "\n".join(out)

def compile_program(ctx, fs):
    vs = dedupe_decls(modernise(fs["vertex"], VS_PATCH))
    fsrc = dedupe_decls(modernise(fs["fragment"], FS_PATCH))
    return ctx.program(vertex_shader=vs, fragment_shader=fsrc)

def main(frag):
    ctx = moderngl.create_standalone_context(require=330)
    fs = preprocess(Path(frag))
    print("camera", fs["camera"], "buffer", fs["buffer"], "presets", list(fs["presets"]), "params", len(fs["params"]))
    prog = compile_program(ctx, fs)
    print("main program OK; uniforms:", sorted(n for n in prog if isinstance(prog[n], moderngl.Uniform)))
    bprog = compile_program(ctx, fs["buffershader"]) if fs["buffershader"] else None
    if bprog: print("buffershader OK")
    W, H = 256, 160
    tri = ctx.buffer(np.array([-1, -1, 0, 3, -1, 0, -1, 3, 0], dtype="f4").tobytes())
    vao = ctx.vertex_array(prog, [(tri, "3f", "vertex_position")])
    a = ctx.texture((W, H), 4, dtype="f4"); b = ctx.texture((W, H), 4, dtype="f4")
    fa = ctx.framebuffer([a]); fb = ctx.framebuffer([b])
    fa.clear(); fb.clear()
    ident = tuple(np.eye(4, dtype="f4").flatten().tolist())
    def setu(p, name, val):
        if name in p:
            u = p[name]
            if u.fmt.endswith("i") and isinstance(val, float): val = int(val)
            try: u.value = val
            except Exception as e: print("uniform", name, e)
    # defaults from preset Default (just camera ones for the spike)
    preset = {}
    for l in fs["presets"].get("Default", []):
        if "=" in l and not l.strip().startswith("//"):
            k, v = l.split("=", 1)
            vals = []
            for x in v.split(","):
                x = x.strip()
                vals.append(True if x == "true" else False if x == "false" else float(x))
            preset[k.strip()] = vals
    print("preset Default:", preset)
    # param defaults from slider annotations
    defaults = {k: v for k, v in fs["params"] if v is not None}
    if fs["buffershader"]: defaults.update({k: v for k, v in fs["buffershader"]["params"] if v is not None})
    src, dst = a, b
    for sub in range(8):
        setu(prog, "projectionMatrix", ident)
        setu(prog, "pixelSize", (1.0 / W, 1.0 / H))
        setu(prog, "subframe", sub)
        setu(prog, "backbuffer", 0)
        for k, v in defaults.items(): setu(prog, k, v)
        for k, v in preset.items():
            setu(prog, k, tuple(v) if len(v) > 1 else v[0])
        src.use(0)
        (fb if dst is b else fa).use()
        vao.render(moderngl.TRIANGLES, 3)
        src, dst = dst, src
    out = ctx.texture((W, H), 4, dtype="f1")
    fo = ctx.framebuffer([out])
    fo.use()
    if bprog:
        bvao = ctx.vertex_array(bprog, [(tri, "3f", "vertex_position")])
        setu(bprog, "projectionMatrix", ident); setu(bprog, "frontbuffer", 0)
        for k, v in dict(Gamma=2.2, Exposure=1.0, Brightness=1.0, Contrast=1.0, Saturation=1.0, ToneMapping=1, Hue=0.0,
                         LumCoeff=(0.2125, 0.7154, 0.0721), AvgLumin=(0.5, 0.5, 0.5)).items():
            setu(bprog, k, v)
        for k, v in defaults.items(): setu(bprog, k, v)
        for k, v in preset.items(): setu(bprog, k, tuple(v) if len(v) > 1 else v[0])
        src.use(0)
        bvao.render(moderngl.TRIANGLES, 3)
    img = np.frombuffer(fo.read(components=4), dtype="u1").reshape(H, W, 4)
    print("image mean", img[..., :3].mean(), "nonzero px", int((img[..., :3].sum(-1) > 0).sum()), "of", W * H)
    from PIL import Image
    Image.fromarray(img[::-1]).save("/tmp/spike/out.png")

if __name__ == "__main__": main(sys.argv[1])

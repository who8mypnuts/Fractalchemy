"""The DE composer's model: a recipe of folds and transforms in a loop, a primitive at the end → a fragment's GLSL.

A kaleidoscopic IFS is "fold, transform, repeat, then measure a shape", and every step has a few numbers. The
composer keeps that as data (`Recipe`: ordered `Step`s with parameter values, a loop count, an end `Shape`) and
writes a complete fragment on `DE-Raytracer.frag` + `Primitives.frag` where every parameter is a slider, so the
result can be tuned live in the Parameters dock; the recipe rides in the `.fafrag` metadata (`composer`) so the
dialog can reopen it. Only steps whose distance estimate is well defined are offered: isometric folds, scalings
(tracked in `s`) and sphere folds / inversions (conformal, tracked too); the estimate is `shape(p) / s`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

Param = tuple[str, object, tuple[float, float]]   # name, default, (min, max)

STEP_KINDS: dict[str, tuple[str, list[Param], str]] = {
    "abs": ("Mirror (abs)", [], "\t\tp = abs(p);"),
    "menger": ("Menger fold (sort |x| ≥ |y| ≥ |z|)", [], "\t\tp = foldMenger(p);"),
    "sierpinski": ("Sierpinski fold", [], "\t\tp = foldSierpinski(p);"),
    "kaleido": ("Kaleido fold in xz", [("Wedges", 6.0, (1.0, 24.0))], "\t\tp.xz = foldKaleido(p.xz, {Wedges});"),
    "plane": ("Fold about a plane", [("Normal", (1.0, -1.0, 0.0), (-1.0, 1.0))], "\t\tp = opFoldPlane(p, {Normal});"),
    "box": ("Box fold", [("Limit", 1.0, (0.0, 3.0))], "\t\tp = foldBox(p, {Limit});"),
    "sphere": ("Sphere fold", [("MinR2", 0.25, (0.0001, 2.0)), ("FixedR2", 1.0, (0.01, 4.0))], "\t\tp = foldSphere(p, s, {MinR2}, {FixedR2});"),
    "invert": ("Sphere inversion", [("Radius2", 1.0, (0.01, 8.0)), ("MinR2", 0.1, (0.001, 2.0)), ("MaxR2", 2.0, (0.1, 8.0))],
               "\t\t{{ float f = {Radius2} / clamp(dot(p, p), {MinR2}, {MaxR2}); p *= f; s *= f; }}"),
    "scale": ("Scale + offset", [("Scale", 2.0, (-4.0, 4.0)), ("Offset", (1.0, 1.0, 1.0), (-4.0, 4.0))],
              "\t\tp = p * {Scale} - {Offset} * ({Scale} - 1.0); s *= abs({Scale});"),
    "scale_start": ("Scale + start point (Mandelbox)", [("Scale", 2.0, (-4.0, 4.0))], "\t\tp = p * {Scale} + p0; s = s * abs({Scale}) + 1.0;"),
    "scale_julia": ("Scale + constant", [("Scale", 2.0, (-4.0, 4.0)), ("C", (0.0, 0.0, 0.0), (-4.0, 4.0))],
                    "\t\tp = p * {Scale} + {C}; s *= abs({Scale});"),
    "rotate": ("Rotate", [("Axis", (0.0, 1.0, 0.0), (-1.0, 1.0)), ("Angle", 30.0, (-180.0, 180.0))],
               "\t\tp = rot3({Axis}, radians({Angle})) * p;"),
    "translate": ("Translate", [("Offset", (0.0, 0.0, 0.0), (-4.0, 4.0))], "\t\tp -= {Offset};"),
    "repeat": ("Repeat", [("Period", (2.0, 2.0, 2.0), (0.1, 8.0))], "\t\tp = opRepeat(p, {Period});"),
    "twist": ("Twist about y", [("Twist", 1.0, (-4.0, 4.0))], "\t\tp = opTwist(p, {Twist});"),
    "menger_shift": ("Menger z shift (Knighty)", [("Offset", (1.0, 1.0, 1.0), (-4.0, 4.0)), ("Scale", 3.0, (1.0, 4.0))],
                     "\t\tif (p.z < -0.5 * {Offset}.z * ({Scale} - 1.0)) p.z += {Offset}.z * ({Scale} - 1.0);"),
}

SHAPES: dict[str, tuple[str, list[Param], str]] = {
    "box": ("Box", [("Size", (1.0, 1.0, 1.0), (0.01, 4.0))], "sdBox(p, {Size})"),
    "sphere": ("Sphere", [("Radius", 1.0, (0.01, 4.0))], "sdSphere(p, {Radius})"),
    "octahedron": ("Octahedron", [("Size", 1.0, (0.01, 4.0))], "sdOctahedron(p, {Size})"),
    "torus": ("Torus", [("Radius", 1.0, (0.01, 4.0)), ("Tube", 0.3, (0.01, 2.0))], "sdTorus(p, {Radius}, {Tube})"),
    "cross": ("Cross", [("Width", 0.3, (0.01, 2.0))], "sdCross(p, {Width})"),
    "cylinder": ("Cylinder", [("Radius", 0.5, (0.01, 4.0)), ("Height", 1.0, (0.01, 4.0))], "sdCylinder(p, {Radius}, {Height})"),
    "point": ("Point (length)", [], "length(p)"),
    "dodecahedron": ("Dodecahedron", [("Radius", 1.0, (0.01, 4.0))], "sdDodecahedron(p, {Radius})"),
    "gyroid": ("Gyroid", [("Frequency", 4.0, (0.5, 20.0)), ("Thickness", 0.05, (0.001, 0.5))], "sdGyroid(p, {Frequency}, {Thickness}, 0.0)"),
}

MENGER_PRESET = [("abs", {}), ("menger", {}), ("scale", {"Scale": 3.0, "Offset": (1.0, 1.0, 1.0)}), ("menger_shift", {"Offset": (1.0, 1.0, 1.0), "Scale": 3.0})]
SIERPINSKI_PRESET = [("sierpinski", {}), ("scale", {"Scale": 2.0, "Offset": (1.0, 1.0, 1.0)})]
MANDELBOX_PRESET = [("box", {"Limit": 1.0}), ("sphere", {"MinR2": 0.25, "FixedR2": 1.0}), ("scale_start", {"Scale": 2.0})]
PRESET_RECIPES = {"Menger sponge": (MENGER_PRESET, 6, "box", {"Size": (1.0, 1.0, 1.0)}),
                  "Sierpinski tetrahedron": (SIERPINSKI_PRESET, 10, "octahedron", {"Size": 1.0}),
                  "Mandelbox": (MANDELBOX_PRESET, 12, "point", {})}


@dataclass
class Step:
    """One step of the loop: a kind from `STEP_KINDS` and its parameter values."""
    kind: str
    values: dict[str, object] = field(default_factory=dict)

    def value(self, name: str):
        for pname, default, _bounds in STEP_KINDS[self.kind][1]:
            if pname == name:
                return self.values.get(name, default)
        raise KeyError(name)


@dataclass
class Recipe:
    """The whole composition."""
    steps: list[Step] = field(default_factory=list)
    iterations: int = 6
    shape: str = "box"
    shape_values: dict[str, object] = field(default_factory=dict)
    name: str = "Composed fractal"

    def to_dict(self) -> dict:
        return {"steps": [{"kind": s.kind, "values": {k: list(v) if isinstance(v, (tuple, list)) else v for k, v in s.values.items()}} for s in self.steps],
                "iterations": self.iterations, "shape": self.shape,
                "shape_values": {k: list(v) if isinstance(v, (tuple, list)) else v for k, v in self.shape_values.items()}, "name": self.name}

    @classmethod
    def from_dict(cls, data: dict | None) -> "Recipe":
        recipe = cls()
        if not data:
            return recipe
        for entry in data.get("steps", []):
            if isinstance(entry, dict) and entry.get("kind") in STEP_KINDS:
                recipe.steps.append(Step(entry["kind"], {k: tuple(v) if isinstance(v, list) else v for k, v in (entry.get("values") or {}).items()}))
        recipe.iterations = max(1, int(data.get("iterations", 6)))
        recipe.shape = data.get("shape", "box") if data.get("shape", "box") in SHAPES else "box"
        recipe.shape_values = {k: tuple(v) if isinstance(v, list) else v for k, v in (data.get("shape_values") or {}).items()}
        recipe.name = str(data.get("name", recipe.name))
        return recipe

    @classmethod
    def preset(cls, name: str) -> "Recipe":
        steps, iterations, shape, shape_values = PRESET_RECIPES[name]
        return cls([Step(kind, dict(values)) for kind, values in steps], iterations, shape, dict(shape_values), name)


# --- GLSL generation ---------------------------------------------------------------------------------------------------
def _uniform(name: str, default, bounds: tuple[float, float]) -> str:
    lo, hi = bounds
    if isinstance(default, (tuple, list)):
        d = ",".join(_num(v) for v in default)
        return f"uniform vec3 {name}; slider[({_num(lo)},{_num(lo)},{_num(lo)}),({d}),({_num(hi)},{_num(hi)},{_num(hi)})]"
    return f"uniform float {name}; slider[{_num(lo)},{_num(default)},{_num(hi)}]"


def _num(value) -> str:
    return f"{float(value):g}"


def generate(recipe: Recipe) -> str:
    """The fragment text for `recipe` (every step parameter a slider named `S<n>_<Param>`)."""
    uniforms: list[str] = [f"uniform int Iterations; slider[1,{recipe.iterations},40]"]
    body: list[str] = []
    for index, step in enumerate(recipe.steps, start=1):
        label, params, template = STEP_KINDS[step.kind]
        names = {}
        for pname, default, bounds in params:
            uniform_name = f"S{index}_{pname}"
            uniforms.append(_uniform(uniform_name, step.values.get(pname, default), bounds))
            names[pname] = uniform_name
        body.append(f"\t\t// {index}. {label}")
        body.append(template.format(**names))
    label, params, template = SHAPES[recipe.shape]
    names = {}
    for pname, default, bounds in params:
        uniform_name = f"Shape_{pname}"
        uniforms.append(_uniform(uniform_name, recipe.shape_values.get(pname, default), bounds))
        names[pname] = uniform_name
    shape_call = template.format(**names)
    lines = [f"#info {recipe.name} — composed with the DE Composer (Build ▸ DE Composer…)",
             '#include "MathUtils.frag"', '#include "DE-Raytracer.frag"', '#include "Primitives.frag"', "",
             "#group Composer", *uniforms, "",
             "float DE(vec3 p) {", "\tvec3 p0 = p;", "\tfloat s = 1.0;", "\tfor (int i = 0; i < Iterations; i++) {", *body, "\t}",
             f"\treturn {shape_call} / s;   // {label}", "}", "",
             "#preset Default", "FOV = 0.4", "Eye = 3.2,2.4,-3.8", "Target = 0,0,0", "Up = 0,1,0", "Detail = -3.0", "DetailAO = -1.3",
             "FudgeFactor = 0.8", "BaseColor = 0.85,0.85,0.9", "OrbitStrength = 0.5", "X = 0.5,0.6,0.6,0.7", "Y = 1,0.6,0,0.4",
             "Z = 0.8,0.78,1,0.5", "R = 0.4,0.7,1,0.12", "BackgroundColor = 0.28,0.3,0.38", "GradientBackground = 0.3", "#endpreset", ""]
    return "\n".join(lines)


__all__ = ["STEP_KINDS", "SHAPES", "PRESET_RECIPES", "Step", "Recipe", "generate"]

"""The scripting reference: every global name and type member, with signatures, descriptions and — for
arguments that take one of a known set of values (variation names, parameter names, …) — where the
options come from.

The Script Editor reads this for tab completion, the dynamic *Context* tab and the *Reference* tab, and
`tests/test_scripting.py` checks it against the real API so the two cannot drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..fractal import variations as V

# Option sources (see `options()`)
VARIATIONS = "variations"
PARAMS = "params"
CURVE_CHANNELS = "curve_channels"
FLAME_FILES = "flame_files"


@dataclass(frozen=True)
class Param:
    """One argument of a function or method."""
    name: str
    type: str = ""
    desc: str = ""
    optional: bool = False
    options: str | tuple[str, ...] | None = None   # an option source name, or literal choices

    @property
    def label(self) -> str:
        return self.name + ("?" if self.optional else "")


@dataclass(frozen=True)
class Entry:
    """One documented name: a global, or a member of a type.

    Attributes:
        kind: `function`, `method`, `property`, `object`, `constant`, `class`, `module`.
        type: The value's type name (properties, objects) — a key of TYPES when it is one of ours.
        returns: What a function / method returns.
        sig: Call signature shown in help (functions / methods).
        desc: One or two sentences.
        params: Arguments (functions / methods).
        example: A short usage snippet.
        readonly: Property that cannot be assigned.
        compat: An Apophysis compatibility alias.
    """
    kind: str
    type: str = ""
    returns: str = ""
    sig: str = ""
    desc: str = ""
    params: tuple[Param, ...] = ()
    example: str = ""
    readonly: bool = False
    compat: bool = False

    def signature(self, name: str) -> str:
        """`name(a, b?)` for callables, `name : type` for values."""
        if self.sig:
            return self.sig
        if self.kind in ("function", "method"):
            return f"{name}({', '.join(p.label for p in self.params)})"
        return f"{name} : {self.type}" if self.type else name


@dataclass(frozen=True)
class TypeDoc:
    """A type the scripts deal with: its members, and what `obj[...]` / iteration yield."""
    desc: str
    members: dict[str, Entry] = field(default_factory=dict)
    element: str = ""            # type of `obj[i]` / `for x in obj`
    dynamic: str = ""            # option source whose names are also valid keys (VariationMap, params)
    builtin: bool = False        # a Python type (list, dict, str …) — members are informational


def prop(type_: str, desc: str, readonly: bool = False) -> Entry:
    return Entry("property", type=type_, desc=desc, readonly=readonly)


def meth(desc: str, *params: Param, returns: str = "", example: str = "", sig: str = "") -> Entry:
    return Entry("method", returns=returns, desc=desc, params=params, example=example, sig=sig)


def func(desc: str, *params: Param, returns: str = "", example: str = "", sig: str = "", compat: bool = False) -> Entry:
    return Entry("function", returns=returns, desc=desc, params=params, example=example, sig=sig, compat=compat)


def obj(type_: str, desc: str, example: str = "", compat: bool = False) -> Entry:
    return Entry("object", type=type_, desc=desc, example=example, compat=compat)


P = Param
NUM = "float"
AFFINE_NOTE = ("Affine coefficients follow the flame-file / Apophysis script order: x′ = a·x + c·y + e, y′ = b·x + d·y + f. "
               "X = (a, b), Y = (c, d) and O = (e, f) are the triangle's vectors; y points down on screen.")
COLOR_NOTE = "A colour is (r, g, b) with 0..255 or a '#rrggbb' string."
XFORM_FIELDS = ("a", "b", "c", "d", "e", "f", "weight", "color", "color_speed", "symmetry", "opacity", "var_color", "name", "coefs",
                "post", "variations", "params", "xaos")

_TRANSFORM_FIELD_PARAMS = (
    P("weight", NUM, "Relative probability (default 0.5).", True), P("color", NUM, "Palette position 0..1.", True),
    P("color_speed", NUM, "0..1, how strongly the point colour moves to `color`.", True), P("opacity", NUM, "0..1.", True),
    P("a", NUM, "", True), P("b", NUM, "", True), P("c", NUM, "", True), P("d", NUM, "", True), P("e", NUM, "", True), P("f", NUM, "", True),
    P("coefs", "tuple", "(a, b, c, d, e, f).", True), P("post", "tuple", "Post affine (a, b, c, d, e, f).", True),
    P("variations", "dict", "{'name': weight, …} — replaces the default linear.", True), P("params", "dict", "{'julian_power': 4, …}.", True),
    P("name", "str", "", True), P("xaos", "list", "Chaos row.", True),
)

TYPES: dict[str, TypeDoc] = {
    "Transform": TypeDoc(
        "A transform of the flame (a live view of one XForm). Attributes are read and assigned directly; editing methods "
        "return the transform so calls chain. " + AFFINE_NOTE,
        {
            "weight": prop(NUM, "Relative probability of choosing this transform (final transforms ignore it)."),
            "color": prop(NUM, "Palette position 0..1 the point colour is pulled towards."),
            "color_speed": prop(NUM, "How strongly each hit pulls the colour to `color` (flam3 semantics, 0..1)."),
            "symmetry": prop(NUM, "Apophysis's symmetry = 1 − 2·color_speed (get/set)."),
            "opacity": prop(NUM, "Plot weight of points leaving this transform (0 = shapes the fractal but draws nothing)."),
            "var_color": prop(NUM, "Blend of direct-colour variations into the point colour (Apophysis var_color)."),
            "name": prop("str", "Optional label."),
            "a": prop(NUM, "Affine a (X vector, x component)."), "b": prop(NUM, "Affine b (X vector, y component)."),
            "c": prop(NUM, "Affine c (Y vector, x component)."), "d": prop(NUM, "Affine d (Y vector, y component)."),
            "e": prop(NUM, "Affine e (origin x)."), "f": prop(NUM, "Affine f (origin y)."),
            "coefs": prop("tuple", "All six coefficients (a, b, c, d, e, f) — get or assign."),
            "post": prop("Affine", "The post-variation affine: `t.post.a`, `t.post.coefs`, `t.post.reset()`."),
            "origin": prop("tuple", "(e, f): where the O point sits — get or assign."),
            "determinant": prop(NUM, "a·d − b·c: the triangle's signed area factor.", readonly=True),
            "variations": prop("VariationMap", "Variation name → weight (live): `t.variations['julian'] = 1`; 0 removes."),
            "variation_names": prop("list[str]", "Names of the variations in use.", readonly=True),
            "params": prop("dict", "Variation parameters keyed as in flame files: `t.params['julian_power'] = 4`."),
            "xaos": prop("list[float]", "This transform's chaos row (weight of every transform following it)."),
            "index": prop("int", "Position in `transforms` (0-based); −1 for the final transform.", readonly=True),
            "is_final": prop("bool", "True for the final transform.", readonly=True),
            "xform": prop("XForm", "The underlying model object.", readonly=True),
            "set_affine": meth("Set all six coefficients.", P("a", NUM), P("b", NUM), P("c", NUM), P("d", NUM), P("e", NUM), P("f", NUM), returns="Transform"),
            "reset_affine": meth("Identity affine.", returns="Transform"),
            "reset_post": meth("Identity post affine.", returns="Transform"),
            "rotate": meth("Turn the triangle about its own origin.", P("degrees", NUM, "Positive = counter-clockwise on screen."),
                           returns="Transform", example="transform.rotate(45)"),
            "rotate_around": meth("Turn the whole triangle (origin included) about a point.", P("degrees", NUM), P("x", NUM, "Pivot x (default 0).", True),
                                  P("y", NUM, "Pivot y (default 0).", True), returns="Transform"),
            "scale": meth("Scale the X and Y vectors about the origin.", P("sx", NUM), P("sy", NUM, "Separate y factor (default = sx).", True), returns="Transform"),
            "translate": meth("Move the origin by (dx, dy) fractal units.", P("dx", NUM), P("dy", NUM), returns="Transform"),
            "move_to": meth("Put the origin at (x, y).", P("x", NUM), P("y", NUM), returns="Transform"),
            "multiply": meth("Apophysis Multiply: compose the 2×2 part with [[a, b], [c, d]].", P("a", NUM), P("b", NUM), P("c", NUM), P("d", NUM), returns="Transform"),
            "flip_horizontal": meth("Mirror in the vertical axis through (0, 0).", returns="Transform"),
            "flip_vertical": meth("Mirror in the horizontal axis through (0, 0).", returns="Transform"),
            "set_variation": meth("Set a variation's weight (0 removes it); its parameters get their defaults.",
                                  P("name", "str", "Formula name.", options=VARIATIONS), P("weight", NUM), returns="Transform",
                                  example="transform.set_variation('julian', 1)"),
            "get_variation": meth("A variation's weight (0 if unused).", P("name", "str", options=VARIATIONS), returns=NUM),
            "has_variation": meth("True if the variation is in use.", P("name", "str", options=VARIATIONS), returns="bool"),
            "remove_variation": meth("Drop one variation.", P("name", "str", options=VARIATIONS), returns="Transform"),
            "clear_variations": meth("Remove every variation.", returns="Transform"),
            "total_variation_weight": meth("Sum of the variation weights.", returns=NUM),
            "normalize_variations": meth("Scale the variation weights to add up to 1.", returns="Transform"),
            "set_param": meth("Set a variation parameter (name checked against the loaded formulas).",
                              P("name", "str", "e.g. julian_power", options=PARAMS), P("value", NUM), returns="Transform"),
            "get_param": meth("A parameter's value, else its formula default.", P("name", "str", options=PARAMS), P("default", NUM, "", True), returns=NUM),
            "copy": meth("A detached copy — add it with add_transform(copy).", returns="Transform"),
            "to_dict": meth("Plain-data snapshot of the transform.", returns="dict"),
        }),
    "Affine": TypeDoc("Six coefficients of an affine (the post transform). " + AFFINE_NOTE, {
        "a": prop(NUM, ""), "b": prop(NUM, ""), "c": prop(NUM, ""), "d": prop(NUM, ""), "e": prop(NUM, ""), "f": prop(NUM, ""),
        "coefs": prop("tuple", "(a, b, c, d, e, f) — get or assign."), "reset": meth("Identity.", returns="Affine")}),
    "VariationMap": TypeDoc("Dict-like: variation name → weight. Any loaded formula name is a valid key; assigning 0 removes "
                            "the variation; new ones get their parameter defaults.", {}, dynamic=VARIATIONS),
    "TransformList": TypeDoc("`transforms`: the flame's transforms as Transform objects — `len()`, `transforms[i]`, slices, "
                             "`for t in transforms`.", {
        "index": meth("Position of a Transform object.", P("transform", "Transform"), returns="int")}, element="Transform"),
    "Camera": TypeDoc("The view. `zoom` is Apophysis's log2 zoom (+1 = twice as close); angles are in degrees.", {
        "x": prop(NUM, "Centre x (fractal units)."), "y": prop(NUM, "Centre y (y points down on screen)."),
        "center": prop("tuple", "(x, y) — get or assign."),
        "scale": prop(NUM, "Pixels per fractal unit at the flame's own width (Apophysis scale)."),
        "zoom": prop(NUM, "log2 magnification: each +1 doubles it."), "rotate": prop(NUM, "Rotation in degrees."),
        "width": prop("int", "The flame's image width in pixels."), "height": prop("int", "The flame's image height."),
        "size": prop("tuple", "(width, height).", readonly=True),
        "pitch": prop(NUM, "3D camera: tilt about the screen's horizontal axis, degrees (Apophysis cam_pitch)."),
        "pitch_y": prop(NUM, "3D camera: tilt about the vertical axis, degrees (Fractalchemy cam_pitch_y)."),
        "yaw": prop(NUM, "3D camera: spin about the plane's normal, degrees (cam_yaw)."),
        "perspective": prop(NUM, "Perspective strength (cam_perspective; 0 = orthographic)."),
        "zpos": prop(NUM, "Depth offset (cam_zpos)."), "dof": prop(NUM, "Depth-of-field blur (cam_dof)."),
        "set_size": meth("The flame's own image size.", P("width", "int"), P("height", "int"), returns="Camera"),
        "reset": meth("Centre (0, 0), scale 200, no zoom, rotation or 3D.", returns="Camera"),
        "reset_3d": meth("Flat again: pitch, yaw, perspective, zpos and dof to 0.", returns="Camera"),
        "pan": meth("Move the centre by (dx, dy) fractal units.", P("dx", NUM), P("dy", NUM), returns="Camera"),
        "zoom_by": meth("Multiply the magnification (2 = twice as close, 0.5 = twice as far).", P("factor", NUM), returns="Camera"),
        "rotate_by": meth("Add to the rotation.", P("degrees", NUM), returns="Camera"),
        "fit": meth("Frame the attractor like the Random Batch does (samples the system); False if it blows up.",
                    P("margin", NUM, "Space around the attractor (default 1.15).", True), returns="bool", example="camera.fit()"),
        "to_dict": meth("Plain-data snapshot.", returns="dict")}),
    "Coloring": TypeDoc("The tone mapping (Apophysis semantics).", {
        "brightness": prop(NUM, "Overall log-density brightness (default 4)."), "gamma": prop(NUM, "Display gamma (default 4)."),
        "gamma_threshold": prop(NUM, "Below this density gamma blends linearly (default 0.01)."),
        "vibrancy": prop(NUM, "1 = colour from palette ratios, 0 = per-channel gamma."), "contrast": prop(NUM, "Density scaling (default 1)."),
        "background": prop("color", "Background colour — (r, g, b) or '#rrggbb'."),
        "background_hex": prop("str", "The background as '#rrggbb'.", readonly=True),
        "reset": meth("Apophysis defaults.", returns="Coloring"),
        "reset_curves": meth("Straighten the tone curves.", P("channel", "str", "One channel, or all when omitted.", True, options=CURVE_CHANNELS), returns="Coloring")}),
    "Gradient": TypeDoc("The flame's palette (256 colours) plus the Gradient Library's node operations. " + COLOR_NOTE, {
        "colors": prop("list", "All 256 palette colours (a copy; assign a list of colours to replace the palette)."),
        "stops": prop("NodeGradient", "The palette as a simplified node gradient (a copy, like the Gradient Library shows).", readonly=True),
        "get_color": meth("One palette entry.", P("index", "int", "0..255"), returns="tuple"),
        "set_color": meth("Set one palette entry.", P("index", "int", "0..255"), P("color", "color"), returns="Gradient"),
        "color_at": meth("The colour a transform with `color = position` paints with.", P("position", NUM, "0..1"), returns="tuple"),
        "hex_colors": meth("All 256 colours as '#rrggbb'.", returns="list[str]"),
        "set_stops": meth("Rebuild the palette from nodes.", P("stops", "list", "A Gradient, or [(position, color), …] with positions 0..1."),
                          returns="Gradient", example="gradient.set_stops([(0, '#000'), (0.6, (255, 120, 0)), (1, '#fff')])"),
        "from_colors": meth("Spread colours evenly over the palette.", P("colors", "list", "e.g. ['#000', '#f80', '#fff']"), returns="Gradient"),
        "random": meth("A whole new random gradient (Gradient Library: Reroll).", returns="Gradient"),
        "randomize_colors": meth("Keep the nodes, new harmonising colours.", returns="Gradient"),
        "randomize_positions": meth("Keep the colours, scatter the nodes.", returns="Gradient"),
        "add_nodes": meth("Insert a few harmonising nodes (Auto increase nodes).", returns="Gradient"),
        "remove_nodes": meth("Drop a share of the nodes (Decrease nodes).", returns="Gradient"),
        "smooth": meth("Blur the colour curve (Smooth gradient).", returns="Gradient"),
        "rotate": meth("Cycle the palette.", P("amount", NUM, "Fraction of the length (0.5 = half a turn), or whole entries when |amount| ≥ 1."), returns="Gradient"),
        "reverse": meth("Reverse the palette.", returns="Gradient"), "invert": meth("Invert every colour.", returns="Gradient"),
        "hue_shift": meth("Turn every colour's hue.", P("degrees", NUM), returns="Gradient"),
        "adjust": meth("The Gradient Library's whole-gradient sliders.", P("hue", NUM, "Degrees.", True), P("saturation", NUM, "Percent −100..100.", True),
                       P("luminance", NUM, "Percent −100..100.", True), returns="Gradient", example="gradient.adjust(hue=30, saturation=20)"),
        "blend": meth("Mix with another palette.", P("other", "list", "A list of colours, a Gradient or another gradient helper."),
                      P("amount", NUM, "0..1 (default 0.5).", True), returns="Gradient"),
        "load": meth("Load a gradient from any file the Gradient Library reads.", P("path", "str", ".ugr, .map, .flame, .chaos, .fa, an image …"),
                     P("index", "int", "Entry in a multi-gradient file (default 0).", True), returns="Gradient")}),
    "Xaos": TypeDoc("The chaos matrix: matrix[from][to] is the relative weight of transform `to` following transform `from` "
                    "(1 = normal, 0 = never). Indices or Transform objects may be given.", {
        "matrix": prop("list", "The full matrix as nested lists (a copy).", readonly=True),
        "is_default": prop("bool", "True when no xaos is in effect.", readonly=True),
        "get": meth("One weight.", P("from_", "int|Transform"), P("to", "int|Transform"), returns=NUM),
        "set": meth("Set one weight.", P("from_", "int|Transform"), P("to", "int|Transform"), P("weight", NUM, "0 = never, 1 = normal, larger = more often."),
                    returns="Xaos", example="xaos.set(0, 1, 0)"),
        "set_matrix": meth("Set the whole matrix from nested lists.", P("matrix", "list"), returns="Xaos"),
        "set_row": meth("All weights leading from one transform.", P("from_", "int|Transform"), P("weights", "list"), returns="Xaos"),
        "set_column": meth("All weights leading to one transform.", P("to", "int|Transform"), P("weights", "list"), returns="Xaos"),
        "reset": meth("No xaos at all.", returns="Xaos"),
        "chain": meth("A ring: i may only be followed by i + 1.", P("allow_self", "bool", "Also allow i → i.", True), returns="Xaos"),
        "isolate": meth("A transform that only follows itself, with nothing leading to it.", P("which", "int|Transform"), returns="Xaos"),
        "from_function": meth("Fill from fn(from_index, to_index) → weight.", P("fn", "callable"), returns="Xaos",
                              example="xaos.from_function(lambda i, j: 0 if i == j else 1)"),
        "randomize": meth("Random on/off links (every transform keeps a way out).", P("probability", NUM, "Chance of a link (default 0.5).", True), returns="Xaos")}),
    "Flame": TypeDoc("The model object behind the helpers (fractalchemy.fractal.scene.Flame). The helpers are friendlier; these "
                     "fields are the raw data.", {
        "name": prop("str", "The flame's name (shown in the title, saved with the file)."),
        "xforms": prop("list[XForm]", "The raw transforms (prefer `transforms`)."), "final": prop("XForm|None", "The raw final transform."),
        "camera": prop("RawCamera", "The raw camera (centre tuple, angles in radians) — prefer `camera`."),
        "coloring": prop("RawColoring", "The raw tone mapping — prefer `coloring`."),
        "palette": prop("list", "The 256 palette colours — prefer `gradient`."),
        "oversample": prop("int", "The file's own final-render oversample hint."), "filter_radius": prop(NUM, "The file's own filter radius hint."),
        "unsupported": prop("list[str]", "Variation names in the file no engine implements.", readonly=True),
        "gradient": prop("NodeGradient", "The palette as a node Gradient (a copy).", readonly=True),
        "set_gradient": meth("Replace the palette by sampling a node Gradient.", P("gradient", "NodeGradient")),
        "renderable": meth("True if some transform has a positive weight.", returns="bool"),
        "copy": meth("An independent copy.", returns="Flame"), "to_dict": meth("JSON-ready data.", returns="dict")}),
    "XForm": TypeDoc("The raw transform dataclass (weight, color, color_speed, opacity, coefs, post, variations, params, chaos, name, var_color).", {
        "weight": prop(NUM, ""), "color": prop(NUM, ""), "color_speed": prop(NUM, ""), "opacity": prop(NUM, ""), "coefs": prop("tuple", ""),
        "post": prop("tuple", ""), "variations": prop("dict", ""), "params": prop("dict", ""), "chaos": prop("list|None", ""), "name": prop("str", ""),
        "var_color": prop(NUM, ""), "copy": meth("Deep copy.", returns="XForm")}),
    "RawCamera": TypeDoc("fractalchemy.fractal.scene.Camera: center (x, y), scale, zoom, rotate (degrees), width, height, pitch / yaw / pitch_y "
                         "(radians), perspective, zpos, dof.", {
        "center": prop("tuple", ""), "scale": prop(NUM, ""), "zoom": prop(NUM, ""), "rotate": prop(NUM, ""), "width": prop("int", ""),
        "height": prop("int", ""), "pitch": prop(NUM, "radians"), "yaw": prop(NUM, "radians"), "pitch_y": prop(NUM, "radians"),
        "perspective": prop(NUM, ""), "zpos": prop(NUM, ""), "dof": prop(NUM, "")}),
    "RawColoring": TypeDoc("fractalchemy.fractal.scene.Coloring.", {
        "brightness": prop(NUM, ""), "gamma": prop(NUM, ""), "gamma_threshold": prop(NUM, ""), "vibrancy": prop(NUM, ""), "contrast": prop(NUM, ""),
        "background": prop("tuple", "(r, g, b)"), "curves": prop("Curves", "Tone curves.")}),
    "NodeGradient": TypeDoc("fractalchemy.model.Gradient: a cyclic list of ColorStop(position, color) nodes.", {
        "name": prop("str", ""), "stops": prop("list[ColorStop]", "Sorted by position."),
        "color_at": meth("Interpolated colour at 0..1.", P("t", NUM), returns="tuple"), "sample": meth("`count` evenly spaced colours.", P("count", "int"), returns="list"),
        "move_stop": meth("Move a node.", P("index", "int"), P("position", NUM), returns="int"),
        "set_color": meth("Recolour a node.", P("index", "int"), P("color", "tuple")), "copy": meth("Deep copy.", returns="NodeGradient")}),
    "ColorStop": TypeDoc("One gradient node.", {"position": prop(NUM, "0..1"), "color": prop("tuple", "(r, g, b)")}),
    "list": TypeDoc("Python list.", {}, builtin=True), "dict": TypeDoc("Python dict.", {}, builtin=True), "str": TypeDoc("Python str.", {}, builtin=True),
    "tuple": TypeDoc("Python tuple.", {}, builtin=True), "float": TypeDoc("Number.", {}, builtin=True), "int": TypeDoc("Integer.", {}, builtin=True),
    "bool": TypeDoc("True / False.", {}, builtin=True),
    "math": TypeDoc("Python's math module.", {n: (Entry("constant", NUM, desc=f"math.{n}") if n in ("pi", "e", "tau", "inf") else
                                                Entry("function", returns=NUM, desc=f"math.{n}", sig=f"{n}(…)"))
                                             for n in ("sin", "cos", "tan", "asin", "acos", "atan", "atan2", "sqrt", "hypot", "exp", "log", "log2", "log10",
                                                       "pow", "floor", "ceil", "radians", "degrees", "fabs", "copysign", "fmod", "pi", "e", "tau", "inf")},
                    builtin=True),
}
TYPES["Transform"].members["variations"] = prop("VariationMap", TYPES["Transform"].members["variations"].desc)

GLOBALS: dict[str, Entry] = {
    # --- objects ------------------------------------------------------------------------------------------------------
    "flame": obj("Flame", "The flame being edited (a copy; the main window takes it over when the script finishes, as one undo step). "
                          "Use the helpers below for most edits.", example="flame.name = 'scripted'"),
    "transforms": obj("TransformList", "The transforms as Transform objects: `transforms[0]`, `for t in transforms:`, `len(transforms)`.",
                      example="for t in transforms:\n    t.rotate(10)"),
    "transform": obj("Transform", "The active transform (Apophysis style). `add_transform()` makes the new one active; "
                                  "`set_active_transform(i)` picks another.", example="transform.weight = 0.5"),
    "camera": obj("Camera", "The view: centre, scale, zoom, rotation, image size and the 3D camera.", example="camera.zoom_by(1.5)"),
    "gradient": obj("Gradient", "The palette and the Gradient Library's operations.", example="gradient.random().hue_shift(40)"),
    "xaos": obj("Xaos", "The chaos matrix.", example="xaos.chain()"),
    "coloring": obj("Coloring", "Brightness, gamma, threshold, vibrancy, contrast, background.", example="coloring.gamma = 3.5"),
    "math": Entry("module", "math", desc="Python's math module (sin, cos, atan2, hypot, …)."),
    "PI": Entry("constant", NUM, desc="3.14159…"), "TAU": Entry("constant", NUM, desc="2π"),
    "Flame": Entry("class", "Flame", desc="The model class (advanced: build flames by hand)."),
    "XForm": Entry("class", "XForm", desc="The raw transform class (advanced)."),
    "Gradient": Entry("class", "NodeGradient", desc="The node-gradient class (for set_stops / blend)."),
    "ColorStop": Entry("class", "ColorStop", desc="A gradient node: ColorStop(position, (r, g, b))."),
    # --- transforms --------------------------------------------------------------------------------------------------------
    "add_transform": func("Append a transform and make it active. Give a Transform / dict to copy, or keyword arguments.",
                          P("spec", "Transform|dict", "What to copy (optional).", True), *_TRANSFORM_FIELD_PARAMS, returns="Transform",
                          example="t = add_transform(weight=1, variations={'spherical': 1}, color=0.3)"),
    "add_random_transform": func("Append a transform with one of Apophysis's random affines and random variations.",
                                 P("variations", "list[str]", "Names to choose from (default: every formula).", True, options=VARIATIONS), returns="Transform"),
    "insert_transform": func("Insert a transform at a position.", P("index", "int"), P("spec", "Transform|dict", "", True), *_TRANSFORM_FIELD_PARAMS, returns="Transform"),
    "remove_transform": func("Delete a transform (default: the active one).", P("which", "int|Transform", "", True), returns="Transform"),
    "copy_transform": func("Duplicate a transform (default: the active one); the copy becomes active.", P("which", "int|Transform", "", True), returns="Transform"),
    "clear_transforms": func("Remove every transform and the final transform."),
    "get_transform": func("A transform by index.", P("which", "int"), returns="Transform"),
    "set_active_transform": func("Choose what `transform` refers to.", P("which", "int|Transform"), returns="Transform"),
    "move_transform": func("Re-order: move a transform to another position.", P("which", "int|Transform"), P("to", "int")),
    "swap_transforms": func("Swap two transforms (their xaos rows and columns follow).", P("first", "int|Transform"), P("second", "int|Transform")),
    "for_each_transform": func("Call fn(transform, index) for every transform.", P("fn", "callable"),
                               example="for_each_transform(lambda t, i: t.set_variation('linear', 1))"),
    "normalize_weights": func("Scale the weights so they add up to 1."),
    "total_weight": func("Sum of the transform weights.", returns=NUM),
    "final_transform": func("The final transform as a Transform, or None.", returns="Transform|None"),
    "set_final_transform": func("Create or replace the final transform (keyword arguments as for add_transform); "
                                "`set_final_transform(None)` removes it.", P("spec", "Transform|dict|None", "", True), *_TRANSFORM_FIELD_PARAMS,
                                returns="Transform", example="set_final_transform(variations={'spherical': 1})"),
    "remove_final_transform": func("Remove the final transform."),
    "new_transform": func("A detached transform to prepare and add later.", P("spec", "Transform|dict", "", True), *_TRANSFORM_FIELD_PARAMS, returns="Transform"),
    # --- flame -----------------------------------------------------------------------------------------------------------------
    "new_flame": func("Start from scratch: no transforms, default camera and colouring (the palette is kept unless keep_gradient=False).",
                      P("name", "str", "", True), P("keep_gradient", "bool", "", True), returns="Flame"),
    "random_flame": func("Replace the flame with a random one, as the Random Batch window makes them.",
                         P("variations", "list[str]", "Formulas to draw from (default: all).", True, options=VARIATIONS),
                         P("transforms", "tuple|int", "(min, max) or a count (default (2, 5)).", True), P("seed", "int", "", True), returns="Flame"),
    "load_flame": func("Replace the flame with an entry of a .flame / .chaos / .fa file.", P("path", "str", options=FLAME_FILES),
                       P("index", "int", "Entry (default 0).", True), returns="Flame"),
    "save_flame": func("Append the flame to a .flame or .fa file (created if missing); returns its index.", P("path", "str"),
                       P("name", "str", "Name to save under (default: the flame's).", True), returns="int"),
    "set_flame": func("Replace the flame with a Flame object (from copy_flame(), Flame(...) …).", P("flame", "Flame"), returns="Flame"),
    "copy_flame": func("An independent copy of the flame.", returns="Flame"),
    "flame_text": func("The flame as .fa parameters text (what Copy Parameters uses).", returns="str"),
    "flame_xml": func("The flame as Apophysis <flame> XML.", returns="str"),
    "from_text": func("Replace the flame from parameters text (.fa JSON, <flame> XML or a Chaotica world).", P("text", "str"), returns="Flame"),
    "snapshot": func("Remember the flame under a key (script-local).", P("key", "str", "", True)),
    "restore": func("Go back to a snapshot.", P("key", "str", "", True), returns="Flame"),
    "validate": func("Problems that would stop the flame rendering (an empty list is good).", returns="list[str]"),
    # --- variations ------------------------------------------------------------------------------------------------------------------
    "list_variations": func("Names of every loaded formula.", P("filter", "str", "Only names containing this.", True), returns="list[str]"),
    "variation_info": func("Facts about a formula: kind, parameters with defaults, origin, note.", P("name", "str", options=VARIATIONS), returns="dict"),
    "variation_params": func("Parameter names of a formula.", P("name", "str", options=VARIATIONS), returns="list[str]"),
    "random_variation": func("A random formula name.", P("exclude", "list[str]", "Names to skip (default ['pre_blur']).", True), returns="str"),
    # --- randomness ---------------------------------------------------------------------------------------------------------------------
    "random": func("random() → 0..1, random(n) → 0..n, random(a, b) → a..b.", P("a", NUM, "", True), P("b", NUM, "", True), returns=NUM),
    "random_int": func("A random integer a..b (both included), or 0..a.", P("a", "int"), P("b", "int", "", True), returns="int"),
    "random_choice": func("A random element.", P("items", "list"), returns="any"),
    "random_gauss": func("A normally distributed number.", P("mean", NUM, "", True), P("sigma", NUM, "", True), returns=NUM),
    "random_bool": func("True with the given probability.", P("probability", NUM, "Default 0.5.", True), returns="bool"),
    "random_color": func("A random (r, g, b).", returns="tuple"),
    "seed": func("Seed the script's random numbers so it repeats exactly.", P("value", "int")),
    # --- maths helpers --------------------------------------------------------------------------------------------------------------------
    "clamp": func("Limit a value to lo..hi.", P("value", NUM), P("lo", NUM), P("hi", NUM), returns=NUM),
    "lerp": func("Linear interpolation a → b.", P("a", NUM), P("b", NUM), P("t", NUM), returns=NUM),
    "deg2rad": func("Degrees → radians.", P("degrees", NUM), returns=NUM), "rad2deg": func("Radians → degrees.", P("radians", NUM), returns=NUM),
    "dist": func("Distance between two points.", P("x1", NUM), P("y1", NUM), P("x2", NUM), P("y2", NUM), returns=NUM),
    "hex_to_rgb": func("'#rrggbb' → (r, g, b).", P("text", "str"), returns="tuple"),
    "rgb_to_hex": func("(r, g, b) → '#rrggbb'.", P("rgb", "tuple"), returns="str"),
    # --- output and interaction ---------------------------------------------------------------------------------------------------------------
    "print": func("Write to the output panel (like Python's print).", P("values", "any", "Anything; separated by spaces."), sig="print(*values, sep=' ', end='\\n')",
                  example="print('weights:', [t.weight for t in transforms])"),
    "clear": func("Clear the output panel."),
    "message": func("Show a message box (the script continues afterwards).", P("text", "str")),
    "input_text": func("Ask the user for text; None if cancelled.", P("prompt", "str", "", True), P("default", "str", "", True), returns="str|None",
                       example="name = input_text('Flame name?', flame.name)"),
    "input_number": func("Ask for a number (asks again until it is one); None if cancelled.", P("prompt", "str", "", True), P("default", NUM, "", True),
                         returns="float|None", example="n = input_number('How many copies?', 4)\nif n is None:\n    stop()"),
    "confirm": func("A Yes / No question.", P("text", "str", "", True), returns="bool"),
    "update": func("Show the flame in the main window now and re-render — for step-by-step previews and animations.",
                   P("wait", "bool", "Wait for the first render pass (default True).", True),
                   example="for i in range(12):\n    camera.rotate_by(30)\n    update()\n    sleep(0.2)"),
    "sleep": func("Pause for a while (Stop still works).", P("seconds", NUM)),
    "progress": func("Show progress 0..1 in the status bar.", P("fraction", NUM)),
    "stop": func("End the script here; what it changed so far is kept.", P("reason", "str", "", True)),
    # --- Apophysis compatibility ---------------------------------------------------------------------------------------------------------------
    "Transform": obj("Transform", "Apophysis alias of `transform` (the active transform).", compat=True),
    "AddTransform": func("Apophysis alias of add_transform().", returns="Transform", compat=True),
    "DeleteTransform": func("Apophysis: delete the active transform.", compat=True),
    "CopyTransform": func("Apophysis alias of copy_transform().", returns="Transform", compat=True),
    "SetActiveTransform": func("Apophysis alias of set_active_transform(i).", P("which", "int"), compat=True),
    "Rotate": func("Apophysis: rotate the active transform.", P("degrees", NUM), compat=True),
    "Scale": func("Apophysis: scale the active transform.", P("factor", NUM), compat=True),
    "Translate": func("Apophysis: translate the active transform.", P("dx", NUM), P("dy", NUM), compat=True),
    "Multiply": func("Apophysis: multiply the active transform's matrix.", P("a", NUM), P("b", NUM), P("c", NUM), P("d", NUM), compat=True),
    "RotateFlame": func("Apophysis: rotate the camera.", P("degrees", NUM), compat=True),
    "NormalizeWeights": func("Apophysis alias of normalize_weights().", compat=True),
    "RandomGradient": func("Apophysis alias of gradient.random().", compat=True),
    "UpdateFlame": func("Apophysis alias of update().", compat=True),
    "ShowMessage": func("Apophysis alias of message().", P("text", "str"), compat=True),
    "Print": func("Apophysis alias of print().", P("values", "any"), sig="Print(*values)", compat=True),
    "Clear": func("Apophysis alias of clear().", compat=True),
    "Random": func("Apophysis: 0..1, or an integer 0..n−1.", P("n", "int", "", True), returns=NUM, compat=True),
    "Trunc": func("Truncate.", P("value", NUM), returns="int", compat=True), "Round": func("Round.", P("value", NUM), returns="int", compat=True),
    "Sqr": func("x².", P("value", NUM), returns=NUM, compat=True),
}

CATEGORIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Objects", ("flame", "transforms", "transform", "camera", "gradient", "xaos", "coloring")),
    ("Transforms", ("add_transform", "add_random_transform", "insert_transform", "remove_transform", "copy_transform", "clear_transforms",
                    "get_transform", "set_active_transform", "move_transform", "swap_transforms", "for_each_transform", "normalize_weights",
                    "total_weight", "final_transform", "set_final_transform", "remove_final_transform", "new_transform")),
    ("Flame", ("new_flame", "random_flame", "load_flame", "save_flame", "set_flame", "copy_flame", "flame_text", "flame_xml", "from_text",
               "snapshot", "restore", "validate")),
    ("Variations", ("list_variations", "variation_info", "variation_params", "random_variation")),
    ("Randomness", ("random", "random_int", "random_choice", "random_gauss", "random_bool", "random_color", "seed")),
    ("Maths helpers", ("clamp", "lerp", "deg2rad", "rad2deg", "dist", "hex_to_rgb", "rgb_to_hex", "math", "PI", "TAU")),
    ("Output & interaction", ("print", "clear", "message", "input_text", "input_number", "confirm", "update", "sleep", "progress", "stop")),
    ("Classes", ("Flame", "XForm", "Gradient", "ColorStop")),
    ("Apophysis compatibility", ("Transform", "AddTransform", "DeleteTransform", "CopyTransform", "SetActiveTransform", "Rotate", "Scale",
                                 "Translate", "Multiply", "RotateFlame", "NormalizeWeights", "RandomGradient", "UpdateFlame", "ShowMessage",
                                 "Print", "Clear", "Random", "Trunc", "Round", "Sqr")),
)


@dataclass(frozen=True)
class Option:
    """One value an argument may take."""
    name: str
    desc: str = ""
    detail: str = ""


def options(source) -> list[Option]:
    """The values an argument with option source `source` may take (variation names, parameter names, …)."""
    if isinstance(source, tuple):
        return [Option(name) for name in source]
    if source == VARIATIONS:
        out = []
        for name in sorted(V.REGISTRY):
            var = V.REGISTRY[name]
            bits = [var.kind] if var.kind != V.NORMAL else []
            if var.z == V.Z_FORMULA:
                bits.append("3D")
            if var.dc:
                bits.append("direct colour")
            out.append(Option(name, ", ".join(bits) or "", ", ".join(var.params)))
        return out
    if source == PARAMS:
        out = []
        for name in sorted(V.REGISTRY):
            for key, default in V.REGISTRY[name].params.items():
                out.append(Option(key, f"{name}, default {default:g}"))
        return out
    if source == CURVE_CHANNELS:
        return [Option(c) for c in ("overall", "red", "green", "blue", "alpha")]
    return []


GUIDE = """\
# Fractalchemy scripting guide

Scripts are **Python**. The names below are available without any import; everything else is ordinary
Python (loops, functions, `math`, `random`, list comprehensions …). A script works on a *copy* of the
fractal shown in the main window; when it finishes, the result replaces it as one undo step (*Revert
flame* on the toolbar goes back too). Press **Ctrl+Enter** (or ▶) to run.

## 1. The basics

```python
# Rotate every transform by a random angle
for t in transforms:
    t.rotate(random(-30, 30))
print('rotated', len(transforms), 'transforms')
```

* `flame` — the fractal (name, raw data)
* `transforms` — the transforms; `transform` is the *active* one
* `camera`, `gradient`, `xaos`, `coloring` — the view, the palette, the chaos matrix, the tone mapping
* `print()` — writes to the output panel under the editor

## 2. Transforms

```python
t = add_transform()                      # a new transform: linear 1, weight 0.5; it is now `transform`
t.variations['linear'] = 0               # remove linear …
t.variations['julian'] = 1               # … add julian (parameters get their defaults)
t.params['julian_power'] = 5
t.set_affine(0.5, 0, 0, 0.5, 0.3, 0)     # a b c d e f:  x' = a·x + c·y + e,  y' = b·x + d·y + f
t.rotate(30).scale(0.8).translate(0.2, 0)
t.weight = 0.75; t.color = 0.3; t.color_speed = 0.5; t.opacity = 1
t.post.a = 1.2                           # post transform
u = add_transform(weight=1, color=0.6, variations={'spherical': 0.7, 'linear': 0.3}, a=0.6, d=0.6)
remove_transform(0)                      # by index or object
set_final_transform(variations={'bubble': 1})   # set_final_transform(None) removes it
```

Every loaded formula can be used — built-ins, plugins and your own (*Help ▸ Formulas…*). Type
`t.variations['` and press Tab to pick from the list.

## 3. Colours and the gradient

```python
gradient.random()                                    # Gradient Library: Reroll
gradient.set_stops([(0, '#000020'), (0.5, (255, 120, 0)), (1, '#ffffff')])
gradient.hue_shift(30).adjust(saturation=20)
gradient.load('~/gradients/sunsets.ugr', 2)         # any file the Gradient Library reads
for i, t in enumerate(transforms):                   # spread the colours along the palette
    t.color = i / max(1, len(transforms) - 1)
coloring.brightness = 5; coloring.gamma = 3.5; coloring.background = '#101020'
```

## 4. Chaos / xaos

`xaos.set(a, b, weight)` controls how likely transform *b* follows transform *a* (0 = never, 1 = normal).

```python
xaos.reset()
xaos.chain()                     # 0 → 1 → 2 → … → 0
xaos.set(0, 0, 0)                # transform 0 never repeats itself
print(xaos)
```

## 5. Camera

```python
camera.x, camera.y = 0, 0.2
camera.scale = 180; camera.zoom = 0.5; camera.rotate = 15
camera.zoom_by(2); camera.rotate_by(90); camera.pan(0.1, 0)
camera.fit()                     # frame the attractor
camera.pitch = 30; camera.perspective = 0.2      # the 3D camera (degrees)
camera.set_size(1920, 1080)
```

## 6. Interaction and animation

```python
n = input_number('How many copies?', 4)
if n is None:
    stop()
if not confirm('Replace the gradient too?'):
    print('keeping the gradient')
for i in range(20):              # a preview animation
    camera.rotate_by(3)
    update()                     # push the flame to the main window and render
    sleep(0.1)
```

## 7. Script metadata

Comment lines at the top are shown in the *Info* tab and name the script when it is saved as a template:

```python
# @name Random rotate
# @author You
# @description Rotates every transform by a random angle.
```

## 8. Tips

* **Tab** completes names; **Ctrl+Space** opens the list anywhere. Inside `set_variation('…')`,
  `variations['…']` and `params['…']` the list holds the valid names.
* The *Context* tab follows the cursor: type `gradient.` to see the palette methods, or put the cursor
  inside a call to see its arguments.
* `seed(42)` makes a random script repeat exactly.
* Errors show the line; click one in the output panel to jump there.
* `snapshot()` / `restore()` try things out inside a script; *Revert flame* undoes a whole run.
* Apophysis users: `Transform`, `AddTransform`, `Rotate`, `Scale`, `Translate`, `Multiply`, `RotateFlame`,
  `UpdateFlame`, `Print`, `ShowMessage`, `Random` work as you expect. Scripts are Python, not Pascal:
  `:=` becomes `=`, blocks are indented, and `Transform.Linear` becomes `transform.variations['linear']`.
"""

__all__ = ["Entry", "Param", "TypeDoc", "Option", "TYPES", "GLOBALS", "CATEGORIES", "GUIDE", "options", "VARIATIONS", "PARAMS",
           "CURVE_CHANNELS", "FLAME_FILES", "XFORM_FIELDS"]

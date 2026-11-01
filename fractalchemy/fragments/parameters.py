"""The parameters a fragment declares with annotated uniforms — FragM's `GuiParameter` family and its value text.

    uniform float Power; slider[1,8,16] Logarithmic Locked      → FloatParameter(from=1, default=8, to=16)
    uniform vec3 Eye; slider[(-50,-50,-50),(0,0,-10),(50,50,50)] → Float3Parameter
    uniform vec3 BaseColor; color[1,1,1]                         → ColorParameter
    uniform vec4 Glow; color[0,0.2,1, 1,1,1]                     → FloatColorParameter (value range + colour)
    uniform int Iterations; slider[1,12,100]  ·  menu[2, A;B;C]  ·  uniform bool Julia; checkbox[false]
    uniform sampler2D tex; file[texture.jpg]                     → SamplerParameter (always locked)

Values are plain Python: `float`, `int`, `bool`, tuples of floats (vectors, colours; a float colour is
`(r, g, b, value)` — the order FragM writes and uploads), or a string for samplers (`"file.png"` or
`"file.exr R;G;B;A"`). The settings text is FragM's `name = value[,value…][ Logarithmic][ LockType]`: what presets
hold, what `F2` copies, what `.fragparams` files contain. Floats are written with 9 significant digits (18 for
`double` types), and a locked value is substituted into the shader as `#define` or `const` (FragM's two options).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

FDEC = 9      # significant digits for floats (FragM's FDEC)
DDEC = 18     # and for doubles (DDEC)
NUMBER = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
LOCK_SUFFIX = re.compile(r"(AlwaysLocked|Locked|NotLocked|NotLockable)\s*.?$")
SLIDER_SUFFIX = re.compile(r"(Logarithmic)\s*.?$")


class LockType(Enum):
    """Whether a parameter is baked into the shader (`Locked`) or stays a uniform."""
    NOT_LOCKED = "NotLocked"
    LOCKED = "Locked"
    NOT_LOCKABLE = "NotLockable"
    ALWAYS_LOCKED = "AlwaysLocked"

    @classmethod
    def from_text(cls, text: str) -> "LockType":
        """Parse FragM's spelling (case-insensitive; empty = NotLocked; unknown = NotLocked with a warning upstream)."""
        lowered = text.strip().lower()
        for member in cls:
            if member.value.lower() == lowered:
                return member
        return cls.NOT_LOCKED

    @property
    def locked(self) -> bool:
        """True when the value is substituted into the source."""
        return self in (LockType.LOCKED, LockType.ALWAYS_LOCKED)


class SliderType(Enum):
    """Linear or logarithmic slider mapping."""
    LINEAR = ""
    LOGARITHMIC = "Logarithmic"

    @classmethod
    def from_text(cls, text: str) -> "SliderType":
        return cls.LOGARITHMIC if text.strip().lower() == "logarithmic" else cls.LINEAR


@dataclass
class GuiParameter:
    """A parameter declared by an annotated uniform.

    Attributes:
        name: The uniform's name.
        glsl_type: The declared type (`float`, `dvec3`, `int`, `bool`, `sampler2D`, …).
        group: The `#group` it appeared in (`""` → the `Default` tab).
        tooltip: The comment line right above the declaration.
        default: The annotation's default value.
        lock: The lock type the annotation asked for (the default the settings text is measured against).
        slider: Linear / logarithmic (the default for the settings text).
        line: Index of the declaration in the preprocessed source (for *Select source* and bound edits).
    """
    name: str
    glsl_type: str
    group: str = ""
    tooltip: str = ""
    default: Any = None
    lock: LockType = LockType.NOT_LOCKED
    slider: SliderType = SliderType.LINEAR
    line: int = -1

    kind = "parameter"

    @property
    def is_double(self) -> bool:
        """`double` / `dvec*` types: 18 significant digits, uploaded as doubles."""
        return self.glsl_type.startswith("d")

    @property
    def components(self) -> int:
        """How many numbers the value carries (1 for scalars, booleans and samplers)."""
        return 1

    @property
    def unique_name(self) -> str:
        """FragM's identity of a widget across rebuilds: the group, name and range (a changed range is a new widget)."""
        return f"{self.group}:{self.name}:{self.default}"

    @property
    def precision(self) -> int:
        return DDEC if self.is_double else FDEC

    def clamp(self, value: Any) -> tuple[Any, bool]:
        """`(value within the parameter's range, whether it had to be clamped)`; scalar kinds accept any value."""
        return value, False

    def random_value(self, rng) -> Any | None:
        """A value drawn uniformly from the parameter's range (None for kinds that have none, e.g. textures)."""
        from_, to = getattr(self, "from_", None), getattr(self, "to", None)
        if self.kind == "bool":
            return bool(rng.random() < 0.5)
        if self.kind == "menu":
            return int(rng.integers(0, max(1, len(getattr(self, "texts", ()) or (0,)))))
        if self.kind == "color":
            return tuple(float(v) for v in rng.random(3))
        if self.kind == "floatcolor":
            return (*(float(v) for v in rng.random(3)), float(rng.uniform(from_, to)))
        if from_ is None or to is None:
            return None
        if isinstance(from_, (tuple, list)):
            value = tuple(float(rng.uniform(lo, hi)) if hi > lo else float(lo) for lo, hi in zip(from_, to))
            return value
        if self.kind == "int":
            return int(rng.integers(int(from_), int(to) + 1))
        return float(rng.uniform(from_, to)) if to > from_ else float(from_)

    def parse(self, text: str) -> Any:
        """A value from settings text (the part after `=`, suffixes removed)."""
        raise NotImplementedError

    def format(self, value: Any) -> str:
        """The value as settings text."""
        raise NotImplementedError

    def glsl_literal(self, value: Any) -> str:
        """The value as a GLSL expression of `glsl_type` (for locked substitution)."""
        raise NotImplementedError


def format_number(value: float, precision: int = FDEC) -> str:
    """FragM's `QString::number(v, 'g', precision)`: shortest form with `precision` significant digits."""
    text = f"{float(value):.{precision}g}"
    return text if text not in ("-0",) else "0"


def glsl_float(value: float, precision: int = FDEC) -> str:
    """A float literal GLSL accepts (a `.0` is added when the text has neither a dot nor an exponent)."""
    text = format_number(value, precision)
    return text if ("." in text or "e" in text or "inf" in text or "nan" in text) else text + ".0"


def parse_numbers(text: str, count: int) -> list[float]:
    """The first `count` numbers in `text` (FragM's MiniParser: missing numbers read as 0)."""
    found = [float(m) for m in NUMBER.findall(text)]
    return (found + [0.0] * count)[:count]


@dataclass
class FloatParameter(GuiParameter):
    """`slider[from, default, to]` on a `float` / `double`."""
    from_: float = 0.0
    to: float = 1.0
    kind = "float"

    @property
    def unique_name(self) -> str:
        return f"{self.group}:{self.name}:{self.from_}:{self.default}:{self.to}"

    def clamp(self, value):
        low, high = min(self.from_, self.to), max(self.from_, self.to)
        clamped = min(max(float(value), low), high)
        return clamped, clamped != float(value)

    def parse(self, text):
        return parse_numbers(text, 1)[0]

    def format(self, value):
        return format_number(value, self.precision)

    def glsl_literal(self, value):
        literal = glsl_float(value, self.precision)
        return literal if not self.is_double else f"double({literal})"


@dataclass
class VectorParameter(GuiParameter):
    """`slider[(…),(…),(…)]` on a `vec2` / `vec3` / `vec4` (and the `d` variants).

    Attributes:
        from_, to: Per-component bounds.
        normalize: FragM's rule: a `vec3` / `vec4` whose bounds are equal is a unit direction, edited by
            renormalising (except one named `Up`, which the camera path animation needs raw).
    """
    from_: tuple[float, ...] = ()
    to: tuple[float, ...] = ()
    normalize: bool = False
    kind = "vector"

    @property
    def components(self) -> int:
        return int(self.glsl_type[-1])

    @property
    def unique_name(self) -> str:
        return f"{self.group}:{self.name}:{list(self.from_)}:{list(self.default)}:{list(self.to)}"

    def clamp(self, value):
        if self.normalize:
            return tuple(float(v) for v in value), False
        out, clamped = [], False
        for v, low, high in zip(value, self.from_, self.to):
            c = min(max(float(v), min(low, high)), max(low, high))
            clamped |= c != float(v)
            out.append(c)
        return tuple(out), clamped

    def parse(self, text):
        return tuple(parse_numbers(text, self.components))

    def format(self, value):
        return ",".join(format_number(v, self.precision) for v in value)

    def glsl_literal(self, value):
        return f"{self.glsl_type}({','.join(glsl_float(v, self.precision) for v in value)})"


@dataclass
class ColorParameter(GuiParameter):
    """`color[r,g,b]` on a `vec3`: a colour chooser."""
    kind = "color"

    @property
    def components(self) -> int:
        return 3

    def clamp(self, value):
        out = tuple(min(max(float(v), 0.0), 1.0) for v in value)
        return out, out != tuple(float(v) for v in value)

    def parse(self, text):
        return tuple(parse_numbers(text, 3))

    def format(self, value):
        return ",".join(format_number(v, self.precision) for v in value)

    def glsl_literal(self, value):
        return f"{self.glsl_type}({','.join(glsl_float(v, self.precision) for v in value)})"


@dataclass
class FloatColorParameter(GuiParameter):
    """`color[min, default, max, r, g, b]` on a `vec4`: a value slider plus a colour, uploaded as `(r, g, b, value)`."""
    from_: float = 0.0
    to: float = 1.0
    kind = "floatcolor"

    @property
    def components(self) -> int:
        return 4

    @property
    def unique_name(self) -> str:
        return f"{self.group}:{self.name}:{self.from_}:{self.default}:{self.to}"

    def clamp(self, value):
        r, g, b, v = (float(x) for x in value)
        low, high = min(self.from_, self.to), max(self.from_, self.to)
        out = (min(max(r, 0.0), 1.0), min(max(g, 0.0), 1.0), min(max(b, 0.0), 1.0), min(max(v, low), high))
        return out, out != (r, g, b, v)

    def parse(self, text):
        return tuple(parse_numbers(text, 4))

    def format(self, value):
        return ",".join(format_number(v, self.precision) for v in value)

    def glsl_literal(self, value):
        return f"{self.glsl_type}({','.join(glsl_float(v, self.precision) for v in value)})"


@dataclass
class IntParameter(GuiParameter):
    """`slider[from, default, to]` on an `int`."""
    from_: int = 0
    to: int = 1
    kind = "int"

    @property
    def unique_name(self) -> str:
        return f"{self.group}:{self.name}:{self.from_}:{self.default}:{self.to}"

    def clamp(self, value):
        clamped = min(max(int(round(float(value))), min(self.from_, self.to)), max(self.from_, self.to))
        return clamped, clamped != int(round(float(value)))

    def parse(self, text):
        return int(round(parse_numbers(text, 1)[0]))

    def format(self, value):
        return str(int(value))

    def glsl_literal(self, value):
        return str(int(value))


@dataclass
class IntMenuParameter(GuiParameter):
    """`menu[default, text;text;…]` on an `int`: a combo box whose index is the value."""
    texts: tuple[str, ...] = ()
    kind = "menu"

    @property
    def unique_name(self) -> str:
        return f"{self.group}:{self.name}:{self.default}:{''.join(self.texts)}"

    def clamp(self, value):
        clamped = min(max(int(round(float(value))), 0), max(0, len(self.texts) - 1))
        return clamped, clamped != int(round(float(value)))

    def parse(self, text):
        return int(round(parse_numbers(text, 1)[0]))

    def format(self, value):
        return str(int(value))

    def glsl_literal(self, value):
        return str(int(value))


@dataclass
class BoolParameter(GuiParameter):
    """`checkbox[true|false]` on a `bool`."""
    kind = "bool"

    def parse(self, text):
        return text.strip().lower() == "true"

    def format(self, value):
        return "true" if value else "false"

    def glsl_literal(self, value):
        return "true" if value else "false"


@dataclass
class SamplerParameter(GuiParameter):
    """`file[name]` / `file[name, channels]` on a sampler: a texture file (always locked — the file is baked in).

    Attributes:
        channels: EXR channel selection (`"R;G;B;A"`), empty for other images.
    """
    channels: str = ""
    kind = "sampler"

    @property
    def unique_name(self) -> str:
        return f"{self.group}:{self.name}:{self.default}:{self.channels}"

    def parse(self, text):
        return text.strip()

    def format(self, value):
        return str(value)

    def glsl_literal(self, value):
        return ""    # samplers are never substituted; they stay uniforms bound to texture units

    @staticmethod
    def split_value(value: str) -> tuple[str, str]:
        """`"file.exr R;G;B;A"` → `("file.exr", "R;G;B;A")`; `"file.png"` → `("file.png", "")`."""
        parts = str(value).strip().split(None, 1)
        return (parts[0], parts[1].strip()) if len(parts) == 2 else ((parts[0] if parts else ""), "")


# --- settings text ------------------------------------------------------------------------------------------------------
@dataclass
class SettingsLine:
    """One parsed `name = value…` line of settings text."""
    name: str
    value_text: str
    lock: LockType | None = None        # None: the line carried no lock suffix (the lock is left as it is)
    slider: SliderType = SliderType.LINEAR   # Linear unless the line says Logarithmic (FragM's rule)


@dataclass
class ParsedSettings:
    """The outcome of `parse_settings`: assignments, easing-curve lines and what could not be read."""
    lines: list[SettingsLine] = field(default_factory=list)
    easing: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def settings_line(param: GuiParameter, value: Any, lock: LockType, slider: SliderType) -> str:
    """FragM's `toSettingsString`: the value, then the slider type and lock type when they differ from the annotation's."""
    suffix = ""
    if slider != param.slider:
        suffix += f" {slider.value}" if slider.value else ""
    if lock != param.lock:
        suffix += f" {lock.value}"
    return f"{param.name} = {param.format(value)}{suffix}"


def is_easing_line(text: str) -> bool:
    """An easing-curve setting has 12 colon-separated fields (`name:type:n:start:end:first:last:period:amp:over:loops:pong`)."""
    return text.count(":") == 11


def parse_settings(text: str) -> ParsedSettings:
    """Read settings text (`setSettings`): `#` and `//` lines are skipped, easing lines collected, the rest split at `=`."""
    parsed = ParsedSettings()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if is_easing_line(line):
            parsed.easing.append(line)
            continue
        if line.startswith("//"):
            continue
        if line.count("=") != 1:
            parsed.warnings.append(f"Expected a key value pair, found: {line}")
            continue
        name, value = (part.strip() for part in line.split("="))
        parsed.lines.append(_split_suffixes(name, value))
    return parsed


def _split_suffixes(name: str, value: str) -> SettingsLine:
    """Peel the `LockType` and `Logarithmic` suffixes off a value (FragM's `fromSettingsString`)."""
    lock = None
    match = LOCK_SUFFIX.search(value)
    if match:
        lock = LockType.from_text(match.group(1))
        value = value[:match.start()] + value[match.end():]
    match = SLIDER_SUFFIX.search(value)
    if match:
        value = value[:match.start()] + value[match.end():]
    slider = SliderType.LOGARITHMIC if match else SliderType.LINEAR   # FragM resets to Linear when the suffix is absent
    return SettingsLine(name, value.strip(), lock, slider)


def locked_substitution(param: GuiParameter, value: Any, use_defines: bool = True) -> str | None:
    """The source line replacing `uniform T name;` for a locked parameter: `#define name literal` or `const T name = literal;`."""
    literal = param.glsl_literal(value)
    if not literal:
        return None
    if use_defines:
        return f"#define {param.name} {literal}"
    return f"const {param.glsl_type} {param.name} = {literal};"


__all__ = ["FDEC", "DDEC", "LockType", "SliderType", "GuiParameter", "FloatParameter", "VectorParameter", "ColorParameter",
           "FloatColorParameter", "IntParameter", "IntMenuParameter", "BoolParameter", "SamplerParameter", "SettingsLine",
           "ParsedSettings", "settings_line", "parse_settings", "is_easing_line", "locked_substitution", "format_number",
           "glsl_float", "parse_numbers"]

"""The 2D and 3D camera controls as pure maths — FragM's `CameraControl.cpp` without the widgets.

The 3D camera is the fragment's `Eye`, `Target`, `Up` and `FOV` uniforms (the `3D.frag` convention); the 2D camera
its `Center` and `Zoom` (plus the optional rotate / stretch transform of `Progressive2D.frag`). Every operation here
takes the current values and an input (a key, a mouse drag in normalised window coordinates, wheel notches) and
returns new values; the viewport writes them back into the parameter state. Constants and formulas are FragM's:
the step size (`1` / `3` / `2` halve / double / ×10, `5` resets, clamped to [1e-5, 10]), the mouse speed
`step · (fov + 0.5)`, rotations of `−Δ · speed · 100` degrees about the up and right vectors, the 2D wheel factor
1.15 in *fixed* (about the cursor) and *traveling* (centre to the cursor) modes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

import numpy as np

Vec = np.ndarray
STEP_MIN, STEP_MAX = 1.0e-5, 10.0
STEP_3D_DEFAULT, STEP_2D_DEFAULT = 0.1, 1.0
ROLL_DEGREES = 2.0               # Q / E
WHEEL_2D_FACTOR = 1.15


def vec(*values) -> Vec:
    return np.array(values if len(values) > 1 else values[0], dtype=float)


def normalize(v: Vec) -> Vec:
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v


def rotate(v: Vec, degrees: float, axis: Vec) -> Vec:
    """`glm::rotate(identity, radians(degrees), axis) * v` (Rodrigues' rotation about a normalised axis)."""
    axis = normalize(axis)
    angle = math.radians(degrees)
    c, s = math.cos(angle), math.sin(angle)
    return v * c + np.cross(axis, v) * s + axis * float(np.dot(axis, v)) * (1.0 - c)


def step_after_key(step: float, key: str, default: float) -> float:
    """FragM's step-size keys: `1` halves, `3` doubles, `2` ×10, `x` ÷10 (2D), `5` resets; clamped."""
    factors = {"1": 0.5, "3": 2.0, "2": 10.0, "x": 0.1}
    if key == "5":
        return default
    return clamp_step(step * factors.get(key, 1.0))


def clamp_step(step: float) -> float:
    return min(max(step, STEP_MIN), STEP_MAX)


# --- 3D -----------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Camera3D:
    """`Eye`, `Target`, `Up` (as tuples) and `FOV`."""
    eye: tuple[float, float, float] = (0.0, 0.0, -10.0)
    target: tuple[float, float, float] = (0.0, 0.0, 0.0)
    up: tuple[float, float, float] = (0.0, 1.0, 0.0)
    fov: float = 0.4

    @property
    def direction(self) -> Vec:
        return vec(self.target) - vec(self.eye)

    @property
    def dir(self) -> Vec:
        return normalize(self.direction)

    @property
    def right(self) -> Vec:
        return normalize(np.cross(self.dir, vec(self.up)))

    def orthogonalized(self) -> "Camera3D":
        """`Up` with its component along the view direction removed (FragM orthogonalises after every move)."""
        up = vec(self.up)
        fixed = up - float(np.dot(up, self.dir)) * self.dir
        return replace(self, up=tuple(fixed))

    def moved(self, offset: Vec) -> "Camera3D":
        return replace(self, eye=tuple(vec(self.eye) + offset), target=tuple(vec(self.target) + offset))

    def turned(self, degrees: float, axis: Vec) -> "Camera3D":
        """Rotate the view direction and the up vector about `axis` through the eye (T / G / Y / H / Q / E)."""
        return replace(self, target=tuple(rotate(self.direction, degrees, axis) + vec(self.eye)),
                       up=tuple(rotate(vec(self.up), degrees, axis)))

    # --- keys ---------------------------------------------------------------------------------------------------------
    def key(self, key: str, step: float, fov_down: float | None = None) -> "Camera3D | None":
        """One key's effect (`w a s d r f t g y h q e`, `~`), or None when the key is not a camera key.

        Args:
            key: Lower-case key text.
            step: The current step size.
            fov_down: The FOV used for the rotation sensitivity (`fovDown · 5` degrees; FragM samples it on press).
        """
        sensitivity = (self.fov if fov_down is None else fov_down) * 5.0
        moves = {"a": -self.right, "d": self.right, "w": self.dir, "s": -self.dir, "r": -vec(self.up), "f": vec(self.up)}
        turns = {"y": (sensitivity, vec(self.up)), "h": (-sensitivity, vec(self.up)), "t": (sensitivity, self.right),
                 "g": (-sensitivity, self.right), "e": (ROLL_DEGREES, self.dir), "q": (-ROLL_DEGREES, self.dir)}
        if key in moves:
            return self.moved(moves[key] * step).orthogonalized()
        if key in turns:
            return self.turned(*turns[key]).orthogonalized()
        if key == "~":
            return replace(self, target=tuple(-vec(self.eye))).orthogonalized()
        return None

    # --- mouse ---------------------------------------------------------------------------------------------------------
    def drag(self, kind: str, down: "Camera3D", dp: tuple[float, float], step: float) -> "Camera3D":
        """The camera after a drag of `dp` (press position − current, in window fractions) from the state at press.

        Args:
            kind: `orient` (left), `orbit_origin` (Shift+left), `orbit_target` (Shift+Alt+left), `pan` (right),
                `dolly` (left + right).
            down: The camera when the button went down (`eyeDown`, `targetDown`, `upDown`, `fovDown`).
            dp: `(mouse_down − mouse) / (width, height)`.
            step: The step size.
        """
        dx, dy = dp
        speed = step * (down.fov + 0.5)
        direction_down = down.direction
        up_down = vec(down.up)
        right_down = np.cross(normalize(direction_down), up_down)
        if kind == "pan":
            offset = -up_down * (dy * 10.0) * speed + right_down * (dx * 10.0) * speed
            return replace(self, eye=tuple(vec(down.eye) + offset), target=tuple(vec(down.target) + offset))
        if kind == "dolly":
            eye = vec(down.eye) - direction_down * dx * speed
            return replace(self, eye=tuple(eye), target=tuple(direction_down + eye))

        def rot(v: Vec) -> Vec:     # my * mx * v
            return rotate(rotate(v, -dx * speed * 100.0, up_down), -dy * speed * 100.0, normalize(right_down))

        if kind == "orbit_origin":
            eye = rot(vec(down.eye))
            return replace(self, eye=tuple(eye), target=tuple(rot(direction_down) + eye), up=tuple(rot(up_down)))
        if kind == "orbit_target":
            return replace(self, eye=tuple(vec(down.target) - rot(direction_down)), up=tuple(rot(up_down)))
        # orient
        return replace(self, target=tuple(rot(normalize(direction_down)) + vec(self.eye)), up=tuple(rot(up_down)))

    def wheel(self, notches: float, step: float) -> "Camera3D":
        """Dolly along the view direction by `step · notches / fov`."""
        return self.moved(self.dir * step * notches / max(self.fov, 1e-9))

    def screen_to_3d(self, sx: float, sy: float, width: int, height: int, depth_inverse: float) -> Vec:
        """The world point under pixel `(sx, sy)` at depth `1 / depth_inverse` (FragM's `screenTo3D`; the depth buffer holds
        `1 / distance` for the raytracers)."""
        coord_x = sx / height * 2.0 - width / height
        coord_y = (height - sy) / height * 2.0 - 1.0
        d = self.dir
        up = normalize(vec(self.up) - float(np.dot(vec(self.up), d)) * d)
        right = normalize(np.cross(d, up))
        ray = (coord_x * right + coord_y * up) * self.fov + d
        return vec(self.eye) + ray / depth_inverse if depth_inverse else vec(self.eye)

    def projection_view(self, aspect: float, near: float = 1e-5, far: float = 1000.0) -> np.ndarray:
        """`perspective(2·atan(fov), aspect) · lookAt(eye, target, up)` — for drawing the camera paths over the image."""
        f = 1.0 / math.tan(math.atan2(1.0, 1.0 / max(self.fov, 1e-9)))
        proj = np.zeros((4, 4))
        proj[0, 0], proj[1, 1] = f / aspect, f
        proj[2, 2], proj[2, 3] = (far + near) / (near - far), 2 * far * near / (near - far)
        proj[3, 2] = -1.0
        d = self.dir
        s = normalize(np.cross(d, vec(self.up)))
        u = np.cross(s, d)
        view = np.eye(4)
        view[0, :3], view[1, :3], view[2, :3] = s, u, -d
        view[:3, 3] = (-float(np.dot(s, vec(self.eye))), -float(np.dot(u, vec(self.eye))), float(np.dot(d, vec(self.eye))))
        return proj @ view


# --- 2D -----------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Camera2D:
    """`Center`, `Zoom` and the optional rotate / stretch transform (`EnableTransform`, `RotateAngle`, `StretchAngle`,
    `StretchAmount`)."""
    center: tuple[float, float] = (0.0, 0.0)
    zoom: float = 1.0
    enable_transform: bool = False
    rotate_angle: float = 0.0
    stretch_angle: float = 0.0
    stretch_amount: float = 0.0

    def transform(self) -> np.ndarray:
        """The 2×2 matrix `Progressive2D.frag` applies (identity unless the transform is enabled)."""
        if not self.enable_transform:
            return np.eye(2)
        b, a = math.radians(self.rotate_angle), math.radians(self.stretch_angle)
        bc, bs, ac, as_ = math.cos(b), math.sin(b), math.cos(a), math.sin(a)
        s = math.sqrt(2.0 ** self.stretch_amount)
        m1 = np.array([[ac, -as_], [as_, ac]])     # glm column-major mat2(ac, as, -as, ac)
        m2 = np.array([[s, 0.0], [0.0, 1.0 / s]])
        m3 = np.array([[ac, as_], [-as_, ac]])
        m4 = np.array([[bc, -bs], [bs, bc]])
        return m1 @ m2 @ m3 @ m4

    def key(self, key: str, step: float) -> "Camera2D | None":
        """`a d w s` pan by `0.1 / zoom` (through the transform), `q e` zoom by `1.05^step`; None otherwise."""
        factor = 1.05 ** step
        z = 0.1 / self.zoom
        pans = {"a": (-z, 0.0), "d": (z, 0.0), "w": (0.0, z), "s": (0.0, -z)}
        if key in pans:
            delta = self.transform() @ vec(pans[key])
            return replace(self, center=tuple(vec(self.center) + delta))
        if key == "q":
            return replace(self, zoom=self.zoom * factor)
        if key == "e":
            return replace(self, zoom=self.zoom / factor)
        return None

    def drag(self, kind: str, down: "Camera2D", mouse_down: tuple[float, float], mouse: tuple[float, float],
             width: int, height: int) -> "Camera2D":
        """`pan` (left) or `zoom` (right: about the press point); positions in pixels, state `down` from the press."""
        p0 = vec(mouse_down[0] / (0.5 * width) - 1.0, 1.0 - mouse_down[1] / (0.5 * height))
        p1 = vec(mouse[0] / (0.5 * width) - 1.0, 1.0 - mouse[1] / (0.5 * height))
        dp = self.transform() @ (p0 - p1)
        if kind == "pan":
            return replace(self, center=tuple(vec(down.center) + dp / down.zoom))
        model = self._model_coord(p0, vec(down.center), down.zoom, width, height)
        new_zoom = down.zoom + dp[1] * down.zoom
        if new_zoom <= 0:
            return self
        ratio = new_zoom / down.zoom
        return replace(self, center=tuple(model - (model - vec(down.center)) / ratio), zoom=new_zoom)

    @staticmethod
    def _model_coord(mouse: Vec, center: Vec, zoom: float, width: int, height: int) -> Vec:
        coord = mouse / zoom + center
        return vec(coord[0] * height / width, coord[1])

    def wheel(self, notches: float, mouse: tuple[float, float], width: int, height: int, traveling: bool = False) -> "Camera2D":
        """Zoom by 1.15 per notch: *fixed* keeps the point under the cursor still; *traveling* moves the centre to it."""
        g = WHEEL_2D_FACTOR if notches > 0 else 1.0 / WHEEL_2D_FACTOR
        if traveling:
            pos = vec(mouse[0] / width - 0.5, 0.5 - mouse[1] / height)
            model = self.transform() @ pos / self.zoom + vec(self.center)
            return replace(self, center=tuple(model), zoom=self.zoom * g)
        u = (mouse[0] / width - 0.5) * 2.0 * width / height
        v = (mouse[1] / height - 0.5) * 2.0
        pos = self.transform() @ vec(-u, v)
        center = vec(self.center) + pos / (self.zoom * g) * (1.0 - g)
        return replace(self, center=tuple(center), zoom=self.zoom * g)


__all__ = ["Camera2D", "Camera3D", "rotate", "normalize", "vec", "step_after_key", "clamp_step", "STEP_2D_DEFAULT",
           "STEP_3D_DEFAULT", "STEP_MIN", "STEP_MAX"]

"""The 3D camera projection (Apophysis `ControlPoint.Project*`), for numpy and GLSL.

After the final transform a point `(x, y, z)` is rotated by the camera's pitch / yaw (/ pitch_y),
optionally blurred by depth of field, and divided by `1 − perspective · z'` before the
flat 2D camera maps it to pixels. A camera with no 3D settings is the identity, so
2D flames pay nothing.
"""

from __future__ import annotations

import numpy as np

from ..fractal.scene import Camera

DOF_SCALE = 0.1   # Apophysis: DofCoef = 0.1 * cam_dof


def project(camera: Camera, x: np.ndarray, y: np.ndarray, z: np.ndarray, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Project to the flat camera plane; returns (x', y')."""
    if not camera.is_3d():
        return x, y
    m = camera.matrix()
    zz = z - camera.zpos
    px = m[0][0] * x + m[1][0] * y + m[2][0] * zz
    py = m[0][1] * x + m[1][1] * y + m[2][1] * zz
    pz = m[0][2] * x + m[1][2] * y + m[2][2] * zz
    zr = 1.0 - camera.perspective * pz
    if camera.dof:
        t = rng.random(x.shape[0]) * 2.0 * np.pi
        dr = rng.random(x.shape[0]) * DOF_SCALE * camera.dof * pz
        px = px + dr * np.cos(t)
        py = py + dr * np.sin(t)
    with np.errstate(divide="ignore", invalid="ignore"):
        return px / zr, py / zr


GLSL_PROJECT = """
uniform mat3 u_cam_m;       // camera matrix, u_cam_m[i][j] as in Camera.matrix()
uniform vec3 u_cam_3d;      // (perspective, zpos, dof coefficient)
uniform bool u_cam_is3d;
vec2 project3d(vec3 p, inout uint s) {
    if (!u_cam_is3d) return p.xy;
    float zz = p.z - u_cam_3d.y;
    float px = u_cam_m[0][0] * p.x + u_cam_m[1][0] * p.y + u_cam_m[2][0] * zz;
    float py = u_cam_m[0][1] * p.x + u_cam_m[1][1] * p.y + u_cam_m[2][1] * zz;
    float pz = u_cam_m[0][2] * p.x + u_cam_m[1][2] * p.y + u_cam_m[2][2] * zz;
    float zr = 1.0 - u_cam_3d.x * pz;
    if (u_cam_3d.z != 0.0) {
        float t = rnd(s) * 2.0 * PI;
        float dr = rnd(s) * u_cam_3d.z * pz;
        px += dr * cos(t); py += dr * sin(t);
    }
    return vec2(px, py) / zr;
}
"""


def glsl_uniforms(camera: Camera) -> dict[str, object]:
    """Values for the uniforms declared in `GLSL_PROJECT`."""
    m = camera.matrix()
    return {
        "u_cam_m": tuple(float(m[i][j]) for i in range(3) for j in range(3)),   # column-major: mat3[i] = row i of matrix()
        "u_cam_3d": (float(camera.perspective), float(camera.zpos), float(DOF_SCALE * camera.dof)),
        "u_cam_is3d": bool(camera.is_3d()),
    }

"""The flam3 classics and Apophysis 7X built-in variations, written natively (numpy + GLSL).

Every entry is defined once for both engines. Apophysis built-ins add `w·z` to the depth
(`z=Z_PASS`), exactly as `XForm.pas` does; the few with their own depth formula say so.
"""

from __future__ import annotations

import math

import numpy as np

from ...fractal.variations import EPS, PI, POST, PRE, Z_FORMULA, Z_PASS, Point, variation

# ---------------------------------------------------------------------------
# Classic flam3 variations 0..
# ---------------------------------------------------------------------------
@variation("linear", "v += w * t;", aliases=("linear3D",), z=Z_PASS, origin="flam3 / Apophysis built-in")
def _linear(p: Point):
    return p.w * p.x, p.w * p.y


@variation("sinusoidal", "v += w * sin(t);", z=Z_PASS)
def _sinusoidal(p: Point):
    return p.w * np.sin(p.x), p.w * np.sin(p.y)


@variation("spherical", "v += w / (r2 + EPS) * t;", z=Z_PASS)
def _spherical(p: Point):
    k = p.w / (p.r2 + EPS)
    return k * p.x, k * p.y


@variation("swirl", """
    float sr = sin(r2), cr = cos(r2);
    v += w * vec2(sr * t.x - cr * t.y, cr * t.x + sr * t.y);""", z=Z_PASS)
def _swirl(p: Point):
    sr, cr = np.sin(p.r2), np.cos(p.r2)
    return p.w * (sr * p.x - cr * p.y), p.w * (cr * p.x + sr * p.y)


@variation("horseshoe", "v += w / (r + EPS) * vec2((t.x - t.y) * (t.x + t.y), 2.0 * t.x * t.y);", z=Z_PASS)
def _horseshoe(p: Point):
    k = p.w / (p.r + EPS)
    return k * (p.x - p.y) * (p.x + p.y), k * 2.0 * p.x * p.y


@variation("polar", "v += w * vec2(theta / PI, r - 1.0);", z=Z_PASS)
def _polar(p: Point):
    return p.w * p.theta / PI, p.w * (p.r - 1.0)


@variation("handkerchief", "v += w * r * vec2(sin(theta + r), cos(theta - r));")
def _handkerchief(p: Point):
    return p.w * p.r * np.sin(p.theta + p.r), p.w * p.r * np.cos(p.theta - p.r)


@variation("heart", "{ float a = theta * r; v += w * r * vec2(sin(a), -cos(a)); }")
def _heart(p: Point):
    a = p.theta * p.r
    return p.w * p.r * np.sin(a), -p.w * p.r * np.cos(a)


@variation("disc", "{ float a = theta / PI, pr = PI * r; v += w * a * vec2(sin(pr), cos(pr)); }", z=Z_PASS)
def _disc(p: Point):
    a, pr = p.theta / PI, PI * p.r
    return p.w * a * np.sin(pr), p.w * a * np.cos(pr)


@variation("spiral", "v += w / (r + EPS) * vec2(cos(theta) + sin(r), sin(theta) - cos(r));", z=Z_PASS)
def _spiral(p: Point):
    k = p.w / (p.r + EPS)
    return k * (np.cos(p.theta) + np.sin(p.r)), k * (np.sin(p.theta) - np.cos(p.r))


@variation("hyperbolic", "v += w * vec2(sin(theta) / (r + EPS), cos(theta) * r);", z=Z_PASS)
def _hyperbolic(p: Point):
    return p.w * np.sin(p.theta) / (p.r + EPS), p.w * np.cos(p.theta) * p.r


@variation("diamond", "v += w * vec2(sin(theta) * cos(r), cos(theta) * sin(r));", z=Z_PASS)
def _diamond(p: Point):
    return p.w * np.sin(p.theta) * np.cos(p.r), p.w * np.cos(p.theta) * np.sin(p.r)


@variation("ex", """
    { float n0 = sin(theta + r), n1 = cos(theta - r);
      float m0 = n0 * n0 * n0 * r, m1 = n1 * n1 * n1 * r;
      v += w * vec2(m0 + m1, m0 - m1); }""")
def _ex(p: Point):
    n0, n1 = np.sin(p.theta + p.r), np.cos(p.theta - p.r)
    m0, m1 = n0 ** 3 * p.r, n1 ** 3 * p.r
    return p.w * (m0 + m1), p.w * (m0 - m1)


@variation("julia", "{ float a = 0.5 * theta + (rnd(s) < 0.5 ? 0.0 : PI); float sr = w * sqrt(r); v += sr * vec2(cos(a), sin(a)); }", random=True)
def _julia(p: Point):
    a = 0.5 * p.theta + np.where(p.rnd() < 0.5, 0.0, PI)
    sr = p.w * np.sqrt(p.r)
    return sr * np.cos(a), sr * np.sin(a)


@variation("bent", "v += w * vec2(t.x < 0.0 ? t.x * 2.0 : t.x, t.y < 0.0 ? t.y * 0.5 : t.y);")
def _bent(p: Point):
    return p.w * np.where(p.x < 0, p.x * 2.0, p.x), p.w * np.where(p.y < 0, p.y * 0.5, p.y)


@variation("waves", "v += w * vec2(t.x + c10 * sin(t.y / (c20 * c20 + EPS)), t.y + c11 * sin(t.x / (c21 * c21 + EPS)));", uses_affine=True)
def _waves(p: Point):
    a, b, c, d, e, f = p.coefs
    return p.w * (p.x + c * np.sin(p.y / (e * e + EPS))), p.w * (p.y + d * np.sin(p.x / (f * f + EPS)))


@variation("fisheye", "{ float k = 2.0 * w / (r + 1.0); v += k * vec2(t.y, t.x); }")
def _fisheye(p: Point):
    k = 2.0 * p.w / (p.r + 1.0)
    return k * p.y, k * p.x


@variation("popcorn", "v += w * vec2(t.x + c20 * sin(tan(3.0 * t.y)), t.y + c21 * sin(tan(3.0 * t.x)));", uses_affine=True)
def _popcorn(p: Point):
    a, b, c, d, e, f = p.coefs
    return p.w * (p.x + e * np.sin(np.tan(3.0 * p.y))), p.w * (p.y + f * np.sin(np.tan(3.0 * p.x)))


@variation("exponential", "{ float dx = w * exp(t.x - 1.0), dy = PI * t.y; v += dx * vec2(cos(dy), sin(dy)); }")
def _exponential(p: Point):
    dx, dy = p.w * np.exp(p.x - 1.0), PI * p.y
    return dx * np.cos(dy), dx * np.sin(dy)


@variation("power", "{ float k = w * pow(r + EPS, sin(theta)); v += k * vec2(cos(theta), sin(theta)); }")
def _power(p: Point):
    k = p.w * np.power(p.r + EPS, np.sin(p.theta))
    return k * np.cos(p.theta), k * np.sin(p.theta)


@variation("cosine", "{ float a = PI * t.x; v += w * vec2(cos(a) * cosh(t.y), -sin(a) * sinh(t.y)); }")
def _cosine(p: Point):
    a = PI * p.x
    return p.w * np.cos(a) * np.cosh(p.y), -p.w * np.sin(a) * np.sinh(p.y)


@variation("rings", """
    { float dx = c20 * c20 + EPS;
      float k = w * (mod(r + dx, 2.0 * dx) - dx + r * (1.0 - dx));
      v += k * vec2(cos(theta), sin(theta)); }""", uses_affine=True)
def _rings(p: Point):
    dx = p.coefs[4] ** 2 + EPS
    k = p.w * (np.mod(p.r + dx, 2.0 * dx) - dx + p.r * (1.0 - dx))
    return k * np.cos(p.theta), k * np.sin(p.theta)


@variation("fan", """
    { float dx = PI * (c20 * c20 + EPS), dx2 = dx * 0.5, dy = c21;
      float a = mod(theta + dy, dx) > dx2 ? theta - dx2 : theta + dx2;
      v += w * r * vec2(cos(a), sin(a)); }""", uses_affine=True)
def _fan(p: Point):
    dx = PI * (p.coefs[4] ** 2 + EPS)
    dx2, dy = dx * 0.5, p.coefs[5]
    a = np.where(np.mod(p.theta + dy, dx) > dx2, p.theta - dx2, p.theta + dx2)
    return p.w * p.r * np.cos(a), p.w * p.r * np.sin(a)


@variation("blob", """
    { float k = r * (P_blob_low + (P_blob_high - P_blob_low) * (0.5 + 0.5 * sin(P_blob_waves * theta)));
      v += w * k * vec2(sin(theta), cos(theta)); }""", {"low": 0.2, "high": 1.0, "waves": 2.0})
def _blob(p: Point):
    low, high, waves = p.p("blob_low"), p.p("blob_high"), p.p("blob_waves")
    k = p.r * (low + (high - low) * (0.5 + 0.5 * np.sin(waves * p.theta)))
    return p.w * k * np.sin(p.theta), p.w * k * np.cos(p.theta)


@variation("pdj", "v += w * vec2(sin(P_pdj_a * t.y) - cos(P_pdj_b * t.x), sin(P_pdj_c * t.x) - cos(P_pdj_d * t.y));",
           {"a": 0.0, "b": 0.0, "c": 0.0, "d": 0.0}, z=Z_PASS)
def _pdj(p: Point):
    a, b, c, d = p.p("pdj_a"), p.p("pdj_b"), p.p("pdj_c"), p.p("pdj_d")
    return p.w * (np.sin(a * p.y) - np.cos(b * p.x)), p.w * (np.sin(c * p.x) - np.cos(d * p.y))


@variation("fan2", """
    { float dy = P_fan2_y, dx = PI * (P_fan2_x * P_fan2_x + EPS), dx2 = dx * 0.5;
      float tt = theta + dy - dx * floor((theta + dy) / dx);
      float a = tt > dx2 ? theta - dx2 : theta + dx2;
      v += w * r * vec2(sin(a), cos(a)); }""", {"x": 0.0, "y": 0.0}, z=Z_PASS)
def _fan2(p: Point):
    dy, dx = p.p("fan2_y"), PI * (p.p("fan2_x") ** 2 + EPS)
    dx2 = dx * 0.5
    tt = p.theta + dy - dx * np.floor((p.theta + dy) / dx)
    a = np.where(tt > dx2, p.theta - dx2, p.theta + dx2)
    return p.w * p.r * np.sin(a), p.w * p.r * np.cos(a)


@variation("rings2", """
    { float dx = P_rings2_val * P_rings2_val + EPS;
      float rr = r + (-2.0 * dx * floor((r + dx) / (2.0 * dx)) + r * (1.0 - dx));
      v += w * rr * vec2(sin(theta), cos(theta)); }""", {"val": 0.0}, z=Z_PASS)
def _rings2(p: Point):
    dx = p.p("rings2_val") ** 2 + EPS
    rr = p.r + (-2.0 * dx * np.floor((p.r + dx) / (2.0 * dx)) + p.r * (1.0 - dx))
    return p.w * rr * np.sin(p.theta), p.w * rr * np.cos(p.theta)


@variation("eyefish", "v += 2.0 * w / (r + 1.0) * t;", z=Z_PASS)
def _eyefish(p: Point):
    k = 2.0 * p.w / (p.r + 1.0)
    return k * p.x, k * p.y


@variation("bubble", "{ float rr = r2 * 0.25 + 1.0; v += w / rr * t; vz += w * (2.0 / rr - 1.0); }", z=Z_FORMULA)
def _bubble(p: Point):
    rr = p.r2 * 0.25 + 1.0
    k = p.w / rr
    return k * p.x, k * p.y, p.w * (2.0 / rr - 1.0)


@variation("cylinder", "v += w * vec2(sin(t.x), t.y); vz += w * cos(t.x);", z=Z_FORMULA)
def _cylinder(p: Point):
    return p.w * np.sin(p.x), p.w * p.y, p.w * np.cos(p.x)


@variation("perspective", """
    { float k = 1.0 / (P_perspective_dist - t.y * sin(P_perspective_angle));
      v += w * P_perspective_dist * k * vec2(t.x, t.y * cos(P_perspective_angle)); }""", {"angle": 0.0, "dist": 1.0})
def _perspective(p: Point):
    angle, dist = p.p("perspective_angle"), p.p("perspective_dist")
    k = 1.0 / (dist - p.y * math.sin(angle))
    return p.w * dist * k * p.x, p.w * dist * k * p.y * math.cos(angle)


@variation("noise", "{ float a = rnd(s) * 2.0 * PI, k = w * rnd(s); v += k * vec2(t.x * cos(a), t.y * sin(a)); }", random=True, z=Z_PASS)
def _noise(p: Point):
    a, k = p.rnd() * 2.0 * PI, p.w * p.rnd()
    return k * p.x * np.cos(a), k * p.y * np.sin(a)


@variation("julian", """
    { float pw = P_julian_power; float n = floor(rnd(s) * abs(pw));
      float a = (phi + 2.0 * PI * n) / pw;
      float k = w * pow(r2 + EPS, P_julian_dist / pw * 0.5);
      v += k * vec2(cos(a), sin(a)); }""", {"power": 1.0, "dist": 1.0}, random=True, z=Z_PASS)
def _julian(p: Point):
    power, dist = p.p("julian_power"), p.p("julian_dist")
    n = np.floor(p.rnd() * abs(power))
    a = (p.phi + 2.0 * PI * n) / power
    k = p.w * np.power(p.r2 + EPS, dist / power * 0.5)
    return k * np.cos(a), k * np.sin(a)


@variation("juliascope", """
    { float pw = P_juliascope_power; float n = floor(rnd(s) * abs(pw));
      float sgn = mod(n, 2.0) == 0.0 ? 1.0 : -1.0;
      float a = (sgn * phi + 2.0 * PI * n) / pw;
      float k = w * pow(r2 + EPS, P_juliascope_dist / pw * 0.5);
      v += k * vec2(cos(a), sin(a)); }""", {"power": 1.0, "dist": 1.0}, random=True, z=Z_PASS)
def _juliascope(p: Point):
    power, dist = p.p("juliascope_power"), p.p("juliascope_dist")
    n = np.floor(p.rnd() * abs(power))
    sgn = np.where(np.mod(n, 2.0) == 0.0, 1.0, -1.0)
    a = (sgn * p.phi + 2.0 * PI * n) / power
    k = p.w * np.power(p.r2 + EPS, dist / power * 0.5)
    return k * np.cos(a), k * np.sin(a)


@variation("blur", "{ float a = rnd(s) * 2.0 * PI, k = w * rnd(s); v += k * vec2(cos(a), sin(a)); }", random=True, z=Z_PASS)
def _blur(p: Point):
    a, k = p.rnd() * 2.0 * PI, p.w * p.rnd()
    return k * np.cos(a), k * np.sin(a)


@variation("gaussian_blur", "{ float a = rnd(s) * 2.0 * PI, k = w * (rnd(s) + rnd(s) + rnd(s) + rnd(s) - 2.0); v += k * vec2(cos(a), sin(a)); }", random=True, z=Z_PASS)
def _gaussian_blur(p: Point):
    a = p.rnd() * 2.0 * PI
    k = p.w * (p.rnd() + p.rnd() + p.rnd() + p.rnd() - 2.0)
    return k * np.cos(a), k * np.sin(a)


@variation("radial_blur", """
    { float spin = sin(P_radial_blur_angle * PI * 0.5), zoom = cos(P_radial_blur_angle * PI * 0.5);
      float g = w * (rnd(s) + rnd(s) + rnd(s) + rnd(s) - 2.0);
      float a = phi + spin * g, rz = zoom * g - 1.0;
      v += vec2(r * cos(a) + rz * t.x, r * sin(a) + rz * t.y); }""", {"angle": 0.0}, random=True, z=Z_PASS)
def _radial_blur(p: Point):
    angle = p.p("radial_blur_angle")
    spin, zoom = math.sin(angle * PI * 0.5), math.cos(angle * PI * 0.5)
    g = p.w * (p.rnd() + p.rnd() + p.rnd() + p.rnd() - 2.0)
    a, rz = p.phi + spin * g, zoom * g - 1.0
    return p.r * np.cos(a) + rz * p.x, p.r * np.sin(a) + rz * p.y


@variation("pie", """
    { float sl = floor(rnd(s) * P_pie_slices + 0.5);
      float a = P_pie_rotation + 2.0 * PI * (sl + rnd(s) * P_pie_thickness) / P_pie_slices;
      float k = w * rnd(s); v += k * vec2(cos(a), sin(a)); }""", {"slices": 6.0, "rotation": 0.0, "thickness": 0.5}, random=True)
def _pie(p: Point):
    slices, rotation, thickness = p.p("pie_slices"), p.p("pie_rotation"), p.p("pie_thickness")
    sl = np.floor(p.rnd() * slices + 0.5)
    a = rotation + 2.0 * PI * (sl + p.rnd() * thickness) / slices
    k = p.w * p.rnd()
    return k * np.cos(a), k * np.sin(a)


@variation("ngon", """
    { float rf = pow(r2 + EPS, P_ngon_power * 0.5);
      float b = 2.0 * PI / P_ngon_sides;
      float ph = phi - b * floor(phi / b);
      if (ph > b * 0.5) ph -= b;
      float amp = P_ngon_corners * (1.0 / (cos(ph) + EPS) - 1.0) + P_ngon_circle;
      v += w * amp / (rf + EPS) * t; }""", {"sides": 5.0, "power": 3.0, "circle": 1.0, "corners": 2.0}, z=Z_PASS)
def _ngon(p: Point):
    sides, power, circle, corners = p.p("ngon_sides"), p.p("ngon_power"), p.p("ngon_circle"), p.p("ngon_corners")
    rf = np.power(p.r2 + EPS, power * 0.5)
    b = 2.0 * PI / sides
    ph = p.phi - b * np.floor(p.phi / b)
    ph = np.where(ph > b * 0.5, ph - b, ph)
    amp = corners * (1.0 / (np.cos(ph) + EPS) - 1.0) + circle
    k = p.w * amp / (rf + EPS)
    return k * p.x, k * p.y


@variation("curl", """
    { float re = 1.0 + P_curl_c1 * t.x + P_curl_c2 * (t.x * t.x - t.y * t.y);
      float im = P_curl_c1 * t.y + 2.0 * P_curl_c2 * t.x * t.y;
      float k = w / (re * re + im * im + EPS);
      v += k * vec2(t.x * re + t.y * im, t.y * re - t.x * im); }""", {"c1": 0.0, "c2": 0.0}, z=Z_PASS)
def _curl(p: Point):
    c1, c2 = p.p("curl_c1"), p.p("curl_c2")
    re = 1.0 + c1 * p.x + c2 * (p.x * p.x - p.y * p.y)
    im = c1 * p.y + 2.0 * c2 * p.x * p.y
    k = p.w / (re * re + im * im + EPS)
    return k * (p.x * re + p.y * im), k * (p.y * re - p.x * im)


@variation("rectangles", """
    { float rx = P_rectangles_x, ry = P_rectangles_y;
      float nx = rx == 0.0 ? t.x : (2.0 * floor(t.x / rx) + 1.0) * rx - t.x;
      float ny = ry == 0.0 ? t.y : (2.0 * floor(t.y / ry) + 1.0) * ry - t.y;
      v += w * vec2(nx, ny); }""", {"x": 1.0, "y": 1.0}, z=Z_PASS)
def _rectangles(p: Point):
    rx, ry = p.p("rectangles_x"), p.p("rectangles_y")
    nx = p.x if rx == 0 else (2.0 * np.floor(p.x / rx) + 1.0) * rx - p.x
    ny = p.y if ry == 0 else (2.0 * np.floor(p.y / ry) + 1.0) * ry - p.y
    return p.w * nx, p.w * ny


@variation("arch", "{ float a = rnd(s) * PI * w; float sa = sin(a), ca = cos(a); v += w * vec2(sa, sa * sa / (ca + EPS)); }", random=True)
def _arch(p: Point):
    a = p.rnd() * PI * p.w
    sa, ca = np.sin(a), np.cos(a)
    return p.w * sa, p.w * sa * sa / (ca + EPS)


@variation("tangent", "v += w * vec2(sin(t.x) / (cos(t.y) + EPS), tan(t.y));")
def _tangent(p: Point):
    return p.w * np.sin(p.x) / (np.cos(p.y) + EPS), p.w * np.tan(p.y)


@variation("square", "v += w * vec2(rnd(s) - 0.5, rnd(s) - 0.5);", random=True)
def _square(p: Point):
    return p.w * (p.rnd() - 0.5), p.w * (p.rnd() - 0.5)


@variation("rays", "{ float a = w * rnd(s) * PI; float k = w / (r2 + EPS); float tr = w * tan(a) * k; v += tr * vec2(cos(t.x), sin(t.y)); }", random=True)
def _rays(p: Point):
    a = p.w * p.rnd() * PI
    k = p.w / (p.r2 + EPS)
    tr = p.w * np.tan(a) * k
    return tr * np.cos(p.x), tr * np.sin(p.y)


@variation("blade", "{ float a = rnd(s) * w * r; float sa = sin(a), ca = cos(a); v += w * t.x * vec2(ca + sa, ca - sa); }", random=True)
def _blade(p: Point):
    a = p.rnd() * p.w * p.r
    sa, ca = np.sin(a), np.cos(a)
    return p.w * p.x * (ca + sa), p.w * p.x * (ca - sa)


@variation("secant2", "{ float cr = cos(w * r); float icr = 1.0 / (cr + EPS); v += w * vec2(t.x, cr < 0.0 ? icr + 1.0 : icr - 1.0); }")
def _secant2(p: Point):
    cr = np.cos(p.w * p.r)
    icr = 1.0 / (cr + EPS)
    return p.w * p.x, p.w * np.where(cr < 0, icr + 1.0, icr - 1.0)


@variation("cross", "{ float ss = t.x * t.x - t.y * t.y; float k = w * sqrt(1.0 / (ss * ss + EPS)); v += k * t; }")
def _cross(p: Point):
    ss = p.x * p.x - p.y * p.y
    k = p.w * np.sqrt(1.0 / (ss * ss + EPS))
    return k * p.x, k * p.y


# ---------------------------------------------------------------------------
# Popular Apophysis plugin variations
# ---------------------------------------------------------------------------
@variation("elliptic", """
    { float tmp = r2 + 1.0, x2 = 2.0 * t.x;
      float xmax = 0.5 * (sqrt(tmp + x2) + sqrt(tmp - x2));
      float a = t.x / xmax, b = 1.0 - a * a, ssx = xmax - 1.0;
      float wp = w / (PI * 0.5);
      b = b < 0.0 ? 0.0 : sqrt(b); ssx = ssx < 0.0 ? 0.0 : sqrt(ssx);
      v.x += wp * atan(a, b);
      v.y += (t.y > 0.0 ? 1.0 : -1.0) * wp * log(xmax + ssx); }""", z=Z_PASS)
def _elliptic(p: Point):
    tmp, x2 = p.r2 + 1.0, 2.0 * p.x
    xmax = 0.5 * (np.sqrt(tmp + x2) + np.sqrt(tmp - x2))
    a = p.x / xmax
    b = np.sqrt(np.maximum(1.0 - a * a, 0.0))
    ssx = np.sqrt(np.maximum(xmax - 1.0, 0.0))
    wp = p.w / (PI * 0.5)
    return wp * np.arctan2(a, b), np.where(p.y > 0, 1.0, -1.0) * wp * np.log(xmax + ssx)


@variation("splits", "v += w * vec2(t.x >= 0.0 ? t.x + P_splits_x : t.x - P_splits_x, t.y >= 0.0 ? t.y + P_splits_y : t.y - P_splits_y);",
           {"x": 0.0, "y": 0.0}, z=Z_PASS)
def _splits(p: Point):
    sx, sy = p.p("splits_x"), p.p("splits_y")
    return p.w * np.where(p.x >= 0, p.x + sx, p.x - sx), p.w * np.where(p.y >= 0, p.y + sy, p.y - sy)


@variation("bipolar", """
    { float tt = r2 + 1.0, x2 = 2.0 * t.x, ps = -PI * 0.5 * P_bipolar_shift;
      float yy = 0.5 * atan(2.0 * t.y, r2 - 1.0) + ps;
      if (yy > PI * 0.5) yy = -PI * 0.5 + mod(yy + PI * 0.5, PI);
      else if (yy < -PI * 0.5) yy = PI * 0.5 - mod(PI * 0.5 - yy, PI);
      float f = tt + x2, g = tt - x2;
      if (g != 0.0 && f / g > 0.0) v += w * (2.0 / PI) * vec2(0.25 * log(f / g), yy); }""", {"shift": 0.0}, z=Z_PASS)
def _bipolar(p: Point):
    shift = p.p("bipolar_shift")
    tt, x2, ps = p.r2 + 1.0, 2.0 * p.x, -PI * 0.5 * shift
    yy = 0.5 * np.arctan2(2.0 * p.y, p.r2 - 1.0) + ps
    yy = np.where(yy > PI * 0.5, -PI * 0.5 + np.mod(yy + PI * 0.5, PI), yy)
    yy = np.where(yy < -PI * 0.5, PI * 0.5 - np.mod(PI * 0.5 - yy, PI), yy)
    f, g = tt + x2, tt - x2
    ok = (g != 0) & (f / np.where(g == 0, 1.0, g) > 0)
    lx = np.where(ok, 0.25 * np.log(np.where(ok, f / np.where(g == 0, 1.0, g), 1.0)), 0.0)
    return p.w * (2.0 / PI) * lx, np.where(ok, p.w * (2.0 / PI) * yy, 0.0)


@variation("hemisphere", "v += w / sqrt(r2 + 1.0) * t;", z=Z_PASS)
def _hemisphere(p: Point):
    k = p.w / np.sqrt(p.r2 + 1.0)
    return k * p.x, k * p.y


@variation("lazysusan", """
    { float xx = t.x - P_lazysusan_x, yy = t.y + P_lazysusan_y;
      float rr = sqrt(xx * xx + yy * yy);
      if (rr < w) {
        float a = atan(yy, xx) + P_lazysusan_spin + P_lazysusan_twist * (w - rr);
        v += w * vec2(rr * cos(a) + P_lazysusan_x, rr * sin(a) - P_lazysusan_y);
      } else {
        rr = w * (1.0 + P_lazysusan_space / (rr + EPS));
        v += rr * vec2(xx + P_lazysusan_x, yy - P_lazysusan_y);
      } }""", {"spin": 0.0, "space": 0.0, "twist": 0.0, "x": 0.0, "y": 0.0}, z=Z_PASS)
def _lazysusan(p: Point):
    spin, space, twist = p.p("lazysusan_spin"), p.p("lazysusan_space"), p.p("lazysusan_twist")
    lx, ly = p.p("lazysusan_x"), p.p("lazysusan_y")
    xx, yy = p.x - lx, p.y + ly
    rr = np.sqrt(xx * xx + yy * yy)
    inside = rr < p.w
    a = np.arctan2(yy, xx) + spin + twist * (p.w - rr)
    ix, iy = p.w * (rr * np.cos(a) + lx), p.w * (rr * np.sin(a) - ly)
    ro = p.w * (1.0 + space / (rr + EPS))
    ox, oy = ro * (xx + lx), ro * (yy - ly)
    return np.where(inside, ix, ox), np.where(inside, iy, oy)


@variation("mobius", """
    { float re_u = P_mobius_Re_A * t.x - P_mobius_Im_A * t.y + P_mobius_Re_B;
      float im_u = P_mobius_Re_A * t.y + P_mobius_Im_A * t.x + P_mobius_Im_B;
      float re_v = P_mobius_Re_C * t.x - P_mobius_Im_C * t.y + P_mobius_Re_D;
      float im_v = P_mobius_Re_C * t.y + P_mobius_Im_C * t.x + P_mobius_Im_D;
      float k = w / (re_v * re_v + im_v * im_v + EPS);
      v += k * vec2(re_u * re_v + im_u * im_v, im_u * re_v - re_u * im_v); }""",
           {"Re_A": 1.0, "Im_A": 0.0, "Re_B": 0.0, "Im_B": 0.0, "Re_C": 0.0, "Im_C": 0.0, "Re_D": 1.0, "Im_D": 0.0}, z=Z_PASS)
def _mobius(p: Point):
    ra, ia, rb, ib = p.p("mobius_Re_A"), p.p("mobius_Im_A"), p.p("mobius_Re_B"), p.p("mobius_Im_B")
    rc, ic, rd, id_ = p.p("mobius_Re_C"), p.p("mobius_Im_C"), p.p("mobius_Re_D"), p.p("mobius_Im_D")
    re_u, im_u = ra * p.x - ia * p.y + rb, ra * p.y + ia * p.x + ib
    re_v, im_v = rc * p.x - ic * p.y + rd, rc * p.y + ic * p.x + id_
    k = p.w / (re_v * re_v + im_v * im_v + EPS)
    return k * (re_u * re_v + im_u * im_v), k * (im_u * re_v - re_u * im_v)


@variation("polynomial", """
    v += w * vec2(P_polynomial_lcx * t.x + P_polynomial_scx * sign(t.x) * pow(abs(t.x), P_polynomial_powx),
                  P_polynomial_lcy * t.y + P_polynomial_scy * sign(t.y) * pow(abs(t.y), P_polynomial_powy));""",
           {"powx": 1.0, "powy": 1.0, "lcx": 0.0, "lcy": 0.0, "scx": 0.0, "scy": 0.0})
def _polynomial(p: Point):
    px, py = p.p("polynomial_powx"), p.p("polynomial_powy")
    lcx, lcy, scx, scy = p.p("polynomial_lcx"), p.p("polynomial_lcy"), p.p("polynomial_scx"), p.p("polynomial_scy")
    return (p.w * (lcx * p.x + scx * np.sign(p.x) * np.power(np.abs(p.x), px)),
            p.w * (lcy * p.y + scy * np.sign(p.y) * np.power(np.abs(p.y), py)))


@variation("wedge", """
    { float a = phi + P_wedge_swirl * r;
      float cc = floor((P_wedge_count * a + PI) * (1.0 / PI) * 0.5);
      float comp = 1.0 - P_wedge_angle * P_wedge_count * (1.0 / PI) * 0.5;
      a = a * comp + cc * P_wedge_angle;
      float k = w * (r + P_wedge_hole);
      v += k * vec2(cos(a), sin(a)); }""", {"angle": 0.0, "hole": 0.0, "count": 1.0, "swirl": 0.0}, z=Z_PASS)
def _wedge(p: Point):
    angle, hole, count, swirl = p.p("wedge_angle"), p.p("wedge_hole"), p.p("wedge_count"), p.p("wedge_swirl")
    a = p.phi + swirl * p.r
    cc = np.floor((count * a + PI) * (1.0 / PI) * 0.5)
    comp = 1.0 - angle * count * (1.0 / PI) * 0.5
    a = a * comp + cc * angle
    k = p.w * (p.r + hole)
    return k * np.cos(a), k * np.sin(a)


@variation("pre_blur", "", random=True, kind=PRE)   # handled specially by the engines: jitters the input point
def _pre_blur(p: Point):
    a = p.rnd() * 2.0 * PI
    k = p.w * (p.rnd() + p.rnd() + p.rnd() + p.rnd() - 2.0)
    return k * np.cos(a), k * np.sin(a)






# ---------------------------------------------------------------------------
# Apophysis depth built-ins (XForm.pas): act on z, rotate about x / y
# ---------------------------------------------------------------------------
@variation("flatten", "vz = 0.0;", kind=POST, z=Z_FORMULA, origin="Apophysis built-in")
def _flatten(p: Point):
    return np.zeros_like(p.x), np.zeros_like(p.y), -p.pz


@variation("zblur", "vz += w * (rnd(s) + rnd(s) + rnd(s) + rnd(s) - 2.0);", random=True, z=Z_FORMULA, origin="Apophysis built-in")
def _zblur(p: Point):
    return np.zeros_like(p.x), np.zeros_like(p.y), p.w * (p.rnd() + p.rnd() + p.rnd() + p.rnd() - 2.0)


@variation("blur3D", """
    { float a = rnd(s) * 2.0 * PI, b = rnd(s) * PI;
      float rr = w * (rnd(s) + rnd(s) + rnd(s) + rnd(s) - 2.0);
      v += rr * sin(b) * vec2(cos(a), sin(a)); vz += rr * cos(b); }""", random=True, z=Z_FORMULA, origin="Apophysis built-in")
def _blur3d(p: Point):
    a, b = p.rnd() * 2.0 * PI, p.rnd() * PI
    rr = p.w * (p.rnd() + p.rnd() + p.rnd() + p.rnd() - 2.0)
    return rr * np.sin(b) * np.cos(a), rr * np.sin(b) * np.sin(a), rr * np.cos(b)


@variation("zscale", "vz += w * tz;", z=Z_FORMULA, origin="Apophysis built-in")
def _zscale(p: Point):
    return np.zeros_like(p.x), np.zeros_like(p.y), p.w * p.z


@variation("ztranslate", "vz += w;", z=Z_FORMULA, origin="Apophysis built-in")
def _ztranslate(p: Point):
    return np.zeros_like(p.x), np.zeros_like(p.y), np.full_like(p.x, p.w)


@variation("zcone", "vz += w * r;", z=Z_FORMULA, origin="Apophysis built-in")
def _zcone(p: Point):
    return np.zeros_like(p.x), np.zeros_like(p.y), p.w * p.r


@variation("pre_zscale", "tz *= w;", kind=PRE, z=Z_FORMULA, origin="Apophysis built-in")
def _pre_zscale(p: Point):
    return np.zeros_like(p.x), np.zeros_like(p.y), p.z * (p.w - 1.0)


@variation("pre_ztranslate", "tz += w;", kind=PRE, z=Z_FORMULA, origin="Apophysis built-in")
def _pre_ztranslate(p: Point):
    return np.zeros_like(p.x), np.zeros_like(p.y), np.full_like(p.x, p.w)


@variation("pre_rotate_x", """
    { float sa = sin(w * PI * 0.5), ca = cos(w * PI * 0.5);
      float nz = ca * tz - sa * t.y; t.y = sa * tz + ca * t.y; tz = nz; }""", kind=PRE, z=Z_FORMULA, origin="Apophysis built-in")
def _pre_rotate_x(p: Point):
    sa, ca = math.sin(p.w * PI * 0.5), math.cos(p.w * PI * 0.5)
    ny, nz = sa * p.z + ca * p.y, ca * p.z - sa * p.y
    return np.zeros_like(p.x), ny - p.y, nz - p.z


@variation("pre_rotate_y", """
    { float sa = sin(w * PI * 0.5), ca = cos(w * PI * 0.5);
      float nx = ca * t.x - sa * tz; tz = sa * t.x + ca * tz; t.x = nx; }""", kind=PRE, z=Z_FORMULA, origin="Apophysis built-in")
def _pre_rotate_y(p: Point):
    sa, ca = math.sin(p.w * PI * 0.5), math.cos(p.w * PI * 0.5)
    nx, nz = ca * p.x - sa * p.z, sa * p.x + ca * p.z
    return nx - p.x, np.zeros_like(p.y), nz - p.z


@variation("post_rotate_x", """
    { float sa = sin(w * PI * 0.5), ca = cos(w * PI * 0.5);
      float nz = ca * vz - sa * v.y; v.y = sa * vz + ca * v.y; vz = nz; }""", kind=POST, z=Z_FORMULA, origin="Apophysis built-in")
def _post_rotate_x(p: Point):
    sa, ca = math.sin(p.w * PI * 0.5), math.cos(p.w * PI * 0.5)
    ny, nz = sa * p.pz + ca * p.py, ca * p.pz - sa * p.py
    return np.zeros_like(p.x), ny - p.py, nz - p.pz


@variation("post_rotate_y", """
    { float sa = sin(w * PI * 0.5), ca = cos(w * PI * 0.5);
      float nx = ca * v.x - sa * vz; vz = sa * v.x + ca * vz; v.x = nx; }""", kind=POST, z=Z_FORMULA, origin="Apophysis built-in")
def _post_rotate_y(p: Point):
    sa, ca = math.sin(p.w * PI * 0.5), math.cos(p.w * PI * 0.5)
    nx, nz = ca * p.px - sa * p.pz, sa * p.px + ca * p.pz
    return nx - p.px, np.zeros_like(p.y), nz - p.pz

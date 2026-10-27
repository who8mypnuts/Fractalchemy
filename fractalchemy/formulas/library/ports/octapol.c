/*
    Fractalchemy formula library — octapol
    Ported by hand from octapol.c (Apophysis 7X src/Plugin, Georg Kiehne "Xyrus02", GPL v2+):
    the double2 points of the original are passed as x/y pairs, which is all that changed.
*/

typedef struct
{
    double rad, s, t, a;
    double ax, ay, bx, by, cx, cy,
           dx, dy, ex, ey, fx, fy,
           gx, gy, hx, hy, ix, iy,
           jx, jy, kx, ky, lx, ly;

    double octapol_polarweight;
    double octapol_radius;
    double octapol_s;
    double octapol_t;
} Variables;

#include "apoplugin.h"

#define DENOM_SQRT2 0.707106781

APO_PLUGIN("octapol");

APO_VARIABLES(
    VAR_REAL(octapol_polarweight, 0.0),
    VAR_REAL(octapol_radius, 1.0),
    VAR_REAL(octapol_s, 0.5),
    VAR_REAL(octapol_t, 0.5)
);

inline double lerp(double a, double b, double p) {
    return a + p * (b - a);
}
inline int hits_rect(double tlx, double tly, double brx, double bry, double px, double py) {
    return (px >= tlx && py >= tly && px <= brx && py <= bry);
}
inline int hits_triangle(double ax, double ay, double bx, double by, double cx, double cy, double px, double py) {
    double v0x = cx - ax, v0y = cy - ay;
    double v1x = bx - ax, v1y = by - ay;
    double v2x = px - ax, v2y = py - ay;
    double d00 = v0x * v0x + v0y * v0y;
    double d01 = v0x * v1x + v0y * v1y;
    double d02 = v0x * v2x + v0y * v2y;
    double d11 = v1x * v1x + v1y * v1y;
    double d12 = v1x * v2x + v1y * v2y;
    double denom = (d00 * d11 - d01 * d01);
    double u = 0, v = 0;
    if (denom != 0) {
        u = (d11 * d02 - d01 * d12) / denom;
        v = (d00 * d12 - d01 * d02) / denom;
    }
    return ((u + v) < 1.0) && (u > 0) && (v > 0);
}

int PluginVarPrepare(Variation* vp)
{
    VAR(s) = fabs(VAR(octapol_s));
    VAR(t) = fabs(VAR(octapol_t));
    VAR(a) = VAR(s) * 0.5 + VAR(t);

    VAR(rad) = DENOM_SQRT2 * VAR(s) * fabs(VAR(octapol_radius));

    VAR(ax) = -0.5 * VAR(s); VAR(ay) = 0.5 * VAR(s) + VAR(t);
    VAR(bx) = 0.5 * VAR(s); VAR(by) = 0.5 * VAR(s) + VAR(t);
    VAR(cx) = VAR(t); VAR(cy) = 0.5 * VAR(s);
    VAR(dx) = VAR(t); VAR(dy) = -0.5 * VAR(s);
    VAR(ex) = 0.5 * VAR(s); VAR(ey) = -0.5 * VAR(s) - VAR(t);
    VAR(fx) = -0.5 * VAR(s); VAR(fy) = -0.5 * VAR(s) - VAR(t);
    VAR(gx) = -VAR(t); VAR(gy) = -0.5 * VAR(s);
    VAR(hx) = -VAR(t); VAR(hy) = 0.5 * VAR(s);
    VAR(ix) = -0.5 * VAR(s); VAR(iy) = 0.5 * VAR(s);
    VAR(jx) = 0.5 * VAR(s); VAR(jy) = 0.5 * VAR(s);
    VAR(kx) = -0.5 * VAR(s); VAR(ky) = -0.5 * VAR(s);
    VAR(lx) = 0.5 * VAR(s); VAR(ly) = -0.5 * VAR(s);

    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double x = FTx * 0.15, y = FTy * 0.15, z = FTz, r = 0;
    int in_circle = 0;
    if (VAR(rad) > 0) {
        if (VAR(rad) == 0.0) in_circle = 1;
        else {
            r = sqrt(sqr(x) + sqr(y));
            in_circle = (r <= VAR(rad));
        }
    }

    if (in_circle) {
        double rd = log(sqr(r / VAR(rad)));
        double phi = atan2(y, x);
        FPx += VVAR * lerp(x, phi, rd * VAR(octapol_polarweight));
        FPy += VVAR * lerp(y, r, rd * VAR(octapol_polarweight));
    } else if (fabs(x) <= VAR(a) && fabs(y) <= VAR(a)) {
        if (hits_rect(VAR(hx), VAR(hy), VAR(kx), VAR(ky), x, y) || hits_rect(VAR(jx), VAR(jy), VAR(dx), VAR(dy), x, y) ||
            hits_rect(VAR(ax), VAR(ay), VAR(jx), VAR(jy), x, y) || hits_rect(VAR(kx), VAR(ky), VAR(ex), VAR(ey), x, y) ||
            hits_triangle(VAR(ix), VAR(iy), VAR(ax), VAR(ay), VAR(hx), VAR(hy), x, y) ||
            hits_triangle(VAR(jx), VAR(jy), VAR(bx), VAR(by), VAR(cx), VAR(cy), x, y) ||
            hits_triangle(VAR(lx), VAR(ly), VAR(dx), VAR(dy), VAR(ex), VAR(ey), x, y) ||
            hits_triangle(VAR(kx), VAR(ky), VAR(fx), VAR(fy), VAR(gx), VAR(gy), x, y)) {
            FPx += VVAR * x; FPy += VVAR * y;
        } else { FPx = 0; FPy = 0; }
    } else { FPx = 0; FPy = 0; }

    FPx += VVAR * x;
    FPy += VVAR * y;
    FPz += VVAR * z;
    return TRUE;
}

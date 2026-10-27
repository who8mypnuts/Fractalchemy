/*
    Fractalchemy formula library — crackle
    Ported from crackle.c (slobo777's "crackle" plugin for Apophysis, GPL v2+) with two changes:
    the cache of cell centres the original pre-computes in PluginVarPrepare is dropped (centres are
    computed on demand — the cache was only a speed-up), and the working point list is a local
    array instead of a struct member. The noise and Voronoi helpers are the original support
    library, shared as noiseb.h / voronoi.h.
*/

#include "noiseb.h"
#include "voronoi.h"

typedef struct
{
    double crackle_cellsize;
    double crackle_power;
    double crackle_distort;
    double crackle_scale;
    double crackle_z;
} Variables;

#include "apoplugin.h"

// position() calculates the cell centre for cell (x, y), given plane slice z, scale factor s, distortion d
void position(int x, int y, double z, double s, double d, double V[2]) {
    double E[3], F[3];
    // Values here are arbitrary, chosen simply to be far enough apart so they do not correlate
    E[_x_] = x * 2.5;
    E[_y_] = y * 2.5;
    E[_z_] = z * 2.5;
    // Cross-over between x and y is intentional
    F[_x_] = y * 2.5 + 30.2;
    F[_y_] = x * 2.5 - 12.1;
    F[_z_] = z * 2.5 + 19.8;
    V[_x_] = (x + d * simplexNoise3D(E)) * s;
    V[_y_] = (y + d * simplexNoise3D(F)) * s;
}

APO_PLUGIN("crackle");

APO_VARIABLES(
    VAR_REAL(crackle_cellsize, 1.0),
    VAR_REAL(crackle_power, 0.2),
    VAR_REAL(crackle_distort, 0.0),
    VAR_REAL(crackle_scale, 1.0),
    VAR_REAL(crackle_z, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double DXo, DYo, L, R, s, trgL;
    double U[2];
    int XCv, YCv;
    double P[VORONOI_MAXPOINTS][2];

    // An infinite number of invisible cells? No thanks!
    if (0.0 == VAR(crackle_cellsize)) {
        return TRUE;
    }

    // Scaling factor
    s = VAR(crackle_cellsize) / 2.0;

    // For a blur effect, base everything starting on a circle radius 1.0
    // (as opposed to reading the values from FTx and FTy)
    double blurr = (random01() + random01()) / 2.0 + (random01() - 0.5) / 4.0;

    double theta = 2 * M_PI * random01();
    U[_x_] = blurr * sin(theta);
    U[_y_] = blurr * cos(theta);

    // Use integer values as Voronoi grid co-ordinates
    XCv = (int)floor(U[_x_] / s);
    YCv = (int)floor(U[_y_] / s);

    // Get a set of 9 square centre points, based around the one above
    int di, dj;
    int i = 0;
    for (di = -1; di < 2; di++) {
        for (dj = -1; dj < 2; dj++) {
            position(XCv + di, YCv + dj, VAR(crackle_z), s, VAR(crackle_distort), P[i]);
            i++;
        }
    }

    int q = closest(P, 9, U);

    int offset[9][2] = { { -1, -1}, { -1, 0}, { -1, 1},
                         { 0, -1}, { 0, 0}, { 0, 1},
                         { 1, -1}, { 1, 0}, { 1, 1} };

    // Remake list starting from chosen square, ensure it is completely surrounded (total 9 points)
    // First adjust centres according to which one was found to be closest
    XCv += offset[q][_x_];
    YCv += offset[q][_y_];

    // Get a new set of 9 square centre points, based around the definite closest point
    i = 0;
    for (di = -1; di < 2; di++) {
        for (dj = -1; dj < 2; dj++) {
            position(XCv + di, YCv + dj, VAR(crackle_z), s, VAR(crackle_distort), P[i]);
            i++;
        }
    }

    L = voronoi(P, 9, 4, U);   // index 4 is centre cell

    // Delta vector from centre
    DXo = U[_x_] - P[4][_x_];
    DYo = U[_y_] - P[4][_y_];

    // Apply "interesting bit" to cell's DXo and DYo co-ordinates
    // trgL is the new value of L
    trgL = pow(L + 1e-100, VAR(crackle_power)) * VAR(crackle_scale);   // ( 0.9 )

    R = trgL / (L + 1e-100);

    DXo *= R;
    DYo *= R;

    // Add cell centre co-ordinates back in
    DXo += P[4][_x_];
    DYo += P[4][_y_];

    // Finally add values in
    FPx += VVAR * DXo;
    FPy += VVAR * DYo;

    return TRUE;
}

/*
    Fractalchemy formula library — translated from the JWildfire variation
        Blob3DFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double blob3D_low;
    double blob3D_high;
    double blob3D_waves;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("blob3D");

APO_VARIABLES(
    VAR_REAL(blob3D_low, 0.3),
    VAR_REAL(blob3D_high, 1.2),
    VAR_REAL(blob3D_waves, 6)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double a = atan2(FTx, FTy);
    double r = sqrt(FTx * FTx + FTy * FTy);
    r = r * (VAR(blob3D_low) + (VAR(blob3D_high) - VAR(blob3D_low)) * (0.5 + 0.5 * sin(VAR(blob3D_waves) * a)));
    double nx = sin(a) * r;
    double ny = cos(a) * r;
    double nz = sin(VAR(blob3D_waves) * a) * r;
    FPx += VVAR * nx;
    FPy += VVAR * ny;
    FPz += VVAR * nz;
    return TRUE;
}

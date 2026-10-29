/*
    Fractalchemy formula library — translated from the JWildfire variation
        DipoleFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double dipole_separation;
    double dipole_strength;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("dipole");

APO_VARIABLES(
    VAR_REAL(dipole_separation, 0.5),
    VAR_REAL(dipole_strength, 0.2)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double dx1 = FTx + VAR(dipole_separation);
    double dx2 = FTx - VAR(dipole_separation);
    double r1 = sqrt(dx1 * dx1 + FTy * FTy);
    double r2 = sqrt(dx2 * dx2 + FTy * FTy);
    r1 = max(r1, 1e-4);
    r2 = max(r2, 1e-4);
    double r13 = r1 * r1 * r1;
    double r23 = r2 * r2 * r2;
    double ex = dx1 / r13 - dx2 / r23;
    double ey = FTy / r13 - FTy / r23;
    FPx += VVAR * (FTx + VAR(dipole_strength) * ex);
    FPy += VVAR * (FTy + VAR(dipole_strength) * ey);
    
    return TRUE;
}

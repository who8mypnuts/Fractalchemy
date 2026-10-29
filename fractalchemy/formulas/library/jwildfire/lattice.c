/*
    Fractalchemy formula library — translated from the JWildfire variation
        LatticeFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double lattice_freq;
    double lattice_pull;
    double lattice_shear;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("lattice");

APO_VARIABLES(
    VAR_REAL(lattice_freq, 3),
    VAR_REAL(lattice_pull, 0.5),
    VAR_REAL(lattice_shear, 0)
);

double clamp(double value, double min, double max)
{
    return max(min, min(max, value));
}

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double lt_freq = max(fabs(VAR(lattice_freq)), 0.01);
    double lt_pull = clamp(VAR(lattice_pull), 0.0, 1.0);
    double lt_cx = round(FTx * lt_freq) / lt_freq;
    double lt_cy = round(FTy * lt_freq) / lt_freq;
    double lt_dx = lt_cx - FTx;
    double lt_dy = lt_cy - FTy;
    FPx += VVAR * (FTx + lt_pull * lt_dx + VAR(lattice_shear) * lt_dy);
    FPy += VVAR * (FTy + lt_pull * lt_dy + VAR(lattice_shear) * lt_dx);
    
    return TRUE;
}

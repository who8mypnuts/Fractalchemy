/*
    Fractalchemy formula library — translated from the JWildfire variation
        QuadrupoleFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double quadrupole_strength;
    double quadrupole_smooth;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("quadrupole");

APO_VARIABLES(
    VAR_REAL(quadrupole_strength, 0.3),
    VAR_REAL(quadrupole_smooth, 0.1)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double r2 = FTx * FTx + FTy * FTy;
    double qp_r2 = r2 + VAR(quadrupole_smooth);
    double qp_theta = atan2(FTy, FTx);
    double qp_field_r = VAR(quadrupole_strength) * cos(2.0 * qp_theta) / qp_r2;
    double qp_field_t = VAR(quadrupole_strength) * sin(2.0 * qp_theta) / qp_r2;
    double qp_r = sqrt(r2 + 1.0e-10);
    double qp_nr = qp_r + qp_field_r;
    double qp_nt = qp_theta + qp_field_t;
    FPx += VVAR * qp_nr * cos(qp_nt);
    FPy += VVAR * qp_nr * sin(qp_nt);
    
    return TRUE;
}

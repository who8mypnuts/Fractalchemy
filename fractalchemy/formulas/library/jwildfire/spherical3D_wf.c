/*
    Fractalchemy formula library — translated from the JWildfire variation
        Spherical3DWFFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    int spherical3D_wf_invert;
    double spherical3D_wf_exponent;
    double spherical3D_wf__regularForm;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("spherical3D_wf");

APO_VARIABLES(
    VAR_INTEGER(spherical3D_wf_invert, 0),
    VAR_REAL(spherical3D_wf_exponent, 2)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(spherical3D_wf__regularForm) = fabs(VAR(spherical3D_wf_exponent) - 2.0) < 1.0e-8;
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double r;
    if(VAR(spherical3D_wf__regularForm)) {
        r = VVAR / (FTx * FTx + FTy * FTy + FTz * FTz + EPS);
    } else {
        r = VVAR / pow(FTx * FTx + FTy * FTy + FTz * FTz + EPS, VAR(spherical3D_wf_exponent) / 2.0);
    }
    if(VAR(spherical3D_wf_invert) == 0) {
        FPx += FTx * r;
        FPy += FTy * r;
        FPz += FTz * r;
    } else {
        FPx -= FTx * r;
        FPy -= FTy * r;
        FPz -= FTz * r;
    }
    return TRUE;
}

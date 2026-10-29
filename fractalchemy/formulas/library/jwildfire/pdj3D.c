/*
    Fractalchemy formula library — translated from the JWildfire variation
        PDJ3DFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double pdj3D_a;
    double pdj3D_b;
    double pdj3D_c;
    double pdj3D_d;
    double pdj3D_e;
    double pdj3D_f;
    double pdj3D_g;
    double pdj3D_h;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("pdj3D");

APO_VARIABLES(
    VAR_REAL(pdj3D_a, 1),
    VAR_REAL(pdj3D_b, 2),
    VAR_REAL(pdj3D_c, 3),
    VAR_REAL(pdj3D_d, 4),
    VAR_REAL(pdj3D_e, 2),
    VAR_REAL(pdj3D_f, 0),
    VAR_REAL(pdj3D_g, 2),
    VAR_REAL(pdj3D_h, 0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    FPx += VVAR * (sin(VAR(pdj3D_a) * FTy) - cos(VAR(pdj3D_b) * FTx));
    FPy += VVAR * (sin(VAR(pdj3D_c) * FTx) - cos(VAR(pdj3D_d) * FTy));
    FPz += VVAR * (sin(VAR(pdj3D_e) * FTy) - cos(VAR(pdj3D_f) * FTz)) * cos(VAR(pdj3D_g) * FTx) + sin(VAR(pdj3D_h) * FTz);
    return TRUE;
}

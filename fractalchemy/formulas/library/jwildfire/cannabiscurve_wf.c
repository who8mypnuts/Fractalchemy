/*
    Fractalchemy formula library — translated from the JWildfire variation
        CannabisCurveWFFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double cannabiscurve_wf_filled;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("cannabiscurve_wf");

APO_VARIABLES(
    VAR_REAL(cannabiscurve_wf_filled, 0.85)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double a = atan2(FTx, FTy);
    double r = (1 + 9.0 / 10.0 * cos(8.0 * a)) * (1 + 1.0 / 10.0 * cos(24.0 * a)) * (9.0 / 10.0 + 1.0 / 10.0 * cos(200.0 * a)) * (1.0 + sin(a));
    a += M_PI / 2.0;
    if(VAR(cannabiscurve_wf_filled) > 0 && VAR(cannabiscurve_wf_filled) > random01()) {
        r *= random01();
    }
    double nx = sin(a) * r;
    double ny = cos(a) * r;
    FPx += VVAR * nx;
    FPy += VVAR * ny;
    
    return TRUE;
}

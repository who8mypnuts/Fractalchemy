/*
    Fractalchemy formula library — translated from the JWildfire variation
        HexagonalFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double hexagonal_scale;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("hexagonal");

APO_VARIABLES(
    VAR_REAL(hexagonal_scale, 1)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double hx_scale = max(fabs(VAR(hexagonal_scale)), 0.0001);
    double SQRT3 = 1.732050807568877;
    double q = (2.0 / 3.0) * FTx / hx_scale;
    double r_hex = ((- 1.0 / 3.0) * FTx + (1.0 / SQRT3) * FTy) / hx_scale;
    double s_hex = - q - r_hex;
    double rq = floor(q + 0.5);
    double rr = floor(r_hex + 0.5);
    double rs = floor(s_hex + 0.5);
    double dq = fabs(rq - q);
    double dr = fabs(rr - r_hex);
    double ds = fabs(rs - s_hex);
    if(dq > dr && dq > ds) rq = - rr - rs;
    else if(dr > ds) rr = - rq - rs;
    double cx = hx_scale * 1.5 * rq;
    double cy = hx_scale * SQRT3 * (rr + rq * 0.5);
    FPx += VVAR * (FTx - cx);
    FPy += VVAR * (FTy - cy);
    
    return TRUE;
}

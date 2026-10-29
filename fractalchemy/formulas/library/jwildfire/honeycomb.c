/*
    Fractalchemy formula library — translated from the JWildfire variation
        HoneycombFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double honeycomb_scale;
    double honeycomb_pull;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("honeycomb");

APO_VARIABLES(
    VAR_REAL(honeycomb_scale, 1),
    VAR_REAL(honeycomb_pull, 0.7)
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
    double hc_s = max(fabs(VAR(honeycomb_scale)), 0.01);
    double hc_p = clamp(VAR(honeycomb_pull), 0.0, 1.0);
    double hc_q = (2.0 / 3.0) * FTx / hc_s;
    double hc_r2 = (- 1.0 / 3.0) * FTx / hc_s + 0.5773502691896257 * FTy / hc_s;
    double hc_rq = round(hc_q);
    double hc_rr = round(hc_r2);
    double hc_rs = round(- hc_q - hc_r2);
    double hc_dq = fabs(hc_rq - hc_q);
    double hc_dr = fabs(hc_rr - hc_r2);
    double hc_ds = fabs(hc_rs - (- hc_q - hc_r2));
    if(hc_dq > hc_dr && hc_dq > hc_ds) hc_rq = - hc_rr - hc_rs;
    else if(hc_dr > hc_ds) hc_rr = - hc_rq - hc_rs;
    double hc_cx = hc_s * (hc_rq + 0.5 * hc_rr);
    double hc_cy = hc_s * 0.8660254037844386 * hc_rr;
    FPx += VVAR * (hc_cx + (FTx - hc_cx) * hc_p);
    FPy += VVAR * (hc_cy + (FTy - hc_cy) * hc_p);
    
    return TRUE;
}

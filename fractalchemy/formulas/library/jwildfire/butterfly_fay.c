/*
    Fractalchemy formula library — translated from the JWildfire variation
        ButterflyFayFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double butterfly_fay_cycles;
    double butterfly_fay_offset;
    int butterfly_fay_unified_inner_outer;
    int butterfly_fay_outer_mode;
    int butterfly_fay_inner_mode;
    double butterfly_fay_outer_spread;
    double butterfly_fay_inner_spread;
    double butterfly_fay_outer_spread_ratio;
    double butterfly_fay_inner_spread_ratio;
    double butterfly_fay_spread_split;
    double butterfly_fay_fill;
    double butterfly_fay_number_of_cycles;
    double butterfly_fay_cycle_length;
    double butterfly_fay_radians_to_close;
    double butterfly_fay_cycles_to_close;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("butterfly_fay");

APO_VARIABLES(
    VAR_REAL(butterfly_fay_offset, 0),
    VAR_INTEGER(butterfly_fay_unified_inner_outer, 1),
    VAR_INTEGER(butterfly_fay_outer_mode, 1),
    VAR_INTEGER(butterfly_fay_inner_mode, 1),
    VAR_REAL(butterfly_fay_outer_spread, 0),
    VAR_REAL(butterfly_fay_inner_spread, 0),
    VAR_REAL(butterfly_fay_outer_spread_ratio, 1),
    VAR_REAL(butterfly_fay_inner_spread_ratio, 1),
    VAR_REAL(butterfly_fay_spread_split, 1),
    VAR_REAL(butterfly_fay_cycles, 0),
    VAR_REAL(butterfly_fay_fill, 0)
);

int PluginVarPrepare(Variation* vp)
{
    if(VAR(butterfly_fay_cycles) == 0) {
        VAR(butterfly_fay_number_of_cycles) = VAR(butterfly_fay_cycles_to_close);
    } else {
        VAR(butterfly_fay_number_of_cycles) = VAR(butterfly_fay_cycles);
    }
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double theta = atan2(FTy, FTx);
    double t = VAR(butterfly_fay_number_of_cycles) * theta;
    double rin = VAR(butterfly_fay_spread_split) * sqrt((FTx * FTx) + (FTy * FTy));
    double r = 0.5 * (exp(cos(t)) - (2 * cos(4 * t)) - pow(abs(sin(t / 12)), 5) + VAR(butterfly_fay_offset));
    if(VAR(butterfly_fay_fill) != 0) {
        r = r + (VAR(butterfly_fay_fill) * (random01() - 0.5));
    }
    double x = r * sin(t);
    double y = - 1 * r * cos(t);
    double xin, yin;
    double rinx, riny;
    if((abs(rin) > abs(r)) || (VAR(butterfly_fay_unified_inner_outer) == 1)) {
        switch(VAR(butterfly_fay_outer_mode)) {
            case 0 : FPx += VVAR * x;
            FPy += VVAR * y;
            break;
            case 1 : rinx = (rin * VAR(butterfly_fay_outer_spread) * VAR(butterfly_fay_outer_spread_ratio)) - (VAR(butterfly_fay_outer_spread) * VAR(butterfly_fay_outer_spread_ratio)) + 1;
            riny = (rin * VAR(butterfly_fay_outer_spread)) - VAR(butterfly_fay_outer_spread) + 1;
            FPx += VVAR * rinx * x;
            FPy += VVAR * riny * y;
            break;
            case 2 : xin = fabs(FTx);
            yin = fabs(FTy);
            if(x < 0) {
                xin = xin * - 1;
            }
            if(y < 0) {
                yin = yin * - 1;
            }
            FPx += VVAR * (x + (VAR(butterfly_fay_outer_spread) * VAR(butterfly_fay_outer_spread_ratio) * (xin - x)));
            FPy += VVAR * (y + (VAR(butterfly_fay_outer_spread) * (yin - y)));
            break;
            case 3 : xin = fabs(FTx);
            yin = fabs(FTy);
            if(x < 0) {
                xin = xin * - 1;
            }
            if(y < 0) {
                yin = yin * - 1;
            }
            FPx += VVAR * (x + (VAR(butterfly_fay_outer_spread) * VAR(butterfly_fay_outer_spread_ratio) * xin));
            FPy += VVAR * (y + (VAR(butterfly_fay_outer_spread) * yin));
            break;
            case 4 : rinx = (0.5 * rin) + (VAR(butterfly_fay_outer_spread) * VAR(butterfly_fay_outer_spread_ratio));
            riny = (0.5 * rin) + VAR(butterfly_fay_outer_spread);
            FPx += VVAR * rinx * x;
            FPy += VVAR * riny * y;
            break;
            case 5 : FPx += VVAR * (x + (VAR(butterfly_fay_outer_spread) * VAR(butterfly_fay_outer_spread_ratio) * FTx));
            FPy += VVAR * (y + (VAR(butterfly_fay_outer_spread) * FTy));
            break;
            default : FPx += VVAR * x;
            FPy += VVAR * y;
            break;
        }
    } else {
        switch(VAR(butterfly_fay_inner_mode)) {
            case 0 : FPx += VVAR * x;
            FPy += VVAR * y;
            break;
            case 1 : rinx = (rin * VAR(butterfly_fay_inner_spread) * VAR(butterfly_fay_inner_spread_ratio)) - (VAR(butterfly_fay_inner_spread) * VAR(butterfly_fay_inner_spread_ratio)) + 1;
            riny = (rin * VAR(butterfly_fay_inner_spread)) - VAR(butterfly_fay_inner_spread) + 1;
            FPx += VVAR * rinx * x;
            FPy += VVAR * riny * y;
            break;
            case 2 : xin = fabs(FTx);
            yin = fabs(FTy);
            if(x < 0) {
                xin = xin * - 1;
            }
            if(y < 0) {
                yin = yin * - 1;
            }
            FPx += VVAR * (x - (VAR(butterfly_fay_inner_spread) * VAR(butterfly_fay_inner_spread_ratio) * (x - xin)));
            FPy += VVAR * (y - (VAR(butterfly_fay_inner_spread) * (y - yin)));
            break;
            case 3 : xin = fabs(FTx);
            yin = fabs(FTy);
            if(x < 0) {
                xin = xin * - 1;
            }
            if(y < 0) {
                yin = yin * - 1;
            }
            FPx += VVAR * (x - (VAR(butterfly_fay_inner_spread) * VAR(butterfly_fay_inner_spread_ratio) * xin));
            FPy += VVAR * (y - (VAR(butterfly_fay_inner_spread) * yin));
            break;
            case 4 : rinx = (0.5 * rin) + (VAR(butterfly_fay_inner_spread) * VAR(butterfly_fay_inner_spread_ratio));
            riny = (0.5 * rin) + VAR(butterfly_fay_inner_spread);
            FPx += VVAR * rinx * x;
            FPy += VVAR * riny * y;
            break;
            case 5 : FPx += VVAR * (x + (VAR(butterfly_fay_inner_spread) * VAR(butterfly_fay_inner_spread_ratio) * FTx));
            FPy += VVAR * (y + (VAR(butterfly_fay_inner_spread) * FTy));
            break;
            default : FPx += VVAR * x;
            FPy += VVAR * y;
            break;
        }
    }
    
    return TRUE;
}

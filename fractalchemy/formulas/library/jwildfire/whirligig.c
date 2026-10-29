/*
    Fractalchemy formula library — translated from the JWildfire variation
        WhirligigFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    int whirligig_Mode;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("whirligig");

APO_VARIABLES(
    VAR_INTEGER(whirligig_Mode, 0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double csin = sin(FTx);
    double ccos = cos(FTx);
    double csinh = sinh(FTy);
    double ccosh = cosh(FTy);
    
    switch(VAR(whirligig_Mode)) {
        case 0 : FPx += VVAR * ccos / ccosh;
        FPy -= VVAR * csin / csinh;
        break;
        case 1 : FPx -= VVAR * ccos / ccosh;
        FPy += VVAR * csin / csinh;
        break;
        case 2 : FPx += VVAR * ccos / ccosh;
        FPy += VVAR * csin / csinh;
        break;
        case 3 : FPx -= VVAR * ccos / ccosh;
        FPy -= VVAR * csin / csinh;
        break;
        case 4 : FPx += VVAR * csin / ccosh;
        FPy -= VVAR * ccos / csinh;
        break;
        case 5 : FPx -= VVAR * csin / ccosh;
        FPy += VVAR * ccos / csinh;
        break;
        case 6 : FPx += VVAR * csin / ccosh;
        FPy += VVAR * ccos / csinh;
        break;
        case 7 : FPx -= VVAR * csin / ccosh;
        FPy -= VVAR * ccos / csinh;
        break;
        case 8 : FPx += VVAR * csin / csinh;
        FPy -= VVAR * ccos / ccosh;
        break;
        case 9 : FPx -= VVAR * csin / csinh;
        FPy += VVAR * ccos / ccosh;
        break;
        case 10 : FPx += VVAR * csin / csinh;
        FPy += VVAR * ccos / ccosh;
        break;
        case 11 : FPx -= VVAR * csin / csinh;
        FPy -= VVAR * ccos / ccosh;
        break;
        case 12 : FPx += VVAR * ccos / csinh;
        FPy -= VVAR * csin / ccosh;
        break;
        case 13 : FPx -= VVAR * ccos / csinh;
        FPy += VVAR * csin / ccosh;
        break;
        case 14 : FPx += VVAR * ccos / csinh;
        FPy += VVAR * csin / ccosh;
        break;
        case 15 : FPx -= VVAR * ccos / csinh;
        FPy -= VVAR * csin / ccosh;
        break;
        default : break;
    }
    return TRUE;
}

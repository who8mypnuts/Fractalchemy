/*
    Fractalchemy formula library — translated from the JWildfire variation
        Petal3DApoFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double petal3D_apo_width;
    double petal3D_apo_Zshape;
    double petal3D_apo_scale1;
    double petal3D_apo_scale2;
    double petal3D_apo_style;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("petal3D_apo");

APO_VARIABLES(
    VAR_REAL(petal3D_apo_width, 1),
    VAR_REAL(petal3D_apo_Zshape, 0.25),
    VAR_REAL(petal3D_apo_scale1, 0.25),
    VAR_REAL(petal3D_apo_scale2, 0.25),
    VAR_REAL(petal3D_apo_style, 0)
);

#define M_SQRT1_2 (sqrt(0.5))

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double shaper, shaper2, tmpPY, tmpPZ, tmpSmth;
    double squeeze;
    int posNeg = 1;
    if(random01() < 0.5) {
        posNeg = - 1;
    }
    double styleSign = VAR(petal3D_apo_style) >= 0 ? 1.0 : - 1.0;
    double a = cos(FTx);
    double bx = (cos(FTx) * cos(FTy)) * (cos(FTx) * cos(FTy)) * (cos(FTx) * cos(FTy));
    double by = (sin(FTx) * cos(FTy)) * (sin(FTx) * cos(FTy)) * (sin(FTx) * cos(FTy));
    FPx += VVAR * a * bx;
    tmpPY = VVAR * a * by * VAR(petal3D_apo_width);
    FPy += tmpPY;
    if(fabs(VAR(petal3D_apo_scale1)) > 1.0) {
        squeeze = fabs(VAR(petal3D_apo_scale1)) - 1.0;
        shaper = (- 1 * sin(FTx * VAR(petal3D_apo_scale1) * M_PI)) * 0.5 + (FTx * squeeze * 0.5) + sin(fabs(FTy * VAR(petal3D_apo_scale2) * M_PI));
        shaper2 = (- 1 * sin(FTx * VAR(petal3D_apo_scale1) * M_PI)) * 0.5 + (FTx * squeeze * 0.5) + tmpPY * VAR(petal3D_apo_scale2) * 0.5;
    } else {
        squeeze = 0.0;
        shaper = (- 1 * sin(FTx * VAR(petal3D_apo_scale1) * M_PI)) * 0.5 + sin(fabs(FTy * VAR(petal3D_apo_scale2) * M_PI));
        shaper2 = (- 1 * sin(FTx * VAR(petal3D_apo_scale1) * M_PI)) * 0.5 + tmpPY * VAR(petal3D_apo_scale2) * 0.5;
    }
    tmpSmth = 0.5 - sqr(VAR(petal3D_apo_style));
    tmpPZ = shaper;
    if(fabs(VAR(petal3D_apo_style)) > M_SQRT1_2) {
        tmpPZ = shaper2 * styleSign;
    } else if(VAR(petal3D_apo_style) < 0.0) {
        tmpPZ = tmpSmth * 2.0 * shaper - (1.0 - tmpSmth * 2.0) * shaper2;
    } else if(VAR(petal3D_apo_style) > 0.0) {
        tmpPZ = tmpSmth * 2.0 * shaper + (1.0 - tmpSmth * 2.0) * shaper2;
    }
    FPz += VVAR * tmpPZ * VAR(petal3D_apo_Zshape);
    return TRUE;
}

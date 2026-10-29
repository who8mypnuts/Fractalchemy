/*
    Fractalchemy formula library — translated from the JWildfire variation
        ShreddedFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double shredded_x1;
    double shredded_x2;
    double shredded_x3;
    double shredded_x_blur_amount;
    double shredded_y1;
    double shredded_y2;
    double shredded_y3;
    double shredded_y_blur_amount;
    double shredded_z1;
    double shredded_z2;
    double shredded_z3;
    double shredded_z_blur_amount;
    int shredded_type;
    int shredded_blur;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("shredded");

APO_VARIABLES(
    VAR_REAL(shredded_x1, 1),
    VAR_REAL(shredded_x2, 3),
    VAR_REAL(shredded_x3, 1),
    VAR_REAL(shredded_x_blur_amount, 0.1),
    VAR_REAL(shredded_y1, 1),
    VAR_REAL(shredded_y2, 3),
    VAR_REAL(shredded_y3, 1),
    VAR_REAL(shredded_y_blur_amount, 0.1),
    VAR_REAL(shredded_z1, 1),
    VAR_REAL(shredded_z2, 3),
    VAR_REAL(shredded_z3, 1),
    VAR_REAL(shredded_z_blur_amount, 0.1),
    VAR_INTEGER(shredded_type, 0),
    VAR_INTEGER(shredded_blur, 0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    if(VAR(shredded_blur) != 0) {
        if(VAR(shredded_type) == 2) {
            FPx += VVAR * VAR(shredded_x3) * (sin(VAR(shredded_x1) * floor(VAR(shredded_x2) * FTx))) + (VAR(shredded_x_blur_amount) * sin((2.0 * M_PI) * random01())) * FTx;
            FPy += VVAR * VAR(shredded_y3) * (cos(VAR(shredded_y1) * floor(VAR(shredded_y2) * FTy))) + (VAR(shredded_y_blur_amount) * sin((2.0 * M_PI) * random01())) * FTy;
            FPz += VVAR * VAR(shredded_z3) * (sin(VAR(shredded_z1) * floor(VAR(shredded_z2) * FTz))) + (VAR(shredded_z_blur_amount) * sin((2.0 * M_PI) * random01()));
        } else if(VAR(shredded_type) == 1) {
            FPx += VVAR * VAR(shredded_x3) * (sin(VAR(shredded_x1) * floor(VAR(shredded_x2) * FTx))) + (VAR(shredded_x_blur_amount) * sin((2.0 * M_PI) * random01())) * FTy;
            FPy += VVAR * VAR(shredded_y3) * (cos(VAR(shredded_y1) * floor(VAR(shredded_y2) * FTy))) + (VAR(shredded_y_blur_amount) * sin((2.0 * M_PI) * random01())) * FTx;
            FPz += VVAR * VAR(shredded_z3) * (sin(VAR(shredded_z1) * floor(VAR(shredded_z2) * FTz))) + (VAR(shredded_z_blur_amount) * sin((2.0 * M_PI) * random01()));
        } else if(VAR(shredded_type) == 0) {
            FPx += VVAR * VAR(shredded_x3) * (sin(VAR(shredded_x1) * floor(VAR(shredded_x2) * FTx)) + cos(VAR(shredded_x1) * floor(VAR(shredded_x2) * FTy))) + (VAR(shredded_x_blur_amount) * sin((2.0 * M_PI) * random01())) * FTy;
            FPy += VVAR * VAR(shredded_y3) * (cos(VAR(shredded_y1) * floor(VAR(shredded_y2) * FTy)) + sin(VAR(shredded_y1) * floor(VAR(shredded_y2) * FTx))) + (VAR(shredded_y_blur_amount) * sin((2.0 * M_PI) * random01())) * FTx;
            FPz += VVAR * VAR(shredded_z3) * (sin(VAR(shredded_z1) * floor(VAR(shredded_z2) * FTz)) + cos(VAR(shredded_z1) * floor(VAR(shredded_z2) * FTz))) + (VAR(shredded_z_blur_amount) * sin((2.0 * M_PI) * random01())) * FTz;
        }
    } else {
        if(VAR(shredded_type) == 2) {
            FPx += VVAR * VAR(shredded_x3) * sin(VAR(shredded_x1) * floor(VAR(shredded_x2) * FTx)) * FTx;
            FPy += VVAR * VAR(shredded_y3) * cos(VAR(shredded_y1) * floor(VAR(shredded_y2) * FTy)) * FTy;
            FPz += VVAR * VAR(shredded_z3) * sin(VAR(shredded_z1) * floor(VAR(shredded_z2) * FTz)) * FTz;
        } else if(VAR(shredded_type) == 1) {
            FPx += VVAR * VAR(shredded_x3) * sin(VAR(shredded_x1) * floor(VAR(shredded_x2) * FTx)) * FTy;
            FPy += VVAR * VAR(shredded_y3) * cos(VAR(shredded_y1) * floor(VAR(shredded_y2) * FTy)) * FTx;
            FPz += VVAR * VAR(shredded_z3) * sin(VAR(shredded_z1) * floor(VAR(shredded_z2) * FTz)) * FTz;
        } else if(VAR(shredded_type) == 0) {
            FPx += VVAR * VAR(shredded_x3) * (sin(VAR(shredded_x1) * floor(VAR(shredded_x2) * FTx)) + cos(VAR(shredded_x1) * floor(VAR(shredded_x2) * FTy))) * FTy;
            FPy += VVAR * VAR(shredded_y3) * (cos(VAR(shredded_y1) * floor(VAR(shredded_y2) * FTy)) + sin(VAR(shredded_y1) * floor(VAR(shredded_y2) * FTx))) * FTx;
            FPz += VVAR * VAR(shredded_z3) * (sin(VAR(shredded_z1) * floor(VAR(shredded_z2) * FTz)) + cos(VAR(shredded_z1) * floor(VAR(shredded_z2) * FTz))) * FTz;
        }
    }
    return TRUE;
}

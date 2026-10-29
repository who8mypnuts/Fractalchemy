/*
    Fractalchemy formula library — translated from the JWildfire variation
        PixelFlowFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double pixel_flow_angle;
    double pixel_flow_len;
    double pixel_flow_width;
    int pixel_flow_seed;
    int pixel_flow_enable_dc;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("pixel_flow");

APO_VARIABLES(
    VAR_REAL(pixel_flow_angle, 90),
    VAR_REAL(pixel_flow_len, 0.1),
    VAR_REAL(pixel_flow_width, 200),
    VAR_INTEGER(pixel_flow_seed, 42),
    VAR_INTEGER(pixel_flow_enable_dc, 0)
);

double hash(int a)
{
    a = (a ^ 61) ^ (a >> 16);
    a = a + (a << 3);
    a = a ^ (a >> 4);
    a = a * 0x27d4eb2d;
    a = a ^ (a >> 15);
    return(double) a / (double) INT_MAX;
}

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double a_rad = VAR(pixel_flow_angle) * 0.0174532925;
    double sina = sin(a_rad);
    double cosa = cos(a_rad);
    int blockx = (int) floor(FTx * VAR(pixel_flow_width));
    blockx += (2.0 - 4.0 * hash(blockx * VAR(pixel_flow_seed) + 1));
    int blocky = (int) floor(FTy * VAR(pixel_flow_width));
    blocky += (2.0 - 4.0 * hash(blocky * VAR(pixel_flow_seed) + 1));
    double fLen = (hash(blocky + blockx * - VAR(pixel_flow_seed)) + hash(blockx + blocky * VAR(pixel_flow_seed) / 2)) * 0.5;
    double r01 = random01();
    double fade = fLen * r01 * r01 * r01 * r01;
    FPx += VVAR * VAR(pixel_flow_len) * cosa * fade;
    FPy += VVAR * VAR(pixel_flow_len) * sina * fade;
    if(VAR(pixel_flow_enable_dc) == 1) TC = r01;
    
    return TRUE;
}

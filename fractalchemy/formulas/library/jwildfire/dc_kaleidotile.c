/*
    Fractalchemy formula library — translated from the JWildfire variation
        DCKaleidotileFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

// keeps a private orbit between points (JWildfire fields updated per point): the statics below
typedef struct {
    double dc_kaleidotile_pull;
    double dc_kaleidotile_rotate;
    double dc_kaleidotile_line_up;
    double dc_kaleidotile_x;
    double dc_kaleidotile_y;
    double dc_kaleidotile_color1;
    double dc_kaleidotile_color2;
    double dc_kaleidotile_speed1;
    double dc_kaleidotile_speed2;
    double dc_kaleidotile__q;
    double dc_kaleidotile__q1;
    double dc_kaleidotile__w;
    double dc_kaleidotile__w1;
    double dc_kaleidotile__e;
    double dc_kaleidotile__e1;
    double dc_kaleidotile__r;
    double dc_kaleidotile__r1;
    double dc_kaleidotile__t;
    double dc_kaleidotile__t1;
    double dc_kaleidotile__i;
    double dc_kaleidotile_c11;
    double dc_kaleidotile_c12;
    double dc_kaleidotile_c21;
    double dc_kaleidotile_c22;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("dc_kaleidotile");

APO_VARIABLES(
    VAR_REAL(dc_kaleidotile_pull, -1.5),
    VAR_REAL(dc_kaleidotile_rotate, 0),
    VAR_REAL(dc_kaleidotile_line_up, 1),
    VAR_REAL(dc_kaleidotile_x, 0),
    VAR_REAL(dc_kaleidotile_y, 0),
    VAR_REAL(dc_kaleidotile_color1, 0),
    VAR_REAL(dc_kaleidotile_speed1, 0),
    VAR_REAL(dc_kaleidotile_color2, 1),
    VAR_REAL(dc_kaleidotile_speed2, 0)
);

static double oldColor = 0;
static double newColor = 0;

int PluginVarPrepare(Variation* vp)
{
    VAR(dc_kaleidotile__q) = VAR(dc_kaleidotile_pull);
    VAR(dc_kaleidotile__q1) = - VAR(dc_kaleidotile_pull);
    VAR(dc_kaleidotile__w) = VAR(dc_kaleidotile_rotate);
    VAR(dc_kaleidotile__w1) = - VAR(dc_kaleidotile_rotate);
    VAR(dc_kaleidotile__e) = VAR(dc_kaleidotile_line_up);
    VAR(dc_kaleidotile__e1) = - VAR(dc_kaleidotile_line_up);
    VAR(dc_kaleidotile__r) = VAR(dc_kaleidotile_x);
    VAR(dc_kaleidotile__r1) = - VAR(dc_kaleidotile_x);
    VAR(dc_kaleidotile__t) = VAR(dc_kaleidotile_y);
    VAR(dc_kaleidotile__t1) = - VAR(dc_kaleidotile_y);
    VAR(dc_kaleidotile_c11) = (1 + VAR(dc_kaleidotile_speed1)) / 2;
    VAR(dc_kaleidotile_c12) = VAR(dc_kaleidotile_color1) * (1 - VAR(dc_kaleidotile_speed1)) / 2;
    VAR(dc_kaleidotile_c21) = (1 + VAR(dc_kaleidotile_speed2)) / 2;
    VAR(dc_kaleidotile_c22) = VAR(dc_kaleidotile_color2) * (1 - VAR(dc_kaleidotile_speed2)) / 2;
    oldColor = 0.5;
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    if(random01() < 0.5) {
        double xin = FTx * 0.831;
        double yin = FTy * 0.831;
        FPx += (((VAR(dc_kaleidotile__w) * xin) * cos(45.0) - yin * sin(45.0) + VAR(dc_kaleidotile__e)) + VAR(dc_kaleidotile__r));
        if(yin > 0) {
            FPy += (((VAR(dc_kaleidotile__w) * yin) * cos(45.0) + xin * sin(45.0) + VAR(dc_kaleidotile__q) + VAR(dc_kaleidotile__e)) + VAR(dc_kaleidotile__t));
        } else {
            FPy += ((VAR(dc_kaleidotile__w) * yin) * cos(45.0) + xin * sin(45.0) - VAR(dc_kaleidotile__q) - VAR(dc_kaleidotile__e));
        }
        newColor = oldColor * VAR(dc_kaleidotile_c11) + VAR(dc_kaleidotile_c12);
    } else {
        double xin = FTx * 0.831;
        double yin = FTy * 0.831;
        FPx += (((VAR(dc_kaleidotile__w1) * xin) * cos(45.0) - yin * sin(45.0) + VAR(dc_kaleidotile__e1)) + VAR(dc_kaleidotile__r1));
        if(yin > 0) {
            FPy += (((VAR(dc_kaleidotile__w1) * yin) * cos(45.0) + xin * sin(45.0) + VAR(dc_kaleidotile__q1) + VAR(dc_kaleidotile__e1)) + VAR(dc_kaleidotile__t1));
        } else {
            FPy += ((VAR(dc_kaleidotile__w1) * yin) * cos(45.0) + xin * sin(45.0) - VAR(dc_kaleidotile__q1) - VAR(dc_kaleidotile__e1));
        }
        newColor = oldColor * VAR(dc_kaleidotile_c21) + VAR(dc_kaleidotile_c22);
    }
    TC = fmod(newColor, 1);
    oldColor = newColor;
    
    return TRUE;
}

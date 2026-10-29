/*
    Fractalchemy formula library — translated from the JWildfire variation
        MultiIFSFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    int multi_ifs_ifs_type;
    int multi_ifs_coloring_mode;
    double multi_ifs_color_speed;
    double multi_ifs_color1;
    double multi_ifs_color2;
    double multi_ifs_color3;
    double multi_ifs_color4;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("multi_ifs");

APO_VARIABLES(
    VAR_INTEGER(multi_ifs_ifs_type, 0),
    VAR_INTEGER(multi_ifs_coloring_mode, 0),
    VAR_REAL(multi_ifs_color_speed, 0.5),
    VAR_REAL(multi_ifs_color1, 0),
    VAR_REAL(multi_ifs_color2, 0.25),
    VAR_REAL(multi_ifs_color3, 0.5),
    VAR_REAL(multi_ifs_color4, 0.75)
);

#define S3D2 (0.4330127018922193)

double fract(double x)
{
    return x - floor(x);
}

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double x = FTx;
    double y = FTy;
    double nx = 0.0, ny = 0.0;
    double newColor = 0.0;
    double rand = random01();
    switch(VAR(multi_ifs_ifs_type)) {
        case 1 : if(rand < 0.25) {
            nx = 0.5 * x;
            ny = 0.5 * y;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = - 0.25 * x - S3D2 * y + 0.25;
            ny = S3D2 * x - 0.25 * y + S3D2;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = - 0.25 * x + S3D2 * y - 0.5;
            ny = - S3D2 * x - 0.25 * y;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = - 0.5 * x - 0.25;
            ny = - 0.5 * y + S3D2;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 2 : if(rand < 0.25) {
            nx = 0.5 * x;
            ny = 0.5 * y;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = 0.5 * x - 0.5;
            ny = 0.5 * y + 0.5;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = - 0.5 * x + 0.5;
            ny = 0.5 * y + 0.5;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = 0.5 * y + 0.5;
            ny = - 0.5 * x + 0.5;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 3 : if(rand < 0.25) {
            nx = 0.5 * x;
            ny = 0.5 * y;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = - 0.5 * x + 0.5;
            ny = 0.5 * y;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = - 0.25 * x - S3D2 * y + 0.25;
            ny = - S3D2 * x + 0.25 * y + S3D2;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = - 0.25 * x + S3D2 * y + 0.25;
            ny = - S3D2 * x - 0.25 * y + S3D2;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 4 : if(rand < 0.25) {
            nx = 0.5 * x;
            ny = 0.5 * y;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = 0.5 * x + 0.5;
            ny = 0.5 * y;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = 0.5 * x;
            ny = 0.5 * y + 0.5;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = 0.5 * y + 0.5;
            ny = - 0.5 * x + 1.0;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 5 : if(rand < 0.25) {
            nx = (0.25 * x) + (- 0.4330127018922193 * y) + 0;
            ny = (0.4330127018922193 * x) + (0.25 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (- 0.25 * x) + (0.4330127018922193 * y) - 0.5;
            ny = (- 0.4330127018922193 * x) + (- 0.25 * y) + 0;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (- 0.25 * x) + (0.4330127018922193 * y) + 0.25;
            ny = (- 0.4330127018922193 * x) + (- 0.25 * y) - 0.4330127018922193;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (- 0.25 * x) + (0.4330127018922193 * y) + 0.25;
            ny = (- 0.4330127018922193 * x) + (- 0.25 * y) + 0.4330127018922193;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 6 : if(rand < 0.25) {
            nx = (- 0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (- 0.25 * x) + (- 0.4330127018922193 * y) + 0.25;
            ny = (- 0.4330127018922194 * x) + (0.25 * y) - 0.4330127018922194;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (- 0.25 * x) + (- 0.4330127018922193 * y) - 0.5;
            ny = (0.4330127018922194 * x) + (- 0.25 * y) - 0.8660254037844387;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (0.5 * x) + (0 * y) + 1.0;
            ny = (0 * x) + (0.5 * y) + 0;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 7 : if(rand < 0.25) {
            nx = (0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (- 0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0 * x) + (- 0.5 * y) + 0;
            ny = (0.5 * x) + (0 * y) - 0.5;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (0 * x) + (0.5 * y) + 0;
            ny = (0.5 * x) + (0 * y) - 0.5;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (0.5 * x) + (0 * y) - 0.5;
            ny = (0 * x) + (0.5 * y) + 0;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 8 : if(rand < 0.25) {
            nx = (- 0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (- 0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0.5 * x) + (0 * y) - 0.25;
            ny = (0 * x) + (- 0.5 * y) + 0.4330127018922194;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (0.25 * x) + (- 0.4330127018922193 * y) + 0.25;
            ny = (0.4330127018922194 * x) + (0.25 * y) + 0.4330127018922194;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (0.25 * x) + (- 0.4330127018922193 * y) + 0.25;
            ny = (0.4330127018922194 * x) + (0.25 * y) - 0.4330127018922194;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 9 : if(rand < 0.25) {
            nx = (0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (- 0.25 * x) + (0.4330127018922193 * y) - 0.5;
            ny = (- 0.4330127018922194 * x) + (- 0.25 * y) + 0;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (- 0.25 * x) + (0.4330127018922193 * y) - 0.25;
            ny = (0.4330127018922194 * x) + (0.25 * y) + 0.4330127018922194;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (- 0.25 * x) + (- 0.4330127018922193 * y) - 0.25;
            ny = (- 0.4330127018922194 * x) + (- 0.25 * y) + 0.4330127018922194;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 10 : if(rand < 0.25) {
            nx = (- 0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0.5 * x) + (0 * y) - 1;
            ny = (0 * x) + (- 0.5 * y) - 1.5;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (- 0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (- 0.5 * y) - 1;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (0.5 * x) + (0 * y) - 1;
            ny = (0 * x) + (0.5 * y) - 1.5;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 11 : if(rand < 0.25) {
            nx = (0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (- 0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (- 0.5 * x) + (0 * y) + 0.5;
            ny = (0 * x) + (0.5 * y) + 0;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (- 0.25 * x) + (- 0.4330127018922193 * y) + 0.25;
            ny = (- 0.4330127018922194 * x) + (0.25 * y) + 0.4330127018922194;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (- 0.25 * x) + (0.4330127018922193 * y) + 0.25;
            ny = (- 0.4330127018922194 * x) + (- 0.25 * y) + 0.4330127018922194;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 12 : if(rand < 0.25) {
            nx = (0 * x) + (0.5 * y) + 0;
            ny = (0.5 * x) + (0 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0 * x) + (0.5 * y) + 0;
            ny = (0.5 * x) + (0 * y) - 0.5;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (0 * x) + (0.5 * y) + 0;
            ny = (- 0.5 * x) + (0 * y) - 0.5;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (0 * x) + (- 0.5 * y) - 1;
            ny = (- 0.5 * x) + (0 * y) - 1;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 13 : if(rand < 0.25) {
            nx = (- 0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (- 0.25 * x) + (- 0.4330127018922193 * y) + 0.5;
            ny = (- 0.4330127018922194 * x) + (0.25 * y) + 0;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (0.5 * x) + (0 * y) + 0.5;
            ny = (0 * x) + (- 0.5 * y) + 0;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (- 0.25 * x) + (0.4330127018922193 * y) + 0.5;
            ny = (0.4330127018922194 * x) + (0.25 * y) + 0;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 14 : if(rand < 0.25) {
            nx = (0 * x) + (- 0.5 * y) + 0;
            ny = (- 0.5 * x) + (0 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0 * x) + (- 0.5 * y) + 0;
            ny = (0.5 * x) + (0 * y) + 0.5;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (0 * x) + (- 0.5 * y) - 0.5;
            ny = (- 0.5 * x) + (0 * y) + 0;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (0 * x) + (0.5 * y) - 0.5;
            ny = (0.5 * x) + (0 * y) + 0.5;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 15 : if(rand < 0.25) {
            nx = (0 * x) + (- 0.5 * y) + 0;
            ny = (- 0.5 * x) + (0 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0.5 * x) + (0 * y) - 1;
            ny = (0 * x) + (0.5 * y) + 0;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (0 * x) + (0.5 * y) - 1.5;
            ny = (0.5 * x) + (0 * y) + 0.5;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (0 * x) + (- 0.5 * y) - 0.5;
            ny = (- 0.5 * x) + (0 * y) + 0.5;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 16 : if(rand < 0.25) {
            nx = (- 0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0 * x) + (0.5 * y) + 0.5;
            ny = (- 0.5 * x) + (0 * y) - 0.5;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (0 * x) + (0.5 * y) + 2;
            ny = (- 0.5 * x) + (0 * y) - 0.5;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (0.5 * x) + (0 * y) + 1;
            ny = (0 * x) + (- 0.5 * y) - 1.5;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 17 : if(rand < 0.25) {
            nx = (- 0.25 * x) + (- 0.4330127018922193 * y) + 0;
            ny = (- 0.4330127018922194 * x) + (0.25 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (- 0.25 * x) + (- 0.4330127018922193 * y) + 0.5;
            ny = (- 0.4330127018922194 * x) + (0.25 * y) - 0.8660254037844387;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (0.25 * x) + (0.4330127018922193 * y) + 0.25;
            ny = (0.4330127018922194 * x) + (- 0.25 * y) - 1.299038105676658;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (- 0.25 * x) + (- 0.4330127018922193 * y) + 1.25;
            ny = (- 0.4330127018922194 * x) + (0.25 * y) + 0.4330127018922194;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 18 : if(rand < 0.25) {
            nx = (0 * x) + (- 0.5 * y) + 0;
            ny = (- 0.5 * x) + (0 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (- 0.5 * y) - 0.5;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (- 0.5 * x) + (0 * y) + 0.5;
            ny = (0 * x) + (0.5 * y) - 0.5;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (0 * x) + (- 0.5 * y) + 0;
            ny = (- 0.5 * x) + (0 * y) - 0.5;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 19 : if(rand < 0.25) {
            nx = (0 * x) + (0.5 * y) + 0;
            ny = (0.5 * x) + (0 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (- 0.5 * x) + (0 * y) + 0.5;
            ny = (0 * x) + (0.5 * y) + 0;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (0 * x) + (0.5 * y) + 0.5;
            ny = (0.5 * x) + (0 * y) + 0;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (0 * x) + (- 0.5 * y) + 0.5;
            ny = (- 0.5 * x) + (0 * y) + 0.5;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 20 : if(rand < 0.25) {
            nx = (0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (- 0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0 * x) + (0.5 * y) + 0.5;
            ny = (0.5 * x) + (0 * y) + 0;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (0 * x) + (- 0.5 * y) + 0.5;
            ny = (- 0.5 * x) + (0 * y) + 0.5;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (- 0.5 * x) + (0 * y) + 0.5;
            ny = (0 * x) + (- 0.5 * y) + 0;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 21 : if(rand < 0.25) {
            nx = (0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (- 0.5 * x) + (0 * y) - 0.5;
            ny = (0 * x) + (- 0.5 * y) + 0.5;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (0 * x) + (0.5 * y) - 0.5;
            ny = (0.5 * x) + (0 * y) + 1;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (- 0.5 * x) + (0 * y) - 0.5;
            ny = (0 * x) + (- 0.5 * y) + 1;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 22 : if(rand < 0.25) {
            nx = (0 * x) + (0.5 * y) + 0;
            ny = (0.5 * x) + (0 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0.5 * x) + (0 * y) - 0.5;
            ny = (0 * x) + (- 0.5 * y) - 0.5;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (0.5 * x) + (0 * y) - 0.5;
            ny = (0 * x) + (- 0.5 * y) - 1;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (0 * x) + (0.5 * y) - 1.5;
            ny = (0.5 * x) + (0 * y) + 0;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 23 : if(rand < 0.25) {
            nx = (0 * x) + (0.5 * y) + 0;
            ny = (0.5 * x) + (0 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (- 0.5 * x) + (0 * y) - 0.5;
            ny = (0 * x) + (- 0.5 * y) - 0.5;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (- 0.5 * y) - 1;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (0 * x) + (- 0.5 * y) - 0.5;
            ny = (0.5 * x) + (0 * y) - 0.5;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 24 : if(rand < 0.25) {
            nx = (0.25 * x) + (0.4330127018922193 * y) + 0;
            ny = (0.4330127018922194 * x) + (- 0.25 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0.25 * x) + (0.4330127018922193 * y) + 0.5;
            ny = (0.4330127018922194 * x) + (- 0.25 * y) - 0.8660254037844387;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (- 0.25 * x) + (- 0.4330127018922193 * y) + 1.5;
            ny = (- 0.4330127018922194 * x) + (0.25 * y) + 0;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (0.25 * x) + (0.4330127018922193 * y) + 1.5;
            ny = (0.4330127018922194 * x) + (- 0.25 * y) + 0;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 25 : if(rand < 0.25) {
            nx = (0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0.25 * x) + (0.4330127018922193 * y) - 0.25;
            ny = (- 0.4330127018922194 * x) + (0.25 * y) + 0.4330127018922194;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (- 0.5 * x) + (0 * y) + 0.5;
            ny = (0 * x) + (0.5 * y) + 0;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (- 0.25 * x) + (0.4330127018922193 * y) + 0.25;
            ny = (- 0.4330127018922194 * x) + (- 0.25 * y) + 0.4330127018922194;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 26 : if(rand < 0.25) {
            nx = (0.25 * x) + (- 0.4330127018922193 * y) + 0;
            ny = (0.4330127018922194 * x) + (0.25 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (- 0.25 * x) + (- 0.4330127018922193 * y) + 0.25;
            ny = (0.4330127018922194 * x) + (- 0.25 * y) - 0.4330127018922194;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (0.5 * x) + (0 * y) + 0.25;
            ny = (0 * x) + (- 0.5 * y) - 0.4330127018922194;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (0.5 * x) + (0 * y) + 0.25;
            ny = (0 * x) + (0.5 * y) - 0.4330127018922194;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 27 : if(rand < 0.25) {
            nx = (0.25 * x) + (0.4330127018922193 * y) + 0;
            ny = (- 0.4330127018922194 * x) + (0.25 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0.25 * x) + (- 0.4330127018922193 * y) + 0.5;
            ny = (0.4330127018922194 * x) + (0.25 * y) + 0;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (- 0.5 * x) + (0 * y) - 0.5;
            ny = (0 * x) + (- 0.5 * y) + 0;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (- 0.5 * x) + (0 * y) + 0.25;
            ny = (0 * x) + (- 0.5 * y) + 0.4330127018922194;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 28 : if(rand < 0.25) {
            nx = (0.25 * x) + (0.4330127018922193 * y) + 0;
            ny = (- 0.4330127018922194 * x) + (0.25 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0.5 * x) + (0 * y) + 0.25;
            ny = (0 * x) + (- 0.5 * y) + 0.4330127018922194;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (- 0.25 * x) + (0.4330127018922193 * y) + 0.25;
            ny = (0.4330127018922194 * x) + (0.25 * y) - 0.4330127018922194;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (- 0.5 * x) + (0 * y) - 0.75;
            ny = (0 * x) + (- 0.5 * y) + 0.4330127018922194;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 29 : if(rand < 0.25) {
            nx = (- 0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (- 0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0 * x) + (0.5 * y) + 0.5;
            ny = (- 0.5 * x) + (0 * y) + 0.5;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (- 0.5 * x) + (0 * y) + 1.5;
            ny = (0 * x) + (- 0.5 * y) + 0;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (0.5 * y) - 0.5;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 30 : if(rand < 0.25) {
            nx = (- 0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (- 0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0.5 * x) + (0 * y) - 0.25;
            ny = (0 * x) + (0.5 * y) + 1.299038105676658;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (0.25 * x) + (0.4330127018922193 * y) - 0.75;
            ny = (0.4330127018922194 * x) + (- 0.25 * y) - 0.4330127018922194;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (0.25 * x) + (0.4330127018922193 * y) - 0.25;
            ny = (0.4330127018922194 * x) + (- 0.25 * y) + 1.299038105676658;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 31 : if(rand < 0.25) {
            nx = (0 * x) + (- 0.5 * y) + 0;
            ny = (0.5 * x) + (0 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0 * x) + (0.5 * y) - 0.5;
            ny = (- 0.5 * x) + (0 * y) + 2;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (0 * x) + (0.5 * y) - 1;
            ny = (- 0.5 * x) + (0 * y) + 1;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (0 * x) + (0.5 * y) - 1.5;
            ny = (- 0.5 * x) + (0 * y) + 0;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 32 : if(rand < 0.25) {
            nx = (- 0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (- 0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0 * x) + (0.5 * y) + 0.5;
            ny = (0.5 * x) + (0 * y) - 1;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (- 0.5 * x) + (0 * y) + 1.5;
            ny = (0 * x) + (- 0.5 * y) + 0;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (0 * x) + (- 0.5 * y) + 0.5;
            ny = (- 0.5 * x) + (0 * y) - 0.5;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 33 : if(rand < 0.25) {
            nx = (0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (- 0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (- 0.25 * x) + (0.4330127018922193 * y) + 0.5;
            ny = (0.4330127018922194 * x) + (0.25 * y) + 0;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (- 0.5 * x) + (0 * y) + 0.5;
            ny = (0 * x) + (- 0.5 * y) + 0;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (- 0.25 * x) + (- 0.4330127018922193 * y) + 0.5;
            ny = (0.4330127018922194 * x) + (- 0.25 * y) + 0;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 34 : if(rand < 0.25) {
            nx = (0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (- 0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0.5 * x) + (0 * y) - 1.5;
            ny = (0 * x) + (- 0.5 * y) + 0;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (- 0.5 * x) + (0 * y) - 1.5;
            ny = (0 * x) + (0.5 * y) - 0.5;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (- 0.5 * y) + 1.5;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 35 : if(rand < 0.25) {
            nx = (- 0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0.5 * x) + (0 * y) - 1;
            ny = (0 * x) + (- 0.5 * y) - 1.5;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (- 0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (- 0.5 * y) - 1;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (0.5 * x) + (0 * y) - 1;
            ny = (0 * x) + (0.5 * y) - 1.5;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 36 : if(rand < 0.25) {
            nx = (0.25 * x) + (- 0.4330127018922193 * y) + 0;
            ny = (0.4330127018922194 * x) + (0.25 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (- 0.5 * x) + (0 * y) + 0.5;
            ny = (0 * x) + (- 0.5 * y) + 0;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (- 0.5 * x) + (0 * y) + 1.25;
            ny = (0 * x) + (- 0.5 * y) - 1.299038105676658;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (0.25 * x) + (0.4330127018922193 * y) + 0.25;
            ny = (- 0.4330127018922194 * x) + (0.25 * y) + 0.4330127018922194;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 37 : if(rand < 0.25) {
            nx = (0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (- 0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0.25 * x) + (0.4330127018922193 * y) - 0.25;
            ny = (- 0.4330127018922194 * x) + (0.25 * y) + 0.4330127018922194;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (- 0.5 * x) + (0 * y) + 0.5;
            ny = (0 * x) + (0.5 * y) + 0;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (- 0.25 * x) + (0.4330127018922193 * y) + 0.25;
            ny = (- 0.4330127018922194 * x) + (- 0.25 * y) + 0.4330127018922194;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 38 : if(rand < 0.25) {
            nx = (- 0.25 * x) + (0.4330127018922193 * y) + 0;
            ny = (0.4330127018922194 * x) + (0.25 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0.25 * x) + (- 0.4330127018922193 * y) + 0.5;
            ny = (0.4330127018922194 * x) + (0.25 * y) + 0;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (- 0.5 * x) + (0 * y) - 0.5;
            ny = (0 * x) + (- 0.5 * y) + 0;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (- 0.5 * x) + (0 * y) + 0.25;
            ny = (0 * x) + (- 0.5 * y) + 0.4330127018922194;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 39 : if(rand < 0.25) {
            nx = (- 0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (- 0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0 * x) + (- 0.5 * y) - 0.5;
            ny = (0.5 * x) + (0 * y) - 1;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (0 * x) + (0.5 * y) + 0.5;
            ny = (- 0.5 * x) + (0 * y) + 0.5;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (- 0.5 * x) + (0 * y) + 1.5;
            ny = (0 * x) + (- 0.5 * y) + 0;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 40 : if(rand < 0.25) {
            nx = (0 * x) + (- 0.5 * y) + 0;
            ny = (- 0.5 * x) + (0 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0.5 * x) + (0 * y) - 1;
            ny = (0 * x) + (0.5 * y) + 0;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (0 * x) + (0.5 * y) - 1.5;
            ny = (0.5 * x) + (0 * y) + 0.5;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (0 * x) + (- 0.5 * y) - 0.5;
            ny = (- 0.5 * x) + (0 * y) + 0.5;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 41 : if(rand < 0.25) {
            nx = (0 * x) + (- 0.5 * y) + 0;
            ny = (- 0.5 * x) + (0 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0 * x) + (- 0.5 * y) + 0;
            ny = (0.5 * x) + (0 * y) + 0.5;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (0 * x) + (- 0.5 * y) - 0.5;
            ny = (- 0.5 * x) + (0 * y) + 0;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (0 * x) + (0.5 * y) - 0.5;
            ny = (0.5 * x) + (0 * y) + 0.5;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 42 : if(rand < 0.25) {
            nx = (0.25 * x) + (0.4330127018922193 * y) + 0;
            ny = (- 0.4330127018922194 * x) + (0.25 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0.5 * x) + (0 * y) + 0.25;
            ny = (0 * x) + (- 0.5 * y) + 0.4330127018922194;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (- 0.25 * x) + (0.4330127018922193 * y) + 0.25;
            ny = (0.4330127018922194 * x) + (0.25 * y) - 0.4330127018922194;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (- 0.5 * x) + (0 * y) - 0.75;
            ny = (0 * x) + (- 0.5 * y) + 0.4330127018922194;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 43 : if(rand < 0.25) {
            nx = (0.25 * x) + (0.4330127018922193 * y) + 0;
            ny = (- 0.4330127018922194 * x) + (0.25 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0.25 * x) + (- 0.4330127018922193 * y) + 0.5;
            ny = (0.4330127018922194 * x) + (0.25 * y) + 0;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (- 0.5 * x) + (0 * y) - 0.5;
            ny = (0 * x) + (- 0.5 * y) + 0;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (- 0.5 * x) + (0 * y) + 0.25;
            ny = (0 * x) + (- 0.5 * y) + 0.4330127018922194;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 44 : if(rand < 0.25) {
            nx = (- 0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (- 0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (- 0.25 * x) + (- 0.4330127018922193 * y) + 0.25;
            ny = (- 0.4330127018922194 * x) + (0.25 * y) - 0.4330127018922194;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (- 0.25 * x) + (0.4330127018922193 * y) + 0.25;
            ny = (- 0.4330127018922194 * x) + (- 0.25 * y) - 0.4330127018922194;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (0.5 * x) + (0 * y) - 0.5;
            ny = (0 * x) + (0.5 * y) + 0;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 45 : if(rand < 0.25) {
            nx = (- 0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0 * x) + (0.5 * y) + 0.5;
            ny = (- 0.5 * x) + (0 * y) - 0.5;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (- 0.5 * x) + (0 * y) - 0.5;
            ny = (0 * x) + (0.5 * y) - 0.5;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (- 0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (- 0.5 * y) - 1;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 46 : if(rand < 0.25) {
            nx = (0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0.5 * x) + (0 * y) - 1.5;
            ny = (0 * x) + (0.5 * y) - 0.5;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (0.5 * y) - 2;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (0.5 * x) + (0 * y) + 0.5;
            ny = (0 * x) + (0.5 * y) - 0.5;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 47 : if(rand < 0.25) {
            nx = (0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (- 0.5 * x) + (0 * y) - 1;
            ny = (0 * x) + (0.5 * y) + 0;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (0 * x) + (0.5 * y) - 0.5;
            ny = (- 0.5 * x) + (0 * y) - 0.5;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (- 0.5 * x) + (0 * y) - 0.5;
            ny = (0 * x) + (- 0.5 * y) - 0.5;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 48 : if(rand < 0.25) {
            nx = (- 0.25 * x) + (0.4330127018922193 * y) + 0;
            ny = (0.4330127018922194 * x) + (0.25 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (- 0.25 * x) + (0.4330127018922193 * y) - 0.75;
            ny = (0.4330127018922194 * x) + (0.25 * y) + 0.4330127018922194;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (0.5 * x) + (0 * y) - 0.5;
            ny = (0 * x) + (- 0.5 * y) + 0;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (0.25 * x) + (- 0.4330127018922193 * y) - 0.5;
            ny = (0.4330127018922194 * x) + (0.25 * y) + 0;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 49 : if(rand < 0.25) {
            nx = (0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (- 0.5 * x) + (0 * y) - 0.5;
            ny = (0 * x) + (- 0.5 * y) + 0.5;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (0 * x) + (0.5 * y) - 0.5;
            ny = (0.5 * x) + (0 * y) + 1;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (- 0.5 * x) + (0 * y) - 0.5;
            ny = (0 * x) + (- 0.5 * y) + 1;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 50 : if(rand < 0.25) {
            nx = (- 0.25 * x) + (0.4330127018922193 * y) + 0;
            ny = (0.4330127018922194 * x) + (0.25 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (- 0.25 * x) + (- 0.4330127018922193 * y) - 0.25;
            ny = (- 0.4330127018922194 * x) + (0.25 * y) + 0.4330127018922194;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (0.25 * x) + (0.4330127018922193 * y) - 0.25;
            ny = (- 0.4330127018922194 * x) + (0.25 * y) + 0.4330127018922194;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (- 0.25 * x) + (- 0.4330127018922193 * y) + 0.5;
            ny = (- 0.4330127018922194 * x) + (0.25 * y) + 0;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 51 : if(rand < 0.25) {
            nx = (0.25 * x) + (0.4330127018922193 * y) + 0;
            ny = (0.4330127018922194 * x) + (- 0.25 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0.5 * x) + (0 * y) - 0.25;
            ny = (0 * x) + (- 0.5 * y) - 0.4330127018922194;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (0.25 * x) + (0.4330127018922193 * y) - 0.25;
            ny = (0.4330127018922194 * x) + (- 0.25 * y) - 0.4330127018922194;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (0.25 * x) + (- 0.4330127018922193 * y) - 0.25;
            ny = (- 0.4330127018922194 * x) + (- 0.25 * y) - 0.4330127018922194;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 52 : if(rand < 0.25) {
            nx = (0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (- 0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (- 0.25 * x) + (0.4330127018922193 * y) - 0.25;
            ny = (0.4330127018922194 * x) + (0.25 * y) - 0.4330127018922194;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (- 0.5 * y) - 0.8660254037844387;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (- 0.25 * x) + (- 0.4330127018922193 * y) + 0.25;
            ny = (- 0.4330127018922194 * x) + (0.25 * y) - 0.4330127018922194;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 53 : if(rand < 0.25) {
            nx = (- 0.25 * x) + (0.4330127018922193 * y) + 0;
            ny = (0.4330127018922194 * x) + (0.25 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (- 0.25 * x) + (0.4330127018922193 * y) - 0.75;
            ny = (0.4330127018922194 * x) + (0.25 * y) + 0.4330127018922194;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (0.5 * x) + (0 * y) - 0.5;
            ny = (0 * x) + (- 0.5 * y) + 0;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (0.25 * x) + (- 0.4330127018922193 * y) - 0.5;
            ny = (0.4330127018922194 * x) + (0.25 * y) + 0;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 54 : if(rand < 0.25) {
            nx = (0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (- 0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (- 0.25 * x) + (- 0.4330127018922193 * y) + 0.5;
            ny = (- 0.4330127018922194 * x) + (0.25 * y) + 0;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (0.5 * x) + (0 * y) + 0.5;
            ny = (0 * x) + (- 0.5 * y) + 0;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (- 0.25 * x) + (0.4330127018922193 * y) + 0.5;
            ny = (0.4330127018922194 * x) + (0.25 * y) + 0;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 55 : if(rand < 0.25) {
            nx = (- 0.25 * x) + (- 0.4330127018922193 * y) + 0;
            ny = (- 0.4330127018922194 * x) + (0.25 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (- 0.25 * x) + (0.4330127018922193 * y) - 0.5;
            ny = (0.4330127018922194 * x) + (0.25 * y) + 0;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (- 0.25 * x) + (0.4330127018922193 * y) + 0.25;
            ny = (0.4330127018922194 * x) + (0.25 * y) + 0.4330127018922194;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (- 0.25 * x) + (- 0.4330127018922193 * y) + 0.25;
            ny = (- 0.4330127018922194 * x) + (0.25 * y) + 0.4330127018922194;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 56 : if(rand < 0.25) {
            nx = (- 0.25 * x) + (0.4330127018922193 * y) + 0;
            ny = (- 0.4330127018922194 * x) + (- 0.25 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0.25 * x) + (0.4330127018922193 * y) + 0.75;
            ny = (- 0.4330127018922194 * x) + (0.25 * y) + 0.4330127018922194;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (0.25 * x) + (0.4330127018922193 * y) - 0.25;
            ny = (- 0.4330127018922194 * x) + (0.25 * y) - 0.4330127018922194;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (- 0.25 * x) + (- 0.4330127018922193 * y) + 0.5;
            ny = (0.4330127018922194 * x) + (- 0.25 * y) + 0;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 57 : if(rand < 0.25) {
            nx = (0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (- 0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (- 0.25 * x) + (0.4330127018922193 * y) - 0.5;
            ny = (0.4330127018922194 * x) + (0.25 * y) + 0;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (- 0.25 * x) + (- 0.4330127018922193 * y) - 0.25;
            ny = (- 0.4330127018922194 * x) + (0.25 * y) - 0.4330127018922194;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (- 0.25 * x) + (- 0.4330127018922193 * y) - 0.5;
            ny = (0.4330127018922194 * x) + (- 0.25 * y) + 0;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 58 : if(rand < 0.25) {
            nx = (- 0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0 * x) + (0.5 * y) + 0.5;
            ny = (- 0.5 * x) + (0 * y) - 0.5;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (- 0.5 * x) + (0 * y) - 0.5;
            ny = (0 * x) + (0.5 * y) - 0.5;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (- 0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (- 0.5 * y) - 1;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 59 : if(rand < 0.25) {
            nx = (0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0.5 * x) + (0 * y) - 1.5;
            ny = (0 * x) + (0.5 * y) - 0.5;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (0.5 * y) - 2;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (0.5 * x) + (0 * y) + 0.5;
            ny = (0 * x) + (0.5 * y) - 0.5;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 60 : if(rand < 0.25) {
            nx = (0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (- 0.5 * x) + (0 * y) - 1;
            ny = (0 * x) + (0.5 * y) + 0;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (0 * x) + (0.5 * y) - 0.5;
            ny = (- 0.5 * x) + (0 * y) - 0.5;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (- 0.5 * x) + (0 * y) - 0.5;
            ny = (0 * x) + (- 0.5 * y) - 0.5;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 61 : if(rand < 0.25) {
            nx = (0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (- 0.25 * x) + (- 0.4330127018922193 * y) - 0.5;
            ny = (0.4330127018922194 * x) + (- 0.25 * y) + 0;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (- 0.5 * x) + (0 * y) - 0.25;
            ny = (0 * x) + (0.5 * y) - 0.4330127018922194;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (- 0.25 * x) + (0.4330127018922193 * y) - 0.25;
            ny = (- 0.4330127018922194 * x) + (- 0.25 * y) - 0.4330127018922194;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 62 : if(rand < 0.25) {
            nx = (0 * x) + (0.5 * y) + 0;
            ny = (0.5 * x) + (0 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0 * x) + (- 0.5 * y) - 1;
            ny = (- 0.5 * x) + (0 * y) - 1.5;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (0 * x) + (0.5 * y) + 0;
            ny = (- 0.5 * x) + (0 * y) - 0.5;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (0 * x) + (0.5 * y) + 0;
            ny = (- 0.5 * x) + (0 * y) - 1;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 63 : if(rand < 0.25) {
            nx = (0 * x) + (0.5 * y) + 0;
            ny = (0.5 * x) + (0 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0 * x) + (0.5 * y) + 0;
            ny = (0.5 * x) + (0 * y) - 1;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (0 * x) + (0.5 * y) + 0;
            ny = (- 0.5 * x) + (0 * y) - 0.5;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (0 * x) + (- 0.5 * y) - 1;
            ny = (0.5 * x) + (0 * y) - 0.5;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 64 : if(rand < 0.25) {
            nx = (0 * x) + (- 0.5 * y) + 0;
            ny = (- 0.5 * x) + (0 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0 * x) + (0.5 * y) + 1.5;
            ny = (- 0.5 * x) + (0 * y) + 0;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (0 * x) + (0.5 * y) + 0.5;
            ny = (- 0.5 * x) + (0 * y) + 0;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (0 * x) + (0.5 * y) + 1;
            ny = (0.5 * x) + (0 * y) - 1;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 65 : if(rand < 0.25) {
            nx = (0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (- 0.25 * x) + (0.4330127018922193 * y) - 0.5;
            ny = (- 0.4330127018922194 * x) + (- 0.25 * y) + 0;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (- 0.25 * x) + (0.4330127018922193 * y) - 0.25;
            ny = (0.4330127018922194 * x) + (0.25 * y) + 0.4330127018922194;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (- 0.25 * x) + (- 0.4330127018922193 * y) - 0.25;
            ny = (- 0.4330127018922194 * x) + (- 0.25 * y) + 0.4330127018922194;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 66 : if(rand < 0.25) {
            nx = (- 0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (- 0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0.5 * x) + (0 * y) + 0.25;
            ny = (0 * x) + (- 0.5 * y) + 0.4330127018922194;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (0.25 * x) + (- 0.4330127018922193 * y) + 0.25;
            ny = (0.4330127018922194 * x) + (0.25 * y) + 0.4330127018922194;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (0.25 * x) + (- 0.4330127018922193 * y) + 0.25;
            ny = (0.4330127018922194 * x) + (0.25 * y) - 0.4330127018922194;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 67 : if(rand < 0.25) {
            nx = (0.25 * x) + (- 0.4330127018922193 * y) + 0;
            ny = (0.4330127018922194 * x) + (0.25 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (- 0.25 * x) + (0.4330127018922193 * y) + 0.5;
            ny = (- 0.4330127018922194 * x) + (- 0.25 * y) + 0;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (- 0.5 * x) + (0 * y) + 0.5;
            ny = (0 * x) + (0.5 * y) + 0;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (- 0.25 * x) + (- 0.4330127018922193 * y) + 0.5;
            ny = (- 0.4330127018922194 * x) + (0.25 * y) + 0;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 68 : if(rand < 0.25) {
            nx = (0.25 * x) + (0.4330127018922193 * y) + 0;
            ny = (- 0.4330127018922194 * x) + (0.25 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (- 0.25 * x) + (- 0.4330127018922193 * y) + 0.25;
            ny = (0.4330127018922194 * x) + (- 0.25 * y) + 0.4330127018922194;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (- 0.25 * x) + (- 0.4330127018922193 * y) + 0.25;
            ny = (- 0.4330127018922194 * x) + (0.25 * y) + 0.4330127018922194;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (- 0.5 * x) + (0 * y) + 0.25;
            ny = (0 * x) + (- 0.5 * y) + 0.4330127018922194;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 69 : if(rand < 0.25) {
            nx = (0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (- 0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (- 0.25 * x) + (0.4330127018922193 * y) - 0.5;
            ny = (0.4330127018922194 * x) + (0.25 * y) + 0;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (- 0.25 * x) + (- 0.4330127018922193 * y) - 0.25;
            ny = (- 0.4330127018922194 * x) + (0.25 * y) - 0.4330127018922194;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (- 0.25 * x) + (- 0.4330127018922193 * y) - 0.5;
            ny = (0.4330127018922194 * x) + (- 0.25 * y) + 0;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 70 : if(rand < 0.25) {
            nx = (- 0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0 * x) + (0.5 * y) + 0.5;
            ny = (- 0.5 * x) + (0 * y) - 0.5;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (- 0.5 * x) + (0 * y) - 0.5;
            ny = (0 * x) + (0.5 * y) - 0.5;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (- 0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (- 0.5 * y) - 1;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 71 : if(rand < 0.25) {
            nx = (0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (0.5 * x) + (0 * y) - 1.5;
            ny = (0 * x) + (0.5 * y) - 0.5;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (0.5 * y) - 2;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (0.5 * x) + (0 * y) + 0.5;
            ny = (0 * x) + (0.5 * y) - 0.5;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 72 : if(rand < 0.25) {
            nx = (0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (- 0.5 * x) + (0 * y) - 1;
            ny = (0 * x) + (0.5 * y) + 0;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (0 * x) + (0.5 * y) - 0.5;
            ny = (- 0.5 * x) + (0 * y) - 0.5;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (- 0.5 * x) + (0 * y) - 0.5;
            ny = (0 * x) + (- 0.5 * y) - 0.5;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 73 : if(rand < 0.25) {
            nx = (0.5 * x) + (0 * y) + 0;
            ny = (0 * x) + (0.5 * y) + 0;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = (- 0.25 * x) + (- 0.4330127018922193 * y) - 0.5;
            ny = (0.4330127018922194 * x) + (- 0.25 * y) + 0;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = (- 0.5 * x) + (0 * y) - 0.25;
            ny = (0 * x) + (0.5 * y) - 0.4330127018922194;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = (- 0.25 * x) + (0.4330127018922193 * y) - 0.25;
            ny = (- 0.4330127018922194 * x) + (- 0.25 * y) - 0.4330127018922194;
            newColor = VAR(multi_ifs_color4);
        }
        break;
        case 0 : default : if(rand < 0.25) {
            nx = 0.5 * x;
            ny = 0.5 * y;
            newColor = VAR(multi_ifs_color1);
        } else if(rand < 0.5) {
            nx = 0.5 * x - 0.5;
            ny = 0.5 * y - 0.5;
            newColor = VAR(multi_ifs_color2);
        } else if(rand < 0.75) {
            nx = 0.5 * x - 0.5;
            ny = 0.5 * y;
            newColor = VAR(multi_ifs_color3);
        } else {
            nx = 0.5 * x;
            ny = 0.5 * y - 0.5;
            newColor = VAR(multi_ifs_color4);
        }
        break;
    }
    double oldColor = TC;
    switch(VAR(multi_ifs_coloring_mode)) {
        case 1 : TC = oldColor + (newColor - oldColor) * VAR(multi_ifs_color_speed);
        break;
        case 0 : default : TC = newColor;
        break;
    }
    FPx += nx * VVAR;
    FPy += ny * VVAR;
    if(!FALSE) {
        FPz += FTz * VVAR;
    }
    return TRUE;
}

/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/truchet_hex_crop/truchet_hex_crop.cpp
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

/*
    Apophysis Plugin

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
*/

// Must define this structure before we include apoplugin.h
typedef struct
{
    double Truchet_hex_crop_wd;
    int Truchet_hex_crop_mode, Truchet_hex_crop_seed, Truchet_hex_crop_inv;
    double d1, d2;
} Variables;

// (SDK header apoplugin.h implied)

// Set the name of this plugin
APO_PLUGIN("Truchet_hex_crop");


// Define the Variables
APO_VARIABLES(
    VAR_REAL_RANGE(Truchet_hex_crop_wd, 0.0, 5.0, 0.2),
    VAR_INTEGER_RANGE(Truchet_hex_crop_mode, 0, 2, 0),
    VAR_INTEGER_RANGE(Truchet_hex_crop_inv, 0, 1, 0),
    VAR_INTEGER(Truchet_hex_crop_seed, 0)
);

// You must call the argument "vp".
int PluginVarPrepare(Variation* vp)
{
    VAR(d1) = 0.5 + VAR(Truchet_hex_crop_wd);
    VAR(d2) = 0.5 - VAR(Truchet_hex_crop_wd);
    // Always return TRUE.
    return TRUE;
}

// You must call the argument "vp".
int PluginVarCalc(Variation* vp)
{
    //get hex
    double x = 0.57735026918962576450914878050196 * FTx - FTy / 3.0; // sqrt(3) / 3
    double z = 2.0 * FTy / 3.0;
    double y = -x - z;

    //round
    double rx = round(x);
    double ry = round(y);
    double rz = round(z);

    double x_diff = abs(rx - x);
    double y_diff = abs(ry - y);
    double z_diff = abs(rz - z);

    if ((x_diff > y_diff) & (x_diff > z_diff)){
        rx = -ry-rz;
    } else if (y_diff > z_diff){
        ry = -rx-rz;
    } else {
        rz = -rx-ry;
    }

    double FX_h = M_SQRT3 * rx + M_SQRT3_2 * rz;
    double FY_h = 1.5 * rz;

    double FX = FTx - FX_h;
    double FY = FTy - FY_h;

    double add = 0.0;

    if (VAR(Truchet_hex_crop_seed) == 1){
        if ((int(rx) % 2 == 0) && (int(rz) % 2 == 0)) {
            add = 1.0471975511965977461542144610932;
        }
    }
    if (VAR(Truchet_hex_crop_seed) >= 2){
        double hash_f = sin(FX_h * 12.9898 + FY_h * 78.233 + double(VAR(Truchet_hex_crop_seed))) * 43758.5453;
        hash_f = hash_f - floor(hash_f);
        if (hash_f < 0.5) {
            add = 1.0471975511965977461542144610932; //pi/3
        }
    }

    double angle = atan2(FY, FX) + 0.52359877559829887307710723054658 - add; // pi/6
    double coef = 0.47746482927568600730665129011754; //1.5 / pi
    double angle2 = floor(angle * coef) / coef + 0.52359877559829887307710723054658 + add; //or subtract 0.5
    double x0 = cos(angle2);
    double y0 = sin(angle2);
    double dist = sqrt(sqr(FX - x0) + sqr(FY - y0));
    if (VAR(Truchet_hex_crop_inv)){
        if ((dist > VAR(d1)) || (dist < VAR(d2))){
            if (VAR(Truchet_hex_crop_mode) < 0.5){
                FX = 0.0;
                FY = 0.0;
            } else {
                if (VAR(Truchet_hex_crop_mode) < 1.5){
                    FX = x0;
                    FY = y0;
                } else {
                    double rangle = atan2(FY - y0, FX - x0);
                    double D;
                    if (random01() < 0.5){
                        D = VAR(d1);
                    } else {
                        D = VAR(d2);
                    }
                    FX = x0 + cos(rangle) * D;
                    FY = y0 + sin(rangle) * D;
                }
            }
        }

    } else {
        if ((dist < VAR(d1)) && (dist > VAR(d2))){
            if (VAR(Truchet_hex_crop_mode) < 0.5){
                FX = 0.0;
                FY = 0.0;
            } else {
                if (VAR(Truchet_hex_crop_mode) < 1.5){
                    FX = x0;
                    FY = y0;
                } else {
                    double rangle = atan2(FY - y0, FX - x0);
                    double D;
                    if (random01() < 0.5){
                        D = VAR(d1);
                    } else {
                        D = VAR(d2);
                    }
                    FX = x0 + cos(rangle) * D;
                    FY = y0 + sin(rangle) * D;
                }
            }
        }
    }

    FPx += (FX + FX_h)* VVAR;
    FPy += (FY + FY_h)* VVAR;

    return TRUE;
}

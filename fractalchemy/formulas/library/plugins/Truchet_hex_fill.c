/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/truchet_hex_crop/truchet_hex_fill.cpp
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
    int Truchet_hex_fill_n, Truchet_hex_fill_seed;
    int Truchet_hex_fill_3n;
    int Truchet_hex_fill_flipx, Truchet_hex_fill_flipy;
    double Truchet_hex_fill_1_3n;
    double Truchet_hex_fill_spreadx, Truchet_hex_fill_spready;
} Variables;

// (SDK header apoplugin.h implied)

// Set the name of this plugin
APO_PLUGIN("Truchet_hex_fill");


// Define the Variables
APO_VARIABLES(
    VAR_INTEGER(Truchet_hex_fill_n, 3),
    VAR_INTEGER_RANGE(Truchet_hex_fill_flipx, 0, 1, 1),
    VAR_INTEGER_RANGE(Truchet_hex_fill_flipy, 0, 1, 1),
    VAR_REAL(Truchet_hex_fill_spreadx, 1.0),
    VAR_REAL(Truchet_hex_fill_spready, 1.0),
    VAR_INTEGER(Truchet_hex_fill_seed, 0)
);

// You must call the argument "vp".
int PluginVarPrepare(Variation* vp)
{
    VAR(Truchet_hex_fill_3n) = 3.0 * VAR(Truchet_hex_fill_n);
    VAR(Truchet_hex_fill_1_3n) = 1.0 / VAR(Truchet_hex_fill_3n);
    // Always return TRUE.
    return TRUE;
}

// You must call the argument "vp".
int PluginVarCalc(Variation* vp)
{
    //round
    double rx = floor(log(random01()) * (random01() < 0.5 ? VAR(Truchet_hex_fill_spreadx) : -VAR(Truchet_hex_fill_spreadx)));
    double rz = floor(log(random01()) * (random01() < 0.5 ? VAR(Truchet_hex_fill_spready) : -VAR(Truchet_hex_fill_spready)));

    double FX_h = M_SQRT3 * rx + M_SQRT3_2 * (random01() < 0.5 ? rz : -rz);
    double FY_h = 1.5 * rz;

    bool add = true;

    if (VAR(Truchet_hex_fill_seed) == 1){
        if ((int(rx) % 2 == 0) && (int(rz) % 2 == 0)) {
            add = false;
        }
    }
    if (VAR(Truchet_hex_fill_seed) >= 2){
        double hash_f = sin(FX_h * 12.9898 + FY_h * 78.233 + double(VAR(Truchet_hex_fill_seed))) * 43758.5453;
        hash_f = hash_f - floor(hash_f);
        if (hash_f < 0.5) {
            add = false; //pi/3
        }
    }

    //exponential to make a tiled circle
    double rangle = floor(random01() * VAR(Truchet_hex_fill_3n)) * M_2PI * VAR(Truchet_hex_fill_1_3n);
    double y_aux = (VAR(Truchet_hex_fill_flipy) ? (add ? FTy : -FTy) : FTy);
    double x_aux = (VAR(Truchet_hex_fill_flipx) ? (add ? FTx : -FTx) : FTx);
    double FY = y_aux * VAR(Truchet_hex_fill_1_3n);
    double FX = x_aux * VAR(Truchet_hex_fill_1_3n);
    double sn, cs;
    fsincos(FY * M_PI + rangle, &sn, &cs);
    double a = 1 + FX * M_PI; //
    FX = a * cs;
    FY = a * sn;
    //split
    double sn2, cs2;
    double A = atan2(FY, FX);
    if (A < 0) A += M_2PI;
    A = floor(1.5 * A * M_1_PI);
    double ang = (M_PI + A * M_2PI) / 3.0;
    fsincos(ang, &sn2, &cs2);
    double FX_new = FX - cs2 * 2.0;
    double FY_new = FY - sn2 * 2.0;
    //rotate by 30 to fit the hex
    if (add) {
        FX = M_SQRT3_2 * FX_new - 0.5 * FY_new;
        FY = 0.5 * FX_new + M_SQRT3_2 * FY_new;
    } else {
        FX = M_SQRT3_2 * FX_new + 0.5 * FY_new;
        FY = -0.5 * FX_new + M_SQRT3_2 * FY_new;
    }

    FPx += VVAR * (FX * 0.5 + FX_h);
    FPy += VVAR * (FY * 0.5 + FY_h);


    return TRUE;
}

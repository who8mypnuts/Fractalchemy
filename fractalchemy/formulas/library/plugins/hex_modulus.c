/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/hex_modulus/hex_modulus.cpp
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
    double hex_modulus_size;
    double hsize, weight;
} Variables;

// (SDK header apoplugin.h implied)

// Set the name of this plugin
APO_PLUGIN("hex_modulus");


// Define the Variables
APO_VARIABLES(
    VAR_REAL(hex_modulus_size, 1.0),
);

// You must call the argument "vp".
int PluginVarPrepare(Variation* vp)
{
    VAR(hsize) = M_SQRT3_2 / VAR(hex_modulus_size);
    VAR(weight) = VVAR / M_SQRT3_2;
    // Always return TRUE.
    return TRUE;
}

// You must call the argument "vp".
int PluginVarCalc(Variation* vp)
{
    //get hex
    double X = FTx * VAR(hsize);
    double Y = FTy * VAR(hsize);
    double x = (0.57735026918962576450914878050196 * X - Y / 3.0); // sqrt(3) / 3
    double z = (2.0 * Y / 3.0);
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

    double FX = X - FX_h;
    double FY = Y - FY_h;

    FPx += FX * VAR(weight);
    FPy += FY * VAR(weight);

    return TRUE;
}

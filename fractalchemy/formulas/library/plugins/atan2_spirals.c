/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        a2spirals.c
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
    double at2sp_sin_add, at2sp_x_mult, at2sp_r_mult;
} Variables;

// (SDK header apoplugin.h implied)

// Set the name of this plugin
APO_PLUGIN("atan2_spirals");


// Define the Variables
APO_VARIABLES(
    VAR_REAL(at2sp_sin_add, 0.0),
    VAR_REAL(at2sp_x_mult, 2.0),
    VAR_REAL(at2sp_r_mult, 1.5)
);

// You must call the argument "vp".
int PluginVarPrepare(Variation* vp)
{
    // Always return TRUE.
    return TRUE;
}

// You must call the argument "vp".
int PluginVarCalc(Variation* vp)
{
  // Atan2_Spirals by Whittaker Courtney 8-8-2018
  // DarkBeam conversion

  // x,y variables
    double x = FTx;
    double y = FTy;
    double xs = x * x;
    double ys = y * y;
    double xy2 = xs + ys;
    double r = sqrt(xy2);

    double fx =  VAR(at2sp_x_mult) * atan2(1.0+VAR(at2sp_r_mult) *r , xy2);
    double fy = sin(atan2(y, x) + VAR(at2sp_sin_add) );

    if(x>=0){
       FPx += VVAR * (-fx + M_PI);
    }
    else{
       FPx += VVAR * (fx - M_PI);
    }

    FPy += VVAR * fy;
	// Add 3D compatibility
	FPz += FTz;

    return TRUE;
}

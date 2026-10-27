/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/Tataz Utility Pack/Source/waves2_radial.c
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
    double w2r_scalex, w2r_scaley;
    double w2r_freqx, w2r_freqy;
    double w2r_null, w2r_distance;
} Variables;

// (SDK header apoplugin.h implied)

// Set the name of this plugin
APO_PLUGIN("waves2_radial");


// Define the Variables
APO_VARIABLES(
    VAR_REAL(w2r_scalex, 0.1),
    VAR_REAL(w2r_scaley,  0.1),
    VAR_REAL(w2r_freqx, 7.0),
    VAR_REAL(w2r_freqy,  13.0),
    VAR_REAL(w2r_null, 2.0),
    VAR_REAL(w2r_distance, 10.0)
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
	double x0 = FTx;
	double y0 = FTy;

	double dist = sqrt(sqr(x0) + sqr(y0));
	double factor = (dist < VAR(w2r_distance)) ? (dist - VAR(w2r_null)) / (VAR(w2r_distance) - VAR(w2r_null)) : 1.0;
    factor = (dist < VAR(w2r_null)) ? 0.0 : factor;

    FPx += VVAR * (x0 + factor * sin(y0 * VAR(w2r_freqx)) * VAR(w2r_scalex));
    FPy += VVAR * (y0 + factor * sin(x0 * VAR(w2r_freqy)) * VAR(w2r_scaley));

    return TRUE;
}

/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/Wierd Waves/waves23.cpp
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
    double waves23_scalex, waves23_scaley;
    double waves23_freqx, waves23_freqy;
} Variables;

// (SDK header apoplugin.h implied)

// Set the name of this plugin
APO_PLUGIN("waves23");


// Define the Variables
APO_VARIABLES(
    VAR_REAL(waves23_scalex, 0.05),
    VAR_REAL(waves23_scaley,  0.05),
    VAR_REAL(waves23_freqx, 7.0),
    VAR_REAL(waves23_freqy,  13.0),
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

	double mx = y0 * VAR(waves23_freqx) * M_1_2PI;
	double fx = mx - floor(mx);
	if (fx > 0.5) fx = 0.5 - fx;
	double my = x0 * VAR(waves23_freqy) * M_1_2PI;
	double fy = my - floor(my);
	if (fy > 0.5) fy = 0.5 - fy;
    FPx += VVAR * (x0 + fx * VAR(waves23_scalex));
    FPy += VVAR * (y0 + fy * VAR(waves23_scaley));

    return TRUE;
}

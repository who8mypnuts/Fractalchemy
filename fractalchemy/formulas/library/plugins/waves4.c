/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/Wierd Waves/waves4.cpp
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
    double waves4_scalex, waves4_scaley;
    double waves4_freqx, waves4_freqy;
    int waves4_cont;
    double waves4_yfact;
} Variables;

// (SDK header apoplugin.h implied)

// Set the name of this plugin
APO_PLUGIN("waves4");


// Define the Variables
APO_VARIABLES(
    VAR_REAL(waves4_scalex, 0.05),
    VAR_REAL(waves4_scaley,  0.05),
    VAR_REAL(waves4_freqx, 7.0),
    VAR_REAL(waves4_freqy,  13.0),
    VAR_INTEGER_RANGE(waves4_cont, 0, 1, 0),
    VAR_REAL(waves4_yfact, 0.1),
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

	double ax = floor(y0 * VAR(waves4_freqx) / M_2PI);
    ax = sin(ax * 12.9898 + ax * 78.233 + 1.0 + y0 * 0.001 * VAR(waves4_yfact)) * 43758.5453;
    ax = ax - (int) ax;
    if (VAR(waves4_cont) == 1) ax = (ax > 0.5) ? 1.0 : 0.0;

    FPx += VVAR * (x0 + sin(y0 * VAR(waves4_freqx)) * ax * ax * VAR(waves4_scalex));
    FPy += VVAR * (y0 + sin(x0 * VAR(waves4_freqy)) * VAR(waves4_scaley));

    return TRUE;
}

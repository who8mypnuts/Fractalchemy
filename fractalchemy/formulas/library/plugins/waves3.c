/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/Wierd Waves/waves3.cpp
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
    double waves3_scalex, waves3_scaley;
    double waves3_freqx, waves3_freqy;
    double waves3_sx_freq, waves3_sy_freq;
} Variables;

// (SDK header apoplugin.h implied)

// Set the name of this plugin
APO_PLUGIN("waves3");


// Define the Variables
APO_VARIABLES(
    VAR_REAL(waves3_scalex, 0.05),
    VAR_REAL(waves3_scaley,  0.05),
    VAR_REAL(waves3_freqx, 7.0),
    VAR_REAL(waves3_freqy,  13.0),
    VAR_REAL(waves3_sx_freq, 0),
    VAR_REAL(waves3_sy_freq,  2.0)
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

	double scalex = 0.5 * VAR(waves3_scalex) * (1.0 + sin(y0 * VAR(waves3_sx_freq)));
	double scaley = 0.5 * VAR(waves3_scaley) * (1.0 + sin(x0 * VAR(waves3_sy_freq)));

    FPx += VVAR * (x0 + sin(y0 * VAR(waves3_freqx)) * scalex);
    FPy += VVAR * (y0 + sin(x0 * VAR(waves3_freqy)) * scaley);

    return TRUE;
}

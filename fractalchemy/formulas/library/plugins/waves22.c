/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/Wierd Waves/waves22.cpp
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
    double waves22_scalex, waves22_scaley;
    double waves22_freqx, waves22_freqy;
    double waves22_powerx, waves22_powery;
    int waves22_modex, waves22_modey;
} Variables;

// (SDK header apoplugin.h implied)

// Set the name of this plugin
APO_PLUGIN("waves22");


// Define the Variables
APO_VARIABLES(
    VAR_REAL(waves22_scalex, 0.05),
    VAR_REAL(waves22_scaley,  0.05),
    VAR_REAL(waves22_freqx, 7.0),
    VAR_REAL(waves22_freqy,  13.0),
    VAR_INTEGER_RANGE(waves22_modex, 0, 1, 0),
    VAR_INTEGER_RANGE(waves22_modey, 0, 1, 0),
    VAR_REAL(waves22_powerx, 2.0),
    VAR_REAL(waves22_powery,  2.0)
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

	double sinx, siny;

	int px = (int) VAR(waves22_powerx);
	int py = (int) VAR(waves22_powery);
	if (VAR(waves22_modex) < 0.5){
        sinx = sin(y0 * VAR(waves22_freqx));
    } else {
        sinx = 0.5 * (1.0 + sin(y0 * VAR(waves22_freqx)));
    }
    double offsetx = pow(sinx, px) * VAR(waves22_scalex);
	if (VAR(waves22_modey) < 0.5){
        siny = sin(x0 * VAR(waves22_freqy));
    } else {
        siny = 0.5 * (1.0 + sin(x0 * VAR(waves22_freqy)));
    }
    double offsety = pow(siny, py) * VAR(waves22_scaley);
    FPx += VVAR * (x0 + offsetx);
    FPy += VVAR * (y0 + offsety);

    return TRUE;
}

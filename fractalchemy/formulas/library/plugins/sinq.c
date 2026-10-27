/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        sinq.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

/*
    sinq Apophysis Plugin
    Copyright 2010 Branden Brown, a.k.a. zephyrtronium
    Maths stoled from Qlib which is copyright 1999 Douglas B Sweetser

    This plugin is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 3 of the License, or
    (at your option) any later version.

    This plugin is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this plugin; if not, see <http://www.gnu.org/licenses/>.

*/

typedef struct
{
} Variables;

// (SDK header apoplugin.h implied)

APO_PLUGIN("sinq");

APO_VARIABLES(
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE; 
}

int PluginVarCalc(Variation* vp)
{
    double abs_v = hypot(FTy, FTz), C, s, c, sh, ch;
    fsincos(FTx, &s, &c);
    sinhcosh(abs_v, &sh, &ch);
    C = VVAR * c * sh / abs_v;

    FPx += VVAR * s * ch;
    FPy += C * FTy;
    FPz += C * FTz;

    return TRUE;
}

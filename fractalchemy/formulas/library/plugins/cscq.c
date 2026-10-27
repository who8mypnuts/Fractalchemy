/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        cscq.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

/*
    cscq Apophysis Plugin
    Copyright 2010 Branden Brown, a.k.a. zephyrtronium

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
#define dabs_v hypot(FTy, FTz)

APO_PLUGIN("cscq");

APO_VARIABLES(
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE; 
}

int PluginVarCalc(Variation* vp)
{
    double abs_v = dabs_v;
    double ni = VVAR / (sqr(FTx) + sqr(FTy) + sqr(FTz));
    double s, c, sh, ch, C, nn;
    fsincos(FTx, &s, &c);
    sinhcosh(abs_v, &sh, &ch);
    C = ni * c * sh / abs_v;

    FPx += s * ch * ni;
    FPy -= C * FTy;
    FPz -= C * FTz;

    return TRUE;
}

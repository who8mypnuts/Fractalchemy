/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        loq.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

/*
    loq Apophysis Plugin
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
    double loq_base;

    double denom;
} Variables;

// (SDK header apoplugin.h implied)
#define dabs_v hypot(FTy, FTz)

APO_PLUGIN("loq");

APO_VARIABLES(
    VAR_REAL_RANGE(loq_base, EPS, DBL_MAX, M_E),
);

int PluginVarPrepare(Variation* vp)
{
    VAR(denom) = 0.5 * VVAR / log(VAR(loq_base));

    return TRUE; 
}

int PluginVarCalc(Variation* vp)
{
    double abs_v = dabs_v, C = VVAR * atan2(abs_v, FTx) / abs_v;

    FPx += log(sqr(FTx) + sqr(abs_v)) * VAR(denom);
    FPy += C * FTy;
    FPz += C * FTz;

    return TRUE;
}

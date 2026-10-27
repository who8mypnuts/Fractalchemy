/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        xerf.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

/*
    xerf Apophysis Plugin
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

APO_PLUGIN("xerf");

APO_VARIABLES(
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE; 
}

int PluginVarCalc(Variation* vp)
{
    double r2 = sqr(sqrt(sqr(FTx) + sqr(FTy) + sqr(FTz)));

    FPx += VVAR * (fabs(FTx) >= 2.0 ? FTx / r2 : erf(FTx));
    FPy += VVAR * (fabs(FTy) >= 2.0 ? FTy / r2 : erf(FTy));
    FPz += VVAR * (fabs(FTz) >= 2.0 ? FTz / r2 : erf(FTz));

    return TRUE;
}

/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        erf.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

/*
    erf and erf3D Apophysis Plugins
    Copyright 2010 Branden Brown, a.k.a. zephyrtronium

    These plugin is free software; you can redistribute it and/or modify
    them under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 3 of the License, or
    (at your option) any later version.

    These plugins are distributed in the hope that they will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with these plugins; if not, see <http://www.gnu.org/licenses/>.

*/

typedef struct
{
} Variables;

// (SDK header apoplugin.h implied)

APO_PLUGIN("erf");
/*
APO_PLUGIN("erf3D");
*/

APO_VARIABLES(
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE; 
}

int PluginVarCalc(Variation* vp)
{
    FPx += VVAR * erf(FTx);
    FPy += VVAR * erf(FTy);
/*
    FPz += VVAR * erf(FTz);
*/

    return TRUE;
}

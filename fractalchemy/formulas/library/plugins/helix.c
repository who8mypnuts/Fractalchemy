/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/helix _ helicoid/helix.c
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

typedef struct
{
    double helix_frequency, helix_width;
} Variables;

// (SDK header apoplugin.h implied)

APO_PLUGIN("helix");
APO_VARIABLES(
    VAR_REAL(helix_frequency, 1.0),
    VAR_REAL(helix_width, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}
int PluginVarCalc(Variation* vp)
{
    double s, c;
    fsincos(FTz * M_2PI * VAR(helix_frequency), &s, &c);
    FPx += VVAR * (FTx + c * VAR(helix_width));
    FPy += VVAR * (FTy + s * VAR(helix_width));
    FPz += VVAR * FTz;
    return 1;
}

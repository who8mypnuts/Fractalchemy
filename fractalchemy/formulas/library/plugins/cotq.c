/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        cotq.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

/*
    cotq Apophysis Plugin
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

APO_PLUGIN("cotq");

APO_VARIABLES(
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE; 
}

int PluginVarCalc(Variation* vp)
{ /* this doesn't seem right, but... */
    double sysz = sqr(FTy) + sqr(FTz);
    double abs_v = dabs_v, ni = VVAR / sqr(sqr(FTx) + sysz);
    double s, c, sh, ch, C, B, stcv, nstcv, ctcv, cb;
    fsincos(FTx, &s, &c);
    sinhcosh(abs_v, &sh, &ch);
    C = c * sh / abs_v;
    B = -s * sh / abs_v;
    stcv = s * ch;
    nstcv = -stcv;
    ctcv = c * ch;

    FPx += (stcv * ctcv + C * B * sysz) * ni;
    FPy -= (nstcv * B * FTy + C * FTy * ctcv) * ni;
    FPz -= (nstcv * B * FTz + C * FTz * ctcv) * ni;

    return TRUE;
}

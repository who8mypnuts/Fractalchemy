/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        shredrad.c
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
    double shredrad_n, shredrad_width;
    double shredrad_alpha;
} Variables;

// (SDK header apoplugin.h implied)

APO_PLUGIN("shredrad");
APO_VARIABLES(
    VAR_REAL_NONZERO(shredrad_n, 4.0),
    VAR_REAL_RANGE(shredrad_width, -1.0, 1.0, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    vp->var.shredrad_alpha = 6.283185307179586476925286766559 / vp->var.shredrad_n;
    return TRUE;
}
int PluginVarCalc(Variation* vp)
{
    const double sa = vp->var.shredrad_alpha;
    const double sw = vp->var.shredrad_width;
    const double vv = vp->vvar;
    
    double* xi = vp->pFTx;
    double* yi = vp->pFTy;
    double* zi = vp->pFTz;

    double* xo = vp->pFPx;
    double* yo = vp->pFPy;
    double* zo = vp->pFPz; *zo += vv * *zi;
    
    const double ang = atan2(*yi, *xi);
    const double rad = sqrt(*xi * *xi + *yi * *yi);
    const double xang = (ang + 9.4247779607693797153879301498385 + sa / 2) / sa;
    const double zang = ((xang - (int)xang) * sw + (int)xang) * sa - 3.1415926535897932384626433832795 - sa / 2 * sw;
    
    double s, c; fsincos(zang, &s, &c);
    *xo += vv * rad * c;
    *yo += vv * rad * s;
    return 1;
}

/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/All/circlecrop.c
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
    double circlecrop_radius, circlecrop_x, circlecrop_y, circlecrop_scatter_area;
    double cA; int circlecrop_zero;
} Variables;

// (SDK header apoplugin.h implied)
#define max(a, b) ((a) > (b) ? (a) : (b))
#define min(a, b) ((a) < (b) ? (a) : (b))

APO_PLUGIN("circlecrop");
APO_VARIABLES(
    VAR_REAL(circlecrop_radius, 1.0),
    VAR_REAL(circlecrop_x, 0.0),
    VAR_REAL(circlecrop_y, 0.0),
    VAR_REAL(circlecrop_scatter_area, 0.0),
    VAR_INTEGER_RANGE(circlecrop_zero, 0, 1, 0)
);

int PluginVarPrepare(Variation* vp)
{
    vp->var.cA = max(-1.0, min(vp->var.circlecrop_scatter_area, 1.0));
    return TRUE;
}
int PluginVarCalc(Variation* vp)
{
    const double x0 = vp->var.circlecrop_x;
    const double y0 = vp->var.circlecrop_y;
    const double cr = vp->var.circlecrop_radius;
    const double ca = vp->var.cA;
    const double vv = vp->vvar;

    double* xi = vp->pFTx; *xi -= x0;
    double* yi = vp->pFTy; *yi -= y0;
    double* zi = vp->pFTz;

    double* xo = vp->pFPx;
    double* yo = vp->pFPy;
    double* zo = vp->pFPz; *zo += vv * *zi;

    const double rad = sqrt(*xi * *xi + *yi * *yi);
    const double ang = atan2(*yi, *xi);
    const double rdc = cr + (random01() * 0.5 * ca);

    const int esc = rad > cr;
    const int cr0 = vp->var.circlecrop_zero;

    double s, c; fsincos(ang, &s, &c);

    if ( cr0 &&  esc) { *xo = *yo = 0; return 1; }
    if ( cr0 && !esc) { *xo += vv * *xi + x0; *yo += vv * *yi + y0; return 1; }
    if (!cr0 &&  esc) { *xo += vv * rdc * c + x0; *yo += vv * rdc * s + y0; return 1; }
    if (!cr0 && !esc) { *xo += vv * *xi + x0; *yo += vv * *yi + y0; return 1; }

    return 0; // error
}

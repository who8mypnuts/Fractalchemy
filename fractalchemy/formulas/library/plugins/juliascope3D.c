/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/All/juliascope3D.c
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
	
	Copyright (c) 2011 Georg Kiehne
*/

typedef struct {
	int juliascope3D_power;
	double juliascope3D_dist;
	
	double rN, cN;
} Variables;

// (SDK header apoplugin.h implied)

//few macros to let me copy-paste MetaCore variation code :)
#define weight (vp->vvar)
#define param(x) (vp->var.x)

#define vari int
#define vard double
#define defi const vari
#define defd const vard

#define does(x) (x != 0)
#define mind(x, x0) (x<x0?x0:x)
#define maxd(x, x1) (x>x1?x1:x)
#define clampd(x, x0, x1) maxd(x0,mind(x,x1))
#define lerpd(x, a, b) (a + x * (b - a))
#define random_double ((((rand()^(rand()<<15))&0xfffffff)*3.72529e-09)-0.5)


APO_PLUGIN("juliascope3D");
APO_VARIABLES(
	VAR_INTEGER_NONZERO(juliascope3D_power, 2),
	VAR_REAL(juliascope3D_dist, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
	vp->var.rN = fabs((double)vp->var.juliascope3D_power);
	vp->var.cN = vp->var.juliascope3D_dist / (double)vp->var.juliascope3D_power / 2.0;

    return 1;
}

int PluginVarCalc(Variation* vp)
{
	defd x_in = *(vp->pFTx);
	defd y_in = *(vp->pFTy);
	defd z_in = *(vp->pFTz);

	defd rn = vp->var.rN;
	defd cn = vp->var.cN;
	
	defi rnd = rand() % (int)rn;
	
	vard sina, cosa;
	
	if (!does(rnd & 1)) fsincos((M_2PI * rnd + atan2(y_in, x_in)) / (double)vp->var.juliascope3D_power, &sina, &cosa);
	else fsincos((M_2PI * rnd - atan2(y_in, x_in)) / (double)vp->var.juliascope3D_power, &sina, &cosa);
	
	defd r = weight * pow(sqr(x_in) + sqr(y_in), cn);
	
	*(vp->pFPx) += r * cosa;
	*(vp->pFPy) += r * sina;
	*(vp->pFPz) += weight * z_in;

    return 1;
}

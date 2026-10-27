/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        apophysis-plugins/plugins/juni/apoplugin.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

typedef struct
{
    int juni_power;
	double juni_stretch;
	int juni_invert;

	int j3_absn;
	double j3_cn;

} Variables;

#define _USE_MATH_DEFINEs
#ifdef _APOMSVC
	// (SDK header apoplugin_msvc.h implied)
#else
	// (SDK header apoplugin.h implied)
#endif

APO_PLUGIN("juni");
APO_VARIABLES(
	VAR_INTEGER_NONZERO(juni_power, 2),
	VAR_INTEGER_RANGE(juni_invert, 0, 1, 0),
	VAR_REAL(juni_stretch, 1.0),
);

#define power   vp->var.juni_power
#define stretch vp->var.juni_stretch
#define inv     vp->var.juni_invert
#define absn    vp->var.j3_absn
#define cn      vp->var.j3_cn
#define vvar    vp->vvar

// (SDK header variable_info.h implied)
/*
    Apophysis Plugin: juni

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

int PluginVarPrepare(Variation* vp)
{
	absn = (int)fabs((double)power);
	cn = (stretch / (double)power - 1) / 2.0;

    return 1;
}

int PluginVarCalc(Variation* vp)
{
	const double x_in = *vp->pFTx;
	const double y_in = *vp->pFTy;
	const double z_in = *vp->pFTz;

	const double zz = z_in / (double)absn;

	const double r2 = x_in * x_in + y_in * y_in;
	const double r  = vvar * pow(r2 + zz * zz, cn);

	*vp->pFPz += r * zz;

	if (
		((r2 > (vvar * vvar) || r2 == 0) && !inv) || 
		((r2 < (vvar * vvar) && r2 != 0) &&  inv)
	) {
		*vp->pFPx += vvar * *vp->pFTx;
		*vp->pFPy += vvar * *vp->pFTy;

		return 1;
	}

	const double xx = vp->a * x_in + vp->b * y_in + vp->e;
	const double yy = vp->c * x_in + vp->d * y_in + vp->f;

	const double theta = (int)(random01() * (double)absn);

	const double alpha = (atan2(yy, xx) + M_2PI * theta) / (double)power;
	const double gamma = r * sqrt(r2);

	double sina, cosa; fsincos(alpha, &sina, &cosa);

	*vp->pFPx += gamma * cosa;
	*vp->pFPy += gamma * sina;

    return 1;
}

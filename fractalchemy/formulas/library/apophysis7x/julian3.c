/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        apophysis-plugins/plugins/julian3/apoplugin.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

typedef struct
{
    int julian3_power;
	double julian3_dist;

	double julian3_real;
	double julian3_imag;

	int j3_absn;
	double j3_cn;
	double j3_vvar2;

} Variables;

#define _USE_MATH_DEFINEs
#ifdef _APOMSVC
	// (SDK header apoplugin_msvc.h implied)
#else
	// (SDK header apoplugin.h implied)
#endif

APO_PLUGIN("julian3");
APO_VARIABLES(
	VAR_INTEGER_NONZERO(julian3_power, 2),
	VAR_REAL(julian3_dist, 1.0),

	VAR_REAL(julian3_real, 0.0),
	VAR_REAL(julian3_imag, 0.0),
);

#define power vp->var.julian3_power
#define dist  vp->var.julian3_dist

#define absn  vp->var.j3_absn
#define cn    vp->var.j3_cn
#define vvar  vp->vvar
#define vvar2 vp->var.j3_vvar2

#define rea   1
#define ima   0
#define reb   0
#define imb   0
#define rec   vp->var.julian3_real
#define imc   vp->var.julian3_imag
#define red   1
#define imd   0

// (SDK header variable_info.h implied)
/*
    Apophysis Plugin: julian3

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
	cn = (dist / (double)power - 1) / 2.0;

    return 1;
}

inline void mobius_transform(Variation* vp, const double x, const double y, double* pX, double* pY)
{
	const double u_real = rea * x - ima * y + reb;
	const double u_imag = rea * y + ima * x + imb;

	const double v_real = rec * x - imc * y + red;
	const double v_imag = rec * y + imc * x + imd;

	const double denominator = 1 / (v_real * v_real + v_imag * v_imag);

	*pX = (u_real * v_real + u_imag * v_imag) * denominator;
	*pY = (u_imag * v_real - u_real * v_imag) * denominator;
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

	double mobx, moby; mobius_transform(vp, x_in, y_in, &mobx, &moby);

	const double xx = vp->a * mobx + vp->b * moby + vp->e;
	const double yy = vp->c * mobx + vp->d * moby + vp->f;

	const double theta = (int)(random01() * (double)absn);

	const double alpha = (atan2(yy, xx) + M_2PI * theta) / (double)power;
	const double gamma = r * sqrt(r2);

	double sina, cosa; fsincos(alpha, &sina, &cosa);

	*vp->pFPx += gamma * cosa;
	*vp->pFPy += gamma * sina;

    return 1;
}

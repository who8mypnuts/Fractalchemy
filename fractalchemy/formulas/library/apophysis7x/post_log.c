/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        apophysis-plugins/plugins/post_log/apoplugin.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

typedef struct
{
	double post_log_base;
	double denom;
} Variables;

#ifdef _APOMSVC
	// (SDK header apoplugin_msvc.h implied)
#else
	// (SDK header apoplugin.h implied)
#endif

#define LOG_BASE_DEF 2.71828182845905

APO_PLUGIN("post_log");
APO_VARIABLES(
	VAR_REAL(post_log_base, LOG_BASE_DEF)
);
// (SDK header variable_info.h implied)
/*
    Apophysis Plugin: post_log

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
	vp->var.denom = 0.5 / log(vp->var.post_log_base);
	
    return 1;
}
int PluginVarCalc(Variation* vp)
{
	const double x_in = FPx;
	const double y_in = FPy;
	const double z_in = FPz;

	FPx = vp->vvar * log(x_in * x_in + y_in * y_in) * vp->var.denom;
	FPy = vp->vvar * atan2(y_in, x_in);
	FPz = vp->vvar * z_in;
	
    return 1;
}


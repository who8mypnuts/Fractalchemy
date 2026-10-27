/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        apophysis-plugins/plugins/post_curl3D/apoplugin.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

typedef struct
{
    double post_curl3D_cx;
	double post_curl3D_cy;
	double post_curl3D_cz;

	double _cx, _cy, _cz,
		   cx2, cy2, cz2,
		   c2x, c2y, c2z,
		   c_2;

} Variables;

#ifdef _APOMSVC
	// (SDK header apoplugin_msvc.h implied)
#else
	// (SDK header apoplugin.h implied)
#endif

APO_PLUGIN("post_curl3D");
APO_VARIABLES(
	VAR_REAL(post_curl3D_cx, 0.0),
	VAR_REAL(post_curl3D_cy, 0.0),
	VAR_REAL(post_curl3D_cz, 0.0)
);

// (SDK header variable_info.h implied)
/*
    Apophysis Plugin: post_curl3D

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

#define xmax(a,b) ((a<b)?b:a)
#define xmin(a,b) ((a>b)?b:a)

int PluginVarPrepare(Variation* vp)
{
	vp->var._cx = VVAR * VAR(post_curl3D_cx);
	vp->var._cy = VVAR * VAR(post_curl3D_cy);
	vp->var._cz = VVAR * VAR(post_curl3D_cz);
	
	vp->var.c2x = 2 * VAR(_cx);
	vp->var.c2y = 2 * VAR(_cy);
	vp->var.c2z = 2 * VAR(_cz);
	
	vp->var.cx2 = VAR(_cx) * VAR(_cx);
	vp->var.cy2 = VAR(_cy) * VAR(_cy);
	vp->var.cz2 = VAR(_cz) * VAR(_cz);
	
	vp->var.c_2 = VAR(cx2) + VAR(cy2) + VAR(cz2);
	
    return 1;
}

int PluginVarCalc(Variation* vp)
{
	const double x = xmax(-1e100, xmin(FPx, 1e100));
	const double y = xmax(-1e100, xmin(FPy, 1e100));
	const double z = xmax(-1e100, xmin(FPz, 1e100));
	
	const double r2 = x * x + y * y + z * z;
	const double r = 1.0 / (r2 * VAR(c_2) + VAR(c2x)*x - VAR(c2y)*y + VAR(c2z)*z + 1);

	FPx = r * (x + VAR(_cx)*r2);
	FPy = r * (y + VAR(_cy)*r2);
	FPz = r * (z + VAR(_cz)*r2);
	
    return 1;
}

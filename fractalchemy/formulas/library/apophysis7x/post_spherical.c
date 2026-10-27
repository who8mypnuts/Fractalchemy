/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        apophysis-plugins/plugins/post_spherical/apoplugin.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

#define APO_NOVARIABLES
#ifdef _APOMSVC
	// (SDK header apoplugin_msvc.h implied)
#else
	typedef struct {} Variables;
	// (SDK header apoplugin.h implied)
#endif

APO_PLUGIN("post_spherical");
// (SDK header variable_info.h implied)
/*
    Apophysis Plugin: post_spherical

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
    return 1;
}

int PluginVarCalc(Variation* vp)
{
	const double r = VVAR / (FPx * FPx + FPy * FPy + 10e-6);
	FPx = FPx * r;
	FPy = FPy * r;
	FPz = VVAR * FPz;
    return 1;
}

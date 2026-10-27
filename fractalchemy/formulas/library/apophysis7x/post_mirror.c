/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        apophysis-plugins/plugins/post_mirror/apoplugin.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

typedef struct
{
    int post_mirror_xaxis;
	int post_mirror_yaxis;
	int post_mirror_zaxis;

	double post_mirror_pos;
	double post_mirror_pos2;
} Variables;

#ifdef _APOMSVC
	// (SDK header apoplugin_msvc.h implied)
#else
	// (SDK header apoplugin.h implied)
#endif

APO_PLUGIN("post_mirror");
APO_VARIABLES(
	VAR_INTEGER_RANGE(post_mirror_xaxis, 0, 1, 1),
	VAR_INTEGER_RANGE(post_mirror_yaxis, 0, 1, 0),
	VAR_REAL(post_mirror_pos, 0.0)
);

#define ax	   VAR(post_mirror_xaxis)
#define ay	   VAR(post_mirror_yaxis)

#define pos	   VAR(post_mirror_pos)
#define pos2   VAR(post_mirror_pos2)

#define e 1e100
#define r ( rand() & 1 )

// (SDK header variable_info.h implied)
/*
    Apophysis Plugin: post_mirror

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
	pos2 = 2 * pos;
	return 1;
}

inline void crop   (double* p, double t) { *p = *p <= t ? *p : e; }
inline void mirror (double* p, const double t, const double tt) { *p = r ? tt - *p : *p; }

int PluginVarCalc(Variation* vp)
{
	if (ax && !ay) 
	{  
		crop(vp->pFPx, pos);
		mirror(vp->pFPx, pos, pos2); 
	}
	else if (!ax && ay) 
	{ 
		crop(vp->pFPy, pos); 
		mirror(vp->pFPy, pos, pos2); 
	}
	else if (ax && ay)
	{
		if (*vp->pFPx > pos || *vp->pFPy > pos)
		{
			*vp->pFPx = e;
			*vp->pFPy = e;
		}

		mirror(vp->pFPx, pos, pos2); 
		mirror(vp->pFPy, pos, pos2); 
	}

    return 1;
}
